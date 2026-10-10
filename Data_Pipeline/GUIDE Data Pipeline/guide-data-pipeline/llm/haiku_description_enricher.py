"""
GUIDE — Claude Haiku POI Description Enricher (TR + EN)
=========================================================
Wikipedia'da açıklaması bulunmayan veya yetersiz olan POI'ler için
Claude Haiku API ile Türkçe ve İngilizce açıklamalar üretir.

Model  : claude-haiku-4-5-20251001
Maliyet: ~$3-4 (2,300 POI için)
Süre   : ~20-30 dakika

Girdi  : poi_merged.json
Çıktı  : poi_enriched_descriptions.json

Kullanım:
    export ANTHROPIC_API_KEY=[API_KEY]
    python haiku_description_enricher.py
"""

import json
import os
import re
import time
import requests
from pathlib import Path

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "[API_KEY]")
MODEL = "claude-haiku-4-5-20251001"
INPUT_FILE = "poi_merged.json"
OUTPUT_FILE = "poi_enriched_descriptions.json"
PROGRESS_FILE = "haiku_enrich_progress.json"
SAVE_EVERY = 10
DELAY = 0.5
MAX_RETRIES = 3

# Açıklama kalite eşiği — bu kadar karakterden kısa olanlar yeniden üretilir
MIN_DESCRIPTION_LENGTH = 80

SYSTEM_PROMPT = """Sen bir Türkiye turizm uzmanısın. Sana verilen POI (Point of Interest) \
bilgilerine dayanarak hem Türkçe hem İngilizce olmak üzere 4-5 cümlelik turistik açıklamalar yazacaksın.

KURALLAR:
1. Her açıklama TAM OLARAK 4-5 cümle olmalı.
2. Turistik çekiciliği ön plana çıkar — ziyaretçiye hitap et.
3. POI'nin kategorisine uygun ton kullan:
   - Tarihi yerler: tarihsel bağlam + günümüz durumu
   - Doğa yerleri: manzara, aktiviteler, mevsimsel öneriler
   - Dini yapılar: mimari özellikler + kültürel önem
   - Müzeler: koleksiyon vurgusu + ziyaretçi deneyimi
4. Şehir ve bölge bağlamını kullan.
5. Mevcut açıklama varsa temel al ama iyileştir; yoksa sıfırdan yaz.
6. Wikipedia disambigulation ifadelerini ("Bu makale ...", "For other uses...") TEMİZLE.
7. Uydurma tarih veya bilgi EKLEME — emin olmadığın detayları atla.

ÇIKTI FORMATI (sadece JSON, başka hiçbir şey yazma):
{
  "description_tr": "Türkçe açıklama...",
  "description_en": "English description..."
}"""


def needs_enrichment(poi: dict) -> bool:
    """POI'nin açıklama üretimine ihtiyacı var mı?"""
    tr = (poi.get("description_tr") or "").strip()
    en = (poi.get("description_en") or "").strip()
    return len(tr) < MIN_DESCRIPTION_LENGTH or len(en) < MIN_DESCRIPTION_LENGTH


def build_user_prompt(poi: dict) -> str:
    existing_tr = (poi.get("description_tr") or "").strip()
    existing_en = (poi.get("description_en") or "").strip()

    return f"""Aşağıdaki POI için Türkçe ve İngilizce açıklamalar yaz:

İsim: {poi.get('name', 'Bilinmiyor')}
Şehir: {poi.get('city', 'Bilinmiyor')}
Kategori: {poi.get('category', '-')}
Alt Kategori: {poi.get('subcategory', '-')}
Koordinat: {poi.get('lat', '-')}, {poi.get('lon', '-')}
Mevcut TR Açıklama: {existing_tr if existing_tr else 'YOK'}
Mevcut EN Açıklama: {existing_en if existing_en else 'YOK'}

Sadece JSON formatında yanıt ver."""


def call_haiku(poi: dict) -> dict | None:
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
    }
    body = {
        "model": MODEL,
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": build_user_prompt(poi)}],
    }

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=body,
                timeout=60,
            )
            if resp.status_code == 429:
                wait = (attempt + 1) * 10
                print(f"  ⏳ Rate limit, {wait}s bekleniyor...")
                time.sleep(wait)
                continue
            if resp.status_code != 200:
                print(f"  ⚠ HTTP {resp.status_code}: {resp.text[:80]}")
                time.sleep(3)
                continue

            text = resp.json()["content"][0]["text"].strip()
            # JSON parse
            text = re.sub(r"^```json\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            return json.loads(text)

        except json.JSONDecodeError:
            print(f"  ⚠ JSON parse hatası, atlanıyor")
            return None
        except Exception as e:
            print(f"  ⚠ Hata: {e}")
            time.sleep(3)
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
    print("GUIDE — Claude Haiku Description Enricher (TR + EN)")
    print("=" * 60)

    if API_KEY == "[API_KEY]":
        print("❌ ANTHROPIC_API_KEY ayarlanmamış!")
        return

    with open(INPUT_FILE, encoding="utf-8") as f:
        data = json.load(f)

    done = load_progress()
    total = sum(len(v) for v in data.values())
    needs = sum(1 for pois in data.values() for p in pois if needs_enrichment(p))

    print(f"Toplam POI: {total}")
    print(f"Açıklama üretilecek: {needs}")
    print()

    processed = enriched = skipped = failed = 0

    for province, pois in data.items():
        for poi in pois:
            key = f"{province}::{poi['name']}"
            if key in done:
                skipped += 1
                continue

            if not needs_enrichment(poi):
                done.add(key)
                skipped += 1
                continue

            result = call_haiku(poi)
            if result:
                if result.get("description_tr"):
                    poi["description_tr"] = result["description_tr"]
                if result.get("description_en"):
                    poi["description_en"] = result["description_en"]
                enriched += 1
                print(f"  ✅ {poi['name']} ({province})")
            else:
                failed += 1
                print(f"  ❌ {poi['name']} ({province})")

            done.add(key)
            processed += 1
            time.sleep(DELAY)

            if processed % SAVE_EVERY == 0:
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                save_progress(done)
                print(f"  💾 {processed}/{needs} işlendi")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    save_progress(done)

    print(f"\n{'='*60}")
    print(f"✅ Üretilen: {enriched}  ❌ Başarısız: {failed}  ⏭ Atlanan: {skipped}")
    print(f"💾 Kaydedildi: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
