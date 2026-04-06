"""
GUIDE — Dataset İstatistik Analiz Scripti
==========================================
POI datasetinin kapsamlı istatistiksel analizini yapar:
  - İl bazlı POI dağılımı
  - Kategori / alt kategori dağılımı
  - Açıklama doluluk oranları (TR / EN / DE)
  - Rating ve yorum istatistikleri
  - Fotoğraf ve ses dosyası coverage
  - Kalite metrikleri (kısa açıklama, koordinat eksikliği vb.)
  - Konsola özet + data_analysis_report.json çıktısı

Kullanım:
    python data_analysis.py
    python data_analysis.py --input poi_final.json
"""

import json
import math
import argparse
from collections import Counter, defaultdict
from pathlib import Path

INPUT_FILE = "poi_final.json"
OUTPUT_FILE = "data_analysis_report.json"


def safe_mean(values: list) -> float | None:
    vals = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return round(sum(vals) / len(vals), 3) if vals else None


def safe_median(values: list) -> float | None:
    vals = sorted(v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v)))
    if not vals:
        return None
    n = len(vals)
    if n % 2 == 0:
        return round((vals[n // 2 - 1] + vals[n // 2]) / 2, 3)
    return round(vals[n // 2], 3)


def analyze(data: dict) -> dict:
    all_pois = []
    for province, pois in data.items():
        for poi in pois:
            poi.setdefault("_province", province)
            all_pois.append(poi)

    total = len(all_pois)

    # ── İl bazlı dağılım ────────────────────────────────────────
    province_counts = {p: len(pois) for p, pois in data.items()}
    province_sorted = sorted(province_counts.items(), key=lambda x: -x[1])

    # Tier sınıflandırma
    tiers = {"tier1_200+": [], "tier2_100-199": [], "tier3_50-99": [], "tier4_under50": []}
    for p, c in province_counts.items():
        if c >= 200:
            tiers["tier1_200+"].append(p)
        elif c >= 100:
            tiers["tier2_100-199"].append(p)
        elif c >= 50:
            tiers["tier3_50-99"].append(p)
        else:
            tiers["tier4_under50"].append(p)

    # ── Kategori dağılımı ────────────────────────────────────────
    category_counter = Counter()
    subcategory_counter = Counter()
    for poi in all_pois:
        cat = poi.get("category") or "unknown"
        sub = poi.get("subcategory") or "unknown"
        category_counter[cat] += 1
        subcategory_counter[f"{cat}/{sub}"] += 1

    # ── Açıklama coverage ───────────────────────────────────────
    desc_stats = {}
    for lang, fields in [
        ("TR", ["description_tr", "medium_description_tr"]),
        ("EN", ["description_en", "medium_description_en"]),
        ("DE", ["description_de", "medium_description_de"]),
    ]:
        filled = 0
        short = 0  # < 80 karakter
        lengths = []
        for poi in all_pois:
            text = ""
            for field in fields:
                text = (poi.get(field) or "").strip()
                if text:
                    break
            if text:
                filled += 1
                lengths.append(len(text))
                if len(text) < 80:
                    short += 1
        desc_stats[lang] = {
            "filled": filled,
            "filled_pct": round(filled / total * 100, 1),
            "missing": total - filled,
            "missing_pct": round((total - filled) / total * 100, 1),
            "short_under80": short,
            "avg_length": safe_mean(lengths),
            "median_length": safe_median(lengths),
        }

    # ── Rating istatistikleri ────────────────────────────────────
    ratings = [poi.get("google_rating") for poi in all_pois]
    ratings_valid = [r for r in ratings if r is not None]
    reviews = [poi.get("google_reviews_total") for poi in all_pois]
    reviews_valid = [r for r in reviews if r is not None]

    rating_stats = {
        "has_rating": len(ratings_valid),
        "has_rating_pct": round(len(ratings_valid) / total * 100, 1),
        "no_rating": total - len(ratings_valid),
        "avg_rating": safe_mean(ratings_valid),
        "median_rating": safe_median(ratings_valid),
        "rating_distribution": {
            "below_3": sum(1 for r in ratings_valid if r < 3.0),
            "3_to_35": sum(1 for r in ratings_valid if 3.0 <= r < 3.5),
            "35_to_4": sum(1 for r in ratings_valid if 3.5 <= r < 4.0),
            "4_to_45": sum(1 for r in ratings_valid if 4.0 <= r < 4.5),
            "above_45": sum(1 for r in ratings_valid if r >= 4.5),
        },
        "has_reviews": len(reviews_valid),
        "avg_reviews": safe_mean(reviews_valid),
        "median_reviews": safe_median(reviews_valid),
    }

    # ── Medya coverage ──────────────────────────────────────────
    photo_count = sum(
        1 for p in all_pois
        if (p.get("photo_urls") and len(p["photo_urls"]) > 0)
        or (p.get("photo_files") and len(p["photo_files"]) > 0)
        or (p.get("photo_count", 0) or 0) > 0
    )
    audio_tr = sum(1 for p in all_pois if p.get("audio_tr") or p.get("audio_tr_path"))
    audio_en = sum(1 for p in all_pois if p.get("audio_en") or p.get("audio_en_path"))
    audio_de = sum(1 for p in all_pois if p.get("audio_de") or p.get("audio_de_path"))

    media_stats = {
        "has_photos": photo_count,
        "has_photos_pct": round(photo_count / total * 100, 1),
        "audio_tr": audio_tr,
        "audio_tr_pct": round(audio_tr / total * 100, 1),
        "audio_en": audio_en,
        "audio_en_pct": round(audio_en / total * 100, 1),
        "audio_de": audio_de,
        "audio_de_pct": round(audio_de / total * 100, 1),
    }

    # ── Koordinat coverage ──────────────────────────────────────
    no_coords = sum(1 for p in all_pois if not p.get("lat") or not p.get("lon"))

    # ── Veri kaynağı dağılımı ───────────────────────────────────
    source_counter = Counter(
        poi.get("source", "unknown") for poi in all_pois
    )

    # ── Sonuç ───────────────────────────────────────────────────
    return {
        "summary": {
            "total_pois": total,
            "total_provinces": len(data),
            "provinces_covered": len([p for p, c in province_counts.items() if c > 0]),
        },
        "province_distribution": {
            "top10": province_sorted[:10],
            "bottom10": province_sorted[-10:],
            "tiers": {k: {"count": len(v), "provinces": v} for k, v in tiers.items()},
            "all": dict(province_sorted),
        },
        "category_distribution": {
            "top_categories": category_counter.most_common(15),
            "top_subcategories": subcategory_counter.most_common(20),
            "unique_categories": len(category_counter),
            "unique_subcategories": len(subcategory_counter),
        },
        "description_coverage": desc_stats,
        "rating_statistics": rating_stats,
        "media_coverage": media_stats,
        "data_quality": {
            "missing_coordinates": no_coords,
            "missing_coordinates_pct": round(no_coords / total * 100, 1),
        },
        "data_sources": dict(source_counter.most_common()),
    }


def print_summary(report: dict):
    s = report["summary"]
    print(f"\n{'='*60}")
    print(f"  GUIDE POI Dataset — İstatistik Raporu")
    print(f"{'='*60}")
    print(f"Toplam POI       : {s['total_pois']:,}")
    print(f"Kapsanan İl      : {s['provinces_covered']} / {s['total_provinces']}")

    print(f"\n─── Açıklama Coverage ───")
    for lang, st in report["description_coverage"].items():
        bar = "█" * int(st["filled_pct"] / 5)
        print(f"  {lang}: {st['filled_pct']:5.1f}%  {bar}  ({st['filled']:,}/{s['total_pois']:,})"
              f"  kısa(<80): {st['short_under80']}")

    print(f"\n─── Medya Coverage ───")
    m = report["media_coverage"]
    print(f"  Fotoğraf : {m['has_photos_pct']}%  ({m['has_photos']:,})")
    print(f"  Ses TR   : {m['audio_tr_pct']}%  ({m['audio_tr']:,})")
    print(f"  Ses EN   : {m['audio_en_pct']}%  ({m['audio_en']:,})")
    print(f"  Ses DE   : {m['audio_de_pct']}%  ({m['audio_de']:,})")

    print(f"\n─── Rating ───")
    r = report["rating_statistics"]
    print(f"  Rating olan : {r['has_rating_pct']}%  ({r['has_rating']:,})")
    print(f"  Ortalama    : {r['avg_rating']}  |  Medyan: {r['median_rating']}")
    dist = r["rating_distribution"]
    print(f"  Dağılım: <3.0={dist['below_3']}  "
          f"3.0-3.5={dist['3_to_35']}  "
          f"3.5-4.0={dist['35_to_4']}  "
          f"4.0-4.5={dist['4_to_45']}  "
          f"≥4.5={dist['above_45']}")

    print(f"\n─── Top 10 Kategori ───")
    for cat, count in report["category_distribution"]["top_categories"][:10]:
        bar = "█" * int(count / s["total_pois"] * 200)
        print(f"  {cat:<35} {count:>5}  {bar}")

    print(f"\n─── Top 10 İl ───")
    for prov, count in report["province_distribution"]["top10"]:
        bar = "█" * int(count / 10)
        print(f"  {prov:<20} {count:>5}  {bar}")

    print(f"\n─── Tier Dağılımı ───")
    for tier, info in report["province_distribution"]["tiers"].items():
        print(f"  {tier:<20}: {info['count']} il")

    dq = report["data_quality"]
    print(f"\n─── Veri Kalitesi ───")
    print(f"  Koordinatsız : {dq['missing_coordinates']} (%{dq['missing_coordinates_pct']})")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=INPUT_FILE)
    parser.add_argument("--output", default=OUTPUT_FILE)
    args = parser.parse_args()

    print(f"📂 Dosya yükleniyor: {args.input}")
    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)

    report = analyze(data)
    print_summary(report)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"📋 Detaylı rapor: {args.output}")


if __name__ == "__main__":
    main()
