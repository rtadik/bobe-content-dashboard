# Plan: Cloudflare R2 Image Storage + Airtable as Primary Data Store

**Created:** 2026-03-05
**Status:** Implemented
**Request:** Replace local Excel + local image storage with Cloudflare R2 for images and Airtable as the primary content store. Everything in the cloud, no local file dependency.

---

## Overview

### What This Plan Accomplishes

Eliminates local Excel files and local image folders as the primary output of the pipeline. Images are uploaded directly to Cloudflare R2 (free tier, public URLs) during generation. Content rows are written directly to Airtable after generation — no Excel intermediate step. The local Flask dashboard and static site builder both read from Airtable and serve R2 image URLs.

### Why This Matters

Currently, content and images exist locally and only reach the cloud after a separate sync/deploy step. This creates dependency on a local machine, makes pipeline runs from GitHub Actions second-class citizens (artifacts expire in 30 days), and requires re-deployment whenever images change. Moving to cloud-primary makes every pipeline run fully persistent, accessible from anywhere, and eliminates the Excel→Airtable sync lag.

---

## Current State

### Relevant Existing Structure

```
scripts/
  pipeline_runner.py      # Orchestrator: Excel-first, then optional Airtable sync
  weekly_pipeline.py      # Creates and writes Excel workbook (openpyxl)
  airtable_sync.py        # Secondary: reads Excel → pushes to Airtable
  nano_banana.py          # EN image gen: saves to outputs/content/{client}/images/
  wavespeed_img.py        # RU image gen: saves to outputs/content/{client}/images/
  web_viewer.py           # Flask dashboard: reads from Excel, serves local images
  build_static.py         # Static site builder: reads from Excel, copies local images

outputs/content/bobe/
  2026-03-02-weekly-content.xlsx         # Primary data store (local only)
  images/2026-03-02-weekly/              # 42 PNG files (local only, 72MB+)

clients/bobe/config.json
  airtable.enabled = true
  airtable.base_id = "appikOGb5GyhPqoCd"
  airtable.images_base_url = "https://rtadik.github.io/bobe-content-dashboard"

.github/workflows/weekly-pipeline.yml
  - Uploads Excel as artifact (30-day expiry)
  - Runs airtable_sync.py after pipeline
```

### Gaps or Problems Being Addressed

- **Ephemeral local storage**: Images and Excel exist only on the machine running the pipeline. GitHub Actions artifacts expire in 30 days.
- **Two-step sync**: Content reaches Airtable only after a separate sync step that reads the Excel. If that step fails, Airtable is stale.
- **Image URL dependency**: Airtable currently stores GitHub Pages image URLs — if the static site isn't deployed, images are broken in Airtable.
- **No cloud persistence**: There is no permanent cloud record of pipeline runs unless manually deployed.

---

## Proposed Changes

### Summary of Changes

- Add `scripts/r2_uploader.py` — utility to upload image bytes to Cloudflare R2 and return a public URL
- Modify `nano_banana.py` and `wavespeed_img.py` — after generating an image, upload to R2 and return the public URL (keep local save as optional backup)
- Add `scripts/airtable_writer.py` — direct Airtable writer (replaces airtable_sync.py logic) that accepts a content dict and creates/updates a single record
- Modify `pipeline_runner.py` — write each content item directly to Airtable after generation; write image R2 URL into Airtable immediately after image generation; remove Excel as primary step
- Modify `web_viewer.py` — read content from Airtable API instead of Excel; images load from R2 URLs
- Modify `build_static.py` — fetch from Airtable at build time; use R2 URLs for images
- Update `airtable_sync.py` — repurpose as a one-off backfill utility (not part of the main pipeline)
- Update `weekly_pipeline.py` — demote to optional Excel export only (keep for backwards compatibility but not called by default)
- Update `clients/bobe/config.json` — add `r2` section with bucket name and public URL
- Update `.env` — add R2 credentials
- Update `.github/workflows/weekly-pipeline.yml` — add R2 secrets, remove Excel artifact upload, remove airtable_sync step (now inline)
- Update `CLAUDE.md` — reflect new architecture

### New Files to Create

| File Path | Purpose |
|-----------|---------|
| `scripts/r2_uploader.py` | Upload image bytes to Cloudflare R2 via S3-compatible API; return public URL |
| `scripts/airtable_writer.py` | Write a single content item dict directly to an Airtable table; handles table creation, field mapping, image attachment |
| `reference/r2-setup.md` | Step-by-step guide for creating R2 bucket, enabling public access, generating API token |

### Files to Modify

