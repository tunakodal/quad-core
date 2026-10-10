"""
GUIDE — Supabase REST API Bulk Insert
======================================
poi_final.json içeriğini Supabase'e HTTPS (port 443) üzerinden yükler.
psql / port bloklama sorunu olmaz.

Yükleme sırası:
    1. cities
    2. pois
    3. poi_contents  (TR, EN, DE açıklamalar)
    4. media_assets  (fotoğraf + ses URL'leri)

Girdi  : poi_final.json (upload_to_s3.py çıktısı)
Maliyet: Ücretsiz (Supabase REST API)

Kullanım:
    pip install requests
    export SUPABASE_URL=https://[YOUR_PROJECT_REF].supabase.co
    export SUPABASE_KEY=[YOUR_SERVICE_ROLE_KEY]
    python insert_to_supabase.py

Supabase API bilgileri:
    Project Settings → API → Project URL
    Project Settings → API → service_role (secret key)
"""

import ast
import json
import math
import os
import re
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ── CONFIG ────────────────────────────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "[YOUR_SUPABASE_URL]")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "[YOUR_SERVICE_ROLE_KEY]")
INPUT_FILE   = "poi_final.json"
BATCH_SIZE   = 50      # her seferinde kaç satır gönderilsin
DELAY        = 0.3     # saniye (rate limit koruması)
# ─────────────────────────────────────────────────────────────────────────────

HEADERS = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "return=minimal",
}

# Retry: 429 / 5xx hatalarında otomatik tekrar
session = requests.Session()
retries = Retry(
    total=5,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504]
)
session.mount("https://", HTTPAdapter(max_retries=retries))


# ── YARDIMCI FONKSİYONLAR ─────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = text.lower().strip()
    for a, b in [("ğ","g"),("ü","u"),("ş","s"),("ı","i"),("ö","o"),("ç","c"),
                 ("â","a"),("î","i"),("û","u")]:
        text = text.replace(a, b)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")[:80]


def clean(v):
    """None ve NaN değerlerini None'a çevirir."""
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def clean_float(v) -> float | None:
    v = clean(v)
    if v is None:
        return None
    try:
        return round(float(v), 4)
    except Exception:
        return None


def clean_int(v) -> int | None:
    v = clean(v)
    if v is None:
        return None
    try:
        return int(v)
    except Exception:
        return None


def parse_categories(raw) -> list[str]:
    """categories alanını list'e çevirir, geçersiz değerleri 'Other' yapar."""
    if not raw:
        return []
    if isinstance(raw, list):
        cats = raw
    elif isinstance(raw, str):
        try:
            cats = ast.literal_eval(raw)
        except Exception:
            cats = [raw]
    else:
        cats = []
    return [str(c).strip() for c in cats if c]


def post_batch(table: str, rows: list) -> bool:
    """Batch insert yapar. Başarısızsa False döner."""
    if not rows:
        return True
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    resp = session.post(url, headers=HEADERS, json=rows, timeout=30)
    if resp.status_code not in (200, 201):
        print(f"\n  ❌ [{table}] HTTP {resp.status_code}: {resp.text[:300]}")
        return False
    return True


