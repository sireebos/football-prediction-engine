#!/usr/bin/env python3
"""
live_zoom.py - Monitor Latest / Live Virtual Rounds & Predictions across all 8 Bet9ja Zoom Leagues.

Usage:
  .venv/bin/python live_zoom.py
  .venv/bin/python live_zoom.py --league premier
  .venv/bin/python live_zoom.py --league liga
"""
import argparse
import sys
from datetime import datetime, timezone
from curl_cffi import requests

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

ZOOM_COMPETITIONS = {
    1: "Premier-Zoom",
    2: "Liga-Zoom",
    3: "Bundes-Zoom",
    4: "SerieA-Zoom",
    5: "Ligue1-Zoom",
    6: "Primeira-Zoom",
    7: "Eredivisie-Zoom",
    11: "Premier-Zoom Turbo",
}


def get_team_mappings():
    url = "https://zoomapi.bet9ja.com/zoomexternalapi/Competition/Init"
    resp = requests.post(
        url,
        json={"clientId": CLIENT_ID, "isShop": 0},
        headers=HEADERS,
        impersonate="chrome110",
        timeout=15,
    )
    data = resp.json().get("data", {})
    team_map = {}
    for comp in data.get("competitions", []):
        for team in comp.get("competitors", []):
            team_map[team["id"]] = team["name"]
    return team_map


def fetch_latest_league_round(comp_id: int, team_map: dict):
    url = "https://zoomapi.bet9ja.com/zoomexternalapi/SeasonResult/Results"
    params = {
        "clientId": CLIENT_ID,
        "competitionId": str(comp_id),
        "previous": "0",
        "offset": "-1",
        "limit": "1",
    }
    resp = requests.get(url, params=params, headers=HEADERS, impersonate="chrome110", timeout=15)
    if resp.status_code != 200:
        return None
    res = resp.json()
    rounds = res.get("data", {}).get("rounds", [])
    return rounds[-1] if rounds else None


def main():
    parser = argparse.ArgumentParser(description="Live Real-Time Zoom Virtual Match Viewer")
    parser.add_argument("--league", type=str, default="all", help="League name or ID, or 'all'")
    args = parser.parse_args()

    print("Fetching team definitions from Bet9ja...")
    team_map = get_team_mappings()

    target_comps = {}
    if args.league.lower() == "all":
        target_comps = ZOOM_COMPETITIONS
    else:
        arg_val = args.league.strip().lower()
        if arg_val.isdigit() and int(arg_val) in ZOOM_COMPETITIONS:
            cid = int(arg_val)
            target_comps = {cid: ZOOM_COMPETITIONS[cid]}
        else:
            for cid, cname in ZOOM_COMPETITIONS.items():
                if arg_val in cname.lower():
                    target_comps[cid] = cname
                    break

    if not target_comps:
        print(f"Unknown league: {args.league}")
        print("Available:", list(ZOOM_COMPETITIONS.values()))
        sys.exit(1)

    print("\n" + "=" * 80)
    print("⚡ ALL 8 BET9JA ZOOM LEAGUES - LATEST ROUND OUTCOMES & MATCHES")
    print("=" * 80)

    for cid, cname in target_comps.items():
        round_info = fetch_latest_league_round(cid, team_map)
        if not round_info:
            print(f"\n▶ [{cname}] ID: {cid} - No completed round in current season yet.")
            continue

        r_id = round_info.get("id")
        r_time = round_info.get("time")
        matches = round_info.get("matches", [])

        print(f"\n⚽ [{cname}] Round {r_id} (Kickoff Time: {r_time} UTC) - {len(matches)} Matches")
        print("-" * 80)
        for m in matches:
            h_name = team_map.get(m.get("homeTeam"), f"Team_{m.get('homeTeam')}")
            a_name = team_map.get(m.get("awayTeam"), f"Team_{m.get('awayTeam')}")
            hg = m.get("homeScore")
            ag = m.get("awayScore")
            ht_hg = m.get("halfTimeHomeScore")
            ht_ag = m.get("halfTimeAwayScore")
            corners_h = m.get("homeCornerScore")
            corners_a = m.get("awayCornerScore")

            res_str = f"{hg} - {ag}" if hg is not None and ag is not None else "Pending"
            ht_str = f"HT: {ht_hg}-{ht_ag}" if ht_hg is not None else ""
            crn_str = f"Corners: {corners_h}-{corners_a}" if corners_h is not None else ""

            extra = " | ".join(filter(None, [ht_str, crn_str]))
            extra_part = f"({extra})" if extra else ""

            print(f"  {h_name:<22} {res_str:^7} {a_name:>22}   {extra_part}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()