| File Path | Changes |
|-----------|---------|
| `scripts/nano_banana.py` | After saving image locally, also upload to R2 and return `(local_path, r2_url)` tuple. Add `--upload-r2` flag. |
| `scripts/wavespeed_img.py` | Same: upload to R2 after generation, return `(local_path, r2_url)` tuple. Add `--upload-r2` flag. |
| `scripts/pipeline_runner.py` | Phase 4: write to Airtable directly after each content item (not after full run). Phase 5: upload image to R2, update Airtable `Image_URL` field. Remove Phase 6.5 airtable_sync call. Keep Excel write as `--export-excel` opt-in flag. |
| `scripts/web_viewer.py` | Replace `load_content()` to fetch from Airtable API filtered by Week + Client. Image `src` becomes R2 URL. |
| `scripts/build_static.py` | Replace Excel reading with Airtable API fetch. Image URLs from R2 (no local image copy step). |
| `scripts/airtable_sync.py` | Add `--backfill` mode header/warning. Keep as utility for migrating old Excel weeks. Not called in main pipeline. |
| `clients/bobe/config.json` | Add `"r2": {"enabled": true, "bucket_name": "bobe-content-images", "public_url": "https://pub-XXX.r2.dev"}` and update `airtable.images_base_url` to R2 URL |
| `.env` | Add `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_PUBLIC_URL` |
| `.github/workflows/weekly-pipeline.yml` | Add R2 env vars from secrets. Remove Excel artifact upload step. Remove explicit airtable_sync.py step. |
| `CLAUDE.md` | Update Scripts table, Pipeline Structure section, API Requirements table, Deployment section |

### Files to Delete (if any)

None deleted — `weekly_pipeline.py` and `airtable_sync.py` kept as utilities.

---

## Design Decisions

### Key Decisions Made

1. **Cloudflare R2 over alternatives**: Free 10GB/month storage, zero egress fees, S3-compatible API, and already have a Cloudflare account with Workers set up. Backblaze B2 is also free but has egress fees; Cloudinary's free tier is too small for 42 images/week; GitHub Pages will bloat the repo.

2. **Airtable as primary, Excel as optional export**: Airtable is already set up, the API is proven, and the schema is stable. Excel becomes an opt-in (`--export-excel` flag) for users who want a local copy. This removes the openpyxl dependency from the core pipeline path.

3. **Image stored as URL text field in Airtable (not Attachment type)**: Airtable's Attachment field requires additional API complexity (field must pre-exist as Attachment type; cannot mix with text). R2 public URLs stored as text are simpler, still clickable/previewable in Airtable, and avoid Airtable plan limits on attachment storage.

4. **Inline Airtable write per item (not batch at end)**: Writing each content row to Airtable immediately after Gemini generates it means partial pipeline runs still produce usable data. The old approach wrote everything to Excel first and synced at the end — if the pipeline crashed at item 35, nothing was in Airtable.

5. **boto3 for R2 upload**: Cloudflare R2 is S3-compatible. boto3 handles AWS Signature V4 signing automatically. Alternative was manual signing with `requests` — more code, more bugs. boto3 is a one-time `pip install`.

6. **Keep local image save as fallback**: `nano_banana.py` and `wavespeed_img.py` still save images locally (to `outputs/content/{client}/images/`) in addition to uploading to R2. This gives a local backup and allows local `web_viewer.py` to serve images even if offline. The local save can be disabled with `--no-local-save` if desired.

7. **web_viewer.py reads from Airtable (not local Excel)**: The local Flask dashboard was already reading Excel which was already derived from Airtable sync. Cutting out the middle layer makes local dev easier — just run the dashboard and it reads live Airtable data.

### Alternatives Considered

- **Supabase Storage + Supabase DB**: Would replace both R2 and Airtable. Too much migration effort and loses the Airtable client-friendly UI.
- **Keep GitHub Pages for images**: Already doing this, but repo bloat is a long-term problem and images are tied to deployment cycles.
- **Cloudinary**: Good image CDN but free tier (25 credits/month) is too tight for 42 images/week at full pipeline frequency.

### Open Questions

1. **R2 public URL type**: Cloudflare offers two options:
   - Free R2 public URL: `https://pub-{hash}.r2.dev/{filename}` (no custom domain needed)
   - Custom domain: `https://images.rejiglabs.com/{filename}` (requires DNS setup)
   Recommend starting with the free public URL — it can be changed later by updating `R2_PUBLIC_URL` in `.env`.

2. **Existing week data**: Old weeks (2026-02-16, 2026-03-02) have image paths pointing to GitHub Pages. These won't auto-migrate. The old `airtable_sync.py` in backfill mode can re-push them with GitHub Pages URLs (unchanged), or we leave old weeks as-is.

