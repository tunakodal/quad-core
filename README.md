# GUIDE Backend

FastAPI + PostgreSQL backend for the GUIDE travel planning system.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your DB credentials
uvicorn main:app --reload
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/routes/generate` | Generate itinerary |
| POST | `/api/v1/routes/replan` | Replan after user edits |
| POST | `/api/v1/routes/suggest-days` | Suggest max trip days |
| POST | `/api/v1/pois/search` | Search POIs |
| GET | `/api/v1/pois/{poi_id}` | Get POI by ID |
| POST | `/api/v1/pois/content` | Get POI content + audio |
| GET | `/health` | Health check |

## Docs
After running: http://localhost:8000/docs

## TODO (Erdem)
- `app/repositories/repositories.py` → Replace Stub* classes with real PostgreSQL queries
- `app/services/itinerary_service.py` → `MonteCarloItineraryPlanner.generate_candidates()` implement et
- `alembic/` → DB migration dosyaları
