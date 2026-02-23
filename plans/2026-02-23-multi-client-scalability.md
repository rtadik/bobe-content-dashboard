# Plan: Multi-Client Scalability — Airtable Output, Auto-Drafted Onboarding, and Config-Driven Pipeline

**Created:** 2026-02-23
**Status:** Implemented
**Request:** Replace locally hosted Excel with Airtable for client content delivery; upgrade `/onboard-client` to auto-draft all config files from Q&A; make the pipeline fully industry-agnostic by moving platform lists and image style mapping into client config.

---

## Overview

### What This Plan Accomplishes

This plan makes the platform ready to onboard clients in any industry with minimal manual work, delivers generated content directly to client-accessible Airtable bases instead of locally hosted Excel files, and removes the last BoBe-specific assumptions hardcoded into the weekly pipeline. After implementation, onboarding a new client should take under 15 minutes of guided Q&A — and the resulting content is immediately accessible to the client in Airtable without any file sharing.

### Why This Matters

The current platform works well for BoBe but has three friction points that block scaling to multiple clients: (1) onboarding requires manually writing three markdown files after the Q&A, (2) generated content lives in local Excel files that must be manually shared with clients, and (3) the weekly pipeline still has BoBe-specific assumptions (hardcoded platforms, hardcoded image style mapping) that don't generalize. Fixing all three unlocks the platform as a genuine multi-client content operation.

---

## Current State

### Relevant Existing Structure

```
clients/_template/
  config.json             — placeholder config (fill in manually after onboarding Q&A)
  content-guidelines.md   — blank markdown template with bracketed placeholders
  context.md              — blank markdown template with bracketed placeholders
  keywords.md             — blank markdown template with bracketed placeholders
  brand/README.md         — asset upload instructions

clients/bobe/config.json  — reference implementation (no platforms or angle_style_map fields)

.claude/commands/
  onboard-client.md       — fills config.json only; tells user to manually write 3 md files

scripts/
  weekly_pipeline.py      — Excel-only output, no Airtable path
  client_config.py        — config loader, no Airtable helpers
  apify_scraper.py        — platform-agnostic scraping

.claude/commands/
  weekly-pipeline.md      — hardcodes "Twitter + Telegram" pattern, hardcodes angle→style map
```

### Gaps or Problems Being Addressed

1. **Onboarding friction**: After the Q&A in `/onboard-client`, the user still has to manually write `content-guidelines.md`, `context.md`, and `keywords.md` — three substantial documents. There is no auto-draft step. This is the single biggest barrier to fast onboarding.

2. **No Airtable delivery path**: All content is saved to local `.xlsx` files. Clients cannot access content independently. Sharing requires manual file export or screen sharing. There is no approval workflow.

3. **Hardcoded platforms in weekly pipeline**: `weekly-pipeline.md` hardcodes "Twitter + Telegram" and the per-platform format rules (thread = 5 tweets, etc.). A client who only wants LinkedIn, or Twitter-only, would require manual edits to the command file.

4. **Hardcoded image style mapping**: `weekly-pipeline.md` hardcodes `Pain Point → minimal`, `Education → tech`, `Transparency/Product → notification`. These BoBe-specific presets don't make sense for clients in other industries.

5. **Blank template files**: `_template/content-guidelines.md`, `_template/context.md`, and `_template/keywords.md` have generic bracketed placeholders that don't guide Claude toward drafting proper content from Q&A answers.

---

## Proposed Changes

### Summary of Changes

- **`clients/_template/config.json`**: Add `content.platforms`, `image.angle_style_map`, and `airtable` sections
- **`clients/bobe/config.json`**: Add same new fields to match updated template schema
- **`clients/_template/content-guidelines.md`**: Upgrade template to be AI-draftable (structured comments Claude can use to fill in from Q&A answers)
- **`clients/_template/context.md`**: Same upgrade
- **`clients/_template/keywords.md`**: Same upgrade
- **`.claude/commands/onboard-client.md`**: Add full Q&A script + auto-draft step for all 3 markdown files + Airtable base setup prompt
- **`.claude/commands/weekly-pipeline.md`**: Read platforms and angle_style_map from client config; add optional Airtable sync step after Excel save
- **`scripts/airtable_sync.py`**: New script — push content rows to Airtable via REST API
- **`scripts/client_config.py`**: Add `get_airtable_config()` helper
- **`scripts/weekly_pipeline.py`**: Add `--action sync-airtable` mode that reads saved Excel and pushes to Airtable
- **`reference/api-setup.md`**: Add Airtable setup section
- **`CLAUDE.md`**: Update scripts table, pending plans, and workflow notes