---

## Step-by-Step Tasks

### Step 1: R2 Setup Reference Guide

Create `reference/r2-setup.md` with step-by-step instructions for setting up the R2 bucket.

**Actions:**

- Create `reference/r2-setup.md` with the following sections:
  1. **Create R2 bucket** in Cloudflare dashboard (Storage & Databases → R2 → Create bucket). Name: `bobe-content-images` (or `{client}-content-images` pattern for multi-client).
  2. **Enable public access**: In bucket settings → "Allow Access" → Enable public access. Note the public URL (format: `https://pub-{hash}.r2.dev`).
  3. **Create R2 API token**: Account → Manage R2 API Tokens → Create Token. Permissions: "Object Read & Write" scoped to the bucket. Save Access Key ID and Secret Access Key.
  4. **Add to .env**: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME=bobe-content-images`, `R2_PUBLIC_URL=https://pub-XXX.r2.dev`
  5. **Add to GitHub Secrets**: Same 5 variables for GitHub Actions runs.
  6. **Install boto3**: `./venv/bin/pip install boto3`

**Files affected:**

- `reference/r2-setup.md` (new)

---

### Step 2: Create `scripts/r2_uploader.py`

New utility module for uploading images to Cloudflare R2.

**Actions:**

Create `scripts/r2_uploader.py` with:

```python
#!/usr/bin/env python3
"""
R2 Uploader — Upload images to Cloudflare R2 via S3-compatible API.
Returns a public URL for the uploaded image.

Environment variables:
  R2_ACCOUNT_ID         Cloudflare account ID
  R2_ACCESS_KEY_ID      R2 API token access key
  R2_SECRET_ACCESS_KEY  R2 API token secret
  R2_BUCKET_NAME        R2 bucket name (e.g. "bobe-content-images")
  R2_PUBLIC_URL         Public base URL (e.g. "https://pub-xxx.r2.dev")
"""

import os
import boto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv()

R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "bobe-content-images")
R2_PUBLIC_URL = os.environ.get("R2_PUBLIC_URL", "").rstrip("/")


def is_configured() -> bool:
    """Return True if R2 credentials are set."""
    return bool(R2_ACCOUNT_ID and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY and R2_PUBLIC_URL)


def get_client():
    """Return a boto3 S3 client configured for Cloudflare R2."""
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
```

**Files affected:**

- `scripts/r2_uploader.py` (new)

---

### Step 3: Create `scripts/airtable_writer.py`

New direct Airtable writer — writes a single content item row to the correct weekly table.

**Actions:**

Create `scripts/airtable_writer.py` with:

