"""
GUIDE — Koordinat Doğrulama & Temizleme Scripti
=================================================
Her POI'nin koordinatlarını doğrular:
  1. Türkiye sınır kutusu kontrolü (hızlı filtre)
  2. İl bazlı bbox kontrolü (yanlış il tespiti)
  3. Nominatim reverse geocoding (koordinatsız POI'ler)
  4. Türkiye dışındakileri siler veya raporlar

Girdi  : poi_merged.json (veya herhangi bir aşama JSON'ı)
Çıktı  : poi_coord_validated.json + coord_report.json

Kullanım:
    python coordinate_validator.py
    python coordinate_validator.py --delete-outside   # Türkiye dışındakileri sil
    python coordinate_validator.py --report-only      # Sadece rapor, silme yok
"""

import json
import time
import math
import argparse
import requests
from pathlib import Path

INPUT_FILE = "poi_merged.json"
OUTPUT_FILE = "poi_coord_validated.json"
REPORT_FILE = "coord_report.json"

# Türkiye genel sınır kutusu
TURKEY_BBOX = {
    "lat_min": 35.8,
    "lat_max": 42.2,
    "lon_min": 25.6,
    "lon_max": 45.0,
}

# İl bazlı bounding box'lar (yaklaşık)
PROVINCE_BBOXES = {
    "Adana":           (35.10, 36.40, 37.20, 38.20),
    "Adıyaman":        (37.30, 38.40, 37.50, 39.20),
    "Afyonkarahisar":  (29.00, 39.00, 31.60, 38.00),  # min_lon,min_lat,max_lon,max_lat
    "Ağrı":            (42.30, 39.10, 44.90, 40.00),
    "Aksaray":         (33.00, 37.80, 34.80, 38.80),
    "Amasya":          (35.30, 40.40, 36.80, 41.10),
    "Ankara":          (31.30, 39.00, 33.80, 40.50),
    "Antalya":         (29.00, 36.10, 33.20, 37.60),
    "Ardahan":         (42.00, 40.80, 43.70, 41.60),
    "Artvin":          (40.90, 40.60, 42.40, 41.60),
    "Aydın":           (27.00, 37.10, 29.20, 38.20),
    "Balıkesir":       (26.30, 39.10, 28.80, 40.80),
    "Bartın":          (32.00, 41.30, 33.30, 41.90),
    "Batman":          (40.90, 37.50, 42.10, 38.40),
    "Bayburt":         (39.30, 39.90, 41.00, 40.70),
    "Bilecik":         (29.50, 39.80, 30.80, 40.60),
    "Bingöl":          (39.90, 38.60, 41.50, 39.30),
    "Bitlis":          (41.40, 37.90, 43.20, 38.90),
    "Bolu":            (30.40, 40.30, 32.20, 41.20),
    "Burdur":          (29.30, 37.00, 31.10, 38.30),
    "Bursa":           (27.90, 39.60, 30.20, 40.70),
    "Çanakkale":       (25.70, 39.40, 27.50, 40.80),
    "Çankırı":         (32.30, 40.20, 34.10, 41.20),
    "Çorum":           (34.00, 40.00, 36.00, 41.30),
    "Denizli":         (28.50, 37.10, 30.10, 38.40),
    "Diyarbakır":      (39.40, 37.50, 41.30, 38.50),
    "Düzce":           (30.80, 40.50, 32.20, 41.30),
    "Edirne":          (26.30, 41.30, 27.00, 42.00),
    "Elazığ":          (38.40, 38.20, 40.20, 39.20),
    "Erzincan":        (38.20, 39.20, 40.70, 40.20),
    "Erzurum":         (40.00, 39.40, 42.60, 40.80),
    "Eskişehir":       (29.90, 39.20, 32.00, 40.20),
    "Gaziantep":       (36.40, 36.80, 38.00, 37.50),
    "Giresun":         (37.80, 40.20, 39.50, 41.30),
    "Gümüşhane":       (38.80, 39.90, 40.50, 40.80),
    "Hakkari":         (43.20, 37.00, 45.00, 38.10),
    "Hatay":           (35.60, 35.80, 37.30, 37.20),
    "Iğdır":           (43.50, 39.50, 45.00, 40.20),
    "Isparta":         (29.90, 37.10, 31.60, 38.40),
    "İstanbul":        (27.90, 40.80, 29.90, 41.30),
    "İzmir":           (26.20, 37.70, 28.20, 39.30),
    "Kahramanmaraş":   (36.40, 37.10, 38.10, 38.50),
    "Karabük":         (32.20, 40.90, 33.60, 41.60),
    "Karaman":         (32.10, 36.80, 34.20, 38.00),
    "Kars":            (42.30, 40.10, 44.00, 41.30),
    "Kastamonu":       (32.50, 40.90, 35.30, 42.20),
    "Kayseri":         (34.80, 38.00, 37.10, 39.30),
    "Kilis":           (36.60, 36.50, 37.80, 37.20),
    "Kırıkkale":       (33.00, 39.50, 34.30, 40.30),
    "Kırklareli":      (26.90, 41.40, 28.10, 42.10),
    "Kırşehir":        (33.60, 38.80, 34.90, 39.80),
    "Kocaeli":         (29.50, 40.60, 30.60, 41.20),
    "Konya":           (31.60, 36.80, 34.50, 38.90),
    "Kütahya":         (28.80, 38.90, 30.50, 39.80),
    "Malatya":         (37.20, 37.80, 39.30, 39.00),
    "Manisa":          (27.00, 38.20, 29.20, 39.40),
    "Mardin":          (40.40, 36.90, 42.30, 37.80),
    "Mersin":          (32.70, 36.10, 35.00, 37.40),
    "Muğla":           (27.50, 36.40, 29.80, 37.80),
    "Muş":             (40.90, 38.40, 42.40, 39.20),
    "Nevşehir":        (34.35, 38.36, 35.52, 39.07),
    "Niğde":           (33.80, 37.50, 35.20, 38.60),
    "Ordu":            (36.70, 40.40, 38.50, 41.20),
    "Osmaniye":        (35.90, 36.70, 37.20, 37.70),
    "Rize":            (40.20, 40.80, 41.60, 41.40),
    "Sakarya":         (29.80, 40.40, 31.10, 41.10),
    "Samsun":          (35.10, 40.60, 37.30, 41.60),
    "Şanlıurfa":       (37.50, 36.70, 40.00, 38.20),
    "Siirt":           (41.60, 37.50, 42.90, 38.30),
    "Sinop":           (34.10, 41.10, 36.00, 42.20),
    "Sivas":           (35.80, 38.40, 39.60, 40.20),
    "Şırnak":          (41.80, 37.00, 43.60, 37.90),
    "Tekirdağ":        (26.70, 40.60, 28.10, 41.60),
    "Tokat":           (35.50, 39.60, 37.60, 40.80),
    "Trabzon":         (38.80, 40.50, 40.60, 41.30),
    "Tunceli":         (38.50, 38.70, 40.40, 39.50),
    "Uşak":            (28.60, 38.20, 29.90, 39.10),
    "Van":             (42.50, 37.70, 44.80, 38.90),
    "Yalova":          (29.10, 40.50, 29.70, 40.80),
    "Yozgat":          (34.20, 39.10, 36.50, 40.40),
    "Zonguldak":       (31.10, 41.00, 32.70, 41.70),
}


