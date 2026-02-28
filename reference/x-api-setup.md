# X (Twitter) API Setup Guide

This guide walks through setting up X developer credentials for direct publishing from the content dashboard.

---

## Overview

Each client has their own X developer app. Credentials are stored in `.env` (local) and GitHub Secrets (remote). The platform uses OAuth 1.0a for write access (posting tweets).

**Free tier rate limits:** 17 write operations per 24 hours. A 5-tweet thread = 5 writes. Post one thread at a time and plan accordingly.

---

## Step 1: Apply for a Developer Account

1. Go to [developer.twitter.com](https://developer.twitter.com/)
2. Log in with the X account that will post content (the client's brand account)
3. Click **Sign up for Free Account** (or **Developer Portal** if you already have access)
4. Fill in the use case form — describe your intent as: "Automated publishing of pre-written content threads for social media marketing"
5. Submit and wait for approval (can take 1-3 days for new accounts)

> **Note:** Apply early. Approval is not instant. The rest of the setup can be done while waiting.

---

## Step 2: Create a Project and App

1. In the Developer Portal, click **Projects & Apps** in the left sidebar
2. Click **+ New Project**
3. Name it (e.g., "BoBe Content Publisher") and select your use case
4. Under the project, click **+ Add App** or **Create a new App**
5. Name the app (e.g., "bobe-publisher")

---

## Step 3: Set App Permissions to Read and Write

1. In your app settings, click **App permissions**
2. Change from "Read" to **Read and Write**
3. Save changes

> This is required to post tweets. Read-only apps cannot create tweets.

---

## Step 4: Generate Credentials

1. Go to your app's **Keys and Tokens** tab
2. Generate and copy the following (save them immediately — they won't be shown again):
   - **API Key** (Consumer Key)
   - **API Key Secret** (Consumer Secret)
   - **Access Token** (for the account that owns the app)
   - **Access Token Secret**

---

## Step 5: Add to Local `.env`

Add the credentials to your `.env` file using the pattern `{CLIENT_ID_UPPER}_X_*`:

```bash
# BoBe client X credentials
BOBE_X_API_KEY=your_api_key_here
BOBE_X_API_SECRET=your_api_secret_here
BOBE_X_ACCESS_TOKEN=your_access_token_here
BOBE_X_ACCESS_TOKEN_SECRET=your_access_token_secret_here
```

For other clients, replace `BOBE` with the client ID in uppercase:
```bash
# Example: client ID "acmecrypto" → prefix "ACMECRYPTO"
ACMECRYPTO_X_API_KEY=...
ACMECRYPTO_X_API_SECRET=...
ACMECRYPTO_X_ACCESS_TOKEN=...
ACMECRYPTO_X_ACCESS_TOKEN_SECRET=...
```

---

## Step 6: Add to GitHub Secrets

1. Go to your repo on GitHub: `Settings → Secrets and variables → Actions`
2. Click **New repository secret** and add each credential:

| Secret Name | Value |
|-------------|-------|
| `BOBE_X_API_KEY` | Your API Key |
| `BOBE_X_API_SECRET` | Your API Key Secret |
| `BOBE_X_ACCESS_TOKEN` | Your Access Token |
| `BOBE_X_ACCESS_TOKEN_SECRET` | Your Access Token Secret |

---

## Step 7: Enable in Client Config

Open `clients/bobe/config.json` and set:

```json
"x_publishing": {
  "enabled": true,
  "x_handle": "@your_x_handle"
}
```

---

## Step 8: Deploy Dashboard

Run `/deploy` to rebuild the static site. The **Publish to X** button will appear on Twitter cards in the live dashboard after the next deploy.

---

## Testing

### Local mock test (no credentials needed)

```bash
# Add mock values to .env
echo "BOBE_X_API_KEY=mock" >> .env
echo "BOBE_X_API_SECRET=mock" >> .env
echo "BOBE_X_ACCESS_TOKEN=mock" >> .env
echo "BOBE_X_ACCESS_TOKEN_SECRET=mock" >> .env

# Enable in config (set x_publishing.enabled = true)

# Run dry run
venv/bin/python scripts/x_publisher.py \
  --client bobe \
  --week-of 2026-02-16 \
  --topic-index 0 \
  --mock
# Expected: prints tweets + TWEET_URLS:["mock://tweet/1",...], exits 0
```

### Local Flask dashboard test

```bash
venv/bin/python scripts/web_viewer.py
# Open localhost:5001
# Twitter tab of each card should show "Publish to X" button (if enabled)
# Click to publish topic 0 in mock mode via the endpoint
```

### Duplicate prevention test

```bash
# Run again with same topic-index (after a successful publish)
venv/bin/python scripts/x_publisher.py --client bobe --week-of 2026-02-16 --topic-index 0
# Expected: "Already published" message, exits 0, no API call made
```

### Remote test (GitHub Actions)

1. Ensure `BOBE_X_*` secrets are added to GitHub repo
2. Go to Actions tab → **Publish to X (Twitter)** → **Run workflow**
3. Enter `client_id`, `week_of`, `topic_index`
4. Verify: logs show tweet URLs, commit step shows xlsx change, deploy completes
5. Open live dashboard: card shows "Published ✓" with disabled button

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `403 Forbidden` when posting | App permissions not set to "Read and Write" — update in Developer Portal |
| `401 Unauthorized` | Credentials are wrong or access tokens regenerated — re-copy from Developer Portal |
| `429 Too Many Requests` | Hit 17 writes/24hr free tier limit — wait and try again next day |
| Button doesn't appear | Check `x_publishing.enabled = true` in config.json and redeploy |
| `tweepy not installed` | Run `venv/bin/pip install tweepy` |
| Developer account pending approval | Apply early — approval can take 1-3 business days |