```python
#!/usr/bin/env python3
"""
Airtable Writer — Write content items directly to Airtable (no Excel intermediate).

Writes one content row at a time to the Week-{week_of} table in the client's
Airtable base. Creates the table if it doesn't exist (via meta API).

Schema written:
  Date, Bucket, Day, Topic, Platform, Format, Content, Image_Prompt,
  Image_URL_EN, Hashtags, Content_RU, Image_Prompt_RU, Image_URL_RU,
  Hashtags_RU, Status, Tweet_URL, Week, Client
"""

import os
import json
import time
import requests
from dotenv import load_dotenv
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
import client_config

load_dotenv()

AIRTABLE_BASE_URL = "https://api.airtable.com/v0"
AIRTABLE_META_URL = "https://api.airtable.com/v0/meta/bases"


def get_api_key(client_id: str = None) -> str:
    key_env = "AIRTABLE_API_KEY"
    if client_id:
        cfg = client_config.load_config(client_id)
        key_env = cfg.get("airtable", {}).get("api_key_env", "AIRTABLE_API_KEY")
    return os.environ.get(key_env, "")


def get_or_create_table(base_id: str, week_of: str, api_key: str) -> str:
    """
    Return the table ID for Week-{week_of}. Creates it if not found.
    Returns table ID string.
    """
    table_name = f"Week-{week_of}"
    headers = {"Authorization": f"Bearer {api_key}"}

    # List existing tables
    resp = requests.get(f"{AIRTABLE_META_URL}/{base_id}/tables", headers=headers, timeout=15)
    resp.raise_for_status()
    tables = resp.json().get("tables", [])

    for t in tables:
        if t["name"] == table_name:
            return t["id"]

    # Create table with required fields
    fields = [
        {"name": "Date", "type": "singleLineText"},
        {"name": "Bucket", "type": "singleLineText"},
        {"name": "Day", "type": "singleLineText"},
        {"name": "Topic", "type": "singleLineText"},
        {"name": "Platform", "type": "singleLineText"},
        {"name": "Format", "type": "singleLineText"},
        {"name": "Content", "type": "multilineText"},
        {"name": "Image_Prompt", "type": "multilineText"},
        {"name": "Image_URL_EN", "type": "url"},
        {"name": "Hashtags", "type": "singleLineText"},
        {"name": "Content_RU", "type": "multilineText"},
        {"name": "Image_Prompt_RU", "type": "multilineText"},
        {"name": "Image_URL_RU", "type": "url"},
        {"name": "Hashtags_RU", "type": "singleLineText"},
        {"name": "Status", "type": "singleLineText"},
        {"name": "Tweet_URL", "type": "url"},
        {"name": "Week", "type": "singleLineText"},
        {"name": "Client", "type": "singleLineText"},
    ]
    body = {"name": table_name, "fields": fields}
    resp = requests.post(
        f"{AIRTABLE_META_URL}/{base_id}/tables",
        headers={**headers, "Content-Type": "application/json"},
        json=body,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def write_record(
    base_id: str,
    table_id: str,
    item: dict,
    week_of: str,
    client_id: str,
    api_key: str,
) -> str:
    """
    Write a single content item to Airtable. Returns the created record ID.
    item keys: date, bucket, day, topic, platform, format, content, image_prompt,
               image_url_en, hashtags, content_ru, image_prompt_ru, image_url_ru,
               hashtags_ru, status, tweet_url (optional)
    """
    hashtags = item.get("hashtags", [])
    hashtags_ru = item.get("hashtags_ru", [])
    if isinstance(hashtags, list):
        hashtags = ", ".join(hashtags)
    if isinstance(hashtags_ru, list):
        hashtags_ru = ", ".join(hashtags_ru)

    fields = {
        "Date": str(item.get("date", "")),
        "Bucket": item.get("bucket", ""),
        "Day": item.get("day", ""),
        "Topic": item.get("topic", ""),
        "Platform": item.get("platform", ""),
        "Format": item.get("format", ""),
        "Content": item.get("content", ""),
        "Image_Prompt": item.get("image_prompt", ""),
        "Image_URL_EN": item.get("image_url_en", "") or None,
        "Hashtags": hashtags,
        "Content_RU": item.get("content_ru", ""),
        "Image_Prompt_RU": item.get("image_prompt_ru", ""),
        "Image_URL_RU": item.get("image_url_ru", "") or None,
        "Hashtags_RU": hashtags_ru,
        "Status": item.get("status", "Draft"),
        "Tweet_URL": item.get("tweet_url", "") or None,
        "Week": week_of,
        "Client": client_id,
    }
    # Remove None values (Airtable rejects null for url fields)
    fields = {k: v for k, v in fields.items() if v is not None}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = f"{AIRTABLE_BASE_URL}/{base_id}/{table_id}"
    resp = requests.post(url, headers=headers, json={"fields": fields}, timeout=15)
    resp.raise_for_status()
    return resp.json()["id"]


def update_image_urls(
    base_id: str,
    table_id: str,
    record_id: str,
    image_url_en: str = None,
    image_url_ru: str = None,
    api_key: str = "",
):
    """Patch image URL fields on an existing record after image generation."""
    fields = {}
    if image_url_en:
        fields["Image_URL_EN"] = image_url_en
    if image_url_ru:
        fields["Image_URL_RU"] = image_url_ru
    if not fields:
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = f"{AIRTABLE_BASE_URL}/{base_id}/{table_id}/{record_id}"
    resp = requests.patch(url, headers=headers, json={"fields": fields}, timeout=15)
    resp.raise_for_status()


def load_records(base_id: str, table_id: str, api_key: str) -> list:
    """Fetch all records from a table. Returns list of {id, fields} dicts."""
    headers = {"Authorization": f"Bearer {api_key}"}
    records = []
    offset = None
    while True:
        params = {"pageSize": 100}
        if offset:
            params["offset"] = offset
        resp = requests.get(
            f"{AIRTABLE_BASE_URL}/{base_id}/{table_id}",
            headers=headers,
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break
        time.sleep(0.25)
    return records
```

**Files affected:**

- `scripts/airtable_writer.py` (new)

---

### Step 4: Modify `nano_banana.py` — R2 Upload Support

Add R2 upload after local save. Return both local path and R2 URL.

**Actions:**

