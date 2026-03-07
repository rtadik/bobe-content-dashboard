# Cloudflare R2 Setup Guide

One-time setup for image cloud storage. R2 is free up to 10 GB storage and 10M reads/month with zero egress fees.

---

## Step 1: Create R2 Bucket

1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Go to **R2 Object Storage** (left sidebar)
3. Click **Create bucket**
4. Name: `bobe-content-images` (or `{client-id}-content-images` for future clients)
5. Leave all other settings default → **Create bucket**

---

## Step 2: Enable Public Access

1. Inside the bucket → **Settings** tab
2. Scroll to **Public access** → click **Allow Access**
3. Confirm — Cloudflare assigns a public URL in the format:
   ```
   https://pub-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX.r2.dev
   ```
4. **Copy this URL** — you'll need it as `R2_PUBLIC_URL`

---

## Step 3: Create R2 API Token

1. In Cloudflare Dashboard → **R2** → **Manage R2 API Tokens** (top right)
2. Click **Create API Token**
3. Name: `bobe-content-pipeline`
4. Permissions: **Object Read & Write**
5. Specify bucket: select `bobe-content-images` (scope to this bucket only)
6. Click **Create API Token**
7. **Save both values shown:**
   - Access Key ID
   - Secret Access Key

> These are only shown once. Store them securely.

---

## Step 4: Get Your Cloudflare Account ID

1. In Cloudflare Dashboard, look at the right sidebar on any page
2. Under **Account ID** — copy the value
3. Format: `a1b2c3d4e5f6...` (32-character hex string)

---

## Step 5: Add to `.env`

Open `.env` in the project root and add:

```
R2_ACCOUNT_ID=your_cloudflare_account_id
R2_ACCESS_KEY_ID=your_r2_access_key_id
R2_SECRET_ACCESS_KEY=your_r2_secret_access_key
R2_BUCKET_NAME=bobe-content-images
R2_PUBLIC_URL=https://pub-XXXXXXXX.r2.dev
```

> Replace all placeholder values with your actual credentials.

---

## Step 6: Add to GitHub Secrets

For GitHub Actions pipelines to upload images to R2, add the same 5 variables as repository secrets:

1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Add each secret:
   - `R2_ACCOUNT_ID`
   - `R2_ACCESS_KEY_ID`
   - `R2_SECRET_ACCESS_KEY`
   - `R2_BUCKET_NAME`
   - `R2_PUBLIC_URL`

---

## Step 7: Update `clients/bobe/config.json`

Update the `r2` section with your actual public URL:

```json
"r2": {
  "enabled": true,
  "bucket_name": "bobe-content-images",
  "public_url": "https://pub-XXXXXXXX.r2.dev"
}
```

Also update `airtable.images_base_url` to the same R2 public URL.

---

## Verification

Run this to confirm credentials are working:

```bash
./venv/bin/python scripts/r2_uploader.py --test
```

Expected output:
```
R2 configured: True
Uploading test image...
Test URL: https://pub-XXX.r2.dev/test/test-upload.png
Upload successful.
```

---

## R2 Object Key Structure

Images are stored under:
```
{client_id}/{week_of}/{filename}.png
```

Example:
```
bobe/2026-03-09/2026-03-09_mon_automated_trading_twitter.png
bobe/2026-03-09/2026-03-09_mon_automated_trading_twitter_ru.png
```

This keeps multi-client images organized in a single bucket and makes it easy to audit or delete a whole week's images.

---

## Cost Estimate

At 42 images/week × ~500KB each = ~21 MB/week = ~1.1 GB/year.
Well within the 10 GB free tier. At current growth, no cost expected for 5+ years.
