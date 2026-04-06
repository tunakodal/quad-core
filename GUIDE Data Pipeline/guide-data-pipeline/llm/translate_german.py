"""
GUIDE — Claude Haiku Almanca Çeviri Scripti
=============================================
Her POI'nin İngilizce açıklamasını (description_en) Claude Haiku ile
Almancaya çevirir ve description_de alanını doldurur.

Model  : claude-haiku-4-5-20251001
Maliyet: ~$2-3 (2,300 POI için)
Süre   : ~20-30 dakika

Girdi  : poi_enriched_descriptions.json
Çıktı  : poi_with_german.json

Kullanım:
    export ANTHROPIC_API_KEY=[API_KEY]
    python translate_german.py
"""

import json
import os
import time
import requests
from pathlib import Path

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "[API_KEY]")
MODEL = "claude-haiku-4-5-20251001"
INPUT_FILE = "poi_enriched_descriptions.json"
OUTPUT_FILE = "poi_with_german.json"
PROGRESS_FILE = "german_translation_progress.json"
SAVE_EVERY = 10
DELAY = 0.5
MAX_RETRIES = 3

SYSTEM_PROMPT = """Du bist ein professioneller Übersetzer für Tourismustexte.
Übersetze den folgenden englischen Text ins Deutsche.

REGELN:
1. Behalte den touristischen, einladenden Ton bei.
2. Behalte Eigennamen (Ortsnamen, historische Namen) im Original.
3. Übersetze natürlich und flüssig — kein wörtliches Maschinenübersetzungs-Deutsch.
4. Behalte die gleiche Länge (4-5 Sätze).
5. Antworte NUR mit der deutschen Übersetzung, nichts anderes — kein Präfix, kein Kommentar."""


def needs_german(poi: dict) -> bool:
    existing = (poi.get("description_de") or "").strip()
    source = (poi.get("description_en") or "").strip()
    return len(existing) < 50 and len(source) > 50


def call_haiku_translate(en_text: str, poi_name: str, city: str) -> str | None:
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
    }
    body = {
        "model": MODEL,
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": (
                    f"Übersetze diese Beschreibung von {poi_name} "
                    f"({city}, Türkei) ins Deutsche:\n\n{en_text}"
                ),
            }
        ],
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

            return resp.json()["content"][0]["text"].strip()

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
    print("GUIDE — Claude Haiku Almanca Çeviri (EN → DE)")
    print("=" * 60)

    if API_KEY == "[API_KEY]":
        print("❌ ANTHROPIC_API_KEY ayarlanmamış!")
        return

    with open(INPUT_FILE, encoding="utf-8") as f:
        data = json.load(f)

    done = load_progress()
    needs = sum(1 for pois in data.values() for p in pois if needs_german(p))
    total = sum(len(v) for v in data.values())

    print(f"Toplam POI      : {total}")
    print(f"Çevrilecek POI  : {needs}")
    print()

    translated = failed = skipped = processed = 0

    for province, pois in data.items():
        for poi in pois:
            key = f"{province}::{poi['name']}"
            if key in done:
                skipped += 1
                continue

            if not needs_german(poi):
                done.add(key)
                skipped += 1
                continue

            en_text = (poi.get("description_en") or "").strip()
            result = call_haiku_translate(en_text, poi["name"], province)

            if result:
                poi["description_de"] = result
                translated += 1
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
    print(f"✅ Çevrilen: {translated}  ❌ Başarısız: {failed}  ⏭ Atlanan: {skipped}")
    print(f"💾 Kaydedildi: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