- Add import: `import r2_uploader`
- Modify `generate_image(prompt, output_path, ..., upload_r2=True, client_id=None)` signature
- After `save_image(img_resp.content, output_path)` succeeds, add:
  ```python
  r2_url = None
  if upload_r2 and r2_uploader.is_configured():
      try:
          filename = Path(output_path).name
          week_of = filename.split("_")[0] if "_" in filename else "unknown"
          key = r2_uploader.make_key(client_id or "bobe", week_of, filename)
          r2_url = r2_uploader.upload_bytes(img_resp.content, key)
          print(f"  Uploaded to R2: {r2_url}")
      except Exception as e:
          print(f"  R2 upload failed (image saved locally): {e}")
  return str(output_path), r2_url
  ```
- Update `main()` CLI: Add `--no-r2` flag. Print R2 URL if uploaded.
- Existing callers that expect only a path string: update to unpack tuple `(path, r2_url)`.

**Files affected:**

- `scripts/nano_banana.py`

---

### Step 5: Modify `wavespeed_img.py` — R2 Upload Support

Same changes as Step 4 for the RU image generator.

**Actions:**

- Add import: `import r2_uploader`
- Modify `generate_image(prompt, output_path, ..., upload_r2=True, client_id=None)` signature
- After `Path(output_path).write_bytes(img_resp.content)`, add same R2 upload block as Step 4
- Return `(str(output_path), r2_url)` tuple
- Update `main()` CLI: Add `--no-r2` flag

**Files affected:**

- `scripts/wavespeed_img.py`

---

### Step 6: Modify `pipeline_runner.py` — Airtable-First + R2 Images

This is the largest change. Replace the Excel-primary flow with Airtable-primary.

**Actions:**

**6a. Add imports and setup (top of file):**
```python
import airtable_writer
import r2_uploader
```

**6b. After Phase 2 (bucket assembly), resolve Airtable table once:**
```python
# Resolve Airtable table for this week
at_api_key = airtable_writer.get_api_key(client_id)
at_base_id = config.get("airtable", {}).get("base_id", "")
at_table_id = None
use_airtable = config.get("airtable", {}).get("enabled", False) and at_base_id and at_api_key
if use_airtable:
    print("  Setting up Airtable table...")
    at_table_id = airtable_writer.get_or_create_table(at_base_id, week_of, at_api_key)
    print(f"  Airtable table: Week-{week_of} ({at_table_id})")
```

**6c. Phase 3 (workbook creation): Make conditional on `--export-excel` flag:**
```python
if args.export_excel:
    print("Phase 3: Creating workbook...")
    # ... existing workbook creation code ...
else:
    print("Phase 3: Skipped (Airtable-primary mode, use --export-excel to generate Excel)")
```

**6d. Phase 4 (content generation): After each item is generated, write to Airtable immediately:**

In the inner loop after `c = extract_json(response)`, build the `content_json` dict as before but add `image_url_en` and `image_url_ru` as empty strings (filled in Phase 5). Then:

```python
# Write to Airtable immediately
at_record_id = None
if use_airtable and platform == "Twitter":  # write once per topic (Twitter row)
    try:
        at_record_id = airtable_writer.write_record(
            at_base_id, at_table_id, content_json, week_of, client_id, at_api_key
        )
        topic_data["at_record_id"] = at_record_id  # store for Phase 5 image URL patch
        time.sleep(0.25)  # Airtable rate limit
    except Exception as e:
        print(f"    Warning: Airtable write failed: {e}")

# Also write Telegram row
if use_airtable and platform == "Telegram":
    try:
        airtable_writer.write_record(
            at_base_id, at_table_id, content_json, week_of, client_id, at_api_key
        )
        time.sleep(0.25)
    except Exception as e:
        print(f"    Warning: Airtable write failed: {e}")
```

Also keep the existing `weekly_pipeline.py save-content` call if `args.export_excel` is True.

**6e. Phase 5 (image generation): Upload to R2, patch Airtable record:**

After generating EN image:
```python
local_en, r2_url_en = nano_banana result  # unpack tuple
# Patch Airtable record with EN image URL
if use_airtable and r2_url_en and topic_data.get("at_record_id"):
    try:
        airtable_writer.update_image_urls(
            at_base_id, at_table_id, topic_data["at_record_id"],
            image_url_en=r2_url_en, api_key=at_api_key
        )
    except Exception as e:
        print(f"    Warning: Airtable image URL update failed: {e}")
```

Same for RU image → `image_url_ru`.

**6f. Remove Phase 6.5 (airtable_sync.py call)** — no longer needed since writing inline.

**6g. Add `--export-excel` CLI flag:**
```python
parser.add_argument("--export-excel", action="store_true",
    help="Also generate local Excel workbook (in addition to Airtable)")
```

**6h. Update `--skip-airtable` flag behavior**: Keep flag, but now it skips the inline Airtable writes too.

**Files affected:**

- `scripts/pipeline_runner.py`

