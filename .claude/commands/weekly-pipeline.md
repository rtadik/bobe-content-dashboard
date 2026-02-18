# Weekly Pipeline

> Fully automated BoBe weekly content pipeline. Run once to generate 21 content sets (3/day × 7 days) — Twitter threads, Telegram posts, and branded images — saved to a weekly Excel workbook. Zero user input required after triggering.

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

3. **Verify prerequisites**:
   ```bash
   ls scripts/weekly_pipeline.py scripts/nano_banana.py scripts/apify_scraper.py
   ```
   Confirm `.env` has `APIFY_API_TOKEN` and `GOOGLE_AI_API_KEY`.

4. **Read now** (required for all content generation):
   - `reference/content-guidelines.md`
   - `reference/bobe-keywords.md`

---

## Phase 1: Scrape Topics

Run the Twitter scraper for the past 7 days:

```bash
python scripts/apify_scraper.py \
  --platform twitter \
  --keywords "trading bot,yield,DCA strategy,automated trading,on-chain yield,crypto automation,AI trading,grid bot,passive crypto,crypto bot,DeFi yield,USDT yield,risk management crypto,emotional trading,crypto strategy" \
  --count 100 \
  --days 7 \
  --top 30 \
  --output /tmp/weekly_scraped.json
```

Load `/tmp/weekly_scraped.json`. Note how many unique relevant topics it contains.

---

## Phase 2: Topic Pool Assembly

You need **21 topics total** (3 per day × 7 days). Build the pool:

1. Use all scraped live topics (sorted by engagement × relevance).
2. Fill remaining slots from the **Evergreen Fallback Bank** below.
3. Assign to days: live/trending topics → Mon–Wed; evergreen → Thu–Sun (plus remaining Mon–Wed slots).
4. Each day should have variety: aim for a mix of Pain Point, Education, and Transparency/Product angles.
5. Across the week, vary the theme so consecutive days don't repeat the same angle.

### Evergreen Fallback Bank (pick in order; skip if angle already covered 3+ times that day)

| # | Topic | Angle |
|---|-------|-------|
| 1 | "Why most traders sabotage their own strategies — and how automation fixes it" | Pain Point |
| 2 | "DCA vs lump-sum investing: which strategy actually wins in volatile markets" | Education |
| 3 | "What on-chain transparency means and why it matters for yield platforms" | Education |
| 4 | "The psychology of holding: why humans sell at the bottom and bots don't" | Pain Point |
| 5 | "Grid trading explained: how bots profit from sideways markets" | Education |
| 6 | "USDT yield in 2026: sustainable sources vs APY theater" | Education |
| 7 | "Spot-only trading: why no-leverage strategies outperform long-term" | Education |
| 8 | "How audited smart contracts change the trust calculus in DeFi" | Transparency |
| 9 | "The hidden cost of manual crypto trading: time, stress, and missed entries" | Pain Point |
| 10 | "From emotional to mechanical: what a systematic trading strategy actually looks like" | Education |
| 11 | "Why crypto automation is not set-and-forget — what real oversight looks like" | Education |
| 12 | "Comparing bot platforms: what features actually matter vs. what's marketing" | Education |
| 13 | "Risk management basics every crypto holder should understand before automating" | Education |
| 14 | "How DeFi yield differs from CeFi yield — and why it matters for your funds" | Education |
| 15 | "The 3 biggest mistakes new crypto traders make and how automation addresses each" | Pain Point |
| 16 | "What consistent small returns beat volatile big wins — the math behind steady yield" | Education |
| 17 | "How trading bots handle market crashes differently than human traders" | Pain Point |
| 18 | "Understanding on-chain yield distribution: how USDT payouts actually work" | Product |
| 19 | "Why retail traders need systematic rules more than better market analysis" | Pain Point |
| 20 | "The compounding effect: why steady automated yield beats inconsistent manual trading" | Education |

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

Expected: `Weekly workbook created: outputs/content/{week_of}-weekly-content.xlsx`

---

## Phase 4: Content Generation Loop

Each of the 21 topics gets **both** a Twitter version and a Telegram version = **42 content items total**.
Number them sequentially: topic 1 Twitter = item 1, topic 1 Telegram = item 2, topic 2 Twitter = item 3, topic 2 Telegram = item 4, etc.