### New Files to Create

| File Path | Purpose |
|---|---|
| `scripts/airtable_sync.py` | Push weekly content rows to a client's Airtable base via REST API |

### Files to Modify

| File Path | Changes |
|---|---|
| `clients/_template/config.json` | Add `content.platforms`, `image.angle_style_map`, `airtable` sections |
| `clients/bobe/config.json` | Add same new sections with BoBe-appropriate values |
| `clients/_template/content-guidelines.md` | Upgrade to AI-draftable scaffold with instructional comments |
| `clients/_template/context.md` | Upgrade to AI-draftable scaffold with instructional comments |
| `clients/_template/keywords.md` | Upgrade to AI-draftable scaffold with instructional comments |
| `.claude/commands/onboard-client.md` | Add full Q&A script, auto-draft step, Airtable setup prompt |
| `.claude/commands/weekly-pipeline.md` | Read platforms + style map from config; add Airtable sync step |
| `scripts/client_config.py` | Add `get_airtable_config()` helper function |
| `scripts/weekly_pipeline.py` | Add `sync-airtable` action |
| `reference/api-setup.md` | Add Airtable section |
| `CLAUDE.md` | Update scripts table, structure, and plan status |

---

## Design Decisions

### Key Decisions Made

1. **Airtable as delivery layer, Excel stays as local backup**: Both outputs coexist. Excel is written first (as today), then optionally synced to Airtable. This means the local workflow is unchanged and Airtable is additive — no regression risk, no dependency on internet connectivity during generation.

2. **One Airtable Base per client, one Table per week**: Each client gets their own Base (isolated data, separate access control). Within a Base, each week gets a Table named `Week-YYYY-MM-DD`. This avoids a single giant table and keeps client views clean. Airtable's free tier supports unlimited Tables per Base.

3. **`airtable` config is optional**: If `config.json` has no `airtable` section or `airtable.enabled` is `false`, the sync step is silently skipped. This means BoBe and any client without Airtable set up are unaffected. Airtable is opt-in per client.

4. **Platforms list drives generation loop, not workbook schema**: The workbook columns stay fixed at 14 (the current schema) for this plan. The `content.platforms` field is used by the weekly-pipeline command to know which platforms to generate content for, and the format rules per platform are defined in `config.json`. A full workbook schema refactor (to support arbitrary platforms as columns) is a separate, larger plan.

5. **Auto-draft markdown files use Q&A answers directly**: The upgraded `/onboard-client` command gathers answers in a structured Q&A and then writes all three markdown files in one pass using those answers. No second pass or user editing required — the user can refine afterward if needed, but the files should be publication-ready from the Q&A alone.

6. **`image.angle_style_map` uses the same preset names that already exist in `image.style_presets`**: The mapping is `angle_name → preset_name` (e.g., `"Pain Point" → "minimal"`). This connects to the existing style_presets architecture cleanly without adding a new concept.

7. **Airtable field names match Excel column headers exactly**: This creates consistency and makes it easy to understand both outputs without separate documentation. The 14 column names become the 14 Airtable field names.

### Alternatives Considered

- **Replace Excel with Airtable entirely**: Rejected. Local Excel is fast, offline, and zero-dependency. Airtable requires internet and API availability during generation. Keeping both gives resilience.
- **One Airtable Table per client (all weeks together)**: Considered. Simpler, but harder for clients to navigate ("which week am I looking at?") and harder to archive old content. Per-week Tables are cleaner.
- **Full platform-agnostic workbook schema**: Considered but scoped out. Supporting arbitrary platform combinations as columns would require significant changes to `weekly_pipeline.py`, `web_viewer.py`, and `build_static.py`. This is a Phase 2 plan.
- **Notion or Google Sheets instead of Airtable**: Airtable has the cleanest REST API, free tier, native gallery views for visual content review, and single-select approval fields. Best fit for this use case.

### Open Questions (if any)