---

### Step 7: Modify `web_viewer.py` — Read from Airtable

Replace `load_content()` (which reads local Excel) with Airtable API fetch.

**Actions:**

- Add imports: `import airtable_writer`
- Replace `load_content(date_key, client_id)` function:
  ```python
  def load_content(date_key: str, client_id: str = None) -> list:
      """Load content items from Airtable for the given week_of date."""
      client_id = client_id or get_active_client()
      cfg = client_config.load_config(client_id)
      at_cfg = cfg.get("airtable", {})
      if not at_cfg.get("enabled"):
          return []
      base_id = at_cfg["base_id"]
      api_key = airtable_writer.get_api_key(client_id)
      # Resolve week_of from date_key (e.g. "week:2026-03-02" → "2026-03-02")
      week_of = date_key.replace("week:", "").replace("mock:", "")
      try:
          table_id = airtable_writer.get_or_create_table(base_id, week_of, api_key)
          records = airtable_writer.load_records(base_id, table_id, api_key)
          return [r["fields"] for r in records]
      except Exception as e:
          print(f"Warning: Airtable load failed: {e}")
          return []
  ```
- Update image serving: Replace local image path serving with R2 URL passthrough. In Flask route that serves images, if content has `Image_URL_EN`, redirect to that URL instead of serving a local file.
- Update `get_available_dates()`: Query Airtable meta API for `Week-*` tables in the client's base instead of scanning local `outputs/content/{client}/` directory.

**Files affected:**

- `scripts/web_viewer.py`

---

### Step 8: Modify `build_static.py` — Read from Airtable, Use R2 Image URLs

**Actions:**

- Replace Excel reading logic with `airtable_writer.load_records()` call
- Remove the step that copies local images to `dist/` — images now load from R2 URLs directly in the generated HTML
- Update Jinja2 templates (or inline HTML generation): Replace `{% image_path %}` with `{% image_url_en %}` / `{% image_url_ru %}`
- Update `get_available_dates()` for static build: Read from Airtable meta (list Week-* tables) instead of local `outputs/` scan

**Files affected:**

- `scripts/build_static.py`

---

### Step 9: Update `clients/bobe/config.json`

Add R2 configuration section. Update `airtable.images_base_url` to reflect R2.

**Actions:**

Add to `clients/bobe/config.json`:
```json
"r2": {
  "enabled": true,
  "bucket_name": "bobe-content-images",
  "public_url": "https://pub-REPLACE_WITH_ACTUAL.r2.dev"
}
```

Update:
```json
"airtable": {
  "enabled": true,
  "base_id": "appikOGb5GyhPqoCd",
  "api_key_env": "AIRTABLE_API_KEY",
  "images_base_url": "https://pub-REPLACE_WITH_ACTUAL.r2.dev"
}
```

Also update `clients/_template/config.json` with the same `r2` section (with placeholder values).

**Files affected:**

- `clients/bobe/config.json`
- `clients/_template/config.json`

---

### Step 10: Update `.env`

**Actions:**

Add 5 new variables to `.env`:
```
R2_ACCOUNT_ID=<your Cloudflare account ID>
R2_ACCESS_KEY_ID=<R2 API token access key>
R2_SECRET_ACCESS_KEY=<R2 API token secret>
R2_BUCKET_NAME=bobe-content-images
R2_PUBLIC_URL=https://pub-XXXXX.r2.dev
```

**Files affected:**

- `.env` (gitignored, manual user edit)

---

### Step 11: Update GitHub Actions Workflows

**Actions:**

In `.github/workflows/weekly-pipeline.yml`:

1. **Add R2 secrets to env block** (alongside existing APIFY, GOOGLE_AI, etc.):
   ```yaml
   R2_ACCOUNT_ID: ${{ secrets.R2_ACCOUNT_ID }}
   R2_ACCESS_KEY_ID: ${{ secrets.R2_ACCESS_KEY_ID }}
   R2_SECRET_ACCESS_KEY: ${{ secrets.R2_SECRET_ACCESS_KEY }}
   R2_BUCKET_NAME: ${{ secrets.R2_BUCKET_NAME }}
   R2_PUBLIC_URL: ${{ secrets.R2_PUBLIC_URL }}
   ```

2. **Add boto3 to pip install**:
   ```yaml
   pip install requests openpyxl google-genai python-dotenv jinja2 flask pillow boto3
   ```

3. **Remove the explicit Excel artifact upload step** (or demote to conditional if `--export-excel` flag is added to the workflow).

4. **Update pipeline command**: Add `--export-excel` flag to workflow inputs (optional, default: false) so Excel generation can be triggered on demand.

