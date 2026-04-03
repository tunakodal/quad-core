"""
GUIDE — Google Places API Enricher
=====================================
Her POI için Google Places (New) API'den
rating, yorum sayısı, fotoğraf sayısı ve place_id çeker.

Girdi  : poi_merged.json
Çıktı  : poi_enriched.json
Tahmini maliyet: ~$10 (2,300 POI × $0.004/istek)
Hız: 0.2s gecikme / istek

Kullanım:
    export GOOGLE_PLACES_API_KEY=[API_KEY]
    python google_enricher.py
"""

import json
import os
import time
import math
import requests
from pathlib import Path

API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "[API_KEY]")
INPUT_FILE = "poi_merged.json"
OUTPUT_FILE = "poi_enriched.json"
PROGRESS_FILE = "google_enrich_progress.json"
SAVE_EVERY = 30
DELAY = 0.2
MAX_RETRIES = 3

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"


def haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def viewport_area_km2(viewport: dict) -> float | None:
    try:
        ne = viewport["high"]
        sw = viewport["low"]
        lat_dist = haversine(sw["latitude"], sw["longitude"], ne["latitude"], sw["longitude"])
        lon_dist = haversine(sw["latitude"], sw["longitude"], sw["latitude"], ne["longitude"])
        return round((lat_dist * lon_dist) / 1e6, 4)
    except Exception:
        return None


def search_place(name: str, lat: float, lon: float) -> dict | None:
    payload = {
        "textQuery": f"{name}, Turkey",
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lon},
                "radius": 5000.0,
            }
        },
        "maxResultCount": 1,
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": (
            "places.id,places.rating,places.userRatingCount,"
            "places.photos,places.viewport"
        ),
    }

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(TEXT_SEARCH_URL, json=payload, headers=headers, timeout=15)
            if resp.status_code == 200:
                places = resp.json().get("places", [])
                return places[0] if places else None
            elif resp.status_code == 429:
                time.sleep(10 * (attempt + 1))
            else:
                return None
        except Exception as e:
            print(f"  ⚠ API error: {e}")
            time.sleep(5)
    return None


def load_progress() -> set:
    if Path(PROGRESS_FILE).exists():
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_progress(done: set):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(done), f)


def main():
    print("=" * 60)
    print("GUIDE — Google Places Enricher")
    print("=" * 60)

    with open(INPUT_FILE, encoding="utf-8") as f:
        data = json.load(f)

    done = load_progress()
    processed = 0
    total_pois = sum(len(v) for v in data.values())

    for province, pois in data.items():
        for poi in pois:
            key = f"{province}::{poi['name']}"
            if key in done:
                continue

            result = search_place(poi["name"], poi["lat"], poi["lon"])
            if result:
                poi["google_place_id"] = result.get("id")
                poi["google_rating"] = result.get("rating")
                poi["google_reviews_total"] = result.get("userRatingCount")
                poi["google_photos_count"] = len(result.get("photos", []))
                poi["viewport_area_km2"] = viewport_area_km2(
                    result.get("viewport", {})
                )
            else:
                poi.update({
                    "google_place_id": None,
                    "google_rating": None,
                    "google_reviews_total": None,
                    "google_photos_count": None,
                    "viewport_area_km2": None,
                })

            done.add(key)
            processed += 1
            time.sleep(DELAY)

            if processed % SAVE_EVERY == 0:
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                save_progress(done)
                print(f"  💾 {processed}/{total_pois} işlendi")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    save_progress(done)

    print(f"\n✅ Tamamlandı: {processed} POI işlendi")
    print(f"💾 Kaydedildi: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
