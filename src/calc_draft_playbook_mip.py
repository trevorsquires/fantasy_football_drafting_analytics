import pandas as pd
from collections import defaultdict
from paths import PROJECT_ROOT
from utils.draft_pool_calcs import compute_proj_by_position  # assumed location
from utils.mip_draft_model import DraftOptimizer  # assumed location

# Load data
filename = "2025_cleaned_data.csv"
player_data_path = PROJECT_ROOT / "assets" / "data" / filename
player_df = pd.read_csv(player_data_path)

# Positional limits (starter slots)
position_constraints = [
    {"positions_against_limit": ["QB"], "limit": 1, "flex": False},
    {"positions_against_limit": ["RB"], "limit": 2, "flex": True},
    {"positions_against_limit": ["WR"], "limit": 2, "flex": True},
    {"positions_against_limit": ["TE"], "limit": 1, "flex": True},
    {"positions_against_limit": ["DEF"], "limit": 1, "flex": False},
    {"positions_against_limit": ["PK"], "limit": 1, "flex": False},
]

flex_limit = 1
rounds = flex_limit + sum([con["limit"] for con in position_constraints])


# Player pick slots in a 12-team snake draft for 8 rounds
def generate_snake_picks(num_teams=12):
    draft_order = []
    for rnd in range(rounds):
        if rnd % 2 == 0:
            draft_order += list(range(1, num_teams + 1))
        else:
            draft_order += list(range(num_teams, 0, -1))
    return draft_order

# Build pick map: pick_number -> player_number
snake_order = generate_snake_picks()
pick_to_player = {pick + 1: player for pick, player in enumerate(snake_order)}

# Reverse map: player -> list of picks
player_picks = defaultdict(list)
for pick, player in pick_to_player.items():
    player_picks[player].append(pick)

# Target positions for each player based on optimization
all_results = {}
positions = ["QB", "RB", "WR", "TE", "DEF", "PK"]

for player_id, picks in player_picks.items():
    picks = picks[:rounds]  # only consider 8 rounds

    proj_matrix = compute_proj_by_position(player_df, picks, positions)

    optimizer = DraftOptimizer(picks=picks,
                               current_roster={p:0 for p in positions},
                               position_constraints=position_constraints,
                               positions=positions,
                               proj_matrix=proj_matrix,
                               flex_limit = flex_limit)

    optimizer.build()
    optimizer.solve()
    draft_plan_df = optimizer.get_solu()

    draft_plan_df["round"] = range(1, len(picks) + 1)
    all_results[player_id] = draft_plan_df

# Combine all results into a single DataFrame for visualization
combined_df = pd.concat({k: df.set_index("round") for k, df in all_results.items()}, names=["player", "round"])
combined_df.reset_index(inplace=True)

# Some stats
total_points_per_player = combined_df.groupby("player")["proj_points"].sum().reset_index()
total_points_per_player.columns = ["Player", "Total Projected Points"]
print(total_points_per_player.sort_values(by="Total Projected Points", ascending=False))

draft_matrix = combined_df.pivot(index="round", columns="player", values="position")
draft_matrix.columns = [f"P{p}" for p in draft_matrix.columns]
print(draft_matrix)

# Save output
combined_df.to_csv(PROJECT_ROOT / "assets" / "data" / "draft_position_targets.csv", index=False)

