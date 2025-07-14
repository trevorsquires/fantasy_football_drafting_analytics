from paths import PROJECT_ROOT
import pandas as pd

adp_filename = "FantasyFootball_2025_PPR_ADP_Rankings.csv"
projections_filename = "espn_2025_projections.csv"

projections_filepath = PROJECT_ROOT / "assets" / "data" / projections_filename
adp_filepath = PROJECT_ROOT / "assets" / "data" / adp_filename

adp_df = pd.read_csv(adp_filepath)
projections_df = pd.read_csv(projections_filepath)

# Fix Defense Naming
adp_df.loc[adp_df['Position'].str.upper() == 'DEF', 'Name'] = adp_df['Team'].str.upper()
projections_df.loc[projections_df['position'] == 'D/ST', 'name'] = projections_df['team'].str.upper()

data_df = projections_df.merge(adp_df, how="inner", left_on="name", right_on="Name")
column_names = [
    "Name",
    "Position",
    "Team",
    "Overall",
    "proj_points"
]
data_df = data_df[column_names]
data_df.rename(columns={"Overall": "ADP"}, inplace=True)

# Output
data_df.to_csv(PROJECT_ROOT / "assets" / "data" / "2025_cleaned_data.csv", index=False)