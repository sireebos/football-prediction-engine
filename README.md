# AI Football Prediction Engine & Bet9ja Zoom Virtual Intelligence ⚽🤖

A comprehensive statistical modeling, automated data harvesting, persistent league memory, and match prediction system for real-world soccer and Bet9ja Zoom Virtual Leagues.

---

## 🌟 Key Architecture & Capabilities

1. **Bet9ja Zoom Virtual Match Engine (`zoom.py`, `zoom_predict.py`)**
   - Harvests multi-season match results, half-time scores, full-time outcomes, corner counts, and goal distribution across all 8 Zoom competitions.
   - Built-in head-to-head (H2H) matrix, team offensive/defensive ratings, and recurring pattern detection.
   - Comparative database with 1,490+ historical match outcomes.

2. **Official Premier League Telemetry (`premier.py`)**
   - Scrapes official Premier League standings, live team form matrices, points-per-game, and goal differentials directly into structured JSON, CSV, and Excel workbooks.

3. **Empirical Analysis & Statistical Reverse-Engineering (`analyze_similarity.py`, `predict_today.py`)**
   - Evaluates season-to-season fixture recurrence, schedule shifting, and head-to-head score stability.
   - Reverse-engineers underlying Bivariate Poisson simulation models and goal distributions ($\lambda_{\text{tot}} \approx 2.62$).
   - Evaluates market leans for 1X2, Over/Under 2.5, BTTS (GG/NG), and exact score probability modes (`1-1`, `1-0`, `0-1`).

4. **Statistical & ML Inference Engine**
   - Poisson distribution goal expectancy models ($P(X=k) = \frac{\lambda^k e^{-\lambda}}{k!}$).
   - Dixon-Coles low-score probability corrections.
   - Home-advantage and form-weighted ratings.
   - Market valuation and bookmaker odds extraction for positive expected value ($+EV$).

---

## 🛠️ Stack

- **Language:** Python 3.11+
- **Data Engineering:** `pandas`, `numpy`, `curl_cffi`, `pypdf`, `openpyxl`
- **Modeling:** Poisson Goal Expectancy, Bivariate Poisson Grid, Dixon-Coles Corrections
- **Data Stores:** JSON, CSV, Excel (`.xlsx`)

---

## 📖 Cross-Platform Installation Guide

For detailed OS-specific installation instructions (Linux, macOS, and Windows with WSL2/PowerShell):
👉 **See [INSTALLATION.md](file:///home/sireebos/Documents/predition_zoom/INSTALLATION.md)**

---

## 🚀 Quickstart

```bash
# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1

# Install dependencies from requirements.txt
pip install -r requirements.txt

# Run Live Real-Time Zoom Viewer across all 8 leagues:
python3 live_zoom.py

# Scrape and update Zoom Virtual database across all leagues
python3 zoom.py --all-leagues

# Predict upcoming match fixture
python3 zoom.py --predict "Z.Man City" "Z.Arsenal"

# Run season similarity and reverse-engineering analysis
python3 analyze_similarity.py

# Run live round predictions
python3 predict_today.py
```
