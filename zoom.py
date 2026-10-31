"""
Bet9ja Premier-Zoom Match Results, Head-to-Head & Match Prediction Engine
Scrapes all rounds and matches from both Current Season and Previous Season for Premier-Zoom (competitionId=1).
Builds a comparative database with 690+ matches, head-to-head statistics, and a Poisson match predictor.

Usage:
  .venv/bin/python zoom.py                                # Scrape both seasons & export Excel, CSV, JSON
  .venv/bin/python zoom.py --predict "Z.Man City" "Z.Arsenal"   # Compare & predict upcoming match
  .venv/bin/python zoom.py --compare "Z.Chelsea" "Z.Liverpool"  # Head-to-head comparison
  .venv/bin/python zoom.py --teams                              # List all teams
"""

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from curl_cffi import requests

OUTPUT_DIR = Path(__file__).resolve().parent

# Bet9ja Zoom API Configuration
INIT_URL = "https://zoomapi.bet9ja.com/zoomexternalapi/Competition/Init"
RESULTS_URL = "https://zoomapi.bet9ja.com/zoomexternalapi/SeasonResult/Results"
STATS_URL = "https://zoomapi.bet9ja.com/zoomexternalapi/SeasonResult/Statistics"

# Premier-Zoom competition ID = 1
DEFAULT_COMPETITION_ID = 1
CLIENT_ID = "101"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "clientId": CLIENT_ID,
    "Referer": "https://zoomapi.bet9ja.com/zoom/results/premier-zoom?clientId=101&offset=3600000",
    "Origin": "https://zoomapi.bet9ja.com",
}


