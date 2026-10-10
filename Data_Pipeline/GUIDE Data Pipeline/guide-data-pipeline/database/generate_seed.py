"""
GUIDE — Database Seed Generator
=================================
poi_final.json → guide_schema.sql + guide_seed.sql

Supabase (PostgreSQL) için:
  - guide_schema.sql  → tablo tanımları
  - guide_seed.sql    → INSERT doldurma

Kullanım:
    python generate_seed.py
    # Çıktı: guide_schema.sql + guide_seed.sql

Supabase'e yükle:
    Supabase SQL Editor → schema'yı çalıştır → seed'i çalıştır
    veya:
    psql "postgresql://postgres:[YOUR_DB_PASSWORD]@db.[YOUR_PROJECT_REF].supabase.co:5432/postgres" -f guide_schema.sql
    psql "postgresql://postgres:[YOUR_DB_PASSWORD]@db.[YOUR_PROJECT_REF].supabase.co:5432/postgres" -f guide_seed.sql
"""

import json
import re
import math
from pathlib import Path

INPUT_FILE = "poi_final.json"
SCHEMA_FILE = "guide_schema.sql"
SEED_FILE = "guide_seed.sql"


def slugify(text: str) -> str:
    text = text.lower().strip()
    for a, b in [
        ("ğ", "g"), ("ü", "u"), ("ş", "s"), ("ı", "i"), ("ö", "o"), ("ç", "c"),
        ("â", "a"), ("î", "i"), ("û", "u"),
    ]:
        text = text.replace(a, b)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")[:80]


def esc(v) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"


def maybe_float(v) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "NULL"
    try:
        return str(round(float(v), 4))
    except Exception:
        return "NULL"


def maybe_int(v) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "NULL"
    try:
        return str(int(v))
    except Exception:
        return "NULL"


SCHEMA_SQL = """
-- ============================================================
--  GUIDE — Database Schema
--  Supabase / PostgreSQL
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- ── cities ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cities (
    city_id         TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    country         TEXT NOT NULL DEFAULT 'TR',
    lat             FLOAT,
    lon             FLOAT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── pois ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pois (
    poi_id              TEXT PRIMARY KEY,
    city_id             TEXT REFERENCES cities(city_id),
    name                TEXT NOT NULL,
    category            TEXT,
    sub_categories      TEXT[],
    lat                 FLOAT NOT NULL,
    lon                 FLOAT NOT NULL,
    osm_id              BIGINT,
    wikipedia           TEXT,
    wikidata            TEXT,
    google_place_id     TEXT,
    google_rating       FLOAT,
    google_reviews_total INTEGER,
    google_photos_count INTEGER,
    viewport_area_km2   FLOAT,
    max_days            INTEGER DEFAULT 1,
    embedding           vector(1024),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pois_city     ON pois(city_id);
CREATE INDEX IF NOT EXISTS idx_pois_category ON pois(category);
CREATE INDEX IF NOT EXISTS idx_pois_rating   ON pois(google_rating DESC NULLS LAST);

-- ── poi_contents ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS poi_contents (
    content_id  TEXT PRIMARY KEY,
    poi_id      TEXT REFERENCES pois(poi_id) ON DELETE CASCADE,
    language    TEXT NOT NULL CHECK (language IN ('TR', 'EN', 'DE')),
    description TEXT,
    UNIQUE (poi_id, language)
);

-- ── media_assets ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS media_assets (
    asset_id    TEXT PRIMARY KEY,
    poi_id      TEXT REFERENCES pois(poi_id) ON DELETE CASCADE,
    url         TEXT NOT NULL,
    media_type  TEXT NOT NULL CHECK (media_type IN ('image', 'audio')),
    language    TEXT,
    sort_order  INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_media_poi ON media_assets(poi_id);
"""


