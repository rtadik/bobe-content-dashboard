# Airtable Setup Guide for Clients

This guide explains how to set up Airtable so your generated content is automatically delivered to a private Airtable base after each pipeline run. You will be able to view, filter, approve, and track all content without needing any files shared.

---

## What You Get

- A private Airtable base with your content
- One table per week (e.g., `Week-2026-02-23`)
- 16 fields per row: date, topic, platform, full content (EN + RU), image paths, hashtags, status
- Native Airtable features: gallery view, filter by platform/status, share links, comment threads

---

## Step 1: Create a Free Airtable Account

1. Go to [airtable.com](https://airtable.com) and click **Sign up**
2. Create a free account (no credit card required)
3. The free plan supports unlimited bases and up to 1,000 records per base
   - At 42 records/week, this covers approximately 23 weeks (~6 months) of content
   - Upgrade to Airtable Team ($20/month) for 50,000 records/base if needed

---

## Step 2: Create Your Content Base

1. Log in to Airtable
2. From your home screen, click **+ Create** → **Start from scratch**
3. Name the base after your brand (e.g., `BoBe Content` or `My Brand Content`)
4. Click **Create base** — you'll see an empty table

**Copy your Base ID:**

- Look at the URL in your browser — it will look like:
  `https://airtable.com/appXXXXXXXXXXXX/tblXXXXXXXXXXXX/...`
- The Base ID is the part starting with `app`: `appXXXXXXXXXXXX`
- Copy and save this — you'll need it in Step 4

> **Official Airtable docs:** [Find your Base ID](https://support.airtable.com/docs/finding-airtable-ids)

---

## Step 3: Create a Personal Access Token

Airtable uses Personal Access Tokens (PATs) for API access — not the older API keys.

1. Go to [airtable.com/create/tokens](https://airtable.com/create/tokens)
2. Click **+ Create new token**
3. Give it a name (e.g., `Content Pipeline`)
4. **Required scopes** — add exactly these two:
   - `data.records:write` — allows creating records in your tables
   - `schema.bases:write` — allows creating new tables (one per week)
5. **Access** — click **+ Add a base** and select your content base
6. Click **Create token**
7. **Copy the token now** — it will only be shown once

The token looks like: `patXXXXXXXXXXXXXX.XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`

> **Official Airtable docs:** [Create and use Personal Access Tokens](https://support.airtable.com/docs/creating-and-using-api-keys-and-access-tokens)

---

## Step 4: Add Your Credentials to the Pipeline

**4a. Add the token to your `.env` file:**

Open the `.env` file in the project root and add:

```
AIRTABLE_API_KEY=patXXXXXXXXXXXXXX.XXXX...your_full_token_here
```

**4b. Add the Base ID to your client config:**

Open `clients/{your_client_id}/config.json` and update the `airtable` section:

```json
"airtable": {
  "enabled": true,
  "base_id": "appXXXXXXXXXXXX",
  "api_key_env": "AIRTABLE_API_KEY"
}
```

Replace `appXXXXXXXXXXXX` with your actual Base ID from Step 2.

---

## Step 5: Test the Connection

Run a mock sync to verify the credentials are correct (no API calls, no records created):

```bash
source venv/bin/activate
python scripts/airtable_sync.py --week-of 2026-02-23 --mock
```

Expected output:
```
Airtable Sync — [Your Brand] ([client_id])
Week: 2026-02-23
[MOCK] Would check/create table 'Week-2026-02-23' in base app...
[MOCK] Would push 42 records to table tblMOCK000000 in base app...
```

If you see an error, check:
- Token is fully copied (they are long — `pat...` followed by a long string after the `.`)
- Token has both required scopes (`data.records:write` and `schema.bases:write`)
- Base ID starts with `app` and is correct
- `airtable.enabled` is `true` in config.json

---

## Step 6: Run Your First Sync

After the next `/weekly-pipeline` run, Airtable sync happens automatically in Phase 6.5.

Or trigger a manual sync on an existing workbook:

```bash
source venv/bin/activate
python scripts/airtable_sync.py --week-of YYYY-MM-DD
```

---

## What the Airtable Table Looks Like

Each week creates a new table (`Week-YYYY-MM-DD`) with these fields:

| Field | Description |
|---|---|
| Date | Post date (YYYY-MM-DD) |
| Day | Day of week (Mon, Tue, etc.) |
| Topic | The content topic |
| Platform | Twitter or Telegram |
| Format | thread, single, or post |
| Content | Full English content |
| Image_Prompt | Prompt used to generate the image |
| Image_Path | Local file path to the generated image |
| Hashtags | English hashtags |
| Content_RU | Full Russian content |
| Image_Prompt_RU | Russian image prompt |
| Image_Path_RU | Local path to Russian image |
| Hashtags_RU | Russian hashtags |
| Status | Draft / Approved / Scheduled |
| Week | Week start date |
| Client | Client ID |

---

## Enabling Inline Image Previews

By default, image fields are stored as plain text file paths. To make images appear inline as viewable thumbnails in Airtable:

**Step 1: Deploy your content dashboard**

Run the deploy command to publish your images to GitHub Pages:

```bash
# In Claude Code
/deploy
```

This publishes your generated images to: `https://rtadik.github.io/bobe-content-dashboard`

**Step 2: Add the deployed URL to your client config**

Open `clients/{client_id}/config.json` and set `airtable.images_base_url`:

```json
"airtable": {
  "enabled": true,
  "base_id": "appXXXXXXXXXX",
  "api_key_env": "AIRTABLE_API_KEY",
  "images_base_url": "https://rtadik.github.io/bobe-content-dashboard"
}
```

> **BoBe note:** This is already configured. No action needed for BoBe.

**Step 3: Sync again**

The next `/weekly-pipeline` run will automatically attach images. Or manually re-sync:

```bash
source venv/bin/activate
python scripts/airtable_sync.py --week-of YYYY-MM-DD
```

Images will now appear as inline thumbnails in Airtable's gallery view.

> **Note:** Images must be deployed before syncing. The Airtable attachment URL points to GitHub Pages — if the image is not yet deployed, the attachment will show a broken link. Always run `/deploy` before syncing when you want inline images.

> **Text-only mode:** Run with `--skip-images` to push content without attaching images (useful for reviewing copy before images are finalized).

---

## Tips for Using Airtable

**Switch to Gallery view** to see content cards visually:
- Click the view switcher (top left) → **Gallery** → group by Platform

**Filter by Status** to see only Draft items:
- Click **Filter** → Status is "Draft"

**Share a view with your team:**
- Click **Share** → Create a shared link (read-only or edit)

**Mark content as Approved:**
- Click the Status field in any row → change to "Approved"

---

## Free Tier Limits

| Limit | Free Plan | Team Plan ($20/user/month) |
|---|---|---|
| Records per base | 1,000 | 50,000 |
| Bases | Unlimited | Unlimited |
| Collaborators | Unlimited | Unlimited |
| API calls | 1,000/month | Unlimited |

At 42 records/week, the free plan lasts approximately **23 weeks** per base. After that:
- Create a new base and update `airtable.base_id` in config.json, OR
- Upgrade to Team plan

---

## Troubleshooting

| Error | Likely Cause | Fix |
|---|---|---|
| `401 Unauthorized` | Wrong or expired token | Regenerate token at airtable.com/create/tokens |
| `403 Forbidden` | Token missing required scope | Add `data.records:write` and `schema.bases:write` scopes |
| `404 Not Found` | Wrong base_id | Check `airtable.base_id` in config.json matches URL |
| `AIRTABLE_API_KEY not set` | Missing from .env | Add `AIRTABLE_API_KEY=pat...` to .env |
| `airtable.enabled is false` | Config not updated | Set `"enabled": true` in config.json |
