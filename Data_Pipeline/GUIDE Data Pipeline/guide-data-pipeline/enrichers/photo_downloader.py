"""
GUIDE — Google Places Photo Downloader
========================================
Her POI için Google Places (New) API'den 3 fotoğraf indirir.
Hem URL'leri JSON'a yazar hem dosyaları diske kaydeder.

Girdi  : poi_enriched.json
Çıktı  : poi_with_photos.json + poi_photos/ klasörü
Tahmini maliyet: ~$69 (2,300 POI × 3 foto)
Tahmini süre  : 30–45 dakika

Kullanım:
    export GOOGLE_PLACES_API_KEY=[API_KEY]
    python photo_downloader.py
"""

import json
import os
import re
import time
import requests
from pathlib import Path

API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "[API_KEY]")
INPUT_FILE = "poi_enriched.json"
OUTPUT_FILE = "poi_with_photos.json"
PROGRESS_FILE = "photo_progress.json"
PHOTO_DIR = "poi_photos"
PHOTOS_PER_POI = 3
PHOTO_MAX_WIDTH = 800
SAVE_EVERY = 20
DELAY = 0.2
MAX_RETRIES = 3

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PHOTO_URL_TEMPLATE = (
    "https://places.googleapis.com/v1/{name}/media"
    "?maxWidthPx={width}&key={key}&skipHttpRedirect=true"
)


def sanitize(name: str) -> str:
    name = re.sub(r"[^\w\s\-]", "", name)
    name = re.sub(r"\s+", "_", name.strip())
    return name[:60]


def get_photo_names(place_id: str, poi_name: str, lat: float, lon: float) -> list[str]:
    """place_id varsa direkt, yoksa text search ile photo name'leri çeker."""
    if place_id:
        # place_id ile doğrudan getir
        url = f"https://places.googleapis.com/v1/places/{place_id}"
        headers = {
            "X-Goog-Api-Key": API_KEY,
            "X-Goog-FieldMask": "photos",
        }
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                return [p["name"] for p in resp.json().get("photos", [])[:PHOTOS_PER_POI]]
        except Exception:
            pass

    # Fallback: text search
    payload = {
        "textQuery": f"{poi_name}, Turkey",
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lon},
                "radius": 3000.0,
            }
        },
        "maxResultCount": 1,
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "places.photos",
    }
    try:
        resp = requests.post(TEXT_SEARCH_URL, json=payload, headers=headers, timeout=15)
        if resp.status_code == 200:
            places = resp.json().get("places", [])
            if places:
                return [p["name"] for p in places[0].get("photos", [])[:PHOTOS_PER_POI]]
    except Exception:
        pass
    return []


def download_photo(photo_name: str, save_path: Path) -> str | None:
    url = PHOTO_URL_TEMPLATE.format(
        name=photo_name, width=PHOTO_MAX_WIDTH, key=API_KEY
    )
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                photo_url = data.get("photoUri")
                if not photo_url:
                    return None
                # İndir
                img_resp = requests.get(photo_url, timeout=30)
                if img_resp.status_code == 200:
                    save_path.parent.mkdir(parents=True, exist_ok=True)
                    save_path.write_bytes(img_resp.content)
                    return str(save_path)
        except Exception as e:
            time.sleep(3 * (attempt + 1))
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
    print("GUIDE — Google Places Photo Downloader")
    print("=" * 60)

    with open(INPUT_FILE, encoding="utf-8") as f:
        data = json.load(f)

    done = load_progress()
    processed = 0
    total = sum(len(v) for v in data.values())

    for province, pois in data.items():
        prov_dir = Path(PHOTO_DIR) / sanitize(province)

        for poi in pois:
            key = f"{province}::{poi['name']}"
            if key in done:
                continue

            photo_names = get_photo_names(
                poi.get("google_place_id"),
                poi["name"],
                poi["lat"],
                poi["lon"],
            )
            time.sleep(DELAY)

            poi["photo_urls"] = []
            poi["photo_files"] = []

            for idx, photo_name in enumerate(photo_names, 1):
                filename = f"{sanitize(poi['name'])}_{idx}.jpg"
                save_path = prov_dir / filename
                local_path = download_photo(photo_name, save_path)
                if local_path:
                    poi["photo_files"].append(local_path)
                time.sleep(DELAY)

            poi["photo_count"] = len(poi["photo_files"])
            done.add(key)
            processed += 1

            if processed % SAVE_EVERY == 0:
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                save_progress(done)
                print(f"  💾 {processed}/{total} işlendi")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    save_progress(done)

    print(f"\n✅ Tamamlandı: {processed} POI işlendi")
    print(f"💾 Kaydedildi: {OUTPUT_FILE} + {PHOTO_DIR}/")


if __name__ == "__main__":
    main()