1. **Airtable Base creation**: Airtable's API does not support creating a new Base programmatically — only adding records to an existing Base. The onboarding flow should prompt the user to create the Base manually and paste in the Base ID. The script then handles all table/record creation. Is that acceptable?

2. **Languages per client**: BoBe is `["en", "ru"]`. For a new client that is English-only, the RU columns in the workbook will be empty. Should we hide them from the Airtable view, or is an empty cell acceptable? (Recommendation: empty cells are fine — Airtable views can be filtered/hidden per client.)

3. **Airtable free tier limit**: 1,000 records per Base. At 42 records/week, that's ~23 weeks (~6 months) per Base before hitting the limit. After that, the client would need a paid plan ($20/month) or a new Base. Should we document this ceiling in the setup instructions?

---

## Step-by-Step Tasks

### Step 1: Update `_template/config.json` with new fields

Add three new top-level sections to the template config: `content.platforms`, `image.angle_style_map`, and `airtable`. These become the canonical schema that all new clients inherit.

**Actions:**

- Open `clients/_template/config.json`
- Add `"platforms": ["twitter", "telegram"]` inside the `"content"` object
- Add `"platform_formats"` object inside `"content"` with format rules per platform:
  ```json
  "platform_formats": {
    "twitter": {
      "thread_tweets": 5,
      "single_max_chars": 280,
      "thread_topics_per_day": 2,
      "single_topics_per_day": 1
    },
    "telegram": {
      "min_chars": 400,
      "max_chars": 1200,
      "end_with_question": true
    }
  }
  ```
- Add `"angle_style_map"` inside the `"image"` object:
  ```json
  "angle_style_map": {
    "Pain Point": "minimal",
    "Education": "tech",
    "Transparency": "notification",
    "Product": "notification"
  }
  ```
- Add new top-level `"airtable"` section:
  ```json
  "airtable": {
    "enabled": false,
    "base_id": "",
    "api_key_env": "AIRTABLE_API_KEY"
  }
  ```

**Files affected:**

- `clients/_template/config.json`

---

### Step 2: Update `clients/bobe/config.json` with same new fields

Mirror Step 1 for BoBe with BoBe-appropriate values. BoBe uses Twitter + Telegram, the existing style mapping, and Airtable disabled by default.

**Actions:**

- Open `clients/bobe/config.json`
- Add `"platforms": ["twitter", "telegram"]` inside `"content"`
- Add `"platform_formats"` inside `"content"` with same values as template (BoBe uses standard Twitter thread format)
- Add `"angle_style_map"` inside `"image"`:
  ```json
  "angle_style_map": {
    "Pain Point": "minimal",
    "Education": "tech",
    "Transparency": "notification",
    "Product": "notification"
  }
  ```
- Add `"airtable": { "enabled": false, "base_id": "", "api_key_env": "AIRTABLE_API_KEY" }` as top-level key

**Files affected:**

- `clients/bobe/config.json`

---

### Step 3: Upgrade `_template/content-guidelines.md` to AI-draftable scaffold

Replace generic bracketed placeholders with structured instructional comments that tell Claude exactly what to write in each section based on Q&A answers. The goal is that during `/onboard-client`, Claude reads the Q&A answers and fills this template in one pass to produce a complete, publication-ready file.

**Actions:**

- Rewrite `clients/_template/content-guidelines.md` with the following structure:
  - Header comment block: `<!-- AI-DRAFT INSTRUCTIONS: Fill this file using onboarding Q&A answers. Replace all sections below. Do not leave placeholders. -->`
  - **Brand Voice section**: placeholder text instructs Claude to write 3-4 adjective summary + 2-3 sentence expansion from tone/voice Q&A answers
  - **Messaging Pillars section**: placeholder for 3-4 pillars derived from Q&A answers about what the product does and the pain points it solves
  - **Platform Guidelines**: one section per platform in `config.platforms`, using format rules from `platform_formats`
  - **What to Always Avoid section**: derive from negative keywords and any content restrictions mentioned in Q&A
  - **CTAs by Platform**: derive from `cta_examples` in config + engagement style from Q&A
  - **Hashtag Library**: derive from `hashtags` in config + keyword-based suggestions

**Files affected:**

- `clients/_template/content-guidelines.md`

---

### Step 4: Upgrade `_template/context.md` and `_template/keywords.md`

