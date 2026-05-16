<div align="center">

# 🍷 Wine Recommender — Conversational Constraint-Satisfaction Engine

### A Flask chatbot that recommends wines through slot-filling dialogue and **automatic constraint relaxation** — the same fallback pattern used in constrained optimization

[![Python](https://img.shields.io/badge/python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![pandas](https://img.shields.io/badge/pandas-1.5-150458?logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

---

## 🎯 What It Does

The Wine Recommender is a conversational agent that guides a user through a structured
dialogue to recommend wines from a curated dataset. It captures preferences across four
dimensions — **colour, alcohol level, country, price** — then optionally refines on
**blend** and **taste profile**.

Its defining feature is a **constraint-relaxation fallback**: when no wine satisfies all
of a user's stated preferences, the engine systematically loosens the least-critical
constraint until the feasible set is non-empty — and reports exactly which constraints it
relaxed.

```text
User: "I want a strong red from Spain"
  → Color=Red, ABV=14-15%, Country=Spain
  → Strict filter: 0 matches
  → Relax ABV constraint → 4 matches found
Bot: "Here are 4 wines. Note: we relaxed the alcohol-level constraint."
```

---

## 📊 Dataset

The recommender operates over a curated dataset of **103 wines** with 20 attributes each:
ABV, winery, vintage, country, region, colour, blend, grape types, ratings, price, body /
tannins / sweetness / acidity scores, tasting notes, and food pairings.

Run the coverage analysis:

```bash
python analyze_dataset.py
```

This computes the **recommender hit-rate metric** — the share of all (colour × ABV ×
country × price) preference combinations that return at least one wine under strict
filtering, versus after constraint relaxation. The gap between the two quantifies how much
the fallback mechanism widens the feasible set.

---

## 🏗️ Architecture

```text
┌─────────────┐    POST /conversation       ┌──────────────────────┐
│  Browser    │ ──────────────────────────► │  Flask app (app.py)  │
│  (static/)  │ ◄────────────────────────── │  session per user_id │
└─────────────┘    JSON {message,options}   └──────────┬───────────┘
                                                        │
                                            ┌───────────▼────────────┐
                                            │  WineRecommender         │
                                            │  · slot-filling FSM      │
                                            │  · free-text regex parse │
                                            │  · strict filter         │
                                            │  · relaxation fallback   │
                                            └──────────────────────────┘
```

Key design elements:

- **Finite state machine** — four `initial_steps` slots (Color, AlcoholLevel, Country,
  PriceRange), then two `refinement_steps` (Blend, Wine Tastes). Each slot is validated
  before the FSM transitions.
- **Session isolation** — each `user_id` gets an independent `WineRecommender` instance
  with its own conversation state, stored server-side in a `sessions` dict.
- **Free-text parsing** — regex interpretation of natural input: `"under $30"`,
  `"less than 13%"`, `"strong"` → `14-15%`, `"light"` → `11-12%`, `"medium"` → `12-13%`.
- **Constraint relaxation** — ordered fallback (`fallback_order = ["AlcoholLevel",
  "PriceRange"]`): the engine drops the ABV constraint first, then widens the price band,
  reporting each relaxation back to the user.
- **Colour-aware refinement** — the Blend options are dynamically filtered to the blends
  actually present for the chosen wine colour.

---

## 🚀 Quick Start

```bash
git clone https://github.com/Raeus1901/wine_bot.git
cd wine_bot
pip install -r requirements.txt

python app.py
# → http://localhost:5001
```

API example:

```bash
curl -X POST "http://localhost:5001/conversation?user_id=demo" \
  -H "Content-Type: application/json" \
  -d '{"message": "I want a strong red from Spain"}'
```

Endpoints:

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Serve the chat UI (`static/index.html`) |
| `/wine_recommender_endpoint` | POST | Stateless greeting on page load |
| `/conversation?user_id=<id>` | POST | Main stateful dialogue turn |
| `/reset?user_id=<id>` | POST | Clear a user's session |

---

## 📈 Relevance to Quantitative & Systematic Work

This is a side project, but its core mechanics map onto patterns used in quantitative
finance:

- **Constraint relaxation = optimization under active constraints.** When a mandate
  (sector cap + tracking-error limit + turnover budget) admits no feasible portfolio, a
  practitioner slackens the least-binding constraint first. The recommender's
  `fallback_order` is exactly this: an explicit, ordered relaxation hierarchy with
  transparent reporting of what was dropped.
- **Slot-filling FSM = structured preference elicitation.** Capturing a client's risk
  tolerance, horizon, and liquidity needs through validated, sequential questioning is the
  same dialogue pattern as capturing colour / ABV / country / price.
- **Hit-rate metric = feasible-region diagnostics.** Measuring the share of preference
  combinations that yield a match is the recommender analogue of asking what fraction of
  mandates are feasible under the current asset universe.

The transferable skill is translating a fuzzy human objective into a structured, relaxable
constraint problem with explicit fallback logic.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask 2.3.2, Werkzeug 2.3.3 |
| Data | pandas 1.5.3, numpy 1.24.3 |
| Frontend | Vanilla HTML / CSS / JS (`static/`) |
| WSGI server | Gunicorn 20.1.0 (`Procfile` included) |

---

## ⚠️ Notes & Limitations

- **Dataset size.** 103 wines is a demonstration dataset; production use would require a
  larger, regularly-refreshed catalogue.
- **Parsing.** Free-text interpretation is regex-based, not a learned NLU model — robust
  for supported phrasings, brittle outside them.
- **Recommendation logic.** Filtering is rule-based; there is no collaborative-filtering
  or learned ranking. A natural extension would be a learned ranker over the feasible set.
- **Price-range relaxation.** The price-band fallback expects a `$min-$max` token format;
  the ABV relaxation is the primary working fallback path.

---

## 👤 Author

**Jean Treves** — M.A. Quantitative Methods in the Social Sciences, Columbia University
[LinkedIn](https://www.linkedin.com/in/jean-treves-bbaa91257/) • [GitHub](https://github.com/Raeus1901)

> Master thesis (FinBERT × SARIMAX): [finbert-sarimax-energy-forecasting](https://github.com/Raeus1901/finbert-sarimax-energy-forecasting)
