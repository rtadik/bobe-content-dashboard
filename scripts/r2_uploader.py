#!/usr/bin/env python3
"""
R2 Uploader — Upload images to Cloudflare R2 via S3-compatible API.
Returns a public URL for the uploaded image.

Environment variables (loaded from .env):
  R2_ACCOUNT_ID         Cloudflare account ID
  R2_ACCESS_KEY_ID      R2 API token access key
  R2_SECRET_ACCESS_KEY  R2 API token secret
  R2_BUCKET_NAME        R2 bucket name (e.g. "bobe-content-images")
  R2_PUBLIC_URL         Public base URL (e.g. "https://pub-xxx.r2.dev")

Usage:
  import r2_uploader
  url = r2_uploader.upload_bytes(image_bytes, "bobe/2026-03-09/image.png")
  url = r2_uploader.upload_file("path/to/image.png", "bobe/2026-03-09/image.png")

  # CLI test:
  python scripts/r2_uploader.py --test
"""

import os
import sys
import argparse
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

try:
    import boto3
    from botocore.config import Config
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "bobe-content-images")
R2_PUBLIC_URL = os.environ.get("R2_PUBLIC_URL", "").rstrip("/")


def is_configured() -> bool:
    """Return True if R2 credentials are set and boto3 is available."""
    return bool(
        HAS_BOTO3
        and R2_ACCOUNT_ID
        and R2_ACCESS_KEY_ID
        and R2_SECRET_ACCESS_KEY
        and R2_PUBLIC_URL
    )


def get_client():
    """Return a boto3 S3 client configured for Cloudflare R2."""
    if not HAS_BOTO3:
        raise ImportError("boto3 not installed. Run: ./venv/bin/pip install boto3")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def upload_bytes(image_data: bytes, key: str) -> str:
    """
    Upload raw image bytes to R2 under the given key.
    Returns the public URL.
    """
    client = get_client()
    client.put_object(
        Bucket=R2_BUCKET_NAME,
        Key=key,
        Body=image_data,
        ContentType="image/png",
    )
    return f"{R2_PUBLIC_URL}/{key}"


def upload_file(local_path: str, key: str) -> str:
    """
    Upload a local file to R2 under the given key.
    Returns the public URL.
    """
    with open(local_path, "rb") as f:
        return upload_bytes(f.read(), key)


def make_key(client_id: str, week_of: str, filename: str) -> str:
    """
    Build a namespaced R2 object key.
    Format: {client_id}/{week_of}/{filename}
    """
    return f"{client_id}/{week_of}/{filename}"


def main():
    parser = argparse.ArgumentParser(description="Cloudflare R2 uploader utility")
    parser.add_argument("--test", action="store_true", help="Run upload test with a dummy PNG")
    parser.add_argument("--file", help="Local file to upload")
    parser.add_argument("--key", help="R2 object key (e.g. bobe/2026-03-09/image.png)")
    args = parser.parse_args()

    print(f"R2 configured: {is_configured()}")
    if not is_configured():
        print("Missing one or more: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_PUBLIC_URL")
        if not HAS_BOTO3:
            print("Also missing: boto3 (run: ./venv/bin/pip install boto3)")
        sys.exit(1)

    if args.test:
        import base64
        # Minimal 1x1 PNG
        png_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        key = "test/test-upload.png"
        print(f"Uploading test image to key: {key}")
        url = upload_bytes(png_bytes, key)
        print(f"Test URL: {url}")
        print("Upload successful.")

    elif args.file and args.key:
        print(f"Uploading {args.file} → {args.key}")
        url = upload_file(args.file, args.key)
        print(f"URL: {url}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
