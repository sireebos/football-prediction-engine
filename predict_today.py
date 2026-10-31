#!/usr/bin/env python3
"""
predict_today.py - Compare today's Bet9ja Zoom fixtures with historical data and Poisson model.
"""
import pandas as pd
import numpy as np
import math

df = pd.read_csv("zoom.csv")

# Sort chronologically: Previous Season (rounds 1-38) -> Current Season (rounds 1-31)
df["season_order"] = df["Season"].apply(lambda s: 0 if "Previous" in s else 1)
df = df.sort_values(by=["season_order", "Round"]).reset_index(drop=True)

n = len(df)
half_life = 300.0
shrink = 5.0

w = [0.5 ** ((n - 1 - i) / half_life) for i in range(n)]
sw = sum(w)

mu_h = sum(wi * r["Home Score"] for wi, (_, r) in zip(w, df.iterrows())) / sw
mu_a = sum(wi * r["Away Score"] for wi, (_, r) in zip(w, df.iterrows())) / sw
avg_goals = (mu_h + mu_a) / 2.0

gf, ga, gp = {}, {}, {}
for wi, (_, r) in zip(w, df.iterrows()):
    h, a = r["Home Team"], r["Away Team"]
    hg, ag = r["Home Score"], r["Away Score"]
    gf[h] = gf.get(h, 0.0) + wi * hg
    ga[h] = ga.get(h, 0.0) + wi * ag
    gp[h] = gp.get(h, 0.0) + wi

    gf[a] = gf.get(a, 0.0) + wi * ag
    ga[a] = ga.get(a, 0.0) + wi * hg
    gp[a] = gp.get(a, 0.0) + wi

att = {t: ((gf[t] + shrink * avg_goals) / (gp[t] + shrink)) / avg_goals for t in gp}
dfn = {t: ((ga[t] + shrink * avg_goals) / (gp[t] + shrink)) / avg_goals for t in gp}

def pois(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam + k * math.log(lam) - math.lgamma(k + 1))

def predict_match(home, away, max_g=8):
    lh = mu_h * att.get(home, 1.0) * dfn.get(away, 1.0)
    la = mu_a * att.get(away, 1.0) * dfn.get(home, 1.0)
    
    grid = np.zeros((max_g + 1, max_g + 1))
    for i in range(max_g + 1):
        for j in range(max_g + 1):
            grid[i, j] = pois(i, lh) * pois(j, la)
            
    p_home = np.sum(np.tril(grid, -1))
    p_draw = np.sum(np.diag(grid))
    p_away = np.sum(np.triu(grid, 1))
    tot = p_home + p_draw + p_away
    p_home, p_draw, p_away = p_home / tot, p_draw / tot, p_away / tot
    
    p_over25 = sum(grid[i, j] for i in range(max_g + 1) for j in range(max_g + 1) if i + j > 2.5) / tot
    p_btts = sum(grid[i, j] for i in range(1, max_g + 1) for j in range(1, max_g + 1)) / tot
    
    idx = np.unravel_index(np.argmax(grid), grid.shape)
    
    return {
        "lh": lh, "la": la,
        "p_h": p_home, "p_d": p_draw, "p_a": p_away,
        "p_over25": p_over25, "p_btts": p_btts,
        "top_score": f"{idx[0]}-{idx[1]}"
    }

fixtures = [
    {"code": 1046, "home": "Z.Chelsea", "away": "Z.Fulham", "odds": (1.54, 4.25, 5.90)},
    {"code": 1549, "home": "Z.Arsenal", "away": "Z.Man United", "odds": (1.78, 4.00, 4.15)},
    {"code": 1882, "home": "Z.Liverpool", "away": "Z.Bournemouth", "odds": (1.48, 4.60, 6.20)},
    {"code": 2277, "home": "Z.Man City", "away": "Z.Everton", "odds": (1.26, 5.85, 11.00)},
    {"code": 2830, "home": "Z.Nottingham Forest", "away": "Z.Tottenham", "odds": (3.85, 3.70, 1.91)},
    {"code": 1014, "home": "Z.Hull City", "away": "Z.Crystal Palace", "odds": (4.15, 3.80, 1.82)},
    {"code": 1113, "home": "Z.Brighton", "away": "Z.Newcastle Utd", "odds": (3.00, 3.50, 2.27)},
    {"code": 1256, "home": "Z.Leeds", "away": "Z.Ipswich Town", "odds": (2.01, 3.40, 3.75)},
    {"code": 1664, "home": "Z.Aston Villa", "away": "Z.Coventry City", "odds": (1.40, 4.70, 7.75)},
    {"code": 1676, "home": "Z.Brentford", "away": "Z.Sunderland", "odds": (2.52, 3.35, 2.73)},
]

