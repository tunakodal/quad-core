"""
GUIDE — Google Cloud TTS (Almanca)
=====================================
Sadece description_de alanını seslendirir.
TR ve EN zaten tts_google.py ile yapıldı.

Girdi  : poi_with_audio.json
Çıktı  : poi_complete.json + poi_audio/**_de.mp3
Tahmini maliyet: ~$8-10
Tahmini süre  : 30–40 dakika

Kullanım:
    export GOOGLE_TTS_API_KEY=[API_KEY]
    python tts_german.py
"""

import json
import os
import re
import time
import base64
import requests
from pathlib import Path

API_KEY = os.environ.get("GOOGLE_TTS_API_KEY", "[API_KEY]")
INPUT_FILE = "poi_with_audio.json"
OUTPUT_FILE = "poi_complete.json"
PROGRESS_FILE = "tts_de_progress.json"
AUDIO_DIR = "poi_audio"
SAVE_EVERY = 20
DELAY = 0.15
MAX_RETRIES = 3

TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"

DE_VOICE = {
    "languageCode": "de-DE",
    "name": "de-DE-Neural2-F",   # Kadın, Neural2 (en doğal Almanca)
    "ssmlGender": "FEMALE",
    # Alternatifler: de-DE-Neural2-A, de-DE-Neural2-B (erkek), de-DE-Neural2-C
}

AUDIO_CONFIG = {
    "audioEncoding": "MP3",
    "sampleRateHertz": 24000,
    "speakingRate": 0.95,
    "pitch": 0.0,
}


def sanitize(name: str) -> str:
    name = re.sub(r"[^\w\s\-]", "", name)
    name = re.sub(r"\s+", "_", name.strip())
    return name[:60]


def synthesize_de(text: str, save_path: Path) -> bool:
    if not text or not text.strip():
        return False

    payload = {
        "input": {"text": text[:4500]},
        "voice": DE_VOICE,
        "audioConfig": AUDIO_CONFIG,
    }

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(
                TTS_URL,
                json=payload,
                params={"key": API_KEY},
                timeout=30,
            )
            if resp.status_code == 200:
                audio_b64 = resp.json().get("audioContent", "")
                if audio_b64:
                    save_path.parent.mkdir(parents=True, exist_ok=True)
                    save_path.write_bytes(base64.b64decode(audio_b64))
                    return True
            elif resp.status_code == 429:
                time.sleep(10 * (attempt + 1))
            else:
                print(f"  ⚠ TTS error {resp.status_code}: {resp.text[:100]}")
                return False
        except Exception as e:
            print(f"  ⚠ Exception: {e}")
            time.sleep(5)
    return False


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
    print("GUIDE — Google Cloud TTS (DE)")
    print("=" * 60)

    with open(INPUT_FILE, encoding="utf-8") as f:
        data = json.load(f)

    done = load_progress()
    processed = 0
    total = sum(len(v) for v in data.values())

    for province, pois in data.items():
        prov_dir = Path(AUDIO_DIR) / sanitize(province)

        for poi in pois:
            key = f"{province}::{poi['name']}::de"
            if key in done:
                continue

            text = poi.get("description_de", "")
            if not text:
                done.add(key)
                continue

            filename = f"{sanitize(poi['name'])}_de.mp3"
            save_path = prov_dir / filename

            ok = synthesize_de(text, save_path)
            if ok:
                poi["audio_de"] = str(save_path)

            done.add(key)
            processed += 1
            time.sleep(DELAY)

            if processed % SAVE_EVERY == 0:
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                save_progress(done)
                print(f"  💾 {processed}/{total} POI işlendi")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    save_progress(done)

    print(f"\n✅ Tamamlandı: {processed} POI işlendi")
    print(f"💾 Kaydedildi: {OUTPUT_FILE} + {AUDIO_DIR}/**_de.mp3")


if __name__ == "__main__":
    main()
