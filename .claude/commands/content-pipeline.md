# Content Pipeline

> Daily content automation for BoBe: scrape → curate → generate copy → generate images → export to Excel

## Variables

date: $ARGUMENTS (optional — defaults to today's date YYYY-MM-DD)

---

## Prerequisites Check

Before starting, verify:
1. `.env` file exists with `APIFY_API_TOKEN` and `GOOGLE_AI_API_KEY`
2. Python packages installed: `pip install requests openpyxl google-genai python-dotenv`
3. `outputs/content/` directory exists (auto-created by scripts)

If not set up, refer to `reference/api-setup.md`.

---

## Workflow

### Phase 1: Scrape & Curate

**Step 1 — Scrape Twitter**
```bash
python scripts/apify_scraper.py --platform twitter \
  --keywords "defi,yield,trading bot,automation,AI trading,on-chain yield,DCA strategy,crypto bot" \
  --count 50 \
  --output /tmp/twitter_topics.json
```

**Step 2 — Scrape Reddit**
```bash
python scripts/apify_scraper.py --platform reddit \
  --subreddits "defi,CryptoCurrency,ethfinance,algotrading" \
  --keywords "yield,automation,trading bot,DCA,passive crypto" \
  --count 50 \
  --output /tmp/reddit_topics.json
```

**Step 3 — Merge and rank**
Combine both JSON files, rank by engagement × relevance score, and present the top 10–15 to the user.

**Step 4 — Create daily Excel workbook**
```bash
python scripts/excel_manager.py --action create --date {date}
```

**Step 5 — Add all topics to Sheet 1**
```bash
python scripts/excel_manager.py --action add-topics \
  --file outputs/content/{date}-content.xlsx \
  --topics /tmp/twitter_topics.json
```

---

### Phase 2: Topic Selection

Present the user with the top 10–15 curated topics in a numbered list showing:
- Platform (Twitter/Reddit)
- Topic summary (first 100 chars)
- Engagement score
- Relevance score

Ask the user:
> "Here are today's top topics. Which 2–3 would you like me to create content for? You can also provide a custom topic."

Wait for selection before proceeding.

---

### Phase 3: Content Generation

For each selected topic, invoke the `content-generator` skill:

1. Read `reference/content-guidelines.md` and `context/BoBe Context.md`
2. Generate:
   - Twitter thread (3–5 tweets)
   - Telegram post (long-form)
   - Image prompt for each
3. Save content as JSON to `/tmp/generated_content_{topic_slug}.json`

**Add generated content to Sheet 2:**
```bash
python scripts/excel_manager.py --action add-content \
  --file outputs/content/{date}-content.xlsx \
  --content /tmp/generated_content_{topic_slug}.json
```

---

### Phase 4: Image Generation

For each piece of content, invoke the `image-generator` skill:

```bash
python scripts/nano_banana.py \
  --prompt "{image_prompt_from_content_generator}" \
  --output outputs/content/images/{date}-daily/{date}_{topic_slug}_{platform}.png
```

Update the Excel Sheet 2 `Image Path` column with the file path for each generated image.

---

### Phase 5: Review & Summary

Present to the user:

1. **Topics covered** — which topics were selected
2. **Content preview** — first tweet/paragraph of each piece
3. **Images created** — file paths to generated images
4. **Excel location** — `outputs/content/{date}-content.xlsx`

Ask the user:
> "Would you like to:
> - Edit any of the content?
> - Regenerate an image with a different style?
> - Generate content for additional topics?"

---

## Output Files

All saved to `outputs/content/`:
- `{date}-content.xlsx` — Full workbook (Sheet 1: Topics, Sheet 2: Content)
- `images/{date}-daily/{date}_{topic_slug}_twitter.png` — Twitter banner image
- `images/{date}-daily/{date}_{topic_slug}_telegram.png` — Telegram banner image

---

### Phase 6: Build Static Dashboard (Optional)

Ask the user:
> "Content generation complete. Would you like me to build and deploy the updated dashboard for your client?"

If yes:

1. **Build static site**
   ```bash
   cd "/Users/rt/Claude Code/bobe-image-content-gen" && ./venv/bin/python scripts/build_static.py --output dist
   ```

2. **Report and offer deployment**
   - Show build summary (pages, images, size)
   - Ask: "Ready to deploy? Run `/deploy` to push it live."

---

## Quick Mode (--mock)

To test the pipeline without API calls:
```bash
python scripts/apify_scraper.py --mock --output /tmp/mock_topics.json
python scripts/excel_manager.py --action create --date {date} --mock
python scripts/nano_banana.py --mock --output outputs/content/{date}_test.png
```

---

## Error Handling

| Error | Recovery |
|-------|----------|
| Apify API fails | Check `APIFY_API_TOKEN` in `.env`; retry; or use `--mock` |
| Image generation fails | Check `GOOGLE_AI_API_KEY`; retry with different style; or skip |
| Excel write fails | Check `openpyxl` installed; verify `outputs/content/` exists |
| No relevant topics found | Broaden keywords or provide custom topic |
