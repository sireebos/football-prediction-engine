
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from curl_cffi import requests

SOURCE_PAGE_URL = (
    "https://www.premierleague.com/"
    "en/tables/premier-league/2026-27"
)
API_URL = (
    "https://sdp-prem-prod.premier-league-prod.pulselive.com/"
    "api/v5/competitions/8/seasons/2026/standings"
)
TEAM_FORM_API_URL = (
    "https://sdp-prem-prod.premier-league-prod.pulselive.com/"
    "api/v1/competitions/8/seasons/2026/teamform"
)

OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.premierleague.com",
    "Referer": SOURCE_PAGE_URL,
}


def is_kickoff_over(kickoff_str, tz_str=""):
    """
    Check if the kickoff / prediction datetime is in the past.
    Returns True if the date has passed or is empty/invalid.
    """
    if not kickoff_str:
        return True
    try:
        parts = kickoff_str.strip().split()
        if len(parts) >= 3:
            dt_part = f"{parts[0]} {parts[1]}"
            tz_code = parts[2]
        else:
            dt_part = kickoff_str.strip()
            tz_code = tz_str or "UTC"

        dt = datetime.strptime(dt_part, "%Y-%m-%d %H:%M:%S")
        if tz_code == "BST":
            tz = timezone(timedelta(hours=1))
        elif tz_code in ("GMT", "UTC"):
            tz = timezone.utc
        else:
            tz = timezone.utc
        dt = dt.replace(tzinfo=tz)
        return dt <= datetime.now(timezone.utc)
    except Exception:
        return False


def fetch_next_matches():
    response = requests.get(
        TEAM_FORM_API_URL,
        headers=HEADERS,
        impersonate="chrome110",
        timeout=30,
    )
    response.raise_for_status()

    next_map = {}
    for item in response.json():
        team_id = str(item.get("id", ""))
        next_match = item.get("next") or {}
        if not team_id or not next_match:
            continue

        # If match is already playing or finished, period is not PreMatch
        period = next_match.get("period", "")
        if period and period != "PreMatch":
            continue

        kickoff = next_match.get("kickoff", "")
        tz = next_match.get("kickoffTimezone", "")

        # Once the prediction date is over, delete / do not include it
        if is_kickoff_over(kickoff, tz):
            continue

        home_team = next_match.get("homeTeam") or {}
        away_team = next_match.get("awayTeam") or {}
        if str(home_team.get("id", "")) == team_id:
            opponent = away_team.get("name", "")
            venue = "Home"
        else:
            opponent = home_team.get("name", "")
            venue = "Away"

        kickoff_str = f"{kickoff} {tz}".strip()

        next_map[team_id] = {
            "Next Opponent": opponent,
            "Next Venue": venue,
            "Next Kickoff": kickoff_str,
        }

    return next_map


