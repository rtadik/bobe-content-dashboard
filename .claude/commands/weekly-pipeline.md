# Weekly Pipeline

> Fully automated bilingual weekly content pipeline. Run once to generate 21 bilingual content sets (3/day x 7 days) for the active client. Twitter threads, Telegram posts, and branded images in English AND Russian, saved to a weekly Excel workbook. Zero user input required after triggering.

## Variables

week_of: $ARGUMENTS (optional — if provided must be YYYY-MM-DD; defaults to Monday of current week)

---

## Before Starting

1. **Calculate `week_of`**: If $ARGUMENTS is a valid YYYY-MM-DD, use it. Otherwise compute today's Monday:
   - Today: {today's date}
   - Monday of this week = today minus today's weekday index (Mon=0)
   - Example: if today is Wednesday 2026-02-18, week_of = 2026-02-16

2. **Compute day dates** for the 7-day schedule:
   - Mon = week_of + 0 days
   - Tue = week_of + 1 day
   - Wed = week_of + 2 days
   - Thu = week_of + 3 days
   - Fri = week_of + 4 days
   - Sat = week_of + 5 days
   - Sun = week_of + 6 days

3. **Determine active client**:
   ```bash
   cat .active-client 2>/dev/null || echo "bobe"
   ```
   Read `clients/{active_client}/config.json` to load brand name, keywords, tone, mascot description, style presets, and all client-specific values. All subsequent steps use these config values instead of hardcoded defaults.

   **Also read from config:**
   - `content.platforms` — which platforms to generate content for (e.g., `["twitter", "telegram"]`)
   - `content.platform_formats` — format rules per platform (thread length, char limits, etc.)
   - `image.angle_style_map` — maps topic angle to image style preset (e.g., `"Pain Point" → "minimal"`)
   - `airtable.enabled` — whether to sync to Airtable after saving Excel

4. **Verify prerequisites**:
   ```bash
   ls scripts/weekly_pipeline.py scripts/nano_banana.py scripts/wavespeed_img.py scripts/apify_scraper.py
   ls clients/{active_client}/config.json
   ```
   Confirm `.env` has `APIFY_API_TOKEN`, `GOOGLE_AI_API_KEY`, and `WAVESPEED_API_KEY`.

5. **Read now** (required for all content generation):
   - `clients/{active_client}/content-guidelines.md`
   - `clients/{active_client}/keywords.md`
   - `clients/{active_client}/context.md`

---

## Phase 1: Scrape Topics

Run the Twitter scraper for the past 7 days. Keywords are loaded automatically from the active client's config:

```bash
python scripts/apify_scraper.py \
  --platform twitter \
  --count 100 \
  --days 7 \
  --top 30 \
  --output /tmp/weekly_scraped.json
```

(To override the client, add `--client {client_id}`. To override keywords, add `--keywords "keyword1,keyword2,..."`)

Load `/tmp/weekly_scraped.json`. Note how many unique relevant topics it contains.

---

## Phase 2: Topic Pool Assembly

You need **21 topics total** (3 per day × 7 days). Build the pool:

1. Use all scraped live topics (sorted by engagement × relevance).
2. Fill remaining slots from the **Evergreen Fallback Bank** below.
3. Assign to days: live/trending topics → Mon–Wed; evergreen → Thu–Sun (plus remaining Mon–Wed slots).
4. Each day should have variety: aim for a mix of Pain Point, Education, and Transparency/Product angles.
5. Across the week, vary the theme so consecutive days don't repeat the same angle.

### Evergreen Fallback Bank

Generate 20 evergreen topics based on the active client's context, keywords, and messaging pillars from `clients/{active_client}/config.json` and `clients/{active_client}/context.md`. Topics should:

- Cover a mix of Pain Point, Education, and Transparency/Product angles
- Be relevant to the client's product and target audience
- Align with the client's tone and voice settings
- Use the client's keywords as thematic anchors
- NEVER use em-dashes, en-dashes, or double-hyphens in topic text

**Print the full 21-topic schedule as a table before proceeding to Phase 3:**

| # | Day | Date | Topic | Angle | Source |
|---|-----|------|-------|-------|--------|
| 1 | Mon | {date} | ... | Pain Point | Live/Evergreen |
| 2 | Mon | {date} | ... | Education | Live/Evergreen |
| 3 | Mon | {date} | ... | Product | Live/Evergreen |
| ... | | | | | |
| 21 | Sun | {date} | ... | Education | Evergreen |

---

## Phase 3: Create Workbook

```bash
python scripts/weekly_pipeline.py --action create-workbook --week-of {week_of}
```

Expected: `Weekly workbook created: outputs/content/{active_client}/{week_of}-weekly-content.xlsx`

---

## Phase 4: Content Generation Loop

Each of the 21 topics gets **both** a Twitter version and a Telegram version in **English AND Russian** = **42 content items total** (21 EN + 21 RU, stored as 42 rows in the workbook).

Number them sequentially: topic 1 Twitter = item 1, topic 1 Telegram = item 2, topic 2 Twitter = item 3, topic 2 Telegram = item 4, etc.

**Format assignment (per topic):**
- Twitter: use thread format (5 tweets) for topics 1–2 of each day; single post format (1 tweet, ≤280 chars) for topic 3 of each day
- Telegram: always long-form (400–1200 chars, educational tone, ends with engagement question)

---

### CRITICAL CONTENT RULES

**No em-dashes or double-hyphens (English AND Russian):**
- **NEVER** use `—` (em-dash U+2014), `–` (en-dash U+2013), or `--` (double-hyphen) as punctuation in any generated content — in either language
- Replace with commas, colons, or rephrase the sentence entirely
- The `---` tweet separator is the only exception (it is structural, not punctuation)
- Violating this rule requires regenerating the affected content before saving

**Russian translation rules:**
- Tone: conversational, like a knowledgeable friend. Not formal, not slang.
- Twitter: maintain ~280 char target (allow up to 340 chars since Russian runs ~30% longer)
- Telegram: maintain structure, engagement question at end
- Keep English fintech hashtags (#DeFi, #USDT, #BoBe) AND add 1–2 Cyrillic ones (#Крипто, #АвтоТрейдинг, #Доходность)
- The `---` tweet separator stays unchanged in Russian threads
- No em-dashes, en-dashes, or double-hyphens in Russian content either

---

**For each topic N (show progress: "Generating 4/21..."):**

**Step 4a — Generate English content** using the content-generator skill (use the active client's tone and voice from config):

Read `content.platforms` from config to determine which platforms to generate for. For each platform, use `content.platform_formats` for the format rules:

- **Twitter** (if in platforms): thread format uses `platform_formats.twitter.thread_tweets` tweets (default 5), separated by `---`, each ≤`platform_formats.twitter.single_max_chars` chars (default 280). Hook + insights + brand connection + soft CTA. Single post: 1 tweet ≤280 chars with 2-3 hashtags.
- **Telegram** (if in platforms): `platform_formats.telegram.min_chars` to `platform_formats.telegram.max_chars` chars (default 400-1200), educational tone, ends with engagement question if `platform_formats.telegram.end_with_question` is true.
- **Other platforms**: use sensible format defaults aligned with the client's voice and the platform's norms.

**Step 4b — Translate to Russian** (immediately after English, while context is warm):
- Produce a full Russian translation of the Twitter content for this topic
- Produce a full Russian translation of the Telegram content for this topic
- Follow the Russian translation rules above
- Generate `image_prompt_ru`: same structure as EN image_prompt but with a Russian headline in Cyrillic
- Generate `hashtags_ru`: keep EN hashtags + add 1–2 Cyrillic ones

**Pre-compute the image paths** using these patterns:

EN image path:
```
outputs/content/{active_client}/images/{week_of}-weekly/{week_of}_{day_lowercase}_{topic_slug}_{platform_lower}.png
```

RU image path (append `_ru` before `.png`):
```
outputs/content/{active_client}/images/{week_of}-weekly/{week_of}_{day_lowercase}_{topic_slug}_{platform_lower}_ru.png
```

Where `topic_slug` = first 30 chars of topic, lowercased, spaces→underscores, special chars removed.
Where `platform_lower` = "twitter" or "telegram".

**Write Twitter content to `/tmp/weekly_content_{2N-1}.json` and Telegram to `/tmp/weekly_content_{2N}.json`:**

```json
{
  "date": "YYYY-MM-DD",
  "day": "Mon",
  "topic": "Topic text",
  "platform": "Twitter",
  "format": "thread",
  "content": "Tweet 1 text\n---\nTweet 2 text\n---\nTweet 3 text\n---\nTweet 4 text\n---\nTweet 5 text",
  "image_prompt": "Detailed Gemini image prompt here...",
  "image_path": "outputs/content/{active_client}/images/{week_of}-weekly/{week_of}_mon_topic-slug_twitter.png",
  "hashtags": ["#DeFi", "#TradingBot", "#BoBe"],
  "content_ru": "Твит 1\n---\nТвит 2\n---\nТвит 3\n---\nТвит 4\n---\nТвит 5",
  "image_prompt_ru": "Same structure as image_prompt but with Cyrillic headline text...",
  "image_path_ru": "outputs/content/{active_client}/images/{week_of}-weekly/{week_of}_mon_topic-slug_twitter_ru.png",
  "hashtags_ru": ["#DeFi", "#TradingBot", "#BoBe", "#Крипто"],
  "status": "Draft"
}
```

**Save to workbook:**
```bash
python scripts/weekly_pipeline.py --action save-content --week-of {week_of} --content-file /tmp/weekly_content_{N}.json
```

Repeat for all 42 items. If a save fails, log the error and continue — do not halt the pipeline.

---

## Phase 5: Image Generation Loop

Generate **42 images total**: 21 EN images via Gemini (`nano_banana.py`) + 21 RU images via WaveSpeed Seedream 4.5 (`wavespeed_img.py`).

**Style mapping:**

Read `image.angle_style_map` from the active client's config. Map each topic's angle to its style preset using that config value.

Example (BoBe default):
- Pain Point → `--style minimal`
- Education → `--style tech`
- Transparency → `--style notification`
- Product → `--style notification`

If a topic angle is not found in `angle_style_map`, default to `--style minimal`.

**For each topic N (progress: "Generating images 2/21 [Mon]: Grid trading... (EN: Gemini + RU: Seedream)"):**

EN image (one per topic, shared between Twitter and Telegram):
```bash
source venv/bin/activate && python scripts/nano_banana.py \
  --prompt "{image_prompt from weekly_content_{2N-1}.json}" \
  --output "outputs/content/{active_client}/images/{week_of}-weekly/{week_of}_{day_lower}_{topic_slug}_{platform_lower}.png" \
  --style {style}
```

RU image (same topic, `_ru` appended before `.png`):
```bash
source venv/bin/activate && python scripts/wavespeed_img.py \
  --prompt "{image_prompt_ru from weekly_content_{2N-1}.json}" \
  --output "outputs/content/{active_client}/images/{week_of}-weekly/{week_of}_{day_lower}_{topic_slug}_{platform_lower}_ru.png"
```

If an image fails, log the error and continue to the next — do not halt.

---

## Phase 6: Finalize

```bash
python scripts/weekly_pipeline.py --action finalize --week-of {week_of}
```

**Then print the full week summary:**

```
{display_name} Weekly Pipeline Complete
Week of: {week_of}

Mon {date}: [topic 1] | [topic 2] | [topic 3]
Tue {date}: [topic 4] | [topic 5] | [topic 6]
Wed {date}: [topic 7] | [topic 8] | [topic 9]
Thu {date}: [topic 10] | [topic 11] | [topic 12]
Fri {date}: [topic 13] | [topic 14] | [topic 15]
Sat {date}: [topic 16] | [topic 17] | [topic 18]
Sun {date}: [topic 19] | [topic 20] | [topic 21]

Content: 42 bilingual rows (21 EN + 21 RU per platform)
Images:  42 total (21 EN via GPT-Image-1.5 + 21 RU via Seedream 4.5)
Excel:   outputs/content/{active_client}/{week_of}-weekly-content.xlsx
Images:  outputs/content/{active_client}/images/{week_of}-weekly/

To review: /view-content week:{week_of}
```

---

## Phase 6.5: Airtable Sync (if enabled)

Check if Airtable is enabled for the active client:

```bash
python -c "
import sys; sys.path.insert(0, 'scripts')
from client_config import is_airtable_enabled
print('enabled' if is_airtable_enabled() else 'disabled')
"
```

**If enabled:**
```bash
source venv/bin/activate && python scripts/airtable_sync.py --week-of {week_of}
```

Expected output:
```
Records pushed: 42/42
Images attached from: https://your-site.pages.dev   ← only if images_base_url is set
Base:  app...
Table: Week-{week_of}
View:  https://airtable.com/{base_id}
```

**Image attachments note:** Images appear inline in Airtable only if `airtable.images_base_url` is set in config.json. This requires running `/deploy` first to publish images to Cloudflare Pages, then setting the deployed URL in config. Without it, image paths are stored as plain text (content is still fully readable).

**If disabled:** skip silently and proceed to Phase 7.

---

## Phase 7: Build Static Dashboard (Optional)

Ask the user:
> "Weekly pipeline complete. Would you like me to build and deploy the updated dashboard for your client?"

If yes:

1. **Build static site**
   ```bash
   cd "/Users/rt/Claude Code/bobe-image-content-gen" && ./venv/bin/python scripts/build_static.py --output dist
   ```

2. **Report and offer deployment**
   - Show build summary (pages, images, size)
   - Ask: "Ready to deploy? Run `/deploy` to push it live."

---

## Error Handling

| Error | Recovery |
|-------|----------|
| Scraping fails / 0 results | Log warning, use 100% evergreen fallback topics, do not halt |
| EN image (GPT-Image-1.5) fails for one topic | Log error, keep pre-computed image_path in workbook, continue |
| RU image (WaveSpeed) fails for one topic | Log error, keep pre-computed image_path_ru in workbook, continue |
| Excel save fails for one item | Log error, continue; other items are already saved |
| Em-dash found in generated content | Regenerate only that item: replace `—`, `–`, `--` with commas or colons |
| WAVESPEED_API_KEY missing | Stop and print "WAVESPEED_API_KEY not set in .env" |
| API key missing | Stop and print the specific missing key name |
| Airtable push fails for one record | Log row number and continue — Excel is source of truth |
| AIRTABLE_API_KEY missing when airtable.enabled is true | Stop and print "AIRTABLE_API_KEY not set in .env — see reference/airtable-client-setup.md" |

---

## Quick Mock Test (no API calls)

```bash
python scripts/weekly_pipeline.py --action scrape --week-of {week_of} --mock --output /tmp/weekly_scraped.json
python scripts/weekly_pipeline.py --action create-workbook --week-of {week_of}
python scripts/weekly_pipeline.py --action finalize --week-of {week_of}
```
