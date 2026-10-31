#!/usr/bin/env python3
import pandas as pd
import numpy as np

df = pd.read_csv("zoom.csv")
curr = df[df["Season"] == "Current Season"].copy()
prev = df[df["Season"] == "Previous Season"].copy()

print("="*60)
print("1. DATASET OVERVIEW")
print("="*60)
print(f"Current Season: {len(curr)} matches (Rounds {curr['Round'].min()} - {curr['Round'].max()})")
print(f"Previous Season: {len(prev)} matches (Rounds {prev['Round'].min()} - {prev['Round'].max()})")

print("\n" + "="*60)
print("2. FIXTURE CALENDAR / SCHEDULE REPETITION")
print("="*60)
# Check if Round N in Current Season has the exact same fixtures as Round N in Previous Season
round_matches = 0
for r in range(1, 32):
    c_fx = set(zip(curr[curr["Round"] == r]["Home Team"], curr[curr["Round"] == r]["Away Team"]))
    p_fx = set(zip(prev[prev["Round"] == r]["Home Team"], prev[prev["Round"] == r]["Away Team"]))
    overlap = len(c_fx.intersection(p_fx))
    if overlap == 10:
        round_matches += 1

print(f"Number of rounds with identical fixture pairings (Round N vs Round N): {round_matches} / 31")

# If rounds are not 1-to-1, do rounds match with an offset (e.g. Current R1 = Previous R5)?
print("\nChecking if entire rounds are shifted or cycled:")
best_match = (0, 0, 0)
for c_r in range(1, 10):
    c_fx = set(zip(curr[curr["Round"] == c_r]["Home Team"], curr[curr["Round"] == c_r]["Away Team"]))
    for p_r in range(1, 39):
        p_fx = set(zip(prev[prev["Round"] == p_r]["Home Team"], prev[prev["Round"] == p_r]["Away Team"]))
        overlap = len(c_fx.intersection(p_fx))
        if overlap > 0:
            print(f"  Current R{c_r} vs Previous R{p_r}: {overlap}/10 identical matches")

print("\n" + "="*60)
print("3. HEAD-TO-HEAD MATCH REPETITIONS (SAME FIXTURE)")
print("="*60)
# When Team A plays Team B at home, what happened in Previous vs Current?
c_matches = curr.set_index(["Home Team", "Away Team"])
p_matches = prev.set_index(["Home Team", "Away Team"])

common_fixtures = c_matches.index.intersection(p_matches.index)
print(f"Total fixtures that occurred in BOTH seasons (Same Home vs Same Away): {len(common_fixtures)}")

exact_score_repeats = 0
exact_outcome_repeats = 0
repeat_details = []

for h, a in common_fixtures:
    c_row = c_matches.loc[(h, a)]
    p_row = p_matches.loc[(h, a)]
    
    # In case there are duplicates
    if isinstance(c_row, pd.DataFrame): c_row = c_row.iloc[0]
    if isinstance(p_row, pd.DataFrame): p_row = p_row.iloc[0]
    
    c_score = f"{c_row['Home Score']}-{c_row['Away Score']}"
    p_score = f"{p_row['Home Score']}-{p_row['Away Score']}"
    
    c_res = c_row["Result 1X2"]
    p_res = p_row["Result 1X2"]
    
    if c_score == p_score:
        exact_score_repeats += 1
        repeat_details.append((h, a, c_score, c_row["Round"], p_row["Round"]))
    if c_res == p_res:
        exact_outcome_repeats += 1

print(f"Identical 1X2 Outcome (Win/Draw/Loss repeated): {exact_outcome_repeats} / {len(common_fixtures)} ({exact_outcome_repeats/len(common_fixtures)*100:.1f}%)")
print(f"Exact Scoreline Repeated (e.g. 2-1 both times): {exact_score_repeats} / {len(common_fixtures)} ({exact_score_repeats/len(common_fixtures)*100:.1f}%)")
print("\nExamples of exact scoreline repetitions:")
for h, a, sc, cr, pr in repeat_details[:10]:
    print(f"  • {h.replace('Z.', '')} vs {a.replace('Z.', '')}: {sc} (Current R{cr}, Previous R{pr})")