def scrape_table():
    response = requests.get(
        API_URL,
        headers=HEADERS,
        impersonate="chrome110",
        timeout=30,
    )
    response.raise_for_status()

    next_matches = fetch_next_matches()

    data = response.json()
    tables = data.get("tables", [])
    if not tables or not tables[0].get("entries"):
        raise RuntimeError(
            "Could not locate standings entries in the API response."
        )

    entries = tables[0]["entries"]
    rows = []
    for entry in entries:
        overall = entry.get("overall", {})
        team = entry.get("team", {})
        team_id = str(team.get("id", ""))
        next_info = next_matches.get(team_id, {})

        kickoff_val = next_info.get("Next Kickoff", "")
        opponent_val = next_info.get("Next Opponent", "")
        venue_val = next_info.get("Next Venue", "")

        # Verify that kickoff date has not passed
        if is_kickoff_over(kickoff_val):
            kickoff_val = ""
            opponent_val = ""
            venue_val = ""

        gf = overall.get("goalsFor", 0)
        ga = overall.get("goalsAgainst", 0)
        rows.append({
            "Position": overall.get("position"),
            "Team": team.get("name"),
            "Played": overall.get("played"),
            "Won": overall.get("won"),
            "Drawn": overall.get("drawn"),
            "Lost": overall.get("lost"),
            "Goals For": gf,
            "Goals Against": ga,
            "Goal Difference": gf - ga,
            "Points": overall.get("points"),
            "Next Opponent": opponent_val,
            "Next Venue": venue_val,
            "Next Kickoff": kickoff_val,
        })

    df = pd.DataFrame(rows)

    numeric_cols = [
        "Position", "Played", "Won", "Drawn",
        "Lost", "Goals For", "Goals Against",
        "Goal Difference", "Points",
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(
            df[col], errors="coerce"
        )

    df = df.dropna(subset=["Position", "Team"])
    df["Position"] = df["Position"].astype(int)

    if len(df) != 20:
        raise RuntimeError(
            f"Expected 20 clubs but found {len(df)}. "
            "Check the source table before exporting."
        )

    return df.sort_values("Position").reset_index(drop=True)


def clean_expired_predictions(json_path=None, csv_path=None, excel_path=None):
    """
    Cleans expired prediction / next match fields from already saved JSON, CSV, and Excel files.
    Deletes the next match fields once the kickoff date has passed.
    """
    json_path = Path(json_path) if json_path else (OUTPUT_DIR / "premier_league_2026_27.json")
    csv_path = Path(csv_path) if csv_path else (OUTPUT_DIR / "premier_league_2026_27.csv")
    excel_path = Path(excel_path) if excel_path else (OUTPUT_DIR / "premier_league_2026_27.xlsx")

    cleaned_count = 0
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for team in data.get("standings", []):
            kickoff = team.get("Next Kickoff")
            if kickoff and is_kickoff_over(kickoff):
                team.pop("Next Opponent", None)
                team.pop("Next Venue", None)
                team.pop("Next Kickoff", None)
                cleaned_count += 1
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    if csv_path.exists():
        df = pd.read_csv(csv_path)
        if "Next Kickoff" in df.columns:
            for idx, val in df["Next Kickoff"].items():
                if is_kickoff_over(str(val) if pd.notna(val) else ""):
                    df.at[idx, "Next Opponent"] = ""
                    df.at[idx, "Next Venue"] = ""
                    df.at[idx, "Next Kickoff"] = ""
            df.to_csv(csv_path, index=False)

    return cleaned_count


def main():
    df = scrape_table()
    timestamp = datetime.now(timezone.utc).isoformat()

    records = []
    for row in df.to_dict(orient="records"):
        # Once the prediction date is over, delete it from the team record in JSON
        kickoff = row.get("Next Kickoff", "")
        if not kickoff or is_kickoff_over(kickoff):
            row.pop("Next Opponent", None)
            row.pop("Next Venue", None)
            row.pop("Next Kickoff", None)
        records.append(row)

    payload = {
        "competition": "Premier League",
        "season": "2026/27",
        "source": SOURCE_PAGE_URL,
        "scraped_at_utc": timestamp,
        "team_count": len(records),
        "standings": records,
    }

    json_path = OUTPUT_DIR / "premier_league_2026_27.json"
    csv_path = OUTPUT_DIR / "premier_league_2026_27.csv"
    excel_path = OUTPUT_DIR / "premier_league_2026_27.xlsx"

    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)

    df.to_csv(csv_path, index=False)

    with pd.ExcelWriter(
        excel_path, engine="openpyxl"
    ) as writer:
        df.to_excel(
            writer, index=False, sheet_name="Standings"
        )
        ws = writer.sheets["Standings"]
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions

        for column in ws.columns:
            letter = column[0].column_letter
            width = max(
                len(str(cell.value or ""))
                for cell in column
            )
            ws.column_dimensions[letter].width = min(
                width + 3, 30
            )

    print(f"Scraped {len(df)} teams successfully.")
    print(f"JSON:  {json_path}")
    print(f"CSV:   {csv_path}")
    print(f"Excel: {excel_path}")
    print()
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
