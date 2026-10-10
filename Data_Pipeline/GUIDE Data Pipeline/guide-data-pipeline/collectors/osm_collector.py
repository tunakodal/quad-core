"""
GUIDE — OSM / Overpass API POI Collector
=========================================
Türkiye'nin tamamındaki turistik, tarihi ve doğal POI'leri
OpenStreetMap Overpass API üzerinden çeker.

Çıktı: poi_raw_osm.json
Tahmini süre: 3–8 dakika
Maliyet: Ücretsiz

Kullanım:
    python osm_collector.py
"""

import requests
import json
import time
from datetime import datetime
from pathlib import Path

OVERPASS_URL = "http://overpass-api.de/api/interpreter"
OUTPUT_FILE = "poi_raw_osm.json"

# Türkiye ili → admin_level=4 relation
TURKEY_PROVINCES = [
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya",
    "Artvin", "Aydın", "Balıkesir", "Bilecik", "Bingöl", "Bitlis", "Bolu",
    "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır",
    "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun",
    "Gümüşhane", "Hakkari", "Hatay", "Isparta", "Mersin", "İstanbul", "İzmir",
    "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir", "Kocaeli", "Konya",
    "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla", "Muş",
    "Nevşehir", "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop",
    "Sivas", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Şanlıurfa", "Uşak",
    "Van", "Yozgat", "Zonguldak", "Aksaray", "Bayburt", "Karaman", "Kırıkkale",
    "Batman", "Şırnak", "Bartın", "Ardahan", "Iğdır", "Yalova", "Karabük",
    "Kilis", "Osmaniye", "Düzce"
]

TOURISM_TAGS = [
    "attraction", "museum", "gallery", "viewpoint", "artwork",
    "theme_park", "zoo", "aquarium"
]

HISTORIC_TAGS = [
    "castle", "monument", "archaeological_site", "ruins",
    "memorial", "fort", "battlefield", "city_gate", "tower"
]

NATURAL_TAGS = [
    "peak", "cave_entrance", "hot_spring", "geyser", "waterfall"
]


def build_overpass_query(province: str) -> str:
    tourism_nodes = "\n".join(
        f'  node["tourism"="{t}"](area.searchArea);' for t in TOURISM_TAGS
    )
    tourism_ways = "\n".join(
        f'  way["tourism"="{t}"](area.searchArea);' for t in TOURISM_TAGS
    )
    historic_nodes = "\n".join(
        f'  node["historic"="{t}"](area.searchArea);' for t in HISTORIC_TAGS
    )
    historic_ways = "\n".join(
        f'  way["historic"="{t}"](area.searchArea);' for t in HISTORIC_TAGS
    )
    natural_nodes = "\n".join(
        f'  node["natural"="{t}"](area.searchArea);' for t in NATURAL_TAGS
    )

    return f"""
[out:json][timeout:120];
area["name"="{province}"]["admin_level"="4"]->.searchArea;
(
{tourism_nodes}
{tourism_ways}
{historic_nodes}
{historic_ways}
{natural_nodes}
);
out body center;
"""


def determine_category(tags: dict) -> tuple[str, str]:
    tourism = tags.get("tourism", "")
    historic = tags.get("historic", "")
    natural = tags.get("natural", "")

    category_map = {
        "museum": ("cultural", "museum"),
        "gallery": ("cultural", "gallery"),
        "attraction": ("cultural", "attraction"),
        "viewpoint": ("natural", "viewpoint"),
        "artwork": ("cultural", "artwork"),
        "theme_park": ("entertainment", "theme_park"),
        "zoo": ("entertainment", "zoo"),
        "aquarium": ("entertainment", "aquarium"),
    }

    historic_map = {
        "castle": ("historical", "castle"),
        "monument": ("historical", "monument"),
        "archaeological_site": ("historical", "archaeological_site"),
        "ruins": ("historical", "ruins"),
        "memorial": ("historical", "memorial"),
        "fort": ("historical", "fort"),
        "battlefield": ("historical", "battlefield"),
        "city_gate": ("historical", "city_gate"),
        "tower": ("historical", "tower"),
    }

    natural_map = {
        "peak": ("natural", "peak"),
        "cave_entrance": ("natural", "cave"),
        "hot_spring": ("natural", "hot_spring"),
        "geyser": ("natural", "geyser"),
        "waterfall": ("natural", "waterfall"),
    }

    if tourism in category_map:
        return category_map[tourism]
    if historic in historic_map:
        return historic_map[historic]
    if natural in natural_map:
        return natural_map[natural]
    return ("other", "other")


def parse_element(element: dict, province: str) -> dict | None:
    tags = element.get("tags", {})
    name = tags.get("name") or tags.get("name:tr") or tags.get("name:en")
    if not name:
        return None

    # Coordinates
    if element["type"] == "node":
        lat, lon = element.get("lat"), element.get("lon")
    else:
        center = element.get("center", {})
        lat, lon = center.get("lat"), center.get("lon")

    if lat is None or lon is None:
        return None

    category, subcategory = determine_category(tags)

    return {
        "name": name,
        "city": province,
        "lat": round(lat, 6),
        "lon": round(lon, 6),
        "category": category,
        "subcategory": subcategory,
        "osm_id": element.get("id"),
        "wikipedia": tags.get("wikipedia"),
        "wikidata": tags.get("wikidata"),
        "source": "osm",
    }


def collect_province(province: str, session: requests.Session) -> list[dict]:
    query = build_overpass_query(province)
    for attempt in range(3):
        try:
            resp = session.post(
                OVERPASS_URL,
                data={"data": query},
                timeout=150
            )
            resp.raise_for_status()
            elements = resp.json().get("elements", [])
            pois = []
            seen_names = set()
            for el in elements:
                poi = parse_element(el, province)
                if poi and poi["name"] not in seen_names:
                    pois.append(poi)
                    seen_names.add(poi["name"])
            return pois
        except Exception as e:
            print(f"  ⚠ Attempt {attempt+1}/3 failed for {province}: {e}")
            time.sleep(5 * (attempt + 1))
    return []


def main():
    print("=" * 60)
    print("GUIDE — OSM POI Collector")
    print("=" * 60)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "GUIDE-TravelApp/1.0 (TOBB ETU Graduation Project)"
    })

    all_pois: dict[str, list] = {}
    total = 0

    for i, province in enumerate(TURKEY_PROVINCES, 1):
        print(f"[{i:2d}/{len(TURKEY_PROVINCES)}] {province}...", end=" ", flush=True)
        pois = collect_province(province, session)
        all_pois[province] = pois
        total += len(pois)
        print(f"{len(pois)} POI")
        time.sleep(1.2)  # Overpass rate limit

    print(f"\n✅ Toplam: {total} POI, {len(all_pois)} il")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_pois, f, ensure_ascii=False, indent=2)

    print(f"💾 Kaydedildi: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
