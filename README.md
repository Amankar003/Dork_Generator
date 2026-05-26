# Dork Optimizer

Fresh source-backed daily B2B dork and keyword intelligence system.

## Quick Start

```bash
cd dork_optimizer
pip install -r requirements.txt
# Edit .env with your GEMINI_API_KEY
python app.py
```

Open http://localhost:8000 for the dashboard.

## Architecture

```
sources/ → source_data table → LLM-1 → trend_analysis table → LLM-2 → recommendations table → dashboard
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /run-daily-pipeline | Run full daily pipeline |
| GET | /today-recommendations | Today's recommendations only |
| GET | /source-data/today | Today's raw source data |
| GET | /recommendations/history | Historical recommendations |
| POST | /dorks/mark-used | Mark a dork as used |

## Database (4 tables)

- **source_data** — Raw fetched data from GDELT, News, RSS, pytrends, seed
- **trend_analysis** — LLM-1 trend analysis output
- **recommendations** — Final dorks/keywords for dashboard
- **dork_history** — User-marked used dorks only

## Sources

- GDELT (free, no key)
- NewsData.io (optional API key)
- RSS feeds (free)
- Google Trends (free, rate-limited)
- Seed data (demo fallback only)
