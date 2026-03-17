# Trade Opportunities API

A **FastAPI** service that analyzes market data and provides structured trade
opportunity insights for specific sectors in India.

---

## Features

| Feature | Details |
|---|---|
| **Core endpoint** | `GET /analyze/{sector}` – returns a Markdown report |
| **Authentication** | Guest JWT (no credentials required for evaluation) |
| **Rate limiting** | Sliding-window: 10 requests / 60 s per token (configurable) |
| **Input validation** | Sector name length & character checks |
| **Data collection** | DuckDuckGo HTML search – no API key needed |
| **AI analysis** | Google Gemini 1.5 Flash (falls back to template if key absent) |
| **Storage** | In-memory only (no database) |
| **Auto docs** | Swagger UI at `/docs`, ReDoc at `/redoc` |

---

## Quick Start

### 1 – Clone / download the project

```bash
git clone <repo-url>
cd trade_api
```

### 2 – Create a virtual environment and install dependencies

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3 – Configure environment variables

```bash
# Required for AI-powered reports
export GEMINI_API_KEY="your_gemini_api_key_here"

# Optional overrides (defaults shown)
export JWT_SECRET_KEY="change_me_in_production"
export JWT_EXPIRE_MINUTES="60"
export RATE_LIMIT_MAX_REQUESTS="10"
export RATE_LIMIT_WINDOW_SECONDS="60"
export GEMINI_MODEL="gemini-1.5-flash"
```

> **Get a free Gemini API key:** https://aistudio.google.com/app/apikey

### 4 – Run the server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API is now live at **http://localhost:8000**

---

## Usage

### Step 1 – Get a guest token

```bash
curl -X POST http://localhost:8000/auth/guest-token
```

Response:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_at": "2024-01-01T13:00:00+00:00",
  "session_id": "uuid-here"
}
```

### Step 2 – Analyze a sector

```bash
TOKEN="eyJ..."   # paste your token here

curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/analyze/pharmaceuticals
```

Save the report to a file:
```bash
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/analyze/agriculture \
     -o agriculture_report.md
```

### Supported sector examples

`pharmaceuticals` · `technology` · `agriculture` · `textiles` · `automotive`
`renewable-energy` · `fintech` · `electronics` · `chemicals` · `food-processing`

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/auth/guest-token` | Issue a guest JWT |
| `GET` | `/analyze/{sector}` | **Main endpoint** – sector trade report |
| `GET` | `/session/stats` | Current token's rate-limit usage |
| `GET` | `/docs` | Swagger interactive docs |
| `GET` | `/redoc` | ReDoc documentation |

---

## Project Structure

```
trade_api/
├── main.py            # FastAPI app, endpoints, rate-limiter
├── auth.py            # JWT creation & verification
├── config.py          # All settings / env vars
├── data_collector.py  # DuckDuckGo search + HTML scraping
├── ai_analyzer.py     # Gemini integration + fallback report
├── models.py          # Pydantic response models
├── requirements.txt
└── README.md
```

---

## Architecture

```
Client
  │
  ▼
FastAPI (main.py)
  ├── Auth middleware  (auth.py)        ← JWT verification
  ├── Rate limiter    (main.py)        ← sliding-window in-memory
  ├── Input validator (main.py)        ← sector name checks
  │
  ├── DataCollector  (data_collector.py)
  │     └── DuckDuckGo HTML search (async, concurrent queries)
  │
  └── AIAnalyzer     (ai_analyzer.py)
        └── Google Gemini 1.5 Flash → Markdown report
```

---

## Security Notes

- JWT secret key **must** be changed in production (`JWT_SECRET_KEY` env var).
- Rate limiting is per-token (10 req/min by default).
- Input validation rejects non-alpha sector names and length extremes.
- CORS is open for evaluation; restrict `allow_origins` in production.

---

## Running Tests (manual)

```bash
# Health check
curl http://localhost:8000/

# Get token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/guest-token | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Analyze sectors
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/analyze/technology
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/analyze/agriculture
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/analyze/pharmaceuticals

# Check rate limit stats
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/session/stats

# Test invalid sector
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/analyze/123invalid
```

---

## License

MIT – free to use and modify.