**Format assignment (per topic):**
- Twitter: use thread format (5 tweets) for topics 1–2 of each day; single post format (1 tweet, ≤280 chars) for topic 3 of each day
- Telegram: always long-form (400–1200 chars, educational tone, ends with engagement question)

**CRITICAL CONTENT RULE — No em-dashes or double-hyphens:**
- **NEVER** use `—` (em-dash U+2014), `–` (en-dash U+2013), or `--` (double-hyphen) as punctuation in any generated content
- Replace with commas, colons, or rephrase the sentence entirely
- The `---` tweet separator is the only exception (it is structural, not punctuation)
- Violating this rule requires regenerating the affected content before saving

**For each topic N (show progress: "Generating 4/21..."):**

Apply the content-generator skill. Generate content aligned with BoBe's voice (transparent, educational, no hype, no guaranteed return claims). Output:
- Twitter thread: 5 tweets separated by `---`, each ≤280 chars, hook + insight + insight + BoBe connection + soft CTA
- Twitter single: 1 tweet ≤280 chars with 2-3 hashtags
- Telegram: 400–1200 chars, educational tone, ends with engagement question

**Pre-compute the image path** using this pattern (do not wait for image generation):
```
outputs/content/images/{week_of}-weekly/{week_of}_{day_lowercase}_{topic_slug}_{platform_lower}.png
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
  "image_path": "outputs/content/images/{week_of}-weekly/{week_of}_mon_topic-slug_twitter.png",
  "hashtags": ["#DeFi", "#TradingBot", "#BoBe"],
  "topic_slug": "topic-slug",
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

For each of the 21 topics, generate a branded image using the image-generator skill.

**Style mapping:**
- Pain Point topics → `--style minimal`
- Education topics → `--style tech`
- Transparency/Product topics → `--style notification`

**For each topic N:**

```bash
source venv/bin/activate && python scripts/nano_banana.py \
  --prompt "{image_prompt from weekly_content_N.json}" \
  --output "outputs/content/images/{week_of}-weekly/{week_of}_{day_lower}_{topic_slug}_{platform_lower}.png" \
  --style {style}
```

Show progress: "Generating image 4/42 [Mon]: Grid trading explained..." (one image per Twitter+Telegram pair — 21 images total, shared between platforms)

If an image fails, log the error and continue to the next — do not halt.

---

## Phase 6: Finalize

```bash
python scripts/weekly_pipeline.py --action finalize --week-of {week_of}
```

**Then print the full week summary:**

```
BoBe Weekly Pipeline Complete
Week of: {week_of}

Mon {date}: [topic 1] | [topic 2] | [topic 3]
Tue {date}: [topic 4] | [topic 5] | [topic 6]
Wed {date}: [topic 7] | [topic 8] | [topic 9]
Thu {date}: [topic 10] | [topic 11] | [topic 12]
Fri {date}: [topic 13] | [topic 14] | [topic 15]
Sat {date}: [topic 16] | [topic 17] | [topic 18]
Sun {date}: [topic 19] | [topic 20] | [topic 21]

Excel: outputs/content/{week_of}-weekly-content.xlsx
Images: outputs/content/images/{week_of}-weekly/

To review: /view-content week:{week_of}
```

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
| Scraping fails / 0 results | Log warning, use 100% evergreen fallback topics — do not halt |
| Image generation fails for one topic | Log error, keep pre-computed image_path in workbook (viewer handles missing files gracefully), continue |
| Excel save fails for one item | Log error, continue — other items are already saved |
| Em-dash found in generated content | Regenerate only that item — replace `—`, `–`, `--` with commas or colons |
| weekly_pipeline.py not found | Check running from project root; verify `scripts/` directory |
| API key missing | Stop and print the specific missing key name |

---

## Quick Mock Test (no API calls)

```bash
python scripts/weekly_pipeline.py --action scrape --week-of {week_of} --mock --output /tmp/weekly_scraped.json
python scripts/weekly_pipeline.py --action create-workbook --week-of {week_of}
python scripts/weekly_pipeline.py --action finalize --week-of {week_of}
```
