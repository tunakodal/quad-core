# GUIDE Data Pipeline README

**Guided User Itinerary & Destination Explorer**
Team: QUAD-CORE | BIL495/496 Graduation Project | TOBB ETÜ

Bu klasör, GUIDE projesinin POI veri toplama, zenginleştirme, ses üretimi, bulut depolama ve veritabanı yükleme süreçlerinde kullanılan tüm Python scriptlerini içerir.

---

## Klasör Yapısı

```
GUIDE Data Pipeline/
├── data_analysis.py                       # Dataset istatistik analizi
├── requirements.txt                       # Bağımlılıklar
│
├── collectors/
│   ├── osm_collector.py                   # OpenStreetMap / Overpass API POI toplama
│   ├── wikipedia_collector.py             # Wikipedia kategori scraping
│   ├── multi_source_poi_collector.py      # Tüm kaynakları birleştir + Wikipedia açıklama
│   └── coordinate_validator.py            # Koordinat doğrulama, Türkiye dışı temizleme
│
├── enrichers/
│   ├── google_enricher.py                 # Google Places API — rating, yorum, place_id
│   └── photo_downloader.py                # Google Places API — fotoğraf indirme
│
├── llm/
│   ├── haiku_description_enricher.py      # Claude Haiku — TR + EN açıklama üretimi
│   └── translate_german.py                # Claude Haiku — EN → DE çeviri
│
├── tts/
│   ├── tts_google.py                      # Google Cloud TTS — TR + EN MP3
│   └── tts_german.py                      # Google Cloud TTS — DE MP3
│
├── storage/
│   └── upload_to_s3.py                    # AWS S3 — medya yükle, JSON URL güncelle
│
└── database/
    ├── generate_seed.py                   # JSON → guide_schema.sql + guide_seed.sql
    └── insert_to_supabase.py              # Supabase REST API ile veri yükleme (port 443)
```

---

## Kurulum

```bash
pip install -r requirements.txt
```

Ortam değişkenlerini ayarla (`.env` dosyası oluştur, **asla commit etme**):

```env
ANTHROPIC_API_KEY=[API_KEY]
GOOGLE_PLACES_API_KEY=[API_KEY]
GOOGLE_TTS_API_KEY=[API_KEY]
AWS_ACCESS_KEY_ID=[API_KEY]
AWS_SECRET_ACCESS_KEY=[API_KEY]
AWS_REGION=[YOUR_AWS_REGION]
S3_BUCKET_NAME=[YOUR_BUCKET_NAME]
SUPABASE_URL=[YOUR_SUPABASE_URL]
SUPABASE_KEY=[YOUR_SERVICE_ROLE_KEY]
```

---

## Pipeline Akışı ve Çalıştırma Sırası

| # | Script | Açıklama | Çıktı |
|---|--------|----------|-------|
| 1 | `collectors/osm_collector.py` | Overpass API ile Türkiye POI toplama | `poi_raw_osm.json` |
| 2 | `collectors/wikipedia_collector.py` | Wikipedia kategori scraping | `poi_raw_wiki.json` |
| 3 | `collectors/multi_source_poi_collector.py` | Kaynakları birleştir, duplicate temizle, Wikipedia açıklama çek | `poi_merged.json` |
| 4 | `collectors/coordinate_validator.py` | Türkiye sınır kontrolü, yanlış il düzeltme, Nominatim geocoding | `poi_coord_validated.json` |
| 5 | `enrichers/google_enricher.py` | Google Places ile rating, yorum, place_id ekleme | `poi_enriched.json` |
| 6 | `llm/haiku_description_enricher.py` | Claude Haiku ile eksik TR + EN açıklama üretimi | `poi_enriched_descriptions.json` |
| 7 | `llm/translate_german.py` | Claude Haiku ile EN → DE çeviri | `poi_with_german.json` |
| 8 | `enrichers/photo_downloader.py` | Google Places ile POI başına 3 fotoğraf indirme | `poi_with_photos.json` |
| 9 | `tts/tts_google.py` | Google Cloud TTS ile TR + EN MP3 üretimi | `poi_with_audio.json` |
| 10 | `tts/tts_german.py` | Google Cloud TTS ile DE MP3 üretimi | `poi_complete.json` |
| 11 | `storage/upload_to_s3.py` | Fotoğraf + ses dosyalarını AWS S3'e yükle, URL güncelle | `poi_final.json` |
| 12 | `database/generate_seed.py` | JSON'dan SQL schema + seed dosyaları üret | `guide_schema.sql` + `guide_seed.sql` |
| 13 | `database/insert_to_supabase.py` | Supabase'e REST API üzerinden veri yükle (port 443, psql gerekmez) | — |
| 14 | `data_analysis.py` | Dataset istatistik raporu | `data_analysis_report.json` |

---

## Kullanılan Teknolojiler ve API Maliyetleri

| Teknoloji / API | Kullanım Amacı | Maliyet |
|-----------------|----------------|---------|
| OpenStreetMap / Overpass API | Temel POI toplama | Ücretsiz |
| Wikipedia / Wikidata API | POI discovery + açıklama | Ücretsiz |
| Nominatim API | Reverse geocoding (koordinat → il) | Ücretsiz |
| Google Places API (New) | Rating, yorum sayısı, fotoğraf | ~$79 |
| Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) | TR+EN açıklama üretimi + DE çeviri | ~$5-7 |
| Google Cloud TTS | TR + EN + DE MP3 seslendirme | ~$34 |
| AWS S3 | Fotoğraf ve ses dosyası depolama | ~$1/ay |
| Supabase (PostgreSQL) | Veritabanı | Ücretsiz (free tier) |

---

## Dataset İstatistikleri (Final)

- **Toplam POI:** 2.337 (Türkiye'nin 81 ili)
- **Dil desteği:** Türkçe, İngilizce, Almanca (açıklama + ses)
- **Ses dosyaları:** ~7.000 MP3 (her POI için 3 dil)
- **Fotoğraflar:** ~7.000 JPG (her POI için 3 adet)
- **Veritabanı:** Supabase PostgreSQL — `cities`, `pois`, `poi_contents`, `media_assets`
- **Medya depolama:** AWS S3

---

## Önemli Notlar

- Tüm scriptler **kaldığı yerden devam** eder — `*_progress.json` dosyaları sayesinde yarıda kesilirse tekrar çalıştırılabilir.
- `guide_seed.sql` büyük bir dosyadır (~8 MB), `.gitignore`'a ekli.
- `poi_photos/` ve `poi_audio/` klasörleri S3'te tutulur, lokale commit edilmez.
- `insert_to_supabase.py` port 443 (HTTPS) kullandığından ISP port engelleme sorununu aşar.
- Supabase yükleme sırası önemlidir: `cities → pois → poi_contents → media_assets`.