print("\n" + "="*60)
print("4. STATISTICAL SIMILARITIES BETWEEN SEASONS")
print("="*60)
for name, s_df in [("Current Season (310 games)", curr), ("Previous Season (380 games)", prev)]:
    h_win = (s_df["Result 1X2"] == "1").mean() * 100
    draw = (s_df["Result 1X2"] == "X").mean() * 100
    a_win = (s_df["Result 1X2"] == "2").mean() * 100
    ov25 = (s_df["Total Goals"] > 2.5).mean() * 100
    btts = (s_df["BTTS (GG/NG)"] == "GG").mean() * 100
    avg_h = s_df["Home Score"].mean()
    avg_a = s_df["Away Score"].mean()
    avg_tot = s_df["Total Goals"].mean()
    
    print(f"\n[{name}]")
    print(f"  • 1X2: Home Wins: {h_win:.1f}% | Draws: {draw:.1f}% | Away Wins: {a_win:.1f}%")
    print(f"  • Goals: Avg Goals: {avg_tot:.2f} (Home: {avg_h:.2f}, Away: {avg_a:.2f})")
    print(f"  • Over 2.5 Goals: {ov25:.1f}% | Under 2.5: {100-ov25:.1f}%")
    print(f"  • Both Teams To Score (GG): {btts:.1f}% | No Goal (NG): {100-btts:.1f}%")
    
    scores = (s_df["Home Score"].astype(str) + "-" + s_df["Away Score"].astype(str)).value_counts()
    top_scores = [f"{sc} ({cnt}x, {cnt/len(s_df)*100:.1f}%)" for sc, cnt in scores.head(6).items()]
    print(f"  • Most Common Exact Scores: {', '.join(top_scores)}")

print("\n" + "="*60)
print("5. TEAM RANKING & STRENGTH CORRELATION")
print("="*60)
def team_table(s_df):
    pts = {}
    for _, r in s_df.iterrows():
        h, a = r["Home Team"], r["Away Team"]
        hs, as_ = r["Home Score"], r["Away Score"]
        if h not in pts: pts[h] = {"pts": 0, "gf": 0, "ga": 0, "w": 0, "d": 0, "l": 0}
        if a not in pts: pts[a] = {"pts": 0, "gf": 0, "ga": 0, "w": 0, "d": 0, "l": 0}
        pts[h]["gf"] += hs; pts[h]["ga"] += as_
        pts[a]["gf"] += as_; pts[a]["ga"] += hs
        if hs > as_:
            pts[h]["pts"] += 3; pts[h]["w"] += 1; pts[a]["l"] += 1
        elif hs == as_:
            pts[h]["pts"] += 1; pts[a]["pts"] += 1; pts[h]["d"] += 1; pts[a]["d"] += 1
        else:
            pts[a]["pts"] += 3; pts[a]["w"] += 1; pts[h]["l"] += 1
    t = pd.DataFrame.from_dict(pts, orient="index")
    t["ppg"] = t["pts"] / (t["w"] + t["d"] + t["l"])
    t["gd_pg"] = (t["gf"] - t["ga"]) / (t["w"] + t["d"] + t["l"])
    return t

curr_t = team_table(curr)
prev_t = team_table(prev)

merged = curr_t[["ppg", "gd_pg"]].join(prev_t[["ppg", "gd_pg"]], lsuffix="_curr", rsuffix="_prev")
corr_ppg = merged["ppg_curr"].corr(merged["ppg_prev"])
corr_gd = merged["gd_pg_curr"].corr(merged["gd_pg_prev"])

print(f"Points-Per-Game Correlation between seasons: {corr_ppg:.3f}")
print(f"Goal-Difference-Per-Game Correlation: {corr_gd:.3f}")
print("\nTop 5 Teams by Points-Per-Game:")
top_curr = merged.sort_values("ppg_curr", ascending=False).head(5)
for idx, r in top_curr.iterrows():
    print(f"  {idx.replace('Z.', ''):18} Current PPG: {r['ppg_curr']:.2f} | Previous PPG: {r['ppg_prev']:.2f}")

print("\nBottom 5 Teams by Points-Per-Game:")
bot_curr = merged.sort_values("ppg_curr", ascending=True).head(5)
for idx, r in bot_curr.iterrows():
    print(f"  {idx.replace('Z.', ''):18} Current PPG: {r['ppg_curr']:.2f} | Previous PPG: {r['ppg_prev']:.2f}")
