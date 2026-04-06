"""
GUIDE — Wikipedia Category POI Collector
==========================================
Wikipedia category ağacını gezerek OSM'de eksik kalan
POI'leri (müze, kale, arkeolojik sit vb.) toplar.
Her POI için koordinat ve kısa açıklama çeker.

Çıktı: poi_raw_wiki.json
Maliyet: Ücretsiz
Hız: 0.3s gecikme / istek

Kullanım:
    python wikipedia_collector.py
"""

import requests
import json
import time
from pathlib import Path

OUTPUT_FILE = "poi_raw_wiki.json"

# Taranacak Wikipedia kategorileri
CATEGORIES_TR = [
    "Türkiye'deki müzeler",
    "Türkiye'deki kaleler",
    "Türkiye'deki arkeolojik alanlar",
    "Türkiye'deki anıtlar",
    "UNESCO Dünya Mirası alanları (Türkiye)",
    "Türkiye'deki millî parklar",
    "Türkiye'deki höyükler",
    "Türkiye'deki mağaralar",
]

CATEGORIES_EN = [
    "Museums in Turkey",
    "Castles in Turkey",
    "Archaeological sites in Turkey",
    "World Heritage Sites in Turkey",
    "Historic sites in Turkey",
    "Ruins in Turkey",
    "Monuments in Turkey",
    "Mosques in Turkey",
    "National parks of Turkey",
]


class WikipediaPOICollector:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "GUIDE-TravelApp/1.0 (TOBB ETU Graduation Project)"
        })

    def fetch_category_members(self, category: str, lang: str = "tr") -> list[str]:
        url = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Kategori:{category}" if lang == "tr" else f"Category:{category}",
            "cmlimit": 500,
            "format": "json",
            "cmtype": "page",
        }
        members = []
        while True:
            try:
                resp = self.session.get(url, params=params, timeout=20)
                data = resp.json()
                batch = data.get("query", {}).get("categorymembers", [])
                members.extend(m["title"] for m in batch)
                if "continue" not in data:
                    break
                params["cmcontinue"] = data["continue"]["cmcontinue"]
                time.sleep(0.3)
            except Exception as e:
                print(f"    ⚠ Category fetch error ({category}): {e}")
                break
        return members

    def fetch_page_coords_and_desc(self, title: str, lang: str = "tr") -> dict | None:
        url = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "titles": title,
            "prop": "coordinates|extracts",
            "exintro": True,
            "explaintext": True,
            "exsentences": 3,
            "format": "json",
            "redirects": 1,
        }
        try:
            resp = self.session.get(url, params=params, timeout=20)
            data = resp.json()
            pages = data.get("query", {}).get("pages", {})
            page = next(iter(pages.values()))

            coords = page.get("coordinates", [])
            if not coords:
                return None

            return {
                "name": page.get("title", title),
                "lat": round(coords[0]["lat"], 6),
                "lon": round(coords[0]["lon"], 6),
                "description_tr" if lang == "tr" else "description_en":
                    page.get("extract", "")[:500],
                "wikipedia": f"{lang}:{page.get('title', title)}",
                "source": "wikipedia",
                "category": "historical",
                "subcategory": "attraction",
            }
        except Exception as e:
            print(f"    ⚠ Page fetch error ({title}): {e}")
            return None

    def collect(self) -> list[dict]:
        pois = []
        seen = set()

        for cat in CATEGORIES_TR:
            print(f"  📂 TR: {cat}")
            members = self.fetch_category_members(cat, lang="tr")
            print(f"     {len(members)} sayfa bulundu")
            for title in members:
                if title in seen:
                    continue
                seen.add(title)
                poi = self.fetch_page_coords_and_desc(title, lang="tr")
                if poi:
                    pois.append(poi)
                time.sleep(0.3)

        for cat in CATEGORIES_EN:
            print(f"  📂 EN: {cat}")
            members = self.fetch_category_members(cat, lang="en")
            print(f"     {len(members)} sayfa bulundu")
            for title in members:
                if title in seen:
                    continue
                seen.add(title)
                poi = self.fetch_page_coords_and_desc(title, lang="en")
                if poi:
                    pois.append(poi)
                time.sleep(0.3)

        return pois


def main():
    print("=" * 60)
    print("GUIDE — Wikipedia POI Collector")
    print("=" * 60)

    collector = WikipediaPOICollector()
    pois = collector.collect()

    print(f"\n✅ Toplam: {len(pois)} Wikipedia POI")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(pois, f, ensure_ascii=False, indent=2)

    print(f"💾 Kaydedildi: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
