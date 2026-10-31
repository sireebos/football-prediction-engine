#!/usr/bin/env python3
"""
zoom_predict.py - fetch Bet9ja "Premier Zoom" results and build a Poisson
team-strength prediction, with a walk-forward backtest so you can see whether
the model has ANY edge over just guessing league base rates.

Pure standard library (Python 3.8+).

Usage
-----
  # 1) download results (or use existing bet9ja_premier_zoom_all_seasons.json)
  python zoom_predict.py fetch --pages 10 --out results_raw.json

  # 2) inspect parsed matches & teams
  python zoom_predict.py inspect --input bet9ja_premier_zoom_all_seasons.json
  python zoom_predict.py teams   --input bet9ja_premier_zoom_all_seasons.json

  # 3) walk-forward backtest on unseen historical matches
  python zoom_predict.py backtest --input bet9ja_premier_zoom_all_seasons.json

  # 4) predict a fixture (optionally compare against bookmaker odds H D A)
  python zoom_predict.py predict --input bet9ja_premier_zoom_all_seasons.json \
         --home "Z.Man City" --away "Z.Arsenal" --odds 2.10 3.40 3.20
"""
import argparse
import json
import math
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime

BASE = "https://zoomapi.bet9ja.com/zoomexternalapi/SeasonResult/Results"

