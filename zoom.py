import pandas as pd
from curl_cffi import requests

# Bet9ja Zoom External API endpoints
init_url = "https://zoomapi.bet9ja.com/zoomexternalapi/Competition/Init"
results_url = "https://zoomapi.bet9ja.com/zoomexternalapi/SeasonResult/Results"

# Request parameters (competitionId 11 = Premier-Zoom Turbo)
params = {
    "clientId": "101",
    "competitionId": "11",
    "previous": "0",
    "offset": "0",
    "limit": "20",
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "clientId": "101",
    "Referer": "https://zoomapi.bet9ja.com/zoom/results/premier-zoom-turbo?clientId=101&offset=3600000",
    "Origin": "https://zoomapi.bet9ja.com",
}

try:
    # 1. Fetch team names mapping from Competition/Init
    team_map = {}
    init_resp = requests.post(
        init_url,
        json={"clientId": "101", "isShop": 0},
        headers=headers,
        impersonate="chrome110",
    )
    if init_resp.status_code == 200:
        init_data = init_resp.json().get("data", {})
        for comp in init_data.get("competitions", []):
            for team in comp.get("competitors", []):
                team_map[team["id"]] = team["name"]

    # 2. Fetch match results from SeasonResult/Results
    response = requests.get(
        results_url, params=params, headers=headers, impersonate="chrome110"
    )

    if response.status_code == 200:
        data = response.json()
        print("Data fetched successfully!")

        # Extract rounds and flatten matches into rows
        rounds = data.get("data", {}).get("rounds", [])
        matches_list = []
        for round_info in rounds:
            round_id = round_info.get("id")
            round_time = round_info.get("time")
            for match in round_info.get("matches", []):
                home_id = match.get("homeTeam")
                away_id = match.get("awayTeam")
                matches_list.append({
                    "roundId": round_id,
                    "time": round_time,
                    "matchId": match.get("matchId"),
                    "homeTeamId": home_id,
                    "homeTeam": team_map.get(home_id, home_id),
                    "awayTeamId": away_id,
                    "awayTeam": team_map.get(away_id, away_id),
                    "homeScore": match.get("homeScore"),
                    "awayScore": match.get("awayScore"),
                    "halfTimeHomeScore": match.get("halfTimeHomeScore"),
                    "halfTimeAwayScore": match.get("halfTimeAwayScore"),
                    "homeCornerScore": match.get("homeCornerScore"),
                    "awayCornerScore": match.get("awayCornerScore"),
                })

        # Convert to Pandas DataFrame
        df = pd.DataFrame(matches_list)

        # Save to CSV and Excel (XLSX)
        df.to_csv("bet9ja_zoom_results.csv", index=False)
        df.to_excel("bet9ja_zoom_results.xlsx", index=False)

        print("Successfully exported results to 'bet9ja_zoom_results.xlsx' and 'bet9ja_zoom_results.csv'!")
        print(df.head())

    else:
        print(f"Failed to fetch data. Status Code: {response.status_code}")
        print("Response text:", response.text[:200])

except Exception as e:
    print(f"An error occurred: {e}")