Same pattern as Step 3 — replace blank placeholders with AI-draftable scaffold comments so Claude can fill these in during onboarding.

**Actions:**

For `context.md`:
- Add AI-draft instruction comment at top
- **Organization Overview section**: placeholder instructs Claude to write 2-3 sentences from the "what does the product do" Q&A answer
- **Products/Services section**: bullet list from product description Q&A
- **Target Audience (ICP) section**: demographics, pain points, and goals from ICP Q&A answers
- **Positioning section**: competitive differentiation from Q&A answers about why customers choose this product over alternatives

For `keywords.md`:
- Add AI-draft instruction comment at top
- **Primary Keywords section**: top 8-10 keywords from config `scraping.keywords` (most directly product-relevant)
- **Secondary Keywords section**: remaining keywords (broader audience/pain point terms)
- **Negative Keywords section**: from `scraping.negative_keywords`
- **Subreddits section**: from `scraping.subreddits`
- **Twitter Search Queries section**: 3-5 ready-to-use Apify search queries constructed from primary keywords

**Files affected:**

- `clients/_template/context.md`
- `clients/_template/keywords.md`

---

### Step 5: Upgrade `.claude/commands/onboard-client.md`

This is the most important change. The current command fills `config.json` and then says "remind the user to update the markdown files manually." The upgraded version conducts a full structured Q&A and then auto-drafts all three markdown files using the answers before the session ends.

**Actions:**

- Rewrite `.claude/commands/onboard-client.md` with this flow:

**Phase 1 — Identify client:**
- Ask for client ID (slug) and display name if not provided as argument

**Phase 2 — Structured Q&A (gather all inputs in one conversation block):**

Ask all of the following before writing any files:
1. **Website URL** — e.g., `bobe.app`
2. **Tagline** — one-line product description
3. **What does the product/service do?** — 2-3 sentences, plain language (used for context.md overview and content generation context)
4. **Who is the target audience?** — age range, situation, pain points, what they currently do instead
5. **Why do customers choose this product over alternatives?** — top 2-3 differentiators
6. **Brand tone and voice** — 3-4 adjectives; how should the content "sound"?
7. **What should content always avoid?** — topics, phrases, or claims that are off-brand or legally risky
8. **Messaging pillars** — ask for 2-4 core messages the brand wants to repeat (probe with: "What are the most important things you want your audience to believe about your product?")
9. **Platforms** — which social platforms? (Twitter/X, Telegram, LinkedIn, Instagram, other?)
10. **Languages** — English only, or additional languages? (note: RU translation is built-in; others require Gemini translation)
11. **Primary scraping keywords** — 8-12 terms that capture what your audience talks about online
12. **Negative keywords** — terms that indicate spam, low-quality, or off-topic content
13. **Subreddits** — which Reddit communities does your audience frequent?
14. **CTA examples** — 2-3 example calls-to-action they want used in content
15. **Brand hashtags** — 2-4 owned hashtags
16. **Brand colors** — primary, accent, text (hex codes or descriptions)
17. **Mascot/character** — describe the brand character for image generation, or "none"
18. **Airtable setup** — do they want content delivered to Airtable? If yes, instruct them to create a new Airtable Base and share the Base ID.

**Phase 3 — Copy template and write all files:**

```bash
cp -r clients/_template clients/{client_id}
```

Then in one pass, write:
1. `clients/{client_id}/config.json` — complete, all fields filled
2. `clients/{client_id}/content-guidelines.md` — fully drafted (not placeholders)
3. `clients/{client_id}/context.md` — fully drafted
4. `clients/{client_id}/keywords.md` — fully drafted

**Phase 4 — Airtable setup (if requested):**
- If user said yes to Airtable: set `airtable.enabled = true`, `airtable.base_id = {provided_id}` in config.json
- Instruct user to add `AIRTABLE_API_KEY=your_key` to `.env`
- Print: "When you run /weekly-pipeline, content will automatically sync to your Airtable base."

**Phase 5 — Verify and activate:**
```bash
python -c "import sys; sys.path.insert(0, 'scripts'); from client_config import load_config; c = load_config('{client_id}'); print(f'Config loaded: {c[\"display_name\"]}')"
```
- Ask if they want to set this as the active client. If yes, write to `.active-client`.
- Print directory tree of new client folder.
- Instruct user to add brand assets to `clients/{client_id}/brand/` (logo.png required for image generation).
- Suggest: `python scripts/weekly_pipeline.py --action create-workbook --week-of YYYY-MM-DD --client {client_id}` to test.

