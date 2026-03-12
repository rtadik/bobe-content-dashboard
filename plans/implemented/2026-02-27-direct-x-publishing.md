# Plan: Direct X (Twitter) Publishing

**Date:** 2026-02-27
**Status:** Implemented 2026-02-28
**Context:** The platform generates Twitter threads but delivers them only as Excel/Airtable exports. Adding direct X publishing removes the last manual step: clients can publish from the dashboard with one click, from their own X account.

---

## Architecture Summary

- Each client has their own X developer app credentials (4 OAuth 1.0a keys)
- Credentials stored in `.env` (local) and GitHub Secrets (remote) — never committed
- MVP: per-topic immediate publish only (one thread at a time)
- Local: Flask `/api/publish-to-x` endpoint → runs `x_publisher.py` subprocess
- Remote: "Publish to X" button on static dashboard → triggers `publish-to-x.yml` GitHub Actions
- After publishing: workbook updated (Status="Published", tweet URLs in new col 16), static site redeployed

---

## Files Created

### `scripts/x_publisher.py`
Core publish script. CLI: `--client`, `--week-of`, `--topic-index`, `--mock`, `--lang`

Key functions:
- `load_x_client(client_id)` — loads OAuth1.0a tweepy.Client from env credentials
- `split_thread(content)` — splits on `---`, warns if any tweet > 280 chars
- `post_thread(client, tweets, mock=False)` — posts sequentially with in_reply_to chain; handles TooManyRequests with one retry
- `read_twitter_rows(excel_path, topic_index)` — maps 0-based index to Excel rows for that topic (platform=twitter); supports both old (14-col) and new (15-col) schema
- `update_excel_after_publish(excel_path, row_nums, tweet_urls)` — sets Status col (O)="Published", Tweet_URL col (P)=comma-joined URLs; creates col P header if absent; emits `TWEET_URLS:[...]` to stdout
- `main()` — argparse → check enabled → get creds → find excel → read rows → check if published → split → post → update

**Duplicate prevention:** if Status already "Published", prints message and exits 0.
**Output protocol:** prints `TWEET_URLS:[...]` as last line for Flask subprocess parser.

### `.github/workflows/publish-to-x.yml`
Two-job workflow:
- **Job `publish`**: checkout main → pip install + tweepy → create .env from secrets → run `x_publisher.py` → git commit updated xlsx → git push
- **Job `deploy`** (`needs: publish`): checkout main → build static site → deploy to gh-pages

Inputs: `client_id`, `week_of`, `topic_index`
Concurrency: `group: gh-pages-deploy` (prevents parallel deploy conflicts)

### `reference/x-api-setup.md`
Step-by-step guide: developer account, app creation, permissions, credential generation, .env + GitHub Secrets setup, enabling per-client, testing (mock + real + duplicate check).

---

## Files Modified

### `clients/bobe/config.json` + `clients/_template/config.json`
Added after `"airtable"` block:
```json
"x_publishing": {
  "enabled": false,
  "x_handle": "@bobe_app"
}
```

### `scripts/client_config.py`
Added after `is_airtable_enabled()`:
- `get_x_publishing_config(client_id)` — returns x_publishing dict from config
- `is_x_publishing_enabled(client_id)` — returns bool
- `get_x_credentials(client_id)` — reads `{CLIENT_ID_UPPER}_X_API_KEY/SECRET/ACCESS_TOKEN/ACCESS_TOKEN_SECRET` from env; raises ValueError with clear message listing missing vars

### `scripts/web_viewer.py`
- Added `HAS_X_PUBLISHER` import check (tweepy)
- `load_content()`: reads `row_status`/`row_tweet_url` from both schema branches; adds `status` and `tweet_url` to topic dict; updates from twitter row when encountered
- CSS: added `.publish-x-btn` styles (X blue / published green states)
- HTML template: "Publish to X" button in Twitter EN content-actions (conditional on `x_publishing_enabled`; shows "Published ✓" if status=Published)
- JS: added `publishToX(idx)` function — POSTs to `/api/publish-to-x`, updates button state
- Flask endpoint: `@app.route("/api/publish-to-x")` — checks HAS_X_PUBLISHER + enabled, runs subprocess, parses TWEET_URLS from stdout
- `render_template_string()` calls: added `x_publishing_enabled` parameter

### `scripts/build_static.py`
- CSS: same `.publish-x-btn` styles
- HTML template: same publish button (calls `triggerPublishToX()`)
- JS constants: added `GH_PUBLISH_WORKFLOW = 'publish-to-x.yml'`
- JS: added `triggerPublishToX(idx)` — uses same PAT flow as `triggerRegen()`, dispatches `publish-to-x.yml`, calls `pollRegenCompletion()`
- `dashboard_template.render()`: added `x_publishing_enabled=client_config.is_x_publishing_enabled(active_client)`

---

## Excel Schema Extension

Added column 16 (P) = `Tweet_URL` after existing column 15 (O) = `Status`.

- Written by `x_publisher.py` after posting
- Read by `load_content()` in web_viewer (imported by build_static)
- Backward-compatible: read with `len(row) > 15` check; write header only if absent

---

## Dependency

`tweepy` installed in `venv/` via `pip install tweepy`.

---

## Activation Checklist

1. Apply for X developer account at developer.twitter.com
2. Create project + app, set permissions to "Read and Write"
3. Generate API Key, API Secret, Access Token, Access Token Secret
4. Add to `.env`: `BOBE_X_API_KEY=...` etc.
5. Add same four vars to GitHub Secrets
6. Set `x_publishing.enabled = true` in `clients/bobe/config.json`
7. Run `/deploy` — "Publish" button appears on Twitter cards

---

## Key Risks + Mitigations

| Risk | Mitigation |
|------|-----------|
| Free tier 17 writes/24hr | MVP is per-topic only; no `--all` flag; guide documents this |
| Tweet > 280 chars | `split_thread()` warns but doesn't block |
| Two publishes conflict on git push | `concurrency: group: gh-pages-deploy` prevents parallel runs |
| Developer account approval delay | `reference/x-api-setup.md` notes this — apply early |
| tweepy not installed | Flask endpoint checks `HAS_X_PUBLISHER`, returns 503 with install hint |