def fetch_competitions_and_teams() -> Dict[int, str]:
    """Fetch competitor teams mapping from Competition/Init endpoint."""
    try:
        resp = requests.post(
            INIT_URL,
            json={"clientId": CLIENT_ID, "isShop": 0},
            headers=HEADERS,
            impersonate="chrome110",
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        team_map = {}
        for comp in data.get("competitions", []):
            for competitor in comp.get("competitors", []):
                team_map[competitor["id"]] = competitor["name"]
        return team_map
    except Exception as e:
        print(f"Warning: Failed to fetch team mappings ({e}). Falling back to IDs.")
        return {}


def fetch_official_stats(competition_id: int, previous_flag: int, team_map: Dict[int, str]) -> List[Dict[str, Any]]:
    """Fetch official season statistics and team form (e.g. ['W', 'D', 'L'])."""
    try:
        resp = requests.get(
            STATS_URL,
            params={"clientId": CLIENT_ID, "competitionId": str(competition_id), "previous": str(previous_flag)},
            headers=HEADERS,
            impersonate="chrome110",
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        stats_list = []
        for s in data:
            c_id = s.get("competitorId")
            stats_list.append({
                "Position": s.get("position"),
                "Team": team_map.get(c_id, f"Team_{c_id}"),
                "Played": s.get("played"),
                "Wins": s.get("wins"),
                "Draws": s.get("draws"),
                "Losses": s.get("loses"),
                "Goals For": s.get("goalsFor"),
                "Goals Against": s.get("goalsAgainst"),
                "Goal Difference": (s.get("goalsFor") or 0) - (s.get("goalsAgainst") or 0),
                "Points": s.get("points"),
                "Recent Form": "".join(s.get("form", [])),
            })
        return stats_list
    except Exception as e:
        print(f"Warning: Failed to fetch official statistics for previous={previous_flag} ({e})")
        return []


def format_scorers(scorers_dict: Any) -> str:
    """Format goalscorer dictionary {'ZPlayerZ': [12, 45]} into readable text."""
    if not isinstance(scorers_dict, dict) or not scorers_dict:
        return ""
    entries = []
    for player, minutes in scorers_dict.items():
        clean_name = str(player).strip("Z")
        mins_str = ", ".join(f"{m}'" for m in minutes) if isinstance(minutes, list) else f"{minutes}'"
        entries.append(f"{clean_name} ({mins_str})")
    return "; ".join(entries)


def scrape_season_rounds(competition_id: int, previous_flag: int, season_label: str, team_map: Dict[int, str]) -> List[Dict[str, Any]]:
    """
    Paginates through all rounds of a specified season (previous_flag=0 for Current, 1 for Previous).
    Returns flattened list of match dictionaries.
    """
    offset = 0
    limit = 20
    season_matches = []
    total_rounds = None
    round_counter = 0

    print(f"\n--- Scraping {season_label} (competitionId={competition_id}, previous={previous_flag}) ---")

    while True:
        params = {
            "clientId": CLIENT_ID,
            "competitionId": str(competition_id),
            "previous": str(previous_flag),
            "offset": str(offset),
            "limit": str(limit),
        }

        resp = requests.get(
            RESULTS_URL,
            params=params,
            headers=HEADERS,
            impersonate="chrome110",
            timeout=30,
        )
        resp.raise_for_status()
        res_json = resp.json()

        if res_json.get("status") != 1:
            err = res_json.get("error", {})
            print(f"API returned error: {err}")
            break

        data = res_json.get("data", {})
        if total_rounds is None:
            total_rounds = data.get("total_rounds", 0)

        rounds = data.get("rounds", [])
        if not rounds:
            break

        round_counter += len(rounds)
        for r in rounds:
            r_id = r.get("id")
            r_time = r.get("time")

            for m in r.get("matches", []):
                h_id = m.get("homeTeam")
                a_id = m.get("awayTeam")
                h_name = team_map.get(h_id, f"Team_{h_id}")
                a_name = team_map.get(a_id, f"Team_{a_id}")

                h_score = m.get("homeScore")
                a_score = m.get("awayScore")
                ht_h_score = m.get("halfTimeHomeScore")
                ht_a_score = m.get("halfTimeAwayScore")

                tot_goals = (h_score + a_score) if (h_score is not None and a_score is not None) else None

                if h_score is not None and a_score is not None:
                    if h_score > a_score:
                        res_1x2 = "1"
                    elif h_score == a_score:
                        res_1x2 = "X"
                    else:
                        res_1x2 = "2"
                    ou15 = "Over 1.5" if tot_goals > 1.5 else "Under 1.5"
                    ou25 = "Over 2.5" if tot_goals > 2.5 else "Under 2.5"
                    ou35 = "Over 3.5" if tot_goals > 3.5 else "Under 3.5"
                    btts = "GG" if (h_score > 0 and a_score > 0) else "NG"
                else:
                    res_1x2 = None
                    ou15 = None
                    ou25 = None
                    ou35 = None
                    btts = None

                if ht_h_score is not None and ht_a_score is not None:
                    if ht_h_score > ht_a_score:
                        ht_res_1x2 = "1"
                    elif ht_h_score == ht_a_score:
                        ht_res_1x2 = "X"
                    else:
                        ht_res_1x2 = "2"
                else:
                    ht_res_1x2 = None

                h_corner = m.get("homeCornerScore")
                a_corner = m.get("awayCornerScore")
                tot_corners = (h_corner + a_corner) if (h_corner is not None and a_corner is not None) else None

                season_matches.append({
                    "Season": season_label,
                    "Round": r_id,
                    "Match Time": r_time,
                    "Match ID": m.get("matchId"),
                    "Home Team ID": h_id,
                    "Home Team": h_name,
                    "Away Team ID": a_id,
                    "Away Team": a_name,
                    "Home Score": h_score,
                    "Away Score": a_score,
                    "Total Goals": tot_goals,
                    "Result 1X2": res_1x2,
                    "Over/Under 1.5": ou15,
                    "Over/Under 2.5": ou25,
                    "Over/Under 3.5": ou35,
                    "BTTS (GG/NG)": btts,
                    "HT Home Score": ht_h_score,
                    "HT Away Score": ht_a_score,
                    "HT Result 1X2": ht_res_1x2,
                    "Home Corners": h_corner,
                    "Away Corners": a_corner,
                    "Total Corners": tot_corners,
                    "HT Home Corners": m.get("halfTimeHomeCornerScore"),
                    "HT Away Corners": m.get("halfTimeAwayCornerScore"),
                    "Goalscorers Home": format_scorers(m.get("goalscorersHome")),
                    "Goalscorers Away": format_scorers(m.get("goalscorersAway")),
                })

        print(f"  -> Fetched rounds {offset + 1} to {offset + len(rounds)} (Total: {round_counter}/{total_rounds} rounds)")
        offset += len(rounds)
        if total_rounds is not None and offset >= total_rounds:
            break

    print(f"✓ Completed {season_label}: {len(season_matches)} matches across {round_counter} rounds.")
    return season_matches


def poisson_pmf(k: int, lmbda: float) -> float:
    """Compute Poisson probability mass function P(X = k; lambda)."""
    if lmbda <= 0:
        return 1.0 if k == 0 else 0.0
    return (lmbda ** k) * math.exp(-lmbda) / math.factorial(k)


def predict_zoom_match(home_team: str, away_team: str, df_history: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """
    Uses historical match data (from both Current and Previous seasons) to calculate:
    1. Head-to-Head (H2H) record between the two teams.
    2. Attack and Defense strength ratings.
    3. Expected goals (xG) for home and away.
    4. Poisson probabilistic 1X2 win probabilities.
    5. Over/Under 1.5, 2.5, 3.5 probabilities.
    6. Both Teams to Score (GG/NG) probabilities.
    7. Most probable scorelines.
    """
    if df_history is None:
        csv_path = OUTPUT_DIR / "bet9ja_premier_zoom_all.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"Historical matches dataset not found at {csv_path}. Run 'python zoom.py' first to scrape.")
        df_history = pd.read_csv(csv_path)

    # Clean team names
    all_teams = sorted(list(set(df_history["Home Team"].dropna().tolist() + df_history["Away Team"].dropna().tolist())))
    
    def match_team_name(name_input: str) -> str:
        name_clean = name_input.strip()
        for t in all_teams:
            if t.lower() == name_clean.lower() or t.replace("Z.", "").lower() == name_clean.lower():
                return t
        for t in all_teams:
            if name_clean.lower() in t.lower():
                return t
        return name_clean

    h_team = match_team_name(home_team)
    a_team = match_team_name(away_team)

    avg_home_goals = float(df_history["Home Score"].mean())
    avg_away_goals = float(df_history["Away Score"].mean())

    home_attack = (df_history.groupby("Home Team")["Home Score"].mean() / avg_home_goals).to_dict()
    home_defense = (df_history.groupby("Home Team")["Away Score"].mean() / avg_away_goals).to_dict()
    away_attack = (df_history.groupby("Away Team")["Away Score"].mean() / avg_away_goals).to_dict()
    away_defense = (df_history.groupby("Away Team")["Home Score"].mean() / avg_home_goals).to_dict()

    ha = home_attack.get(h_team, 1.0)
    ad = away_defense.get(a_team, 1.0)
    aa = away_attack.get(a_team, 1.0)
    hd = home_defense.get(h_team, 1.0)

    xg_home = ha * ad * avg_home_goals
    xg_away = aa * hd * avg_away_goals

    max_g = 6
    p_h = 0.0
    p_d = 0.0
    p_a = 0.0
    p_under15 = 0.0
    p_under25 = 0.0
    p_under35 = 0.0
    p_btts = 0.0

    score_matrix = []
    for h in range(max_g + 1):
        ph = poisson_pmf(h, xg_home)
        for a in range(max_g + 1):
            pa = poisson_pmf(a, xg_away)
            prob = ph * pa
            score_matrix.append((f"{h}-{a}", prob))
            if h > a:
                p_h += prob
            elif h == a:
                p_d += prob
            else:
                p_a += prob
            tot = h + a
            if tot < 1.5:
                p_under15 += prob
            if tot < 2.5:
                p_under25 += prob
            if tot < 3.5:
                p_under35 += prob
            if h > 0 and a > 0:
                p_btts += prob

    score_matrix.sort(key=lambda x: x[1], reverse=True)

    # Head-to-Head subset
    h2h = df_history[
        ((df_history["Home Team"] == h_team) & (df_history["Away Team"] == a_team))
        | ((df_history["Home Team"] == a_team) & (df_history["Away Team"] == h_team))
    ]

    h_wins = len(h2h[((h2h["Home Team"] == h_team) & (h2h["Home Score"] > h2h["Away Score"])) | ((h2h["Away Team"] == h_team) & (h2h["Away Score"] > h2h["Home Score"]))])
    a_wins = len(h2h[((h2h["Home Team"] == a_team) & (h2h["Home Score"] > h2h["Away Score"])) | ((h2h["Away Team"] == a_team) & (h2h["Away Score"] > h2h["Home Score"]))])
    draws = len(h2h[h2h["Home Score"] == h2h["Away Score"]])

    # Recommended Pick
    if p_h >= p_a and p_h >= p_d:
        rec_pick = f"1 ({h_team} Win)"
        conf = p_h
    elif p_a >= p_h and p_a >= p_d:
        rec_pick = f"2 ({a_team} Win)"
        conf = p_a
    else:
        rec_pick = "X (Draw)"
        conf = p_d

    return {
        "fixture": f"{h_team} (Home) vs {a_team} (Away)",
        "home_team": h_team,
        "away_team": a_team,
        "historical_database": {
            "total_matches_in_memory": len(df_history),
            "seasons_included": "Current Season + Previous Season",
        },
        "head_to_head": {
            "h2h_matches_analyzed": len(h2h),
            f"{h_team}_wins": h_wins,
            f"{a_team}_wins": a_wins,
            "draws": draws,
            "h2h_avg_goals": round(float(h2h["Total Goals"].mean()), 2) if not h2h.empty else 0.0,
            "h2h_over_2_5_pct": f"{((h2h['Total Goals'] > 2.5).mean() * 100):.1f}%" if not h2h.empty else "N/A",
            "h2h_btts_pct": f"{((h2h['BTTS (GG/NG)'] == 'GG').mean() * 100):.1f}%" if not h2h.empty else "N/A",
        },
        "expected_goals_xG": {
            h_team: round(xg_home, 2),
            a_team: round(xg_away, 2),
        },
        "probabilities_1X2": {
            f"1 ({h_team})": f"{p_h * 100:.1f}%",
            "X (Draw)": f"{p_d * 100:.1f}%",
            f"2 ({a_team})": f"{p_a * 100:.1f}%",
        },
        "over_under_goals": {
            "Over 1.5": f"{(1 - p_under15) * 100:.1f}%",
            "Under 1.5": f"{p_under15 * 100:.1f}%",
            "Over 2.5": f"{(1 - p_under25) * 100:.1f}%",
            "Under 2.5": f"{p_under25 * 100:.1f}%",
            "Over 3.5": f"{(1 - p_under35) * 100:.1f}%",
            "Under 3.5": f"{p_under35 * 100:.1f}%",
        },
        "both_teams_to_score": {
            "GG (Yes)": f"{p_btts * 100:.1f}%",
            "NG (No)": f"{(1 - p_btts) * 100:.1f}%",
        },
        "top_most_probable_scorelines": [
            f"{s} (Prob: {p * 100:.1f}%)" for s, p in score_matrix[:5]
        ],
        "ai_recommended_bet": {
            "primary_pick": rec_pick,
            "confidence": f"{conf * 100:.1f}%",
            "total_goals_lean": "Over 2.5" if (1 - p_under25) > 0.52 else "Under 2.5",
            "btts_lean": "GG" if p_btts > 0.50 else "NG",
        },
    }


def scrape_and_save_all():
    """Scrapes both current and previous seasons, saves Excel/CSV/JSON, and prints summaries."""
    print("=" * 70)
    print("Bet9ja Premier-Zoom Full Historical Scraper")
    print("Target: Current Season + Previous Season (All Available Data)")
    print("=" * 70)

    # 1. Fetch team names mapping
    team_map = fetch_competitions_and_teams()

    # 2. Fetch official statistics with Form
    print("\nFetching official season statistics from /SeasonResult/Statistics...")
    stats_curr = fetch_official_stats(DEFAULT_COMPETITION_ID, 0, team_map)
    stats_prev = fetch_official_stats(DEFAULT_COMPETITION_ID, 1, team_map)
    df_stats_curr = pd.DataFrame(stats_curr)
    df_stats_prev = pd.DataFrame(stats_prev)

    # 3. Scrape Current Season (previous=0)
    curr_matches = scrape_season_rounds(
        competition_id=DEFAULT_COMPETITION_ID,
        previous_flag=0,
        season_label="Current Season",
        team_map=team_map,
    )

    # 4. Scrape Previous Season (previous=1)
    prev_matches = scrape_season_rounds(
        competition_id=DEFAULT_COMPETITION_ID,
        previous_flag=1,
        season_label="Previous Season",
        team_map=team_map,
    )

    # 5. Build DataFrames
    df_curr = pd.DataFrame(curr_matches)
    df_prev = pd.DataFrame(prev_matches)
    df_all = pd.concat([df_curr, df_prev], ignore_index=True)

    # 6. File Paths
    excel_path = OUTPUT_DIR / "bet9ja_premier_zoom_all_seasons.xlsx"
    csv_all_path = OUTPUT_DIR / "bet9ja_premier_zoom_all.csv"
    csv_zoom_path = OUTPUT_DIR / "zoom.csv"
    csv_curr_path = OUTPUT_DIR / "bet9ja_premier_zoom_current.csv"
    csv_prev_path = OUTPUT_DIR / "bet9ja_premier_zoom_previous.csv"
    json_path = OUTPUT_DIR / "bet9ja_premier_zoom_all_seasons.json"

    # 7. Export to CSVs
    df_all.to_csv(csv_all_path, index=False)
    df_all.to_csv(csv_zoom_path, index=False)
    df_curr.to_csv(csv_curr_path, index=False)
    df_prev.to_csv(csv_prev_path, index=False)

    # 8. Export to Multi-Sheet Excel
    print("\nExporting to Excel workbook with formatted sheets...")
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df_all.to_excel(writer, index=False, sheet_name="All Matches")
        df_curr.to_excel(writer, index=False, sheet_name="Current Season")
        df_prev.to_excel(writer, index=False, sheet_name="Previous Season")
        if not df_stats_curr.empty:
            df_stats_curr.to_excel(writer, index=False, sheet_name="Current Season Table & Form")
        if not df_stats_prev.empty:
            df_stats_prev.to_excel(writer, index=False, sheet_name="Previous Season Table & Form")

        for s_name in writer.sheets:
            ws = writer.sheets[s_name]
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for col in ws.columns:
                col_letter = col[0].column_letter
                max_len = max(len(str(c.value or "")) for c in col)
                ws.column_dimensions[col_letter].width = min(max_len + 3, 35)

    # 9. Export to Structured JSON
    payload = {
        "competition": "Premier-Zoom",
        "competitionId": DEFAULT_COMPETITION_ID,
        "scraped_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "current_season_matches": len(df_curr),
            "current_season_rounds": int(df_curr["Round"].nunique()) if not df_curr.empty else 0,
            "previous_season_matches": len(df_prev),
            "previous_season_rounds": int(df_prev["Round"].nunique()) if not df_prev.empty else 0,
            "total_matches_saved": len(df_all),
        },
        "statistics_current": stats_curr,
        "statistics_previous": stats_prev,
        "matches_current": df_curr.to_dict(orient="records"),
        "matches_previous": df_prev.to_dict(orient="records"),
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("ALL DATA ACQUIRED & EXPORTED!")
    print("=" * 70)
    print(f"Excel (Multi-Sheet): {excel_path}")
    print(f"CSV (Combined):      {csv_all_path}")
    print(f"CSV (Current):       {csv_curr_path}")
    print(f"CSV (Previous):      {csv_prev_path}")
    print(f"JSON Payload:        {json_path}")
    print("-" * 70)
    print(f"Total Matches Collected: {len(df_all)}")
    print(f"  • Current Season:      {len(df_curr)} matches ({df_curr['Round'].nunique()} rounds)")
    print(f"  • Previous Season:     {len(df_prev)} matches ({df_prev['Round'].nunique()} rounds)")
    print("=" * 70)

    if not df_stats_curr.empty:
        print("\nCurrent Season Top 5 Standings with Form:")
        print(df_stats_curr.head(5).to_string(index=False))

    return df_all


def main():
    parser = argparse.ArgumentParser(description="Bet9ja Premier-Zoom Scraper & Prediction Engine")
    parser.add_argument("--predict", nargs=2, metavar=("HOME", "AWAY"), help="Compare and predict match between HOME and AWAY")
    parser.add_argument("--compare", nargs=2, metavar=("TEAM1", "TEAM2"), help="Compare head-to-head between TEAM1 and TEAM2")
    parser.add_argument("--teams", action="store_true", help="List all teams in dataset")
    args = parser.parse_args()

    if args.teams:
        csv_path = OUTPUT_DIR / "bet9ja_premier_zoom_all.csv"
        if not csv_path.exists():
            scrape_and_save_all()
        df = pd.read_csv(csv_path)
        teams = sorted(list(set(df["Home Team"].dropna().tolist() + df["Away Team"].dropna().tolist())))
        print(f"\nAvailable Teams ({len(teams)} teams):")
        for i, t in enumerate(teams, 1):
            print(f"  {i:2d}. {t}")
        return

    if args.predict or args.compare:
        team1, team2 = args.predict if args.predict else args.compare
        csv_path = OUTPUT_DIR / "bet9ja_premier_zoom_all.csv"
        if not csv_path.exists():
            scrape_and_save_all()
        pred = predict_zoom_match(team1, team2)
        print("\n" + "=" * 70)
        print(f"AI MATCH COMPARISON & PREDICTION: {pred['fixture']}")
        print("=" * 70)
        print(json.dumps(pred, indent=2))
        return

    # Default action: scrape both seasons
    scrape_and_save_all()


if __name__ == "__main__":
    main()
