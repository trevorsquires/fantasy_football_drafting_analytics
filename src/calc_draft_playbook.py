import pandas as pd
from paths import PROJECT_ROOT

# Load VOR playbook
filename = "vor_playbook.csv"
playbook_filepath = PROJECT_ROOT / "assets" / "data" / filename
vor_df = pd.read_csv(playbook_filepath)

# Positional limits (starter slots)
position_limits = {
    "QB": 1,
    "RB": 2,
    "WR": 2,
    "TE": 1,
    "FLEX": 1,  # Can be RB or WR
    "PK": 1
}

# Player pick slots in a 12-team snake draft for 8 rounds
def generate_snake_picks(num_teams=12, rounds=8):
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
from collections import defaultdict
player_picks = defaultdict(list)
for pick, player in pick_to_player.items():
    player_picks[player].append(pick)

# Determine best position to target per pick, respecting roster limits
def recommend_draft_plan(vor_df, player_picks, position_limits):
    plans = {}
    for player_id, picks in player_picks.items():
        picks = picks[:8]  # Limit to 8 rounds
        roster = {pos: 0 for pos in position_limits}
        plan = []

        for i, pick in enumerate(picks):
            picks_until_next = picks[i + 1] - pick if i + 1 < len(picks) else 12
            row = vor_df[(vor_df['pick_number'] == pick) & (vor_df['picks_until_next'] == picks_until_next)]

            if row.empty:
                plan.append((pick, "NA"))
                continue

            row = row.iloc[0]
            position_vors = {
                "QB": row.get("qb_vor", 0),
                "RB": row.get("rb_vor", 0),
                "WR": row.get("wr_vor", 0),
                "TE": row.get("te_vor", 0),
                "PK": row.get("pk_vor", 0)
            }

            # Zero out VORs of filled positions (including FLEX logic)
            if roster["QB"] >= position_limits["QB"]:
                position_vors["QB"] = -float("inf")
            if roster["RB"] >= position_limits["RB"] and roster["FLEX"] >= position_limits["FLEX"]:
                position_vors["RB"] = -float("inf")
            if roster["WR"] >= position_limits["WR"] and roster["FLEX"] >= position_limits["FLEX"]:
                position_vors["WR"] = -float("inf")
            if roster["TE"] >= position_limits["TE"]:
                position_vors["TE"] = -float("inf")
            if roster["PK"] >= position_limits["PK"]:
                position_vors["PK"] = -float("inf")

            # Choose best available position
            best_pos = max(position_vors, key=position_vors.get)
            plan.append((pick, best_pos))

            # Update roster
            if best_pos in ["RB", "WR"]:
                if roster[best_pos] < position_limits[best_pos]:
                    roster[best_pos] += 1
                elif roster["FLEX"] < position_limits["FLEX"]:
                    roster["FLEX"] += 1
            else:
                roster[best_pos] += 1

        plans[player_id] = plan

    return plans

# Example usage:
plans = recommend_draft_plan(vor_df, player_picks, position_limits)

# Convert to DataFrame: 12 columns (players), 8 rows (draft rounds)
plan_df = pd.DataFrame({player: [pos for _, pos in picks] for player, picks in plans.items()})
plan_df.index.name = "round"
print(plan_df)

# Optionally save
plan_df.to_csv(PROJECT_ROOT / "assets" / "data" / "draft_position_targets.csv")

# Print draft plans
for player, plan in plans.items():
    print(f'Strategy for player {player}')
    for pick, pos in plan:
        print(f"\tPick {pick}: {pos}")
    print('\n')
