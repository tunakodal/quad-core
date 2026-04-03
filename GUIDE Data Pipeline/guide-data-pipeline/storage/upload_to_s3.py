"""
GUIDE — AWS S3 Media Upload Script
=====================================
poi_complete.json'daki lokal fotoğraf ve ses yollarını
AWS S3'e yükler, JSON'daki path'leri S3 URL'leriyle değiştirir.

Girdi  : poi_complete.json + poi_photos/ + poi_audio/
Çıktı  : poi_final.json (S3 URL'leriyle güncellenmiş)
S3 yapısı:
    guide-media2/
        photos/<Province>/<POI>_1.jpg
        audio/<Province>/<POI>_tr.mp3

Kullanım:
    export AWS_ACCESS_KEY_ID=[API_KEY]
    export AWS_SECRET_ACCESS_KEY=...
    python upload_to_s3.py
    python upload_to_s3.py --dry-run      # sadece listele
    python upload_to_s3.py --only-photos  # sadece fotoğraflar
    python upload_to_s3.py --only-audio   # sadece ses
"""

import json
import os
import re
import argparse
import mimetypes
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION = os.environ.get("AWS_REGION", "[YOUR_AWS_REGION]")
BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "[YOUR_BUCKET_NAME]")

INPUT_FILE = "poi_complete.json"
OUTPUT_FILE = "poi_final.json"

S3_BASE_URL = f"https://{BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com"

AUDIO_FIELDS = {
    "TR": "audio_tr",
    "EN": "audio_en",
    "DE": "audio_de",
}


def get_s3_client():
    return boto3.client(
        "s3",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )


def sanitize(name: str) -> str:
    name = re.sub(r"[^\w\s\-]", "", name)
    name = re.sub(r"\s+", "_", name.strip())
    return name[:60]


def upload_file(s3, local_path: str, s3_key: str, content_type: str) -> str | None:
    try:
        s3.upload_file(
            local_path,
            BUCKET_NAME,
            s3_key,
            ExtraArgs={"ContentType": content_type},
        )
        return f"{S3_BASE_URL}/{s3_key}"
    except ClientError as e:
        print(f"  ❌ Upload failed ({s3_key}): {e}")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only-photos", action="store_true")
    parser.add_argument("--only-audio", action="store_true")
    parser.add_argument("--input", default=INPUT_FILE)
    parser.add_argument("--output", default=OUTPUT_FILE)
    args = parser.parse_args()

    do_photos = not args.only_audio
    do_audio = not args.only_photos

    print("=" * 60)
    print("GUIDE — AWS S3 Upload")
    print(f"Bucket: {BUCKET_NAME} ({AWS_REGION})")
    if args.dry_run:
        print("⚠️  DRY RUN — hiçbir şey yüklenmeyecek")
    print("=" * 60)

    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)

    s3 = None if args.dry_run else get_s3_client()

    photo_ok = photo_fail = photo_skip = 0
    audio_ok = audio_fail = audio_skip = 0

    for province, pois in data.items():
        prov_safe = sanitize(province)

        for poi in pois:
            name_safe = sanitize(poi["name"])

            # Fotoğraflar
            if do_photos:
                new_urls = []
                for idx, local_path in enumerate(poi.get("photo_files") or [], 1):
                    if not Path(local_path).exists():
                        photo_skip += 1
                        continue
                    ext = Path(local_path).suffix or ".jpg"
                    s3_key = f"photos/{prov_safe}/{name_safe}_{idx}{ext}"
                    ct = mimetypes.guess_type(local_path)[0] or "image/jpeg"

                    if args.dry_run:
                        url = f"{S3_BASE_URL}/{s3_key}"
                        print(f"  [DRY] {s3_key}")
                        photo_ok += 1
                    else:
                        url = upload_file(s3, local_path, s3_key, ct)
                        if url:
                            photo_ok += 1
                        else:
                            photo_fail += 1
                            continue
                    new_urls.append(url)

                if new_urls:
                    poi["photo_urls"] = new_urls

            # Ses dosyaları
            if do_audio:
                for lang, field in AUDIO_FIELDS.items():
                    local_path = poi.get(field)
                    if not local_path or not Path(local_path).exists():
                        audio_skip += 1
                        continue
                    s3_key = f"audio/{prov_safe}/{name_safe}_{lang.lower()}.mp3"
                    ct = "audio/mpeg"

                    if args.dry_run:
                        url = f"{S3_BASE_URL}/{s3_key}"
                        print(f"  [DRY] {s3_key}")
                        audio_ok += 1
                    else:
                        url = upload_file(s3, local_path, s3_key, ct)
                        if url:
                            poi[field] = url
                            audio_ok += 1
                        else:
                            audio_fail += 1

    print(f"\n{'='*55}")
    if do_photos:
        print(f"🖼  Fotoğraf  — ✅ {photo_ok}  ❌ {photo_fail}  ⏭ {photo_skip}")
    if do_audio:
        print(f"🔊 Ses       — ✅ {audio_ok}  ❌ {audio_fail}  ⏭ {audio_skip}")
    print(f"{'='*55}")

    if not args.dry_run:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 Kaydedildi: {args.output}")


if __name__ == "__main__":
    main()