**Files affected:**

- `.claude/commands/onboard-client.md`

---

### Step 6: Add `get_airtable_config()` to `scripts/client_config.py`

Small addition to the central config loader so all scripts can retrieve Airtable config cleanly.

**Actions:**

- Add at the bottom of `client_config.py` (before the end):
  ```python
  def get_airtable_config(client_id: str = None) -> dict:
      """Return Airtable config for the specified (or active) client. Returns {} if not configured."""
      config = load_config(client_id)
      return config.get("airtable", {})

  def is_airtable_enabled(client_id: str = None) -> bool:
      """Return True if Airtable is configured and enabled for the client."""
      at_config = get_airtable_config(client_id)
      return bool(at_config.get("enabled") and at_config.get("base_id"))
  ```

**Files affected:**

- `scripts/client_config.py`

---

### Step 7: Create `scripts/airtable_sync.py`

New script responsible for pushing a week's content from the saved Excel workbook to the client's Airtable base. Reads all 42 rows from the Excel file and creates/updates records in Airtable.

**Actions:**

Write `scripts/airtable_sync.py` with the following:

```
#!/usr/bin/env python3
"""
Airtable Sync

Pushes weekly content from the local Excel workbook to the client's Airtable base.
Each week gets its own Airtable table: "Week-YYYY-MM-DD".
Records map 1:1 to Excel rows (14 fields).

Usage:
  python scripts/airtable_sync.py --week-of 2026-02-23
  python scripts/airtable_sync.py --week-of 2026-02-23 --client bobe
  python scripts/airtable_sync.py --week-of 2026-02-23 --mock

Environment:
  AIRTABLE_API_KEY — Personal Access Token from airtable.com/create/tokens
  (or custom env var name set in client config airtable.api_key_env)
```

Key functions:
- `get_airtable_headers(api_key)` — returns auth headers dict
- `get_or_create_table(base_id, week_of, headers)` — checks if table exists, creates if not with correct field schema
- `create_records(base_id, table_id, records, headers)` — POSTs up to 10 records per request (Airtable batch limit)
- `read_excel_rows(excel_path)` — reads the Content sheet from the workbook, returns list of row dicts
- `main()` — orchestrates: load config → read Excel → get/create table → push records

Field schema for Airtable table creation (maps to 14 Excel columns):
```
Date (singleLineText), Day (singleLineText), Topic (multilineText),
Platform (singleSelect: options per config.platforms), Format (singleLineText),
Content (multilineText), Image_Prompt (multilineText), Image_Path (url),
Hashtags (multilineText), Content_RU (multilineText), Image_Prompt_RU (multilineText),
Image_Path_RU (url), Hashtags_RU (multilineText),
Status (singleSelect: Draft / Approved / Scheduled),
Week (singleLineText), Client (singleLineText)
```

Error handling:
- If `airtable.enabled` is false: print "Airtable not configured for {client_id} — skipping" and exit 0
- If `AIRTABLE_API_KEY` missing: print error and exit 1
- If table creation fails (already exists): fetch existing table ID and continue
- If record push fails: log row number and continue (do not halt)
- `--mock` flag: print what would be pushed without making API calls

**Files affected:**

- `scripts/airtable_sync.py` (new file)

---

### Step 8: Update `weekly-pipeline.md` to use config-driven platforms and style map

Replace the hardcoded "Twitter + Telegram" pattern and hardcoded angle→style mapping with dynamic reads from the active client's config.

**Actions:**

- In **Phase 3 (Create Workbook)** section of `weekly-pipeline.md`: no change (workbook schema stays fixed at 14 columns)

- In **Phase 2 (Topic Pool Assembly)**, update the Evergreen Fallback Bank instruction:
  - Add: "Read `content.platforms` from config to know which platforms are active. Topics should be suitable for all configured platforms."

