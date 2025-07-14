import pandas as pd
from collections import defaultdict
from paths import PROJECT_ROOT
import numpy as np

def calculate_expected_vor(df: pd.DataFrame, pick_number: int, picks_until_next: int):
    """
    Calculate expected VOR (Value Over Replacement) for each position
    based on current pick number and gap until next pick.

    Computes average of 3 estimates:
    1. VOR at exact pick_number
    2. VOR at pick_number - 6 (early)
    3. VOR at pick_number + 6 (late)
    """
    offsets = [0, -6, 6]
    vor_by_position = defaultdict(list)

    for offset in offsets:
        this_pick = pick_number + offset
        next_pick = this_pick + picks_until_next
        if this_pick < 1:
            continue  # Skip invalid picks
        single_vor = compute_single_vor(df, this_pick, next_pick)
        for pos, vor in single_vor.items():
            vor_by_position[pos].append(vor)

    # Average the 3 estimates
    avg_vor = {
        pos: sum(vor_list) / len(vor_list)
        for pos, vor_list in vor_by_position.items()
    }
    return avg_vor


def compute_single_vor(df: pd.DataFrame, pick_number: int, next_pick: int):
    """
    Compute VOR of each position given a pick number and picks until next pick.
    VOR = Projected Points - Replacement Level Points (based on projected next available)
    """
    draftable_players = df[df['ADP'] >= pick_number].sort_values('ADP')
    taken_players = df[df['ADP'] < pick_number]
    replacement_pool = df[df['ADP'] >= next_pick].sort_values('ADP')

    position_vor = {}
    for pos in df['position'].unique():
        expected_proj = draftable_players[draftable_players['position'] == pos]['proj_points'].max()
        replacement_proj = replacement_pool[replacement_pool['position'] == pos]['proj_points'].max()

        # Ensure expected_proj and replacement_proj are valid numbers
        if pd.isna(expected_proj):
            expected_proj = 0
        if pd.isna(replacement_proj):
            replacement_proj = 0

        position_vor[pos] = expected_proj - replacement_proj



    return position_vor


def compute_proj_by_position(df: pd.DataFrame, picks: list, positions: list) -> dict:
    """
    Constructs a projection matrix: (pick_number, position) → projected points.

    Parameters:
    - df: pd.DataFrame with columns ['Player Name', 'Position', 'proj_points', 'ADP']
    - picks: list[int] of overall pick numbers to simulate drafting at
    - positions: list[str] of positions to consider

    Returns:
    - Dict[(int, str), float]: projection_matrix mapping (pick, position) to average projected points
    """
    projection_matrix = {}

    # Ensure ADP and proj_points are float
    df = df.copy()
    df["ADP"] = df["ADP"].astype(float)
    df["proj_points"] = df["proj_points"].astype(float)

    for pick in picks:
        for pos in positions:
            proj_samples = []

            # Consider 3 anchor points: ADP, ADP+6, ADP-6 to simulate positional availability
            for offset in [0, -6, 6]:
                adp_cutoff = pick + offset

                # Filter by players available at this point and at the right position
                available = df[(df["ADP"] >= adp_cutoff) & (df["Position"] == pos)]

                if not available.empty:
                    top_proj = available["proj_points"].max()
                    proj_samples.append(top_proj)

            # If we found any data points, take average; otherwise set to 0
            avg_proj = np.mean(proj_samples) if proj_samples else 0.0
            projection_matrix[(pick, pos)] = avg_proj

    return projection_matrix

# filename = "2025_cleaned_data.csv"
# projection_filepath = PROJECT_ROOT / "assets" / "data" / filename
# data_df = pd.read_csv(projection_filepath)
#
# picks = [10, 22, 34, 46]
# positions = ["RB", "WR", "QB", "TE"]
#
# proj_matrix = compute_proj_by_position(data_df, picks, positions)
# for k, v in proj_matrix.items():
#     print(f"{k}: {v:.2f}")