output = []
for fx in fixtures:
    h, a = fx["home"], fx["away"]
    oh, od, oa = fx["odds"]
    pred = predict_match(h, a)
    
    # H2H analysis
    h2h = df[((df["Home Team"] == h) & (df["Away Team"] == a)) | ((df["Home Team"] == a) & (df["Away Team"] == h))]
    h_wins = len(h2h[((h2h["Home Team"] == h) & (h2h["Result 1X2"] == "1")) | ((h2h["Away Team"] == h) & (h2h["Result 1X2"] == "2"))])
    draws = len(h2h[h2h["Result 1X2"] == "X"])
    a_wins = len(h2h[((h2h["Home Team"] == a) & (h2h["Result 1X2"] == "1")) | ((h2h["Away Team"] == a) & (h2h["Result 1X2"] == "2"))])
    
    recent_list = []
    for _, r in h2h.tail(3).iterrows():
        ht = r["Home Team"].replace("Z.", "")
        at = r["Away Team"].replace("Z.", "")
        recent_list.append(f"{ht} {r['Home Score']}-{r['Away Score']} {at}")
    
    ev_h = (pred["p_h"] * oh) - 1.0
    ev_d = (pred["p_d"] * od) - 1.0
    ev_a = (pred["p_a"] * oa) - 1.0
    
    # Pick value bet
    evs = [("1", ev_h, oh, pred["p_h"]), ("X", ev_d, od, pred["p_d"]), ("2", ev_a, oa, pred["p_a"])]
    evs.sort(key=lambda x: x[1], reverse=True)
    best_ev = evs[0]
    
    res = {
        "code": fx["code"],
        "match": f"{h} vs {a}",
        "h2h": f"{h.replace('Z.', '')} {h_wins}W - {draws}D - {a.replace('Z.', '')} {a_wins}W ({len(h2h)} played)",
        "recent": ", ".join(recent_list),
        "xg": f"{pred['lh']:.2f} : {pred['la']:.2f}",
        "top_score": pred["top_score"],
        "p_h": pred["p_h"] * 100,
        "p_d": pred["d" if False else "p_d"] * 100,
        "p_a": pred["p_a"] * 100,
        "odds_h": oh, "odds_d": od, "odds_a": oa,
        "ev_h": ev_h * 100, "ev_d": ev_d * 100, "ev_a": ev_a * 100,
        "over25": pred["p_over25"] * 100,
        "btts": pred["p_btts"] * 100,
        "best_pick": best_ev[0],
        "best_ev": best_ev[1] * 100,
        "best_prob": best_ev[3] * 100,
        "best_odds": best_ev[2]
    }
    output.append(res)

for r in output:
    print(f"Match [{r['code']}]: {r['match']}")
    print(f"  • H2H History: {r['h2h']} | Recents: {r['recent']}")
    print(f"  • Expected Goals: {r['xg']} | Most Likely Score: {r['top_score']}")
    print(f"  • 1X2 Probs vs Odds: Home: {r['p_h']:.1f}% (@{r['odds_h']}) | Draw: {r['p_d']:.1f}% (@{r['odds_d']}) | Away: {r['p_a']:.1f}% (@{r['odds_a']})")
    print(f"  • Goals Lean: Over 2.5: {r['over25']:.1f}% | BTTS (GG): {r['btts']:.1f}%")
    print(f"  • Expected Value (EV): 1: {r['ev_h']:+.1f}% | X: {r['ev_d']:+.1f}% | 2: {r['ev_a']:+.1f}%")
    print(f"  ⭐ Recommended Pick: '{r['best_pick']}' @ {r['best_odds']} (EV: {r['best_ev']:+.1f}%, Win Prob: {r['best_prob']:.1f}%)")
    print("-" * 75)