# ----------------------------------------------------------------- fetching
def fetch_page(page, client_id, competition_id, limit):
    qs = urllib.parse.urlencode({
        "clientId": client_id, "competitionId": competition_id,
        "previous": page, "offset": -1, "limit": limit,
    })
    req = urllib.request.Request(f"{BASE}?{qs}", headers={
        "clientId": str(client_id),
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
        "Origin": "https://zoomapi.bet9ja.com",
        "Referer": "https://zoomapi.bet9ja.com/zoom/results/premier-zoom",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def cmd_fetch(a):
    pages = []
    for p in range(a.pages):
        try:
            data = fetch_page(p, a.client_id, a.competition_id, a.limit)
        except Exception as e:  # noqa
            print(f"page {p}: failed ({e}); stopping", file=sys.stderr)
            break
        pages.append(data)
        print(f"page {p}: ok")
    with open(a.out, "w") as f:
        json.dump(pages, f)
    print(f"saved {len(pages)} page(s) -> {a.out}")

# ------------------------------------------------------------------ parsing
def norm(k):
    return re.sub(r"[^a-z0-9]", "", str(k).lower())


KEYS = {
    "home": ["hometeam", "home", "homename", "hometeamname", "homeshortname", "team1", "hteam"],
    "away": ["awayteam", "away", "awayname", "awayteamname", "awayshortname", "team2", "ateam"],
    "hs": ["homescore", "homegoals", "hscore", "homeresult", "score1", "hg", "homefulltime"],
    "as": ["awayscore", "awaygoals", "ascore", "awayresult", "score2", "ag", "awayfulltime"],
    "id": ["matchid", "id", "eventid"],
    "time": ["starttime", "datetime", "matchdate", "date", "kickoff", "eventdate",
             "matchtime", "starttimeutc", "time"],
    "score": ["score", "result", "fulltime", "ft", "finalscore"],
}


def pick(d, names):
    m = {norm(k): v for k, v in d.items()}
    for n in names:
        if n in m and m[n] is not None:
            return m[n]
    return None


def team_name(v):
    if isinstance(v, dict):
        v = pick(v, ["name", "shortname", "code", "teamname", "title"])
    return None if v is None else str(v).strip()


def to_int(v):
    try:
        if isinstance(v, bool):
            return None
        return int(v)
    except (TypeError, ValueError):
        return None


def parse_time(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v) / 1000.0 if v > 1e11 else float(v)
    s = str(v).strip()
    for fmt in ("%d-%m-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s.split(".")[0], fmt).timestamp()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def extract(d):
    home, away = team_name(pick(d, KEYS["home"])), team_name(pick(d, KEYS["away"]))
    if not home or not away:
        return None
    hg, ag = to_int(pick(d, KEYS["hs"])), to_int(pick(d, KEYS["as"]))
    if hg is None or ag is None:
        s = pick(d, KEYS["score"])
        m = re.search(r"(\d+)\s*[-:]\s*(\d+)", str(s)) if s is not None else None
        if not m:
            return None
        hg, ag = int(m.group(1)), int(m.group(2))
    return {"id": pick(d, KEYS["id"]), "t": parse_time(pick(d, KEYS["time"])),
            "home": home, "away": away, "hg": hg, "ag": ag}


def walk(obj, out):
    if isinstance(obj, dict):
        rec = extract(obj)
        if rec:
            out.append(rec)
            return
        for v in obj.values():
            walk(v, out)
    elif isinstance(obj, list):
        for v in obj:
            walk(v, out)


def load_matches(path, newest_first=True):
    with open(path) as f:
        data = json.load(f)
    raw = []
    walk(data, raw)
    seen, matches = set(), []
    for r in raw:
        key = r["id"] if r["id"] is not None else (r["home"], r["away"], r["t"], r["hg"], r["ag"])
        if key in seen:
            continue
        seen.add(key)
        matches.append(r)
    if matches and all(m["t"] is not None for m in matches):
        matches.sort(key=lambda m: m["t"])
    elif newest_first:
        matches.reverse()
    return matches  # oldest -> newest

# -------------------------------------------------------------------- model
def pois(k, lam):
    return math.exp(-lam + k * math.log(lam) - math.lgamma(k + 1)) if lam > 0 else float(k == 0)


class Model:
    def __init__(self, matches, half_life=300, shrink=5.0):
        n = len(matches)
        w = [0.5 ** ((n - 1 - i) / half_life) for i in range(n)]
        sw = sum(w) or 1.0
        self.mu_h = sum(wi * m["hg"] for wi, m in zip(w, matches)) / sw
        self.mu_a = sum(wi * m["ag"] for wi, m in zip(w, matches)) / sw
        avg = (self.mu_h + self.mu_a) / 2 or 1.0
        gf, ga, gp = {}, {}, {}
        for wi, m in zip(w, matches):
            for t, f, a in ((m["home"], m["hg"], m["ag"]), (m["away"], m["ag"], m["hg"])):
                gf[t] = gf.get(t, 0) + wi * f
                ga[t] = ga.get(t, 0) + wi * a
                gp[t] = gp.get(t, 0) + wi
        self.att, self.dfn = {}, {}
        for t in gp:  # shrink toward league average
            self.att[t] = ((gf[t] + shrink * avg) / (gp[t] + shrink)) / avg
            self.dfn[t] = ((ga[t] + shrink * avg) / (gp[t] + shrink)) / avg

    def lambdas(self, home, away):
        return (self.mu_h * self.att.get(home, 1.0) * self.dfn.get(away, 1.0),
                self.mu_a * self.att.get(away, 1.0) * self.dfn.get(home, 1.0))

    def grid(self, home, away, mx=10):
        lh, la = self.lambdas(home, away)
        return [[pois(i, lh) * pois(j, la) for j in range(mx + 1)] for i in range(mx + 1)]

    def probs(self, home, away):
        g = self.grid(home, away)
        h = sum(g[i][j] for i in range(len(g)) for j in range(len(g)) if i > j)
        d = sum(g[i][i] for i in range(len(g)))
        a = sum(g[i][j] for i in range(len(g)) for j in range(len(g)) if i < j)
        s = h + d + a
        return h / s, d / s, a / s


def outcome(m):
    return 0 if m["hg"] > m["ag"] else (1 if m["hg"] == m["ag"] else 2)

# ---------------------------------------------------------------- commands
def cmd_inspect(a):
    ms = load_matches(a.input, not a.oldest_first)
    print(f"parsed {len(ms)} matches")
    for m in ms[:3] + ms[-3:]:
        print(m)
    if not ms:
        print("\nNothing parsed. Open the JSON, find one finished match, and add its\n"
              "key names to the KEYS dict at the top of this script.")


def cmd_teams(a):
    ms = load_matches(a.input, not a.oldest_first)
    print(sorted({m["home"] for m in ms} | {m["away"] for m in ms}))


def cmd_backtest(a):
    ms = load_matches(a.input, not a.oldest_first)
    if len(ms) < a.warmup + 20:
        sys.exit(f"only {len(ms)} matches; need at least {a.warmup + 20}")
    ll_m = ll_b = br_m = br_b = hit_m = hit_b = n = 0
    base = None
    for i in range(a.warmup, len(ms)):
        if (i - a.warmup) % a.refit == 0:
            train = ms[:i]
            model = Model(train, a.half_life, a.shrink)
            c = [0, 0, 0]
            for m in train:
                c[outcome(m)] += 1
            base = [(x + 1) / (len(train) + 3) for x in c]
        m = ms[i]
        o = outcome(m)
        pm = model.probs(m["home"], m["away"])
        for p, store in ((pm, "m"), (base, "b")):
            ll = -math.log(max(p[o], 1e-9))
            br = sum((p[k] - (k == o)) ** 2 for k in range(3))
            hit = int(max(range(3), key=lambda k: p[k]) == o)
            if store == "m":
                ll_m += ll; br_m += br; hit_m += hit
            else:
                ll_b += ll; br_b += br; hit_b += hit
        n += 1
    print(f"walk-forward on {n} matches")
    print(f"{'':10}{'logloss':>10}{'brier':>10}{'accuracy':>10}")
    print(f"{'model':10}{ll_m/n:10.4f}{br_m/n:10.4f}{hit_m/n:10.3f}")
    print(f"{'baseline':10}{ll_b/n:10.4f}{br_b/n:10.4f}{hit_b/n:10.3f}")
    edge = ll_b / n - ll_m / n
    print(f"\nlogloss improvement over baseline: {edge:+.4f}")
    if edge < 0.003:
        print("=> No meaningful signal. Team history does not predict these results\n"
              "   better than base rates (expected if outcomes are RNG-generated).")
    else:
        print("=> Some signal, but check it holds on fresh data and beats the bookmaker's\n"
              "   margin before staking anything.")


def cmd_predict(a):
    ms = load_matches(a.input, not a.oldest_first)
    model = Model(ms, a.half_life, a.shrink)
    for t in (a.home, a.away):
        if t not in model.att:
            print(f"warning: team '{t}' not in data; using league average. Try the `teams` command.")
    ph, pd, pa = model.probs(a.home, a.away)
    g = model.grid(a.home, a.away)
    n = len(g)
    over25 = sum(g[i][j] for i in range(n) for j in range(n) if i + j > 2)
    btts = sum(g[i][j] for i in range(1, n) for j in range(1, n))
    lh, la = model.lambdas(a.home, a.away)
    print(f"{a.home} vs {a.away}   (expected goals {lh:.2f} - {la:.2f}, from {len(ms)} matches)")
    print(f"  1X2:  Home {ph:.1%}   Draw {pd:.1%}   Away {pa:.1%}")
    print(f"  Over 2.5: {over25:.1%}   Under 2.5: {1-over25:.1%}   BTTS: {btts:.1%}")
    top = sorted(((g[i][j], i, j) for i in range(n) for j in range(n)), reverse=True)[:5]
    print("  Likely scores: " + ", ".join(f"{i}-{j} ({p:.1%})" for p, i, j in top))
    if a.odds:
        print("\n  vs odds (EV per 1 unit staked; positive = model thinks it's value):")
        for name, p, o in zip(("Home", "Draw", "Away"), (ph, pd, pa), a.odds):
            print(f"    {name}: odds {o:.2f}  implied {1/o:.1%}  model {p:.1%}  EV {p*o-1:+.1%}")
        print(f"    bookmaker margin: {sum(1/o for o in a.odds)-1:.1%}")
    print("\n  Run `backtest` first. If it shows no edge, these numbers are not informative.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)

    f = sp.add_parser("fetch")
    f.add_argument("--pages", type=int, default=10)
    f.add_argument("--limit", type=int, default=20)
    f.add_argument("--client-id", default="101")
    f.add_argument("--competition-id", default="1")
    f.add_argument("--out", default="results_raw.json")
    f.set_defaults(fn=cmd_fetch)

    def common(s):
        s.add_argument("--input", default="bet9ja_premier_zoom_all_seasons.json")
        s.add_argument("--oldest-first", action="store_true",
                       help="file order is oldest->newest (only used when no timestamps are found)")
        s.add_argument("--half-life", type=float, default=300, help="recency half-life in matches")
        s.add_argument("--shrink", type=float, default=5.0, help="pull team ratings toward average")

    for name, fn in (("inspect", cmd_inspect), ("teams", cmd_teams),
                     ("backtest", cmd_backtest), ("predict", cmd_predict)):
        s = sp.add_parser(name)
        common(s)
        s.set_defaults(fn=fn)
        if name == "backtest":
            s.add_argument("--warmup", type=int, default=200)
            s.add_argument("--refit", type=int, default=10)
        if name == "predict":
            s.add_argument("--home", required=True)
            s.add_argument("--away", required=True)
            s.add_argument("--odds", type=float, nargs=3, metavar=("H", "D", "A"))

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

