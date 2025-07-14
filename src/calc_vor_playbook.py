import pandas as pd
from utils.draft_pool_calcs import calculate_expected_vor
from paths import PROJECT_ROOT

filename = "2025_cleaned_data.csv"
projection_filepath = PROJECT_ROOT / "assets" / "data" / filename
data_df = pd.read_csv(projection_filepath)

results = []

for pick_number in range(1, 101):
    for picks_until_next in range(1, 25):
        vor = calculate_expected_vor(data_df, pick_number, picks_until_next)

        results.append({
            "pick_number": pick_number,
            "picks_until_next": picks_until_next,
            "rb_vor": vor.get("RB", 0),
            "wr_vor": vor.get("WR", 0),
            "qb_vor": vor.get("QB", 0),
            "te_vor": vor.get("TE", 0),
            "pk_vor": vor.get("PK", 0)
        })

vor_df = pd.DataFrame(results)
vor_df.to_csv(PROJECT_ROOT / "assets" / "data" / "vor_playbook.csv", index=False)

print(vor_df.head())
