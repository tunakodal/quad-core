# GUIDE — Guided User Itinerary & Destination Explorer

**An integrated, constraint-aware multi-day itinerary planning and POI exploration system for Türkiye.**

> BIL495 / BIL496 Graduation Project · Team **QUAD-CORE** · TOBB University of Economics and Technology, Department of Computer Engineering, Ankara
>
> 🎓 Accepted and published at **MUISC 2026** (Maltepe University International Student Congress) — see [Publication](#-publication--conference).

---

## Table of Contents

1. [Overview](#overview)
2. [Publication & Conference](#-publication--conference)
3. [Key Features](#key-features)
4. [Repository Structure](#repository-structure)
5. [System Architecture](#system-architecture)
6. [How the Itinerary Planner Works](#how-the-itinerary-planner-works)
7. [The POI Dataset](#the-poi-dataset)
8. [Tech Stack](#tech-stack)
9. [Running the Project Locally](#running-the-project-locally)
10. [API Reference](#api-reference)
11. [Testing](#testing)
12. [Documentation](#documentation)
13. [Project Status](#project-status)
14. [Team](#team)

---

## Overview

Travel planning is usually done through a fragmented mix of map services, review platforms and manual spreadsheets. Users have to combine spatial, temporal and categorical information by hand, which is slow and often produces inefficient or inconsistent itineraries.

**GUIDE** turns a handful of user constraints into a structured, route-aware, multi-day itinerary within a single workflow:

| You provide | GUIDE returns |
|---|---|
| Destination city | A day-by-day plan of POIs |
| Trip duration (days) | Road-based distance, duration and geometry for every leg |
| Preferred POI categories | An interactive map view of each day |
| Target daily travel distance range | Curated text, photos and multilingual audio for each POI |

After the plan is generated, users can **add, remove and reorder** POIs and have the itinerary re-computed instantly.

## 🎓 Publication & Conference

GUIDE was accepted to, and is included in the official abstract book of:

| | |
|---|---|
| **Congress** | Maltepe University International Student Congresses (MUISC 2026) — *International Congress on Undergraduate Capstone Projects in Engineering and Natural Sciences* |
| **Dates / Venue** | 11–12 May 2026 · Istanbul, Türkiye · Hybrid format |
| **Organizer** | Faculty of Engineering and Natural Sciences, Maltepe University |
| **Presentation track** | Online Presentations |
| **Abstract title** | *GUIDE: An Integrated Constraint-Aware Multi-Day Itinerary Planning and POI Exploration System for Türkiye* (abstract book p. 73) |
| **Authors** | Ebrar Sude Doğan\*, Erdem Baran, Kayrahan Toprak Tosun, Tuna Kodal, Yücel Çimtay (\*corresponding author) |
| **Proceedings** | Electronic Book of Abstracts, published July 2026 · e-ISBN 978-605-2124-82-6 |
| **Abstract book (open access)** | <https://hdl.handle.net/20.500.12415/14317> |

> The abstract book is © Maltepe University and is therefore **not** redistributed in this repository; please use the link above.

## Key Features

- **Constraint-aware planning** — city, duration, categories and daily-distance targets drive candidate filtering.
- **Monte Carlo itinerary generation** — randomized POI subsets per day, scored by a multi-criteria function.
- **Real road routing** — a locally deployed OSRM instance on OpenStreetMap data provides distance, duration and geometry (encoded polylines to keep payloads small).
- **Interactive replanning** — add, remove or reorder POIs; the plan is recomputed from the request data alone.
- **Rich POI content** — curated descriptions, photos and optional offline-generated audio guides in Turkish, English and German.
- **Stateless backend** — no server-side session; every request carries everything it needs, which keeps the service scalable and predictable.
- **Curated Türkiye POI dataset** — validated coordinates, standardized categories, popularity indicators (see [The POI Dataset](#the-poi-dataset)).

## Repository Structure

```
quad-core/
├── README.md                     ← you are here
├── index.html                    ← GitHub Pages landing page (kept at root on purpose)
│
├── quad-core/                    ← THE APPLICATION
│   ├── src/                      ← React frontend (pages, layout, ui, api client, styles)
│   ├── public/                   ← static assets (logo, API logos, team photos, flow icons)
│   ├── package.json, vite.config.js, index.html
│   └── guide-backend/            ← FastAPI backend
│       ├── main.py               ← app entry point
│       ├── app/
│       │   ├── api/              ← routes (route_endpoints, poi_endpoints), validator, error mapper
│       │   ├── services/         ← itinerary planner / builder / ranker, routing, POI & content services
│       │   ├── integration/      ← OSRM client
│       │   ├── repositories/     ← data access (interfaces, Supabase repos, stubs)
│       │   ├── models/           ← domain models (POI, route, geo, media, enums)
│       │   ├── schemas/          ← request/response DTOs
│       │   └── core/             ← config, DI container, database
│       ├── data/                 ← fallback JSON data (pois.json, contents.json)
│       ├── db/schema.sql         ← database schema
│       └── tests/                ← unit · integration · system · performance
│
├── Data_Pipeline/                ← POI dataset construction
│   ├── GUIDE Data Pipeline/
│   │   ├── guide-data-pipeline/  ← collectors · enrichers · llm · tts · storage · database scripts
│   │   ├── json_to_tabular_construction/  ← notebooks (JSON → tabular DB)
│   │   └── poi_dataset_complete_v11_fixed.json
│   └── GUIDE Data Pipeline README.md   ← detailed pipeline guide (run order, costs, stats)
│
├── Documentation/
│   ├── BIL495_Documentation/     ← Proposal, Specification, Analysis, High-Level Design reports
│   ├── BIL496_Documentation/     ← Final Report, Low-Level Design, Test Plan, PKE document
│   ├── Page_Designs/             ← UI mock-ups (v1 and v2)
│   └── Deprecated_Files/         ← sprint-by-sprint working documents (Sprints 1–5), old versions
│
└── Legacy_Root_Files/            ← earlier copies of backend files that used to sit in the repo root
                                    (main.py, pytest.ini, requirements.txt, data/, db/);
                                    the maintained versions live in quad-core/guide-backend/
```

**Where do I look first?**

| I want to… | Go to |
|---|---|
| Run the app | [`quad-core/`](quad-core) and [`quad-core/guide-backend/`](quad-core/guide-backend) |
| Understand the algorithm | [`quad-core/guide-backend/app/services/`](quad-core/guide-backend/app/services) and the Final Report |
| See how the dataset was built | [`Data_Pipeline/`](Data_Pipeline) |
| Read the project reports | [`Documentation/BIL496_Documentation/`](Documentation/BIL496_Documentation) |
| See UI designs | [`Documentation/Page_Designs/`](Documentation/Page_Designs) |

## System Architecture

GUIDE follows a **layered, service-oriented** design:

```
┌──────────────────────────────────────────────────────────────┐
│ Presentation   React + Vite + Leaflet                        │
│                Landing · Planning · Journey · Route ·        │
│                Replanning · POI detail · How it works        │
└───────────────────────────────┬──────────────────────────────┘
                                │ REST / JSON (stateless)
┌───────────────────────────────▼──────────────────────────────┐
│ Application    FastAPI · validation · itinerary planner ·    │
│                plan ranker · POI & content services          │
└───────────────┬───────────────────────────────┬──────────────┘
                │                               │
┌───────────────▼─────────────┐   ┌─────────────▼──────────────┐
│ Integration                 │   │ Data                       │
│ OSRM client (OSM road data) │   │ Supabase / PostgreSQL      │
│ → distance, time, polyline  │   │ pois · poi_contents ·      │
└─────────────────────────────┘   │ media_assets · S3 media    │
                                  └────────────────────────────┘
```

The backend uses dependency injection (`app/core/containers.py`) and a repository pattern, so the data source (Supabase, or the bundled JSON fallback) can be swapped without touching the planning logic.

## How the Itinerary Planner Works

1. **Filter** — the candidate POI pool is restricted by city and selected categories.
2. **Sample** — for each day, multiple randomized POI subsets (within min/max size limits) are drawn from the remaining pool (**Monte Carlo** candidate generation).
3. **Score** — every subset is scored by a multi-criteria function balancing:
   - average popularity,
   - category diversity,
   - closeness to the target daily distance (straight-line approximation during evaluation),
   - spatial continuity between consecutive POIs,
   - total POI count.
4. **Select** — the best subset becomes that day's plan; its POIs are removed from the pool so days stay diverse.
5. **Route** — once all days are fixed, OSRM computes real road distance, duration and geometry per segment.
6. **Replan** — add / remove / reorder requests re-run the pipeline for the affected days using only the data in the request.

Configurable limits live in `app/core/config.py` (e.g. max 10 trip days, max 9 POIs per day, max 110 POIs in total).

## The POI Dataset

Public destination data is inconsistent and incomplete for structured planning, so a dedicated dataset was engineered as part of the project:

- **2,337 POIs** covering all **81 provinces** of Türkiye
- Sources: OpenStreetMap (Overpass), Wikipedia/Wikidata, Google Places (ratings, reviews, photos)
- Validated coordinates (out-of-Türkiye points removed, province assignments corrected)
- Standardized hierarchical categories and structured popularity indicators
- Descriptions in **Turkish, English and German** (LLM-assisted, then translated)
- ~7,000 audio guides (TTS, generated offline) and ~7,000 photos, stored on AWS S3
- Loaded into a Supabase PostgreSQL database: `cities → pois → poi_contents → media_assets`

The complete, ordered 14-step pipeline is documented in [`Data_Pipeline/GUIDE Data Pipeline README.md`](Data_Pipeline/GUIDE%20Data%20Pipeline%20README.md).

## Tech Stack

| Area | Technologies |
|---|---|
| Frontend | React 19, Vite 7, React Router 7, Leaflet / react-leaflet, CSS Modules |
| Backend | Python, FastAPI, Pydantic v2, httpx, Uvicorn |
| Routing | OSRM (self-hosted) + OpenStreetMap |
| Database | Supabase (PostgreSQL) |
| Data / AI | Overpass, Wikipedia, Google Places, Claude Haiku, Google Cloud TTS |
| Storage | AWS S3 |
| Testing | pytest (+ asyncio) |

## Running the Project Locally

> **Note:** the production deployment (hosting, OSRM server and managed database) is no longer running, so a full local run requires you to provide your own services. The repository is primarily kept as a presentation and archival artifact.

### Backend

```bash
cd quad-core/guide-backend
pip install -r requirements.txt
```

Create a `.env` file in `quad-core/guide-backend/` (all values optional — the app falls back to bundled JSON data when Supabase is not configured):

```env
SUPABASE_URL=...
SUPABASE_KEY=...                    # anon / publishable key
OSRM_BASE_URL=http://localhost:5000
```

```bash
uvicorn main:app --reload           # http://localhost:8000  (docs at /docs)
```

### Frontend

```bash
cd quad-core
npm install
npm run dev                         # http://localhost:5173 (proxies /api → localhost:8000)
```

### OSRM (optional, for real routing)

Run an OSRM backend with a Türkiye OpenStreetMap extract on port `5000` (see the OSRM documentation).

## API Reference

Base path: `/api/v1`

| Method | Path | Description |
|---|---|---|
| `POST` | `/routes/generate` | Generate a multi-day itinerary |
| `POST` | `/routes/replan` | Replan after the user adds, removes or reorders POIs |
| `POST` | `/routes/suggest-days` | Suggest the maximum feasible number of trip days |
| `POST` | `/pois/search` | Search POIs by city / category |
| `GET` | `/pois/{poi_id}` | Get a single POI |
| `POST` | `/pois/content` | Get POI content, media and audio |
| `GET` | `/health` | Health check |

Interactive docs are served at `http://localhost:8000/docs` while the backend is running.

## Testing

```bash
cd quad-core/guide-backend
pytest                              # all tests
pytest tests/unit                   # unit tests
pytest tests/integration            # integration tests
pytest tests/system                 # system tests (ST-01 … ST-07)
pytest tests/performance            # performance tests (PT-01 … PT-07)
```

The suite covers unit, integration, system and performance levels (latency, upper-bound stability, memory and CPU behaviour, audio-on-demand). The test strategy is described in `Documentation/BIL496_Documentation/Test_Plan_Report.pdf`.

## Documentation

| Phase | Documents |
|---|---|
| **BIL495** (design) | `GUIDE_Proposal`, `GUIDE_Project_Specification_Report`, `GUIDE_Analysis_Report`, `GUIDE_High_Level_Design_Report` |
| **BIL496** (implementation) | `Final_Report`, `Low_Level_Design_Report`, `Test_Plan_Report`, `PKE_document` |
| **UI design** | `Page_Designs/v1`, `Page_Designs/v2` |
| **Process history** | `Deprecated_Files/Sprint_1 … Sprint_5` (meeting notes, reviews, retrospectives, IEEE SRS/SDD/STP, diagrams) |

All of the above live under [`Documentation/`](Documentation).

## Project Status

The system was fully implemented and evaluated as an undergraduate capstone project and presented at MUISC 2026. The live deployment has since been taken down (hosting and API costs); the code, data pipeline, reports and designs in this repository are preserved for presentation and reference.

## Team

**QUAD-CORE**

- Ebrar Sude Doğan
- Kayrahan Toprak Tosun
- Erdem Baran
- Tuna Kodal

**Links:** [Project site (GitHub Pages)](https://tunakodal.github.io/quad-core/) · [Shared Google Drive](https://drive.google.com/drive/folders/1lyXuqaJ0JrhiMycv8PPHxm4y8imNcxqK?usp=sharing)
