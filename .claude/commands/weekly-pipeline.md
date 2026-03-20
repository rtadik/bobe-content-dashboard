# Weekly Pipeline

> Fully automated bilingual weekly content pipeline. Generates 14 topics (2 buckets × 7 days) for the active client: 7 Trending + 7 Education. Produces Twitter threads and Telegram posts in English, writes all content to Airtable, and generates 14 EN branded images via GPT-Image-1.5. RU images generate separately after EN approval. Zero user input required after triggering.

## Variables

week_of: $ARGUMENTS (optional — if provided must be YYYY-MM-DD; defaults to Monday of current week)

---

## Before Starting

1. **Calculate `week_of`**: If $ARGUMENTS is a valid YYYY-MM-DD, use it. Otherwise compute today's Monday:
   - Today: {today's date}
   - Monday of this week = today minus today's weekday index (Mon=0)
   - Example: if today is Thursday 2026-03-20, week_of = 2026-03-16

2. **Determine active client**:
   ```bash
   cat .active-client 2>/dev/null || echo "bobe"
   ```
   Read `clients/{active_client}/config.json` — confirms `content.content_types` is `["trending", "education"]` and `content.bucket_size` is 7.

3. **Verify prerequisites**:
   ```bash
   ls scripts/pipeline_runner.py scripts/nano_banana.py scripts/apify_scraper.py scripts/bucket_generators.py
   ls clients/{active_client}/config.json
   ```
   Confirm `.env` has `APIFY_API_TOKEN`, `GOOGLE_AI_API_KEY`, `WAVESPEED_API_KEY`, and `AIRTABLE_API_KEY`.

---

## Run the Pipeline

The pipeline is fully automated via `pipeline_runner.py`. Run:

```bash
source venv/bin/activate && python scripts/pipeline_runner.py \
  --client {active_client} \
  --week-of {week_of} \
  --skip-deploy
```

**What it does (in order):**

- **Phase 1**: Scrapes Twitter for trending topics via Apify (100 posts, past 7 days, top 30 filtered)
- **Phase 2**: Generates 14 topics — 7 Trending (from scrape/evergreen) + 7 Education (from `belief-journey.md`)
- **Phase 3**: Content generation loop — for each of 14 topics, generates Twitter thread (5 tweets) + Telegram post in English. Writes each item to Airtable immediately.
- **Phase 4**: RU translation — translates all 28 content items to Russian, writes back to Airtable.
- **Phase 5**: Image generation — generates 14 EN branded images via GPT-Image-1.5, uploads to Cloudflare R2, updates Airtable `Image_URL_EN` fields. RU images are deferred until EN approval.

**To also deploy after pipeline:**
```bash
source venv/bin/activate && python scripts/pipeline_runner.py \
  --client {active_client} \
  --week-of {week_of}
```
(omit `--skip-deploy` to auto-build and deploy static site after completion)

**Mock run (no API calls):**
```bash
source venv/bin/activate && python scripts/pipeline_runner.py \
  --client {active_client} \
  --week-of {week_of} \
  --mock \
  --skip-deploy
```

---

## Topic Schedule

Each day gets 1 Trending topic + 1 Education topic:

| Day | Trending | Education |
|-----|----------|-----------|
| Mon | Trending#1 | Education#1 |
| Tue | Trending#2 | Education#2 |
| Wed | Trending#3 | Education#3 |
| Thu | Trending#4 | Education#4 |
| Fri | Trending#5 | Education#5 |
| Sat | Trending#6 | Education#6 |
| Sun | Trending#7 | Education#7 |

Both topics per day get **Twitter thread format** (5 tweets) and **Telegram post format** (400–1200 chars).

---

## Output

- **Airtable**: `Week-{week_of}` table in the client's base — 28 records (14 topics × 2 platforms)
- **Images**: `outputs/content/{active_client}/images/{week_of}-weekly/` — 14 EN PNGs
- **R2**: Images uploaded to `https://pub-afa75fbdf1cc4d43ac9fbe9f1eac5f5b.r2.dev/`
- **No Excel** — Airtable is the sole data store

After pipeline completes, print a summary:

```
{display_name} Weekly Pipeline Complete
Week of: {week_of}

Mon {date}: [trending topic] | [education topic]
Tue {date}: [trending topic] | [education topic]
...
Sun {date}: [trending topic] | [education topic]

Content: 28 items (14 topics × 2 platforms)
Images:  14 EN via GPT-Image-1.5 (RU pending EN approval)
Airtable: Week-{week_of} table — {base_id}

To view: http://localhost:5001 (run /view-content first)
To deploy: /deploy
```

---

## Error Handling

| Error | Recovery |
|-------|----------|
| Scraping fails / 0 results | Log warning, use 100% evergreen fallback topics from keywords.md |
| EN image fails for one topic | Log error, continue — image_path stored in Airtable, can regen later |
| Airtable write fails for one record | Log row + continue — other records already saved |
| `AIRTABLE_API_KEY` missing | Stop: print "AIRTABLE_API_KEY not set in .env" |
| `WAVESPEED_API_KEY` missing | Stop: print "WAVESPEED_API_KEY not set in .env" |
| Gemini (bucket_generators) returns placeholders | Check that `_call_gemini()` is called with `client_id` as keyword arg, not positional |

---

## Notes

- **Announcements** are NOT part of the weekly pipeline. Clients submit announcement text via the dashboard Announcements tab, which triggers a separate `generate-announcement.yml` workflow.
- **RU images** are generated after EN image approval via the approval workflow (regen button on dashboard or `pipeline_runner.py --regen-type image_ru`).
- **bucket_generators.py**: always call `_call_gemini(prompt, client_id=client_id)` — never positional — or the client ID gets passed as the model name, causing 404 errors and placeholder fallback.
