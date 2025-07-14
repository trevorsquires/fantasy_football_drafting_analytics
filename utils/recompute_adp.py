import pandas as pd
import random
from collections import defaultdict
from paths import PROJECT_ROOT
import numpy as np

# Load VOR playbook
filename = "vor_playbook.csv"
playbook_filepath = PROJECT_ROOT / "assets" / "data" / filename
vor_df = pd.read_csv(playbook_filepath)

# Load player projection data
player_data_path = PROJECT_ROOT / "assets" / "data" / "2024_retrospective_data.csv"
player_df = pd.read_csv(player_data_path)

# Positional limits (starter slots)
position_limits = {
    "QB": 1,
    "RB": 2,
    "WR": 2,
    "TE": 1,
    "FLEX": 1,  # Can be RB or WR
    "PK": 1
}

# Helper to generate snake draft order
def generate_snake_order(num_teams=12, rounds=8):
    order = []
    for r in range(rounds):
        if r % 2 == 0:
            order += list(range(1, num_teams + 1))
        else:
            order += list(range(num_teams, 0, -1))
    return order

# Draft simulation core
def simulate_draft(player_df, num_teams=12, rounds=8):
    snake_order = generate_snake_order(num_teams, rounds)
    pick_to_team = {i + 1: team for i, team in enumerate(snake_order)}
    team_rosters = {i: defaultdict(int) for i in range(1, num_teams + 1)}
    team_picks = {i: [] for i in range(1, num_teams + 1)}
    available = player_df.copy()

    for i, pick_num in enumerate(range(1, num_teams * rounds + 1)):
        team = pick_to_team[pick_num]
        next_pick_num = pick_num + num_teams if (i + num_teams) < num_teams * rounds else pick_num + 12
        pick = make_pick(available, team_rosters[team], next_pick_num)

        if pick is not None:
            team_picks[team].append((pick_num, pick['name'], pick['position'], pick['proj_points']))
            team_rosters[team][pick['position']] += 1
            available = available[available['name'] != pick['name']]

    return team_picks

# Sub-function to make a single pick
def make_pick(pool, roster, next_pick):
    replacement_pool = pool[pool['ADP'] >= next_pick]
    pos_vor = {}

    for pos in pool['position'].unique():
        expected_proj = pool[pool['position'] == pos]['proj_points'].max()
        replacement_proj = replacement_pool[replacement_pool['position'] == pos]['proj_points'].max()
        vor = expected_proj - replacement_proj

        if pos not in roster or roster[pos] < position_limits.get(pos, 99):
            pos_vor[pos] = vor
        elif pos in ["RB", "WR", "TE"]:
            flex_limit = position_limits["RB"] + position_limits["WR"] + position_limits["TE"] + position_limits["FLEX"]
            flex_count = roster["RB"] + roster["WR"] + roster["TE"]
            if flex_count < flex_limit:
                pos_vor[pos] = vor

    best_pos = max(pos_vor, key=pos_vor.get)
    best_points = pool[pool['position'] == best_pos]['proj_points'].max()
    candidates = pool[(pool['position'] == best_pos) & (pool['proj_points'] > best_points*0.9)]
    candidate = candidates.sample(1).iloc[0] if not candidates.empty else None
    return candidate

# Run iterative simulation to convergence

def run_iterative_simulation(player_df, max_iters=50, tolerance=0.05):
    adp_history = []
    total_points_history = []
    prev_adp = None
    working_df = player_df.copy()

    for i in range(max_iters):
        pick_records = defaultdict(list)
        team_points = []

        sim_result = simulate_draft(working_df)
        for team in sim_result:
            total_points = sum([x[3] for x in sim_result[team]])
            team_points.append(total_points)
            for pick_num, name, pos, proj in sim_result[team]:
                pick_records[name].append(pick_num)

        adp_data = [
            {"name": name, "position": player_df[player_df['name'] == name]['position'].values[0],
             "sim_adp": sum(picks) / len(picks), "times_drafted": len(picks)}
            for name, picks in pick_records.items()
        ]

        adp_df = pd.DataFrame(adp_data).sort_values("sim_adp")
        adp_df = adp_df.merge(player_df[['name', 'proj_points']], on='name')
        adp_history.append(adp_df[['name', 'sim_adp', 'position']].copy())
        total_points_history.append(team_points)

        # Convergence check
        if prev_adp is not None:
            merged = prev_adp.merge(adp_df[['name', 'sim_adp']], on='name', suffixes=('_prev', '_curr'))
            merged['abs_diff'] = abs(merged['sim_adp_prev'] - merged['sim_adp_curr'])
            avg_change = merged['abs_diff'].mean()
            print(f"Iteration {i+1}: Δ ADP = {avg_change:.3f}, Avg Total Points = {np.mean(team_points):.1f}, Spread = {np.std(team_points):.1f}")
            if avg_change < tolerance:
                break
        else:
            print(f"Iteration {i+1}: Avg Total Points = {np.mean(team_points):.1f}, Spread = {np.std(team_points):.1f}")

        prev_adp = adp_df[['name', 'sim_adp']].copy()
        working_df = working_df.drop(columns=["ADP"], errors='ignore')
        working_df = working_df.merge(adp_df[['name', 'sim_adp']], on='name', how='left')
        working_df = working_df.rename(columns={"sim_adp": "ADP"})
        working_df["ADP"] = working_df["ADP"].fillna(150)

    final_adp = prev_adp.sort_values("sim_adp")
    return final_adp, adp_history, total_points_history

# Run
final_adp, adp_history, team_scores = run_iterative_simulation(player_df, max_iters=50)

# Compute final average ADP over last X iterations
history_threshold = min(10, len(adp_history))
combined_adps = adp_history[-history_threshold:]
avg_adp_df = pd.concat(combined_adps).groupby(["name", "position"]).mean().reset_index()
avg_adp_df = avg_adp_df.rename(columns={"sim_adp": "final_average_adp"}).sort_values('final_average_adp')
print(avg_adp_df.head(5))

avg_adp_df.to_csv(PROJECT_ROOT / "assets" / "data" / "simulated_adp.csv", index=False)


