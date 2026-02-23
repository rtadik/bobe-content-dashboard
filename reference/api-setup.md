# API Setup Guide

Setup instructions for all external APIs used by the BoBe content pipeline.

---

## Environment Variables

All API keys are stored in `.env` at the project root. This file is gitignored and never committed.

```bash
APIFY_API_TOKEN=your_token_here
GOOGLE_AI_API_KEY=your_key_here
WAVESPEED_API_KEY=your_key_here
AIRTABLE_API_KEY=your_pat_token_here   # Optional — only needed if airtable.enabled in client config
```

To load them in your shell session:
```bash
source .env
# or use a tool like direnv
```

---

## Apify (Twitter + Reddit Scraping)

**Used by:** `scripts/apify_scraper.py`

### Getting Your Token
1. Sign up at [apify.com](https://apify.com)
2. Go to Console → Account → Integrations
3. Copy your **API token**
4. Set: `APIFY_API_TOKEN=your_token`

### Actors Used

| Platform | Actor ID | Actor Name |
|----------|----------|------------|
| Twitter/X | `apidojo/tweet-scraper` | Tweet Scraper V2 |
| Reddit | `trudax/reddit-scraper` | Reddit Scraper |

### Usage & Costs
- Free tier: $5/month in credits included
- Tweet Scraper: ~$0.50–$1 per 1,000 tweets
- Reddit Scraper: ~$0.25–$0.50 per 1,000 posts
- Typical daily pipeline run: ~$0.05–$0.20

### Rate Limits
- Apify runs are asynchronous; allow 30–120 seconds for results
- Do not run more than 5 concurrent actors on free tier

---

## Google AI (Nano Banana Pro / Gemini Image Generation)

**Used by:** `scripts/nano_banana.py`

### Getting Your Key
1. Go to [Google AI Studio](https://ai.google.dev/)
2. Sign in with Google account
3. Click **Get API key** → Create API key
4. Set: `GOOGLE_AI_API_KEY=your_key`

### Model Used
- **Model ID:** `gemini-3-pro-image-preview`
- Other available image models: `gemini-2.0-flash-exp-image-generation`, `gemini-2.5-flash-image`

### Billing Requirement
Image generation models have **free tier quota = 0** — billing must be enabled:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select the project linked to your AI Studio key
3. Enable billing (add a payment method)
4. Image generation will then work at standard pay-per-use rates

### Usage & Costs
- Requires billing enabled (no free tier for image generation)
- `gemini-3-pro-image-preview`: ~$0.013–$0.04 per image
- Typical daily pipeline: 3–6 images = ~$0.05–$0.25

### Rate Limits
- Free tier: 15 requests/minute, 1,500/day
- Images may take 10–30 seconds to generate

---

---

## Airtable (Content Delivery — Optional)

**Used by:** `scripts/airtable_sync.py`

Airtable is opt-in per client. When enabled, all 42 weekly content rows are automatically pushed to the client's Airtable base after the pipeline finishes.

For a complete step-by-step setup guide (including token creation, scopes, and troubleshooting), see:

**`reference/airtable-client-setup.md`**

### Quick Setup Summary

1. Create a free Airtable account at [airtable.com](https://airtable.com)
2. Create a new Base for the client
3. Copy the Base ID from the URL (`appXXXXXXXXXX`)
4. Create a Personal Access Token at [airtable.com/create/tokens](https://airtable.com/create/tokens)
   - Required scopes: `data.records:write` + `schema.bases:write`
5. Add to `.env`: `AIRTABLE_API_KEY=pat...your_token`
6. Update client config: `"airtable": {"enabled": true, "base_id": "appXXXX..."}`

### Usage & Costs

- **Free tier:** 1,000 records/base (~23 weeks at 42 records/week), unlimited bases
- **Team plan:** $20/user/month for 50,000 records/base
- **API calls:** Free tier includes 1,000 API calls/month — enough for ~23 weekly syncs

---

## GitHub Actions (Remote Pipeline Execution)

**Used by:** `.github/workflows/weekly-pipeline.yml`, `.github/workflows/onboard-client.yml`, `admin/index.html`

GitHub Actions runs the full pipeline on GitHub's servers, triggered via the admin panel or GitHub UI. No local machine required.

For complete setup instructions including Secrets, Pages settings, workflow permissions, and PAT creation, see:

**`reference/github-actions-setup.md`**

### Quick Setup Summary

1. Add all four API keys as GitHub Secrets in the repo settings
2. Enable GitHub Pages on the `gh-pages` branch
3. Set workflow permissions to "Read and write"
4. Create a GitHub PAT with `actions:write` scope for the admin panel

---

## Python Dependencies

Install before running any scripts:

```bash
pip install requests openpyxl google-genai python-dotenv
```

Or using a virtual environment (recommended):

```bash
python3 -m venv venv
source venv/bin/activate
pip install requests openpyxl google-genai python-dotenv
```

### Full requirements:
```
requests>=2.28.0
openpyxl>=3.1.0
google-genai>=1.0.0
python-dotenv>=1.0.0
```

---

## Verifying Setup

Run the test commands to verify each API is working:

```bash
# Test Apify
python scripts/apify_scraper.py --mock

# Test image generation
python scripts/nano_banana.py --mock

# Test Excel manager
python scripts/excel_manager.py --action create --date 2026-02-18 --mock
```

All scripts support `--mock` flag to test without making real API calls.