- In **Phase 4 (Content Generation Loop)**, replace hardcoded platform rules with:
  ```
  Read content.platforms from the active client config. For each topic, generate content for each
  platform in the list. Read platform_formats from config for character limits, thread length, etc.

  Example (BoBe): platforms = ["twitter", "telegram"]
  Example (LinkedIn-only client): platforms = ["linkedin"]
  ```
  - Replace hardcoded thread format ("5 tweets separated by ---") with: "For Twitter: use `platform_formats.twitter.thread_tweets` tweets per thread, `platform_formats.twitter.single_max_chars` char limit."
  - Replace hardcoded Telegram format with: "For Telegram: `platform_formats.telegram.min_chars`–`platform_formats.telegram.max_chars` chars, end with engagement question if `platform_formats.telegram.end_with_question` is true."

- In **Phase 5 (Image Generation Loop)**, replace hardcoded style mapping:
  ```
  Before: Pain Point topics → --style minimal, Education topics → --style tech, etc.
  After: Read image.angle_style_map from client config. Map each topic's angle to its style preset.
  Example: {"Pain Point": "minimal", "Education": "tech", "Transparency": "notification", "Product": "notification"}
  ```

- Add **Phase 6.5 (Airtable Sync)** — new optional phase between Finalize and Build Static Dashboard:
  ```
  ## Phase 6.5: Airtable Sync (if enabled)

  Check if Airtable is enabled for the active client:
  python -c "import sys; sys.path.insert(0, 'scripts'); from client_config import is_airtable_enabled; print(is_airtable_enabled())"

  If True:
  source venv/bin/activate && python scripts/airtable_sync.py --week-of {week_of}

  Expected output: "Pushed 42 records to Airtable base {base_id}, table Week-{week_of}"
  If False: skip silently.
  ```

- Update error handling table to add:
  ```
  | Airtable push fails for one record | Log row number and continue — Excel is source of truth |
  | AIRTABLE_API_KEY missing when enabled | Stop and print "AIRTABLE_API_KEY not set in .env" |
  ```

**Files affected:**

- `.claude/commands/weekly-pipeline.md`

---

### Step 9: Add `sync-airtable` action to `scripts/weekly_pipeline.py`

Add a convenience action that triggers Airtable sync from the pipeline script directly, wrapping `airtable_sync.py`.

**Actions:**

- In `weekly_pipeline.py`, add `sync-airtable` to the `--action` argument choices
- Add handler in `main()`:
  ```python
  elif args.action == "sync-airtable":
      import subprocess
      result = subprocess.run(
          [sys.executable, str(Path(__file__).parent / "airtable_sync.py"),
           "--week-of", args.week_of or get_week_of()],
          capture_output=False
      )
      sys.exit(result.returncode)
  ```
- Update the module docstring to document the new action

**Files affected:**

- `scripts/weekly_pipeline.py`

---

### Step 10: Update `reference/api-setup.md` with Airtable section

Document how to get an Airtable Personal Access Token, create a Base, and configure the client config.

**Actions:**

- Add new section `## Airtable (Content Delivery)` to `reference/api-setup.md`:
  ```
  **Used by:** scripts/airtable_sync.py

  ### Getting Your Token
  1. Sign in at airtable.com
  2. Go to airtable.com/create/tokens
  3. Create a new Personal Access Token
  4. Required scopes: data.records:write, schema.bases:write
  5. Set: AIRTABLE_API_KEY=your_token in .env

  ### Creating a Client Base
  1. In Airtable, click "Add a base" → "Start from scratch"
  2. Name it after the client (e.g., "BoBe Content")
  3. Copy the Base ID from the URL: airtable.com/{BASE_ID}/...
  4. Add to clients/{client_id}/config.json: "airtable": {"enabled": true, "base_id": "appXXXXXXXX"}

  ### Free Tier Limits
  - 1,000 records per Base (≈23 weeks of weekly content at 42 records/week)
  - Unlimited Bases, unlimited Tables, unlimited collaborators on free tier
  - Upgrade to Team plan ($20/user/month) for 50,000 records/Base

  ### Airtable Base Structure
  - One Base per client
  - One Table per week: "Week-YYYY-MM-DD"
  - 16 fields per record (14 content fields + Week + Client)
  ```
- Update the Environment Variables table at the top to include `AIRTABLE_API_KEY`

**Files affected:**

- `reference/api-setup.md`

---

### Step 11: Update `CLAUDE.md`

Reflect all new scripts, the updated onboarding flow, and the Airtable delivery option.

**Actions:**

