"""
GUIDE — Multi-Source POI Collector & Merger
=============================================
OSM, Wikipedia ve Wikidata kaynaklarını birleştirir,
duplicate'leri temizler, il bazında JSON üretir.

Girdi  : poi_raw_osm.json, poi_raw_wiki.json
Çıktı  : poi_merged.json
Maliyet: Ücretsiz

Kullanım:
    python multi_source_poi_collector.py
"""

import json
import math
import re
import time
import requests
from pathlib import Path

OSM_FILE = "poi_raw_osm.json"
WIKI_FILE = "poi_raw_wiki.json"
OUTPUT_FILE = "poi_merged.json"

# İl sınır kutuları (bounding boxes) — il tespiti için
PROVINCE_BBOXES = {
    "İstanbul":       (40.80, 27.98, 41.53, 29.95),
    "Ankara":         (39.35, 31.38, 40.68, 33.67),
    "İzmir":          (37.55, 26.17, 38.97, 28.25),
    "Antalya":        (36.07, 29.02, 37.60, 32.55),
    "Nevşehir":       (38.36, 34.35, 39.07, 35.52),
    "Bursa":          (39.55, 28.31, 40.45, 30.13),
    "Konya":          (36.68, 31.58, 38.81, 34.14),
    "Trabzon":        (40.62, 39.41, 41.24, 40.49),
    "Kayseri":        (38.13, 35.10, 39.24, 36.82),
    "Gaziantep":      (36.63, 36.67, 37.43, 37.73),
    "Adana":          (36.55, 34.99, 38.15, 36.63),
    "Diyarbakır":     (37.46, 39.32, 38.52, 41.29),
    "Şanlıurfa":      (36.71, 37.51, 38.13, 40.00),
    "Muğla":          (36.44, 27.53, 37.77, 29.75),
    "Mardin":         (36.98, 40.37, 37.81, 42.25),
    "Van":            (37.73, 42.48, 38.86, 44.76),
    "Erzurum":        (39.49, 40.49, 40.75, 42.84),
    "Sakarya":        (40.37, 29.83, 41.04, 30.98),
    "Denizli":        (37.20, 28.47, 38.42, 30.00),
    "Hatay":          (35.82, 35.77, 37.06, 36.74),
}

TURKEY_BBOX = (35.8, 26.0, 42.1, 45.0)

DUPLICATE_DISTANCE_M = 150  # Bu mesafeden yakın iki POI → aynı yer


def haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def assign_province(lat: float, lon: float) -> str:
    for province, (min_lat, min_lon, max_lat, max_lon) in PROVINCE_BBOXES.items():
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            return province
    return "Diğer"


def in_turkey(lat, lon) -> bool:
    min_lat, min_lon, max_lat, max_lon = TURKEY_BBOX
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon


def normalize_name(name: str) -> str:
    name = name.lower().strip()
    for a, b in [("ğ", "g"), ("ü", "u"), ("ş", "s"), ("ı", "i"), ("ö", "o"), ("ç", "c")]:
        name = name.replace(a, b)
    return re.sub(r"[^a-z0-9]", "", name)


def remove_duplicates(pois: list[dict]) -> list[dict]:
    """Aynı isim veya 150m içindeki POI'leri çıkarır."""
    kept = []
    for poi in pois:
        duplicate = False
        for existing in kept:
            # İsim benzerliği
            if normalize_name(poi["name"]) == normalize_name(existing["name"]):
                duplicate = True
                break
            # Mesafe kontrolü
            dist = haversine(poi["lat"], poi["lon"], existing["lat"], existing["lon"])
            if dist < DUPLICATE_DISTANCE_M:
                duplicate = True
                break
        if not duplicate:
            kept.append(poi)
    return kept


def enrich_with_wikipedia_descriptions(pois: list[dict]) -> list[dict]:
    """wikipedia alanı varsa TR ve EN açıklamaları çeker."""
    session = requests.Session()
    session.headers.update({"User-Agent": "GUIDE-TravelApp/1.0"})

    for i, poi in enumerate(pois):
        if not poi.get("wikipedia"):
            continue
        if poi.get("description_tr") and poi.get("description_en"):
            continue

        wiki_ref = poi["wikipedia"]
        lang = "tr" if ":" not in wiki_ref else wiki_ref.split(":")[0]
        title = wiki_ref.split(":")[-1] if ":" in wiki_ref else wiki_ref

        for fetch_lang in ["tr", "en"]:
            desc_key = f"description_{fetch_lang}"
            if poi.get(desc_key):
                continue
            try:
                resp = session.get(
                    f"https://{fetch_lang}.wikipedia.org/w/api.php",
                    params={
                        "action": "query", "titles": title,
                        "prop": "extracts", "exintro": True,
                        "explaintext": True, "exsentences": 4,
                        "format": "json", "redirects": 1,
                    },
                    timeout=15,
                )
                pages = resp.json().get("query", {}).get("pages", {})
                page = next(iter(pages.values()))
                extract = page.get("extract", "").strip()
                if extract:
                    poi[desc_key] = extract[:600]
            except Exception:
                pass
            time.sleep(0.3)

        if (i + 1) % 50 == 0:
            print(f"  Wikipedia enrichment: {i+1}/{len(pois)}")

    return pois


def main():
    print("=" * 60)
    print("GUIDE — Multi-Source POI Merger")
    print("=" * 60)

    # OSM verisi yükle
    with open(OSM_FILE, encoding="utf-8") as f:
        osm_data = json.load(f)

    # Düzleştir
    all_pois = []
    if isinstance(osm_data, dict):
        for province_pois in osm_data.values():
            all_pois.extend(province_pois)
    else:
        all_pois = osm_data

    print(f"OSM: {len(all_pois)} POI yüklendi")

    # Wikipedia verisi ekle
    if Path(WIKI_FILE).exists():
        with open(WIKI_FILE, encoding="utf-8") as f:
            wiki_pois = json.load(f)
        # Koordinat filtreleme (Türkiye sınırı)
        wiki_pois = [p for p in wiki_pois if in_turkey(p["lat"], p["lon"])]
        all_pois.extend(wiki_pois)
        print(f"Wikipedia: {len(wiki_pois)} POI eklendi")

    # İl ata
    print("İl ataması yapılıyor...")
    for poi in all_pois:
        if not poi.get("city"):
            poi["city"] = assign_province(poi["lat"], poi["lon"])

    # Duplicate temizle
    print("Duplicate temizleniyor...")
    before = len(all_pois)
    all_pois = remove_duplicates(all_pois)
    print(f"Duplicate kaldırıldı: {before - len(all_pois)}")

    # Wikipedia açıklamaları çek
    print("Wikipedia açıklamaları çekiliyor...")
    all_pois = enrich_with_wikipedia_descriptions(all_pois)

    # İl bazında grupla
    by_province: dict[str, list] = {}
    for poi in all_pois:
        province = poi.get("city", "Diğer")
        by_province.setdefault(province, []).append(poi)

    # Kaydet
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(by_province, f, ensure_ascii=False, indent=2)

    total = sum(len(v) for v in by_province.values())
    print(f"\n✅ Toplam: {total} POI, {len(by_province)} il")
    print(f"💾 Kaydedildi: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