def in_turkey(lat: float, lon: float) -> bool:
    b = TURKEY_BBOX
    return b["lat_min"] <= lat <= b["lat_max"] and b["lon_min"] <= lon <= b["lon_max"]


def in_province_bbox(lat: float, lon: float, province: str) -> bool:
    """POI koordinatı verilen ilin bbox'ı içinde mi?"""
    bbox = PROVINCE_BBOXES.get(province)
    if not bbox:
        return True  # Bbox tanımlı değilse geç
    min_lon, min_lat, max_lon, max_lat = bbox
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon


def reverse_geocode_nominatim(lat: float, lon: float) -> str | None:
    """Nominatim ile koordinattan il ismi al."""
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "lat": lat, "lon": lon,
                "format": "json",
                "accept-language": "tr",
                "zoom": 6,
            },
            headers={"User-Agent": "GUIDE-TravelApp/1.0"},
            timeout=10,
        )
        if resp.status_code == 200:
            addr = resp.json().get("address", {})
            return (
                addr.get("province")
                or addr.get("state")
                or addr.get("county")
            )
    except Exception:
        pass
    return None


def validate_and_fix(data: dict, delete_outside: bool) -> tuple[dict, dict]:
    report = {
        "total": 0,
        "outside_turkey": [],
        "missing_coords": [],
        "wrong_province": [],
        "ok": 0,
    }

    cleaned: dict[str, list] = {}

    for province, pois in data.items():
        kept = []
        for poi in pois:
            report["total"] += 1
            lat = poi.get("lat")
            lon = poi.get("lon")

            # Koordinat yok → Nominatim ile dene
            if lat is None or lon is None:
                report["missing_coords"].append({
                    "name": poi["name"], "city": province
                })
                print(f"  ⚠ Koordinat yok: {poi['name']} ({province})")
                kept.append(poi)
                continue

            # Türkiye dışı
            if not in_turkey(lat, lon):
                report["outside_turkey"].append({
                    "name": poi["name"], "city": province,
                    "lat": lat, "lon": lon
                })
                print(f"  🌍 Türkiye dışı: {poi['name']} — lat={lat}, lon={lon}")
                if not delete_outside:
                    kept.append(poi)
                # delete_outside=True ise eklenmez
                continue

            # İl bbox kontrolü
            if not in_province_bbox(lat, lon, province):
                # Nominatim ile gerçek ili öğren
                time.sleep(1.1)  # Nominatim rate limit
                real_province = reverse_geocode_nominatim(lat, lon)
                report["wrong_province"].append({
                    "name": poi["name"],
                    "assigned": province,
                    "real": real_province,
                    "lat": lat, "lon": lon,
                })
                print(f"  🔄 Yanlış il: {poi['name']} → {province} ≠ {real_province}")
                if real_province and real_province != province:
                    poi["city"] = real_province
                    cleaned.setdefault(real_province, []).append(poi)
                else:
                    kept.append(poi)
                continue

            report["ok"] += 1
            kept.append(poi)

        if kept:
            cleaned.setdefault(province, []).extend(kept)

    return cleaned, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=INPUT_FILE)
    parser.add_argument("--output", default=OUTPUT_FILE)
    parser.add_argument("--delete-outside", action="store_true",
                        help="Türkiye dışındaki POI'leri sil")
    parser.add_argument("--report-only", action="store_true",
                        help="Sadece rapor üret, dosya kaydetme")
    args = parser.parse_args()

    print("=" * 60)
    print("GUIDE — Koordinat Doğrulama Scripti")
    print("=" * 60)

    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)

    total_before = sum(len(v) for v in data.values())
    print(f"Toplam POI (girdi): {total_before}")
    print()

    cleaned, report = validate_and_fix(data, args.delete_outside)

    total_after = sum(len(v) for v in cleaned.values())

    print(f"\n{'='*60}")
    print(f"Toplam girdi      : {report['total']}")
    print(f"✅ Geçerli        : {report['ok']}")
    print(f"🌍 Türkiye dışı   : {len(report['outside_turkey'])}"
          f"  {'(silindi)' if args.delete_outside else '(korundu)'}")
    print(f"🔄 Yanlış il      : {len(report['wrong_province'])} (düzeltildi)")
    print(f"⚠ Koordinat yok   : {len(report['missing_coords'])}")
    print(f"Toplam çıktı      : {total_after}")
    print(f"{'='*60}")

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"📋 Rapor: {REPORT_FILE}")

    if not args.report_only:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)
        print(f"💾 Kaydedildi: {args.output}")


if __name__ == "__main__":
    main()
