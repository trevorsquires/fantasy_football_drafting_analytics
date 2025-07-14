import pandas as pd
from pyomo.environ import *


class DraftOptimizer:
    def __init__(self, picks, current_roster, position_constraints, positions, proj_matrix, flex_limit=1):
        """
        Initialize the optimizer with draft data.

        Parameters:
        - picks: List[int] -> The list of overall pick numbers for the drafter
        - current_roster: Dict[str, int] -> Number of already-drafted players by position
        - position_constraints: List[Dict] -> Each dict has "positions_against_limit", "limit", and "flex"
        - proj_matrix: Dict[(int, str), float] -> Mapping from (pick_number, position) to projected points
        - positions: List[str] -> Positions considered in the draft (excluding FLEX)
        - flex_limit: int -> Number of FLEX slots available
        """
        self.picks = picks
        self.current_roster = current_roster or {}
        self.position_constraints = position_constraints
        self.positions = positions
        self.proj_matrix = proj_matrix
        self.flex_limit = flex_limit
        self.model = None

    def build(self):
        model = ConcreteModel(name="Fantasy_Draft_Optimizer")

        rounds = list(range(len(self.picks)))
        model.positions = Set(initialize=self.positions)
        model.rounds = Set(initialize=rounds)
        model.constraint_indices = RangeSet(0, len(self.position_constraints) - 1)

        model.x = Var(model.rounds, model.positions, domain=Binary)
        model.flex = Var(model.constraint_indices, domain=NonNegativeIntegers)

        # Objective: maximize total projected points
        def total_projected_points(m):
            return sum(
                m.x[i, p] * self.proj_matrix.get((self.picks[i], p), 0.0)
                for i in m.rounds for p in m.positions
            )
        model.total_points = Objective(rule=total_projected_points, sense=maximize)

        # One position per pick
        def one_position_per_pick(m, i):
            return sum(m.x[i, p] for p in m.positions) == 1 # ensure only 1 selection is made I AM MAKING CHANGES
        model.pick_one_position = Constraint(model.rounds, rule=one_position_per_pick)

        # Constraint for each group (e.g. QB, WR, WR+RB+TE etc.)
        def constraint_by_group(m, j):
            constraint = self.position_constraints[j]
            pos_list = constraint["positions_against_limit"]
            limit = constraint["limit"]
            drafted = sum(m.x[i, p] for i in m.rounds for p in pos_list)
            current = sum(self.current_roster.get(p, 0) for p in pos_list)
            return drafted + current <= limit + m.flex[j]
        model.constraint_groups = Constraint(model.constraint_indices, rule=constraint_by_group)

        # Force flex[j] = 0 for constraints where flex=False
        def flex_zero_rule(m, j):
            if not self.position_constraints[j].get("flex", False):
                return m.flex[j] == 0
            return Constraint.Skip
        model.disable_flex = Constraint(model.constraint_indices, rule=flex_zero_rule)

        # Total FLEX usage must not exceed flex_limit
        def flex_cap(m):
            return sum(m.flex[j] for j in m.constraint_indices) <= self.flex_limit
        model.flex_total_limit = Constraint(rule=flex_cap)

        self.model = model

    def solve(self, solver_name="gurobi", **solver_args):
        if self.model is None:
            raise RuntimeError("Model not built. Call `.build()` first.")
        solver = SolverFactory(solver_name)
        self.results = solver.solve(self.model, tee=True, **solver_args)

    def get_solu(self):
        if self.model is None:
            raise RuntimeError("No model available.")

        picks = self.picks
        rounds = list(range(len(picks)))
        chosen = []

        for i in rounds:
            for p in self.model.positions:
                if value(self.model.x[i, p]) > 0.5:
                    chosen.append({
                        "round_index": i,
                        "pick_number": picks[i],
                        "position": p,
                        "proj_points": self.proj_matrix.get((picks[i], p), 0.0)
                    })

        df = pd.DataFrame(chosen)
        df["cumulative_points"] = df["proj_points"].cumsum()
        return df
