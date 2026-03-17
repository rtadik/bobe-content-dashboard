# Client API Setup Tutorials

Step-by-step instructions for connecting your API keys. These tutorials are shown inline on the Settings page.

---

## Google AI (Gemini) — Content Generation

Used to generate your social media copy and translations.

1. Go to [aistudio.google.com](https://aistudio.google.com/)
2. Sign in with your Google account
3. Click "Get API Key" in the top menu
4. Click "Create API Key" and select a project (or create one)
5. Copy the generated key (starts with `AIza...`)
6. Paste it into the Google AI field on your Settings page

**Free tier**: 15 requests/minute, 1M tokens/day. More than enough for weekly content generation.

---

## WaveSpeed — Image Generation

Used to generate branded images for your posts (English).

1. Go to [wavespeed.ai](https://wavespeed.ai/)
2. Create an account or sign in
3. Go to Account > API Keys
4. Click "Create New Key"
5. Copy the key
6. Paste it into the WaveSpeed field on your Settings page

**Pricing**: Pay-per-image. Each weekly batch uses ~21 EN images. Budget ~$2-5/week depending on model.

---

## WaveSpeed RU — Russian Image Generation (Optional)

Used to generate images with Cyrillic text overlays. Uses the same WaveSpeed account.

If you want Russian language images, paste the same WaveSpeed API key into the "WaveSpeed RU" field. If you skip this, only English images will be generated.

---

## Airtable — Content Storage

Used to store and organize your generated content.

1. Go to [airtable.com](https://airtable.com/) and create a free account
2. Create a new Base (e.g., "My Content")
3. Copy the Base ID from the URL: `https://airtable.com/appXXXXXXXXXXXXXX/...` — the part starting with `app` is your Base ID
4. Go to [airtable.com/create/tokens](https://airtable.com/create/tokens)
5. Click "Create new token"
6. Name it (e.g., "Content Platform")
7. Add scopes: `data.records:write`, `data.records:read`, `schema.bases:write`, `schema.bases:read`
8. Add access to your base
9. Click "Create token" and copy it (starts with `pat...`)
10. Paste the API Key and Base ID into the Airtable fields on your Settings page

**Free tier**: 1,000 records per base, 1 GB attachments. Sufficient for ~12 weeks of content.

---

## Apify — Trending Topic Scraping

Used to scrape Twitter/X and Reddit for trending topics in your niche.

1. Go to [console.apify.com](https://console.apify.com/)
2. Create a free account
3. Go to Settings > Integrations
4. Copy your API Token
5. Paste it into the Apify field on your Settings page

**Free tier**: $5/month credit (enough for weekly scraping).

---

## X (Twitter) Publishing (Optional)

Used to publish threads directly from the dashboard.

1. Go to [developer.x.com](https://developer.x.com/)
2. Sign up for a developer account (Free tier available)
3. Create a new App in the Developer Portal
4. Go to your app's "Keys and Tokens" page
5. Under "Consumer Keys", copy API Key and API Secret
6. Under "Authentication Tokens", generate Access Token and Secret
7. Make sure your app has **Read and Write** permissions
8. Paste all 4 values into the X Publishing fields on your Settings page

**Note**: Free tier allows 1,500 tweets/month. More than enough for weekly content.