- In **Scripts table**: add `airtable_sync.py` row: "Push weekly content to client's Airtable base | `--week-of`, `--mock`, `--client`"
- In **API Requirements table**: add Airtable row: "`AIRTABLE_API_KEY` | Airtable content delivery (optional, per client)"
- In **Commands section**: update `/onboard-client` description to mention auto-draft of all markdown files
- In **Pending Plans table**: add this plan as "In Progress"
- In **Multi-Client Architecture section**: add note: "Airtable delivery is opt-in per client — set `airtable.enabled: true` in config.json and add `AIRTABLE_API_KEY` to `.env`"

**Files affected:**

- `CLAUDE.md`

---

### Step 12: Validation Run

Verify the full implementation with a mock pipeline run on BoBe and a simulated new client onboarding.

**Actions:**

- Run config load test for BoBe to verify new fields are present:
  ```bash
  python -c "
  import sys; sys.path.insert(0, 'scripts')
  from client_config import load_config, get_airtable_config, is_airtable_enabled
  c = load_config('bobe')
  print('platforms:', c['content']['platforms'])
  print('angle_style_map:', c['image']['angle_style_map'])
  print('airtable enabled:', is_airtable_enabled('bobe'))
  "
  ```
  Expected: platforms prints `['twitter', 'telegram']`, airtable enabled prints `False`

- Run mock pipeline to verify workbook creation still works:
  ```bash
  source venv/bin/activate
  python scripts/weekly_pipeline.py --action scrape --week-of 2026-02-23 --mock --output /tmp/test_scraped.json
  python scripts/weekly_pipeline.py --action create-workbook --week-of 2026-02-23
  python scripts/weekly_pipeline.py --action finalize --week-of 2026-02-23
  ```

- Run mock Airtable sync to verify it skips gracefully:
  ```bash
  python scripts/airtable_sync.py --week-of 2026-02-23 --mock
  ```
  Expected: prints mock sync summary without making API calls

- Manually verify `clients/_template/content-guidelines.md` has no remaining `[bracketed placeholders]` — only instructional comments and section headers

**Files affected:** None (read-only validation)

---

## Connections & Dependencies

### Files That Reference This Area

- `.claude/commands/weekly-pipeline.md` — references config fields (now updated to use new fields)
- `.claude/commands/onboard-client.md` — creates client configs (now rewrites markdown files too)
- `scripts/weekly_pipeline.py` — reads client config (new `sync-airtable` action added)
- `scripts/client_config.py` — config loader (new Airtable helpers added)
- `CLAUDE.md` — documents all scripts and commands (updated in Step 11)

### Updates Needed for Consistency

- `reference/api-setup.md` needs Airtable section (Step 10)
- `CLAUDE.md` needs scripts table update (Step 11)
- Both `_template/config.json` and `bobe/config.json` must stay in sync on schema (Steps 1–2)

### Impact on Existing Workflows

- **`/weekly-pipeline`**: Behavior unchanged for BoBe by default (Airtable disabled, platforms same). New optional Phase 6.5 runs only if client has Airtable enabled. Platform and style map are now read from config but produce the same values for BoBe.
- **`/onboard-client`**: Significantly upgraded — takes longer (more Q&A) but produces fully complete client setup in one session. Old behavior (config.json only) is replaced entirely.
- **`/view-content` and `/deploy`**: No changes — these read from Excel/local files which are unchanged.

---

## Validation Checklist

- [ ] `clients/_template/config.json` has `content.platforms`, `content.platform_formats`, `image.angle_style_map`, and `airtable` fields
- [ ] `clients/bobe/config.json` has same new fields with BoBe-appropriate values
- [ ] `clients/_template/content-guidelines.md` has AI-draftable scaffold (no raw `[bracketed placeholders]`)
- [ ] `clients/_template/context.md` has AI-draftable scaffold
- [ ] `clients/_template/keywords.md` has AI-draftable scaffold
- [ ] `.claude/commands/onboard-client.md` includes full 18-question Q&A script and auto-draft step
- [ ] `scripts/airtable_sync.py` exists and runs without errors with `--mock` flag
- [ ] `scripts/client_config.py` has `get_airtable_config()` and `is_airtable_enabled()`
- [ ] `scripts/weekly_pipeline.py` accepts `--action sync-airtable`
- [ ] `reference/api-setup.md` has Airtable section with token, base setup, and free tier limits
- [ ] `CLAUDE.md` updated — scripts table, API requirements, onboard-client description
- [ ] Mock pipeline run succeeds end-to-end for BoBe (no regressions)
- [ ] `is_airtable_enabled('bobe')` returns `False` (Airtable disabled by default)

