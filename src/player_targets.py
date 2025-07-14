import pandas as pd
from collections import defaultdict
from paths import PROJECT_ROOT
from utils.draft_pool_calcs import compute_proj_by_position  # assumed location
from utils.mip_draft_model import DraftOptimizer  # assumed location


def get_overall_pick(player_number: int, round_number: int, players_per_round: int = 12) -> int:
    """
    Calculates the overall pick number in a snake draft.

    Args:
        player_number (int): The player's position in the draft order (1-indexed).
        round_number (int): The current round number (1-indexed).
        players_per_round (int): Total number of players in the draft.

    Returns:
        int: The overall pick number.
    """
    if round_number % 2 == 1:
        # Odd round (left to right)
        return (round_number - 1) * players_per_round + player_number
    else:
        # Even round (right to left)
        return (round_number) * players_per_round - player_number + 1


def drafted_player(player_df, position, player, round):
    pick_number = get_overall_pick(player, round)
    filtered_df = player_df[(player_df.ADP >= pick_number) & (player_df.Position == position)]
    best_player = player_df[(player_df.ADP >= pick_number) & (player_df.Position == position)].nlargest(1, 'proj_points')
    return best_player.Name.iloc[0]

# Load data
filename = "2025_cleaned_data.csv"
player_data_path = PROJECT_ROOT / "assets" / "data" / filename
player_df = pd.read_csv(player_data_path)

filename = "draft_position_targets.csv"
draft_target_path = PROJECT_ROOT / "assets" / "data" / filename
draft_target_df = pd.read_csv(draft_target_path)


player_target_rows = []

for _, row in draft_target_df.iterrows():
    player = drafted_player(player_df, row.position, row.player, row['round'])
    player_target_rows.append({
        'player': row.player,
        'round': row['round'],
        'position': row['position'],
        'player_name': player
    })

player_targets_df = pd.DataFrame(player_target_rows)

frequency_df = (
    player_targets_df
    .groupby('player_name')
    .size()
    .reset_index(name='frequency_drafted')
)