def generate_seed(data: dict) -> str:
    city_rows = []
    poi_rows = []
    content_rows = []
    media_rows = []

    city_id_map: dict[str, str] = {}
    poi_id_count: dict[str, int] = {}

    # Cities
    for province in sorted(data.keys()):
        pois = data[province]
        if not pois:
            continue
        city_id = slugify(province)
        city_id_map[province] = city_id

        # Ortalama koordinat
        lats = [p["lat"] for p in pois if p.get("lat")]
        lons = [p["lon"] for p in pois if p.get("lon")]
        avg_lat = round(sum(lats) / len(lats), 4) if lats else "NULL"
        avg_lon = round(sum(lons) / len(lons), 4) if lons else "NULL"

        city_rows.append(
            f"  ({esc(city_id)}, {esc(province)}, 'TR', {avg_lat}, {avg_lon})"
        )

    # POIs
    for province, pois in data.items():
        city_id = city_id_map.get(province, slugify(province))

        for poi in pois:
            base_id = f"{city_id}-{slugify(poi['name'])}"
            n = poi_id_count.get(base_id, 0)
            poi_id_count[base_id] = n + 1
            poi_id = base_id if n == 0 else f"{base_id}-{n}"

            poi["_poi_id"] = poi_id  # geçici referans

            sub_cats = poi.get("sub_categories") or []
            sub_cats_pg = (
                "ARRAY[" + ",".join(f"'{c}'" for c in sub_cats) + "]"
                if sub_cats else "ARRAY[]::TEXT[]"
            )

            poi_rows.append(
                f"  ({esc(poi_id)}, {esc(city_id)}, {esc(poi['name'])}, "
                f"{esc(poi.get('category'))}, {sub_cats_pg}, "
                f"{maybe_float(poi.get('lat'))}, {maybe_float(poi.get('lon'))}, "
                f"{maybe_int(poi.get('osm_id'))}, {esc(poi.get('wikipedia'))}, "
                f"{esc(poi.get('wikidata'))}, {esc(poi.get('google_place_id'))}, "
                f"{maybe_float(poi.get('google_rating'))}, "
                f"{maybe_int(poi.get('google_reviews_total'))}, "
                f"{maybe_int(poi.get('google_photos_count'))}, "
                f"{maybe_float(poi.get('viewport_area_km2'))})"
            )

            # Contents
            for lang, field in [("TR", "description_tr"), ("EN", "description_en"), ("DE", "description_de")]:
                desc = poi.get(field, "")
                if desc:
                    content_id = f"{poi_id}-{lang.lower()}"
                    content_rows.append(
                        f"  ({esc(content_id)}, {esc(poi_id)}, {esc(lang)}, {esc(desc[:1000])})"
                    )

            # Media — photos
            for idx, url in enumerate(poi.get("photo_urls") or [], 1):
                asset_id = f"{poi_id}-img-{idx}"
                media_rows.append(
                    f"  ({esc(asset_id)}, {esc(poi_id)}, {esc(url)}, 'image', NULL, {idx})"
                )

            # Media — audio
            for lang, field in [("TR", "audio_tr"), ("EN", "audio_en"), ("DE", "audio_de")]:
                path = poi.get(field)
                if path and isinstance(path, str) and path.strip():
                    asset_id = f"{poi_id}-audio-{lang.lower()}"
                    media_rows.append(
                        f"  ({esc(asset_id)}, {esc(poi_id)}, {esc(path.strip())}, 'audio', {esc(lang)}, 1)"
                    )

    lines = [
        "-- ============================================================",
        f"--  GUIDE Seed Data  |  {sum(len(v) for v in data.values())} POIs  |  {len(data)} cities",
        "-- ============================================================\n",
        "BEGIN;\n",
        "INSERT INTO cities (city_id, name, country, lat, lon) VALUES",
        ",\n".join(city_rows) + ";\n",
        "INSERT INTO pois (poi_id, city_id, name, category, sub_categories, lat, lon,",
        "  osm_id, wikipedia, wikidata, google_place_id, google_rating,",
        "  google_reviews_total, google_photos_count, viewport_area_km2) VALUES",
        ",\n".join(poi_rows) + ";\n",
    ]

    if content_rows:
        lines += [
            "INSERT INTO poi_contents (content_id, poi_id, language, description) VALUES",
            ",\n".join(content_rows) + ";\n",
        ]

    if media_rows:
        lines += [
            "INSERT INTO media_assets (asset_id, poi_id, url, media_type, language, sort_order) VALUES",
            ",\n".join(media_rows) + ";\n",
        ]

    lines.append("COMMIT;")
    return "\n".join(lines)


def main():
    print("=" * 60)
    print("GUIDE — Database Seed Generator")
    print("=" * 60)

    with open(INPUT_FILE, encoding="utf-8") as f:
        data = json.load(f)

    total = sum(len(v) for v in data.values())
    print(f"Loaded: {total} POIs from {len(data)} provinces")

    # Schema
    with open(SCHEMA_FILE, "w", encoding="utf-8") as f:
        f.write(SCHEMA_SQL)
    print(f"💾 Schema: {SCHEMA_FILE}")

    # Seed
    seed_sql = generate_seed(data)
    with open(SEED_FILE, "w", encoding="utf-8") as f:
        f.write(seed_sql)

    size_kb = len(seed_sql) // 1024
    print(f"💾 Seed: {SEED_FILE} ({size_kb} KB)")
    print(f"\n✅ Tamamlandı. Supabase'e yüklemek için:")
    print(f"   1. SQL Editor → {SCHEMA_FILE} çalıştır")
    print(f"   2. SQL Editor veya psql → {SEED_FILE} çalıştır")


if __name__ == "__main__":
    main()
