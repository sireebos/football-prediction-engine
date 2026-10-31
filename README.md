# AI Football Prediction Engine ⚽🤖

A machine learning and statistical modeling pipeline for match analysis, league memory, real-time odds tracking, and football outcome forecasting.

---

## 🌟 Key Architecture & Capabilities

1. **Pulse Live & Official Premier League Scraper (`premier.py`)**
   - Harvests official Premier League standings, live team form matrices, points per game, and goal differentials.
   - Outputs clean normalized JSON and CSV data stores.

2. **Turbo / Virtual Zoom Odds & Results Extractor (`zoom.py`)**
   - Interacts with high-frequency live match telemetry feeds.
   - Tracks half-time scorelines, full-time results, and corner distributions across multi-round matchdays.

3. **Statistical & ML Inference Engine**
   - Poisson distribution goal expectancy models ($P(X=k) = \frac{\lambda^k e^{-\lambda}}{k!}$).
   - Dixon-Coles low-score probability corrections.
   - Home-advantage and form-weighted Elo rating adjustments.
   - Outcome probabilities for 1X2, Over/Under 2.5, Both Teams to Score (BTTS), and corner counts.

---

## 🛠️ Stack

- **Language:** Python 3.11+
- **Data Engineering:** `pandas`, `numpy`, `curl_cffi` (high-performance HTTP client with TLS fingerprint simulation)
- **Modeling:** Poisson Goal Expectancy, Logistic Regression, Elo Rating Adjusters
- **Data Stores:** JSON, CSV, SQLite

---

## 🚀 Quickstart

```bash
# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install pandas curl_cffi

# Ingest live Premier League telemetry
python3 premier.py

# Ingest Turbo match results
python3 zoom.py
```
