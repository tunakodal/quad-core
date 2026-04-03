# GUIDE Data Pipeline README

**Guided User Itinerary & Destination Explorer**
Team: QUAD-CORE | BIL495/496 Graduation Project | TOBB ETÜ

This folder contains all Python scripts used in the GUIDE project's POI data collection, enrichment, audio generation, cloud storage, and database upload processes.

---

## Folder Structure

```
GUIDE Data Pipeline/
├── data_analysis.py                       # Dataset statistics and analysis
├── requirements.txt                       # Dependencies
│
├── collectors/
│   ├── osm_collector.py                   # OpenStreetMap / Overpass API POI collection
│   ├── wikipedia_collector.py             # Wikipedia category scraping
│   ├── multi_source_poi_collector.py      # Merge all sources + fetch Wikipedia descriptions
│   └── coordinate_validator.py            # Coordinate validation, remove out-of-Turkey POIs
│
├── enrichers/
│   ├── google_enricher.py                 # Google Places API — rating, reviews, place_id
│   └── photo_downloader.py                # Google Places API — photo download
│
├── llm/
│   ├── haiku_description_enricher.py      # Claude Haiku — generate TR + EN descriptions
│   └── translate_german.py                # Claude Haiku — EN → DE translation
│
├── tts/
│   ├── tts_google.py                      # Google Cloud TTS — TR + EN MP3 generation
│   └── tts_german.py                      # Google Cloud TTS — DE MP3 generation
│
├── storage/
│   └── upload_to_s3.py                    # AWS S3 — upload media, update JSON with URLs
│
└── database/
    ├── generate_seed.py                   # JSON → guide_schema.sql + guide_seed.sql
    └── insert_to_supabase.py              # Bulk insert to Supabase via REST API (port 443)
```

---

## Setup

```bash
pip install -r requirements.txt
```

Set environment variables (create a `.env` file, **never commit it**):

```env
ANTHROPIC_API_KEY=[API_KEY]
GOOGLE_PLACES_API_KEY=[API_KEY]
GOOGLE_TTS_API_KEY=[API_KEY]
AWS_ACCESS_KEY_ID=[API_KEY]
AWS_SECRET_ACCESS_KEY=[API_KEY]
AWS_REGION=[YOUR_AWS_REGION]
S3_BUCKET_NAME=[YOUR_BUCKET_NAME]
SUPABASE_URL=[YOUR_SUPABASE_URL]
SUPABASE_KEY=[YOUR_SERVICE_ROLE_KEY]
```

---

## Pipeline Flow and Execution Order

| # | Script | Description | Output |
|---|--------|-------------|--------|
| 1 | `collectors/osm_collector.py` | Collect POIs from Turkey via Overpass API | `poi_raw_osm.json` |
| 2 | `collectors/wikipedia_collector.py` | Wikipedia category scraping | `poi_raw_wiki.json` |
| 3 | `collectors/multi_source_poi_collector.py` | Merge sources, remove duplicates, fetch Wikipedia descriptions | `poi_merged.json` |
| 4 | `collectors/coordinate_validator.py` | Turkey boundary check, fix wrong province assignments, Nominatim geocoding | `poi_coord_validated.json` |
| 5 | `enrichers/google_enricher.py` | Add rating, review count, place_id via Google Places | `poi_enriched.json` |
| 6 | `llm/haiku_description_enricher.py` | Generate missing TR + EN descriptions with Claude Haiku | `poi_enriched_descriptions.json` |
| 7 | `llm/translate_german.py` | Translate EN descriptions to DE with Claude Haiku | `poi_with_german.json` |
| 8 | `enrichers/photo_downloader.py` | Download 3 photos per POI via Google Places | `poi_with_photos.json` |
| 9 | `tts/tts_google.py` | Generate TR + EN MP3 audio via Google Cloud TTS | `poi_with_audio.json` |
| 10 | `tts/tts_german.py` | Generate DE MP3 audio via Google Cloud TTS | `poi_complete.json` |
| 11 | `storage/upload_to_s3.py` | Upload photos + audio to AWS S3, update JSON with URLs | `poi_final.json` |
| 12 | `database/generate_seed.py` | Generate SQL schema + seed files from JSON | `guide_schema.sql` + `guide_seed.sql` |
| 13 | `database/insert_to_supabase.py` | Bulk insert to Supabase via REST API (port 443, no psql needed) | — |
| 14 | `data_analysis.py` | Dataset statistics report | `data_analysis_report.json` |

---

## Technologies and API Costs

| Technology / API | Purpose | Cost |
|------------------|---------|------|
| OpenStreetMap / Overpass API | Base POI collection | Free |
| Wikipedia / Wikidata API | POI discovery + descriptions | Free |
| Nominatim API | Reverse geocoding (coordinates → province) | Free |
| Google Places API (New) | Ratings, review counts, photos | ~$79 |
| Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) | TR+EN description generation + DE translation | ~$5-7 |
| Google Cloud TTS | TR + EN + DE MP3 audio generation | ~$34 |
| AWS S3 | Photo and audio file storage | ~$1/month |
| Supabase (PostgreSQL) | Database | Free (free tier) |

---

## Dataset Statistics (Final)

- **Total POIs:** 2,337 (covering all 81 provinces of Turkey)
- **Language support:** Turkish, English, German (descriptions + audio)
- **Audio files:** ~7,000 MP3s (3 languages per POI)
- **Photos:** ~7,000 JPGs (3 per POI)
- **Database:** Supabase PostgreSQL — `cities`, `pois`, `poi_contents`, `media_assets`
- **Media storage:** AWS S3

---

## Important Notes

- All scripts are **resumable** — if interrupted, re-running continues from where it left off via `*_progress.json` files.
- `guide_seed.sql` is a large file (~8 MB) and is listed in `.gitignore`.
- `poi_photos/` and `poi_audio/` directories are stored on S3 and are not committed locally.
- `insert_to_supabase.py` uses port 443 (HTTPS), bypassing ISP port blocking issues.
- Supabase insert order matters: `cities → pois → poi_contents → media_assets`.