def insert_all(table: str, rows: list, label: str):
    """rows listesini BATCH_SIZE'lık parçalara bölerek insert eder."""
    total = len(rows)
    inserted = 0
    failed = 0

    for i in range(0, total, BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        ok = post_batch(table, batch)
        if ok:
            inserted += len(batch)
        else:
            failed += len(batch)
        pct = (i + len(batch)) / total * 100
        print(f"\r  {label}: {i+len(batch)}/{total} ({pct:.0f}%)  ✅{inserted} ❌{failed}", end="")
        time.sleep(DELAY)

    print()  # satır sonu
    return inserted, failed


# ── VERİ HAZIRLIĞI ────────────────────────────────────────────────────────────

def build_rows(data: dict):
    """JSON verisinden tablo satırlarını üretir."""
    city_rows    = []
    poi_rows     = []
    content_rows = []
    media_rows   = []

    city_id_map:  dict[str, str] = {}
    poi_id_count: dict[str, int] = {}

    # cities
    for province, pois in sorted(data.items()):
        if not pois:
            continue
        city_id = slugify(province)
        city_id_map[province] = city_id

        lats = [p["lat"] for p in pois if p.get("lat")]
        lons = [p["lon"] for p in pois if p.get("lon")]

        city_rows.append({
            "city_id": city_id,
            "name":    province,
            "country": "TR",
            "lat":     round(sum(lats) / len(lats), 4) if lats else None,
            "lon":     round(sum(lons) / len(lons), 4) if lons else None,
        })

    # pois + contents + media
    for province, pois in data.items():
        city_id = city_id_map.get(province, slugify(province))

        for poi in pois:
            # poi_id üret
            base = f"{city_id}-{slugify(poi['name'])}"
            n = poi_id_count.get(base, 0)
            poi_id_count[base] = n + 1
            poi_id = base if n == 0 else f"{base}-{n}"

            # poi satırı
            poi_rows.append({
                "poi_id":               poi_id,
                "city_id":              city_id,
                "name":                 poi.get("name"),
                "category":             clean(poi.get("category")),
                "sub_categories":       parse_categories(poi.get("sub_categories") or poi.get("categories")),
                "lat":                  clean_float(poi.get("lat")),
                "lon":                  clean_float(poi.get("lon")),
                "osm_id":               clean_int(poi.get("osm_id")),
                "wikipedia":            clean(poi.get("wikipedia")),
                "wikidata":             clean(poi.get("wikidata")),
                "google_place_id":      clean(poi.get("google_place_id")),
                "google_rating":        clean_float(poi.get("google_rating")),
                "google_reviews_total": clean_int(poi.get("google_reviews_total")),
                "google_photos_count":  clean_int(poi.get("google_photos_count")),
                "viewport_area_km2":    clean_float(poi.get("viewport_area_km2")),
                "max_days":             clean_int(poi.get("max_days")) or 1,
            })

            # poi_contents (TR, EN, DE)
            for lang, fields in [
                ("TR", ["description_tr", "medium_description_tr"]),
                ("EN", ["description_en", "medium_description_en"]),
                ("DE", ["description_de", "medium_description_de"]),
            ]:
                text = ""
                for f in fields:
                    text = (poi.get(f) or "").strip()
                    if text:
                        break
                if text:
                    content_rows.append({
                        "content_id": f"{poi_id}-{lang.lower()}",
                        "poi_id":     poi_id,
                        "language":   lang,
                        "description": text[:1000],
                    })

            # media_assets — fotoğraflar
            for idx, url in enumerate(poi.get("photo_urls") or [], 1):
                if url:
                    media_rows.append({
                        "asset_id":   f"{poi_id}-img-{idx}",
                        "poi_id":     poi_id,
                        "url":        url,
                        "media_type": "image",
                        "language":   None,
                        "sort_order": idx,
                    })

            # media_assets — sesler
            for lang, field in [("TR", "audio_tr"), ("EN", "audio_en"), ("DE", "audio_de")]:
                path = (poi.get(field) or "").strip()
                if path:
                    media_rows.append({
                        "asset_id":   f"{poi_id}-audio-{lang.lower()}",
                        "poi_id":     poi_id,
                        "url":        path,
                        "media_type": "audio",
                        "language":   lang,
                        "sort_order": 1,
                    })

    return city_rows, poi_rows, content_rows, media_rows


# ── ANA FONKSİYON ─────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("GUIDE — Supabase REST API Bulk Insert")
    print("=" * 60)

    if "[YOUR_" in SUPABASE_URL or "[YOUR_" in SUPABASE_KEY:
        print("❌ SUPABASE_URL ve SUPABASE_KEY ortam değişkenlerini ayarla!")
        print("   export SUPABASE_URL=https://xxxx.supabase.co")
        print("   export SUPABASE_KEY=eyJ...")
        return

    # Bağlantı testi
    print("🔗 Bağlantı test ediliyor...")
    try:
        resp = session.get(
            f"{SUPABASE_URL}/rest/v1/cities?limit=1",
            headers=HEADERS,
            timeout=10
        )
        if resp.status_code == 200:
            print("✅ Bağlantı başarılı\n")
        else:
            print(f"⚠ HTTP {resp.status_code}: {resp.text[:100]}")
            print("Devam ediliyor...\n")
    except Exception as e:
        print(f"❌ Bağlantı hatası: {e}")
        return

    # Veri yükle
    print(f"📂 Yükleniyor: {INPUT_FILE}")
    with open(INPUT_FILE, encoding="utf-8") as f:
        data = json.load(f)

    total_pois = sum(len(v) for v in data.values())
    print(f"   {total_pois:,} POI, {len(data)} il\n")

    # Satırları hazırla
    print("⚙️  Satırlar hazırlanıyor...")
    city_rows, poi_rows, content_rows, media_rows = build_rows(data)
    print(f"   cities      : {len(city_rows):,}")
    print(f"   pois        : {len(poi_rows):,}")
    print(f"   poi_contents: {len(content_rows):,}")
    print(f"   media_assets: {len(media_rows):,}")
    print()

    # Insert
    results = {}

    print("📤 cities yükleniyor...")
    ok, fail = insert_all("cities", city_rows, "cities")
    results["cities"] = {"ok": ok, "fail": fail}

    print("📤 pois yükleniyor...")
    ok, fail = insert_all("pois", poi_rows, "pois")
    results["pois"] = {"ok": ok, "fail": fail}

    print("📤 poi_contents yükleniyor...")
    ok, fail = insert_all("poi_contents", content_rows, "poi_contents")
    results["poi_contents"] = {"ok": ok, "fail": fail}

    print("📤 media_assets yükleniyor...")
    ok, fail = insert_all("media_assets", media_rows, "media_assets")
    results["media_assets"] = {"ok": ok, "fail": fail}

    # Özet
    print(f"\n{'='*60}")
    print("ÖZET")
    print(f"{'='*60}")
    for table, r in results.items():
        status = "✅" if r["fail"] == 0 else "⚠️ "
        print(f"  {status} {table:<20} ✅ {r['ok']:>5}  ❌ {r['fail']:>4}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
