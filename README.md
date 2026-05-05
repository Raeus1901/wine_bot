# Wine Assistant Bot

[![Python](https://img.shields.io/badge/Python-3.10-blue?style=flat-square&logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3-black?style=flat-square&logo=flask)](https://flask.palletsprojects.com/)
[![Heroku](https://img.shields.io/badge/Deployed-Heroku-79589F?style=flat-square&logo=heroku)](https://www.heroku.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

A conversational web application that recommends wines based on a multi-step Q&A flow, backed by a custom Vivino-scraped dataset of 103 wines enriched with 20 attributes (alcohol, blend, region, ratings, tannins, sweetness, food pairings, and more).

The bot guides each user through preference elicitation (color → ABV → country → price), returns top matches, and offers an optional refinement step on blend variety and taste profile. A constraint-relaxation fallback ensures the user always receives recommendations, even when their initial criteria yield zero matches.

---

## Demo Flow

```
User: I'd like a red wine, around 13-14%, from Italy, under $30
Bot:  Found 4 matches in your range:

      1. Tenuta San Guido — Sassicaia 2018 (Bolgheri, Italy)
         · ABV: 13.5% · Price: $28 · Rating: 4.6/5 (1,247 reviews)
         · Tasting notes: Fruity, full-bodied, smooth tannins
         · Food pairing: Red meat, aged cheese
      ...

      Would you like to refine your search with Blend and Wine Tastes?
```

---

## Architecture

```
┌─────────────────────┐         ┌──────────────────────┐         ┌─────────────────────┐
│   Frontend (HTML/   │  HTTP   │   Flask API (app.py) │ Session │  WineRecommender    │
│   CSS/JavaScript)   │◄───────►│   /conversation      │◄───────►│  (state machine +   │
│                     │         │   /reset             │  state  │   pandas filtering) │
└─────────────────────┘         └──────────────────────┘         └─────────────────────┘
                                          │                                │
                                          │                                ▼
                                          │                  ┌─────────────────────┐
                                          │                  │   Vivino dataset    │
                                          │                  │   (103 wines × 20   │
                                          │                  │    attributes, CSV) │
                                          │                  └─────────────────────┘
                                          ▼
                                ┌──────────────────────┐
                                │ Multi-session store  │
                                │ (per user_id)        │
                                └──────────────────────┘
```

The application is stateless from the client's perspective — `user_id` is generated client-side via `localStorage` and passed to the server, where each session maintains its own `WineRecommender` instance with independent criteria state.

---

## Key Features

**Slot-filling conversational state machine.** The recommender tracks six slots — Color, AlcoholLevel, Country, PriceRange, Blend, Wine Tastes — and prompts the user for whichever is unfilled, in priority order.

**Free-text natural language parsing.** Users can phrase preferences flexibly: *"I'd like a strong red under $30 from Italy"* is parsed into `Color=Red`, `AlcoholLevel=14-15%`, `PriceRange=$20-30`, `Country=Italy` in a single message via regex and keyword matching.

**Constraint-relaxation fallback.** If no wines match all criteria, the system progressively relaxes lower-priority constraints (AlcoholLevel first, then PriceRange) until at least one match is found. The user is informed which constraints were relaxed.

**Multi-user session isolation.** Each browser instance receives a unique `user_id`, ensuring concurrent users don't interfere with each other's preference state.

**Production-ready deployment.** Configured for Heroku via `Procfile` and `gunicorn`, with `runtime.txt` pinning Python 3.10.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.10 · Flask 2.3 · Flask-CORS · gunicorn |
| **Data** | pandas 1.5 · numpy 1.24 · custom Vivino scraper (BeautifulSoup) |
| **Frontend** | Vanilla JavaScript · HTML5 · CSS3 |
| **Deployment** | Heroku (Procfile + runtime.txt) |
| **Logging** | Python `logging` module (DEBUG level for development) |

---

## The Dataset

103 wines scraped from Vivino, enriched with 20 attributes per wine:

| Category | Fields |
|----------|--------|
| **Identity** | Winery, Name, Vintage, Country, Region |
| **Composition** | Blend, Grape Types, Alcohol Level (ABV), Colour of Wine |
| **Quality signals** | Ratings, Number of Ratings, Price |
| **Sensory profile** | Body (Light–Bold), Tannins (Smooth–Tannic), Sweetness (Dry–Sweet), Acidity (Soft–Acidic), Wine Tastes, Flavor Notes |
| **Pairing** | Description, Food Pairings |

Data is loaded once at startup, validated for unrealistic ABV values (filtered to 5–20%), and cached in memory across sessions.

---

## Project Structure

```
wine_bot/
├── app.py                           # Flask routes + session management
├── wine_recommender.py              # Slot-filling state machine + filtering
├── multi_client.py                  # Multi-user session service example
├── wine_database_new.py             # Database utilities
├── enriched_wine_data_safari.csv    # 103-wine Vivino-scraped dataset
├── static/
│   ├── index.html                   # Chat UI
│   ├── styles.css                   # Styling
│   └── app.js                       # Client-side logic + localStorage user_id
├── requirements.txt                 # Python dependencies
├── runtime.txt                      # Python version pin (3.10)
└── Procfile                         # Heroku entrypoint
```

---

## Getting Started

### Local development

```bash
git clone https://github.com/Raeus1901/wine_bot.git
cd wine_bot

pip install -r requirements.txt
python app.py
```

The bot is now available at `http://localhost:5001`.

### Deployment (Heroku)

```bash
heroku create your-wine-bot
git push heroku main
heroku open
```

The `Procfile` automatically launches gunicorn against `app:app`.

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serves the chat UI |
| `/conversation?user_id={id}` | POST | Send a message, receive bot response + options |
| `/reset?user_id={id}` | POST | Clear the user's session state |

**Example request:**

```bash
curl -X POST "http://localhost:5001/conversation?user_id=user_123" \
  -H "Content-Type: application/json" \
  -d '{"message": "Red wine from France under $30"}'
```

**Response:**

```json
{
  "message": "What is your preferred alcohol range?",
  "options": ["11-12%", "12-13%", "13-14%", "14-15%"]
}
```

---

## Author

**Jean Trèves** — M.A. QMSS, Columbia University  
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/jean-treves-bbaa91257)
[![GitHub](https://img.shields.io/badge/GitHub-Raeus1901-black?style=flat-square&logo=github)](https://github.com/Raeus1901)