In `.github/workflows/regenerate-item.yml`:
- Add the same 5 R2 env vars (regen also generates images that need uploading).

In `.github/workflows/generate-announcement.yml`:
- Add the same 5 R2 env vars.

**Files affected:**

- `.github/workflows/weekly-pipeline.yml`
- `.github/workflows/regenerate-item.yml`
- `.github/workflows/generate-announcement.yml`

---

### Step 12: Install boto3 in venv

**Actions:**

```bash
./venv/bin/pip install boto3
```

Verify:
```bash
./venv/bin/python -c "import boto3; print(boto3.__version__)"
```

**Files affected:**

- `venv/` (no tracked files change)

---

### Step 13: Test End-to-End (Mock Mode)

**Actions:**

1. Run pipeline in mock + R2 mode:
   ```bash
   ./venv/bin/python scripts/pipeline_runner.py --client bobe --week-of 2026-03-09 --mock
   ```
   Expected: Airtable table `Week-2026-03-09` created, mock content rows written.

2. Run pipeline in real mode (small):
   ```bash
   ./venv/bin/python scripts/pipeline_runner.py --client bobe --week-of 2026-03-09 --skip-images
   ```
   Expected: Real content generated and written to Airtable, no images.

3. Test image upload:
   ```bash
   ./venv/bin/python scripts/r2_uploader.py  # add a simple test in __main__
   ```
   Expected: Test PNG uploaded to R2, public URL returned and accessible in browser.

4. Test Flask dashboard:
   ```bash
   ./venv/bin/python scripts/web_viewer.py
   ```
   Open http://localhost:5001 — content loads from Airtable, images load from R2 URLs.

**Files affected:**

- None (validation only)

---

### Step 14: Update CLAUDE.md

**Actions:**

- Update **Scripts table**: `airtable_sync.py` → "Backfill utility only (not called in main pipeline)"; add `r2_uploader.py` and `airtable_writer.py` rows
- Update **Pipeline Structure section**: Replace "Excel workbook" references with "Airtable (primary)". Update image step to mention R2 upload.
- Update **API Requirements table**: Add R2 row with 5 env vars
- Update **Deployment section**: Note that images are now served from R2 (not GitHub Pages)
- Update **Weekly Pipeline Structure**: Note that Excel is opt-in (`--export-excel`)

**Files affected:**

- `CLAUDE.md`

---

## Connections & Dependencies

### Files That Reference This Area

- `.github/workflows/weekly-pipeline.yml` — calls `pipeline_runner.py`, uploads artifacts
- `.github/workflows/regenerate-item.yml` — regenerates images (needs R2 upload)
- `.github/workflows/generate-announcement.yml` — generates content (needs Airtable write)
- `scripts/x_publisher.py` — reads from Excel to update Status/Tweet_URL cols. After this plan, should update Airtable instead (out of scope — note for follow-up)
- `scripts/client_config.py` — `load_config()` used by all scripts; no change needed but add `r2` section to the reference template

### Updates Needed for Consistency

- `scripts/x_publisher.py`: Currently reads/writes Excel. After this plan, it should update the Airtable record's `Status` and `Tweet_URL` fields directly. This is a follow-up task.
- `clients/_template/config.json`: Add `r2` section so new clients created via `/onboard-client` get the R2 config scaffold.
- `reference/airtable-client-setup.md`: Add note that `Image_URL_EN` and `Image_URL_RU` are now URL-type fields (not text), and that R2 setup is required.

### Impact on Existing Workflows

- **`/weekly-pipeline` command**: No change from user perspective. Behind the scenes, writes to Airtable + R2 instead of Excel. Add note that `--export-excel` can be passed for a local copy.
- **`/deploy` command**: Still works — `build_static.py` now reads from Airtable instead of Excel. No change needed in the command itself.
- **`/view-content` command**: Still launches Flask on port 5001 — but now reads from Airtable live.
- **Regen buttons on live dashboard**: Still trigger GitHub Actions workflows. The regen workflow generates a new image and needs to upload to R2 + update the Airtable record (not rebuild the Excel).

---

## Validation Checklist