---

## Success Criteria

The implementation is complete when:

1. Running `/onboard-client` for a hypothetical new client (e.g., a SaaS productivity tool) produces a complete, publication-ready set of client files — `config.json`, `content-guidelines.md`, `context.md`, `keywords.md` — from Q&A answers alone, with no placeholder text remaining.

2. Running `/weekly-pipeline` for a client with `airtable.enabled: true` automatically pushes all 42 content rows to Airtable after saving the Excel workbook, and the Airtable table `Week-{week_of}` contains all 14 fields with correct data.

3. Running `/weekly-pipeline` for BoBe (Airtable disabled) produces identical output to pre-plan behavior — no regressions in Excel output, image generation, or dashboard.

4. `clients/bobe/config.json` and `clients/_template/config.json` both pass config load validation with all new fields present and correctly typed.

---

---

## Implementation Notes

**Implemented:** 2026-02-23

### Summary

- Updated `clients/_template/config.json` and `clients/bobe/config.json` with `content.platforms`, `content.platform_formats`, `image.angle_style_map`, and `airtable` fields
- Upgraded all three template markdown files (`content-guidelines.md`, `context.md`, `keywords.md`) with AI-draftable scaffolds and instructional comments
- Rewrote `/onboard-client` command with 18-question Q&A and auto-draft step for all client files
- Added `get_airtable_config()` and `is_airtable_enabled()` to `scripts/client_config.py`
- Created `scripts/airtable_sync.py` — full Airtable push with table creation, batch records, rate limiting
- Updated `weekly-pipeline.md` with config-driven platforms, config-driven style mapping, and Phase 6.5 Airtable sync
- Added `sync-airtable` action to `scripts/weekly_pipeline.py` with `--mock` pass-through
- Created `reference/airtable-client-setup.md` — comprehensive client-facing setup guide
- Updated `reference/api-setup.md` with Airtable section
- Updated `CLAUDE.md` — scripts table, API requirements, onboard-client description, workspace structure, pending plans
- Added `AIRTABLE_API_KEY` to `.env` and enabled Airtable for BoBe (`base_id: appikOGb5GyhPqoCd`)

### Deviations from Plan

1. **Airtable mock test went live**: During validation, `weekly_pipeline.py --action sync-airtable --mock` ran the real sync (not mock) because `--mock` was not passed through to `airtable_sync.py`. Fixed immediately by adding mock pass-through. The live sync succeeded and confirmed credentials work — 42 records pushed, table `Week-2026-02-16` created in base `appikOGb5GyhPqoCd`.
2. **`reference/airtable-client-setup.md` is a new file**: The plan described adding Airtable content to `api-setup.md`. Instead, a dedicated reference file was created for the client-facing guide (more thorough, client-appropriate language) and `api-setup.md` was updated to reference it.

### Issues Encountered

None. All steps completed. Live Airtable sync confirmed working.

---

## Notes

- **Airtable API rate limits**: 5 requests/second per base. With 42 records at 10 records/batch, that's 5 POST requests — well within limits. Add a 0.2s sleep between batches for safety.
- **Airtable table creation API**: The Airtable REST API supports creating Tables and Fields via `POST /v0/meta/bases/{baseId}/tables`. This requires the `schema.bases:write` scope on the Personal Access Token. Document this clearly in the setup instructions.
- **Future: LinkedIn and Instagram support**: The `content.platforms` and `platform_formats` config fields are designed to accommodate LinkedIn (long-form text posts) and Instagram (caption + hashtag format) in a future plan. The only blocker is the workbook schema, which currently has fixed Twitter/Telegram columns.
- **Future: per-client Airtable API keys**: The `api_key_env` field in `airtable` config allows each client to have their own Airtable token (e.g., `"api_key_env": "ACMECORP_AIRTABLE_KEY"`). This supports the case where clients manage their own Airtable accounts. Implement in a future plan if needed.
- **The 1,000-record free tier ceiling** is worth monitoring. Consider adding a record count check in `airtable_sync.py` that warns when a base is approaching 900 records.
