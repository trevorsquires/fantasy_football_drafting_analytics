import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re

def scrape_espn_projections(max_players=600):
    def split_on_second_capital(s):
        matches = list(re.finditer(r'[A-Z]', s))
        if len(matches) < 2:
            return s, ""  # Return a fallback
        second_cap_pos = matches[1].start()
        return s[:second_cap_pos], s[second_cap_pos:]

    url = "https://fantasy.espn.com/football/players/projections?leagueFormatId=3"

    options = Options()
    # options.add_argument("--headless=new")  # Comment this out if you want to view the browser
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    driver.get(url)

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "ButtonGroup"))
    )

    # Click "Sortable Projections" tab
    buttons = driver.find_elements(By.CSS_SELECTOR, "button.Button--filter.player--filters__projections-button")
    for btn in buttons:
        try:
            span = btn.find_element(By.TAG_NAME, "span")
            if span.text.strip() == "Sortable Projections":
                btn.click()
                time.sleep(5)
                break
        except Exception:
            continue

    all_data = []

    while len(all_data) < max_players:
        rows = driver.find_elements(By.CSS_SELECTOR, 'table tbody tr')
        num_rows = len(rows)

        if num_rows < 150:
            print(f"Warning: unexpected number of rows on page: {num_rows}")
            break

        players_this_page = 0
        for i in range(50):
            if len(all_data) >= max_players:
                break

            try:
                player_cols = rows[i].find_elements(By.TAG_NAME, "td")
                raw_text = player_cols[1].text.strip()
                split_parts = raw_text.split("\n")

                if len(split_parts)<3:
                    continue

                if split_parts[1] == 'Q':
                    split_parts = [split_parts[0]] + split_parts[2:]

                if split_parts[2] == 'D/ST':
                    split_parts[0] = split_parts[0].removesuffix(" D/ST")


                if len(split_parts) < 3:
                    continue

                name = split_parts[0].strip()
                team = split_parts[1].strip()
                position = split_parts[2].strip()

                proj_cols = rows[i + 100].find_elements(By.TAG_NAME, "td")
                proj_points_text = proj_cols[0].text.strip()
                proj_points = float(proj_points_text) if proj_points_text and proj_points_text != '--' else 0.0

                all_data.append({
                    "name": name,
                    "position": position,
                    "team": team,
                    "proj_points": proj_points
                })
                players_this_page += 1

            except Exception as e:
                print(f"Error parsing row {i}: {e}")
                continue

        # Try to click "Next" only if we need more players
        if len(all_data) < max_players:
            try:
                next_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.Pagination__Button--next'))
                )

                next_button.click()
                time.sleep(5)
            except Exception:
                print("No more pages or could not click 'Next'.")
                break

    driver.quit()

    df = pd.DataFrame(all_data)
    df = df[df["proj_points"] > 0]
    return df.reset_index(drop=True)

# Example usage
if __name__ == "__main__":
    df = scrape_espn_projections(max_players=300)
    print(df.head())
    df.to_csv("espn_2025_projections.csv", index=False)