- [ ] `./venv/bin/pip install boto3` succeeds
- [ ] `r2_uploader.is_configured()` returns True with correct `.env` values
- [ ] Test image upload: bytes upload to R2, public URL is accessible in browser
- [ ] `airtable_writer.get_or_create_table()` creates `Week-{week_of}` with correct 18-field schema
- [ ] Mock pipeline run writes rows to Airtable (check Airtable UI)
- [ ] Real pipeline run with `--skip-images`: content rows appear in Airtable immediately after each item (not at the end)
- [ ] Real pipeline run with images: `Image_URL_EN` and `Image_URL_RU` populated in Airtable; URLs load in browser
- [ ] `web_viewer.py` at http://localhost:5001 shows content from Airtable, images from R2
- [ ] `build_static.py` produces correct `dist/` HTML with R2 image URLs (not local paths)
- [ ] GitHub Actions `weekly-pipeline.yml` run completes with R2 secrets; no artifact upload errors
- [ ] `--export-excel` flag still produces a local `.xlsx` file (backwards-compat check)
- [ ] `CLAUDE.md` updated to reflect new architecture

---

## Success Criteria

The implementation is complete when:

1. Running `/weekly-pipeline` produces no local Excel file by default; content appears in Airtable and images load from R2 URLs in the Airtable records within minutes of generation.
2. The Flask dashboard (`/view-content`) shows the current week's content reading live from Airtable, with images served directly from R2 — no local `outputs/` folder required.
3. GitHub Actions pipeline runs end-to-end (scrape → generate → R2 upload → Airtable write → static deploy) with all content and images permanently accessible via cloud URLs.

---

## Notes

- **R2 folder structure**: Keys follow `{client_id}/{week_of}/{filename}.png` — this keeps multi-client images separated in one bucket and makes it easy to audit or delete a whole week.
- **Old weeks (2026-02-16, 2026-03-02)**: Images for these are on GitHub Pages. The `airtable_sync.py` script (in backfill mode) can re-push those records unchanged. Optionally, old images can be manually uploaded to R2 and the Airtable records updated — but this is not required.
- **`x_publisher.py` follow-up**: Currently updates the Excel Status and Tweet_URL columns. After this plan, it should patch the Airtable record instead. Recommended as the next plan after this one.
- **Cost at scale**: At 42 images/week × 52 weeks = 2,184 images/year. Average image size ~500KB = ~1.1GB/year. Well within R2's 10GB free tier. Airtable free plan allows 1,000 records/base — at 42 rows/week that's ~23 weeks per table. Airtable's `Plus` plan ($10/month) allows 5,000 records. Since tables are per-week (separate tables), free tier should be fine indefinitely.
- **Cloudflare R2 public access**: Must be explicitly enabled per-bucket. The public URL format `https://pub-{hash}.r2.dev` is assigned automatically when enabling public access. A custom domain (e.g., `https://images.rejiglabs.com`) can be added later via Cloudflare DNS without changing code — just update `R2_PUBLIC_URL`.

---

## Implementation Notes

**Implemented:** 2026-03-05

### Summary

- Created `scripts/r2_uploader.py` — S3-compatible R2 upload module (boto3)
- Created `scripts/airtable_writer.py` — inline Airtable write module (18-field schema, per-item writes, `records_to_topics()` for dashboard compat)
- Created `reference/r2-setup.md` — 7-step R2 setup guide
- Modified `scripts/nano_banana.py` — returns `(local_path, r2_url)` tuple; `--no-r2` flag
- Modified `scripts/wavespeed_img.py` — same R2 upload pattern; `--no-r2` flag
- Modified `scripts/pipeline_runner.py` — Airtable inline writes (Phase 4), R2 direct upload (Phase 5), `--export-excel` flag; Excel demoted to opt-in
- Modified `scripts/web_viewer.py` — loads from Airtable first (via `list_week_tables`), falls back to Excel; `image_src`/`image_src_ru` fields handle R2 URLs vs local paths
- Modified `scripts/build_static.py` — same Airtable-first load; skips R2 URLs during image copy
- Modified `clients/bobe/config.json` — added `r2` section
- Modified `clients/_template/config.json` — added `r2` section with disabled defaults
- Modified `.env` — added R2 placeholder vars
- Modified `.github/workflows/weekly-pipeline.yml` — boto3, R2 secrets in both generate and deploy jobs
- Modified `.github/workflows/regenerate-item.yml` — boto3, R2 secrets in both jobs
- Modified `.github/workflows/generate-announcement.yml` — boto3, R2 secrets

### Deviations from Plan

- R2 upload in `pipeline_runner.py` is done directly (not via subprocess return value) — subprocesses use `--no-r2` flag, then runner calls `r2_uploader.upload_file()` after subprocess completes. This avoids subprocess return-value parsing complexity.
- `web_viewer.py` template uses `image_src`/`image_src_ru` instead of `image_filename` for both R2 URLs and local paths.

### Issues Encountered

- `web_viewer.py` edit failed with "File has been modified since read" — a linter modified `wavespeed_img.py` during the same session, causing the read cache to mismatch. Fixed by re-reading before editing.
