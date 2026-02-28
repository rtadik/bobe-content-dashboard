# Plan: Three-Bucket Content Strategy

**Created:** 2026-02-26
**Status:** Implemented
**Request:** Restructure the weekly pipeline from 21 all-trending topics into 3 configurable content buckets of 7 topics each (Trending, Announcements, Education by default). Add belief-journey.md auto-generation at onboarding, client announcement input on the dashboard, 3-tab dashboard UI, 6+ content type options in the intake form, and parallel agent execution throughout implementation.

---

## Overview

### What This Plan Accomplishes

Replaces the current flat 21-topic-all-trending weekly pipeline with a structured 3-bucket system: each week produces 7 trending topics, 7 education topics (belief-building, derived from the client's buyer journey), and 7 announcement angles (generated from a single client-input text). The dashboard gains a tab-based UI where each bucket is its own view, and the Announcements tab includes an input form for the client to submit their weekly update. Clients can choose their 3 content buckets from 7 options at intake, making the system fully configurable per client.

### Why This Matters

The current system is reactive-only (all trending), which leaves two strategic content jobs unfilled: nurturing leads through a belief journey, and letting clients inject their own narrative. The 3-bucket split gives every week a clear structure: discovery (Trending), conversion (Education), and retention/trust (Announcements). This makes the system a proper content funnel, not just a topic reactor.

---

## Current State

### Relevant Existing Structure

- `scripts/pipeline_runner.py` — standalone pipeline, hardcoded 21-topic all-trending logic
- `scripts/weekly_pipeline.py` — workbook management, content save/load, translate
- `scripts/apify_scraper.py` — Twitter/Reddit scraping
- `scripts/client_config.py` — config loader, all scripts import this
- `scripts/web_viewer.py` — Flask dashboard, async job pattern, `/api/` routes
- `scripts/build_static.py` — static site builder, same HTML template as web_viewer
- `clients/bobe/config.json` — client config schema (no content_types field yet)
- `clients/_template/` — template for new clients (no belief-journey.md yet)
- `intake/index.html` + `intake/intake.js` — client self-serve intake form
- `.github/workflows/weekly-pipeline.yml` — GH Actions pipeline runner
- `.github/workflows/auto-onboard.yml` — GH Actions auto-onboard from intake
- `.claude/commands/onboard-client.md` — manual onboarding Q&A command
- `.claude/commands/weekly-pipeline.md` — weekly pipeline Claude command

### Gaps or Problems Being Addressed

- All 21 topics are scraped trending topics — no belief-building, no client voice
- No mechanism for clients to inject their own announcements or updates
- No buyer journey mapping during onboarding — clients lack a structured education framework
- Dashboard shows 42 cards in a flat grid — no categorization or strategic context
- No configurable content strategy at intake — all clients get the same topic sourcing logic
- Workbook has no "Bucket" column — no way to filter or route content by type post-generation

---

## Proposed Changes

### Summary of Changes

- Add `content.content_types` array to `config.json` schema (3 bucket IDs per client)
- Add `content.bucket_size: 7` to config schema
- Add `Bucket` column to workbook Content sheet (column B, 15 columns total)
- Create `scripts/bucket_generators.py` — one generator function per content type
- Refactor `pipeline_runner.py` to read `content_types` from config and run the 3 configured buckets
- Create `clients/{client_id}/belief-journey.md` — 7 belief stages, auto-generated at onboarding
- Add belief-journey generation step to `onboard-client.md` command
- Add belief-journey generation step to `auto-onboard.yml` GitHub Actions workflow
- Add `belief-journey.md` template to `clients/_template/`
- Add `get_belief_journey_path()` helper to `client_config.py`
- Restructure dashboard into 3 tabs (one per bucket) in `web_viewer.py` + `build_static.py`
- Add `POST /api/generate-announcement` endpoint to Flask (`web_viewer.py`)
- Add `.github/workflows/generate-announcement.yml` for live dashboard announcement input
- Add "Content Strategy" section to `intake/index.html` (7 checkboxes, pick exactly 3)
- Update `intake/intake.js` to include `content_types` in JSON and enforce max-3 validation
- Update `auto-onboard.yml` to write `content_types` from intake into `config.json`
- Update `clients/_template/config.json` with `content_types` and `bucket_size` fields
- Update `clients/bobe/config.json` with `content_types` (default: trending, education, announcements)
- Generate `clients/bobe/belief-journey.md` from existing BoBe context files
- Update `.claude/commands/weekly-pipeline.md` to reflect 3-bucket topic assembly
- Update `CLAUDE.md` to reflect new architecture

### New Files to Create

| File Path | Purpose |
|-----------|---------|
| `scripts/bucket_generators.py` | Generation logic per content type: trending, education, announcements, social_proof, behind_the_scenes, community_engagement, market_commentary |
| `clients/_template/belief-journey.md` | Template placeholder for client belief journey (7 stages) |
| `clients/bobe/belief-journey.md` | BoBe-specific belief journey auto-generated from existing context |
| `.github/workflows/generate-announcement.yml` | GH Actions workflow: receives client announcement text, generates 7 angles, rebuilds static site |

### Files to Modify

| File Path | Changes |
|-----------|---------|
| `clients/_template/config.json` | Add `content.content_types`, `content.bucket_size` fields |
| `clients/bobe/config.json` | Add `content_types: ["trending", "education", "announcements"]`, `bucket_size: 7` |
| `scripts/client_config.py` | Add `get_belief_journey_path()`, `get_content_types()`, `get_bucket_size()` helpers |
| `scripts/weekly_pipeline.py` | Add `Bucket` column to workbook schema (15 cols), update `create_weekly_workbook()` and `append_content_row()` |
| `scripts/pipeline_runner.py` | Refactor `run_pipeline()` to read `content_types` and dispatch to `bucket_generators.py`; reduce scrape target from 21 to 7 topics |
| `scripts/web_viewer.py` | Add `bucket` field to `load_content()`, restructure dashboard HTML into 3-tab layout, add `/api/generate-announcement` endpoint |
| `scripts/build_static.py` | Mirror web_viewer tab layout in static render |
| `intake/index.html` | Add "Content Strategy" section with 7 content type checkboxes (pick 3) |
| `intake/intake.js` | Add `content_types` to `buildIntakeJSON()`, enforce max-3 checkbox validation |
| `.github/workflows/auto-onboard.yml` | Add steps: write `content_types` to config.json, generate `belief-journey.md` via Gemini |
| `.claude/commands/onboard-client.md` | Add Phase 3f: generate belief-journey.md from Q&A answers |
| `.claude/commands/weekly-pipeline.md` | Update Phase 2 to describe 3-bucket topic assembly (scrape 7 trending + generate 7 education + reserve 7 announcement slots) |
| `CLAUDE.md` | Update pipeline description, workbook columns (15), new bucket system, new workflow, new files |

---

## Design Decisions

### Key Decisions Made

1. **Bucket column added to workbook (not a separate sheet)**: Keeps the single-sheet Content format that all existing scripts understand, while enabling bucket-level filtering. The new column B is `Bucket` (value: "trending", "education", or "announcements"). All column indices shift by 1 from C onwards — this is a breaking schema change handled in one place (`weekly_pipeline.py`).

2. **Announcements are reserved placeholder rows during pipeline run, filled on client input**: The pipeline creates 7 empty announcement rows with status `"Pending Input"`. These are never content-generated during the pipeline run. Content is generated only when the client submits text from the dashboard. This avoids wasting API calls on unconfirmed copy and gives clients full control.

3. **Belief journey is a static markdown file, not regenerated each week**: Written once at onboarding (by Claude reading intake data), editable by the operator, and referenced every week by the Education bucket generator. This gives stability and editability. The Education bucket generates fresh content angles each week from the same belief stages.

4. **`bucket_generators.py` as a standalone module**: Isolates all bucket-specific generation logic from the orchestrator (`pipeline_runner.py`). Each generator function takes `(config, week_of, day_dates, topics_so_far)` and returns a list of 7 topic dicts with `bucket` field set. Makes it easy to add new bucket types.

5. **Auto-gen fallback for all input-dependent buckets**: For `social_proof`, `behind_the_scenes`, etc. — if no client input exists, the generator produces auto-content (e.g., Social Proof generates community-voice posts using the brand's value props; Behind the Scenes generates process/philosophy posts). Client input text is stored in `outputs/content/{client_id}/{week_of}-bucket-inputs.json` when submitted, and the generator reads this file first before falling back to auto-gen.

6. **3 tabs named dynamically from `content_types`**: Tab labels are derived from the configured bucket types, not hardcoded. The dashboard reads `config.content_types` to name and order tabs. This makes the UI future-proof for any combination of 3 from 7.

7. **Announcement generation for live dashboard uses a new GitHub Actions workflow**: Mirrors the existing `regenerate-item.yml` pattern. Client inputs text on the live dashboard, JS calls GitHub API to trigger `generate-announcement.yml`, workflow generates 7 angles, writes to workbook, rebuilds static site. The PAT in sessionStorage is reused.

8. **BoBe gets `content_types: ["trending", "education", "announcements"]` as default**: The most strategically complete combination. Migration involves only adding new fields to config.json and generating belief-journey.md — no content regeneration needed.

### Alternatives Considered

- **Separate workbook sheets per bucket**: Simpler conceptually, but breaks all existing code that reads a single "Content" sheet. Rejected in favour of the Bucket column approach.
- **Belief journey regenerated each week**: Would ensure fresh framing but risks drift. Since belief stages don't change week to week (the product doesn't change), static-and-editable is more reliable.
- **Announcement generation happening inside the weekly pipeline with a placeholder prompt**: Would pre-generate "generic announcement" content. Rejected because it produces content the client didn't ask for and wastes image generation API calls.

### Open Questions

- None — all design decisions resolved through Q&A.

---

## Step-by-Step Tasks

### Step 1: Config Schema and client_config.py

Update the config schema in `_template/config.json` and `bobe/config.json`, and add helper functions to `client_config.py`. This is the foundational step — all subsequent agents depend on it.

**Actions:**

- In `clients/_template/config.json`: add `"content_types": ["trending", "education", "announcements"]` and `"bucket_size": 7` inside the `"content"` block
- In `clients/bobe/config.json`: add the same two fields with the same defaults
- In `scripts/client_config.py`: add three helpers:
  ```python
  def get_content_types(client_id=None) -> list:
      """Return the 3 content bucket type IDs for the client."""
      config = load_config(client_id)
      return config.get("content", {}).get("content_types", ["trending", "education", "announcements"])

  def get_bucket_size(client_id=None) -> int:
      """Return topics per bucket (always 7)."""
      config = load_config(client_id)
      return config.get("content", {}).get("bucket_size", 7)

  def get_belief_journey_path(client_id=None) -> Path:
      """Return path to the client's belief-journey.md file."""
      return get_client_dir(client_id) / "belief-journey.md"
  ```

**Files affected:**
- `clients/_template/config.json`
- `clients/bobe/config.json`
- `scripts/client_config.py`

---

### Step 2: Workbook Schema Update (weekly_pipeline.py)

Add `Bucket` as column B in the Content sheet. This is a breaking change — all column indices from "Day" onwards shift right by 1 (C→D). Update `create_weekly_workbook()`, `append_content_row()`, `update_ru_columns()`, and `regenerate_topic_content()`.

**Actions:**

- `create_weekly_workbook()`: Update `content_headers` list to insert `"Bucket"` at index 1 (after `"Date"`):
  ```python
  content_headers = [
      "Date", "Bucket", "Day", "Topic", "Platform Target", "Format",
      "Content", "Image Prompt", "Image Path", "Hashtags",
      "Content_RU", "Image_Prompt_RU", "Image_Path_RU", "Hashtags_RU", "Status",
  ]
  content_col_widths = [12, 14, 6, 30, 14, 10, 70, 50, 40, 35, 70, 50, 40, 35, 12]
  ```
- `append_content_row()`: Add `content_item.get("bucket", "trending")` as column 2 value; shift all subsequent column writes right by 1
- `update_ru_columns()`: Shift RU column indices from J/K/L/M (10/11/12/13) to K/L/M/N (11/12/13/14)
- `regenerate_topic_content()`: Update column references — topic name is now column C (index 2+1=3 in 1-based), content is now column G (index 7), etc.
- Update the content_item dict in `pipeline_runner.py` to include `"bucket"` key in every `content_json` dict
- Update `airtable_sync.py` column references if it reads by index (check and fix)

**Files affected:**
- `scripts/weekly_pipeline.py`
- `scripts/pipeline_runner.py` (content_json dict: add `"bucket"` field)
- `scripts/airtable_sync.py` (verify column indices, update if needed)

---

### Step 3: Parallel Agent Execution — 5 Agents

**After Steps 1 and 2 are complete**, spin up 5 parallel subagents. Each agent handles one independent workstream. Launch all 5 in a single message using the Task tool.

---

#### Agent A: `bucket_generators.py` — New script

Create `scripts/bucket_generators.py` with one generator function per content type. Each function returns a list of 7 topic dicts with all fields needed by the content generation loop.

**Function signatures:**
```python
def generate_trending_topics(config, week_of, day_dates, gemini_client, scraped_posts) -> list[dict]
def generate_education_topics(config, week_of, day_dates, gemini_client) -> list[dict]
def generate_announcement_placeholders(config, week_of, day_dates) -> list[dict]
def generate_social_proof_topics(config, week_of, day_dates, gemini_client, client_input=None) -> list[dict]
def generate_behind_the_scenes_topics(config, week_of, day_dates, gemini_client, client_input=None) -> list[dict]
def generate_community_engagement_topics(config, week_of, day_dates, gemini_client) -> list[dict]
def generate_market_commentary_topics(config, week_of, day_dates, gemini_client, scraped_posts=None) -> list[dict]
```

**Each returned topic dict structure:**
```python
{
    "bucket": "trending",          # bucket type ID
    "topic_num": 1,                # 1–7 within this bucket
    "day": "Mon",
    "date": "2026-03-02",
    "topic": "Topic text here",
    "angle": "Pain Point",         # Pain Point | Education | Transparency | Product | Announcement | Social Proof | Behind the Scenes | Community | Market
    "source": "Live",              # Live | Evergreen | Belief Journey | Client Input | Auto
}
```

**`generate_trending_topics` logic:**
- Uses scraped_posts (already fetched), runs TOPIC_POOL_PROMPT variant asking for 7 topics (not 21)
- Falls back to 7 evergreen topics if scraping produced 0 results
- All 7 assigned to days Mon–Sun (1 per day)
- Angles: mix of Pain Point, Trend Reaction, Market Commentary

**`generate_education_topics` logic:**
- Reads `clients/{client_id}/belief-journey.md`
- Extracts 7 belief stages from the file
- Each stage becomes a topic (1 per day, Mon–Sun)
- The topic text is the belief stage reframed as an educational angle
- Prompt: "Write a topic title for social media that teaches [belief stage] to [ICP] without being preachy. Keep it under 80 chars."

**`generate_announcement_placeholders` logic:**
- Returns 7 placeholder dicts with `"status": "Pending Input"` and empty content fields
- These are the slots that get filled when client submits their announcement text
- Loads `{output_dir}/{week_of}-bucket-inputs.json` and checks for `announcements.text` field
- If found: generates 7 angles from the text using Gemini (announcement_angles_prompt)
- If not found: returns placeholder rows

**`announcement_angles_prompt` template:**
```
You are a content strategist for {display_name}.

The client has submitted this announcement:
"{announcement_text}"

Generate 7 different content TOPICS (not full posts) based on this announcement, one per day of the week.
Each topic must approach the announcement from a different angle:
1. Direct announcement angle ("What's new")
2. User benefit angle ("What this means for you")
3. Behind-the-scenes angle ("How we built this")
4. Social proof angle ("What users are saying about this")
5. Educational angle ("Why this matters for [industry]")
6. Comparison angle ("Before vs after this change")
7. Future vision angle ("Where this is taking us")

Rules:
- Each topic max 80 chars
- No em-dashes, en-dashes, double-hyphens
- Tone: {tone}

Return ONLY a JSON array of 7 strings (topic titles), no other text.
```

**`generate_social_proof_topics` logic:**
- If `client_input` provided: derive 7 topics from testimonials/results text
- If not: generate 7 auto topics like "What BoBe users say about automated yield" using community voice framing
- Always use angle: "Social Proof"

**`generate_behind_the_scenes_topics` logic:**
- If `client_input` provided: derive 7 topics from team/process text
- If not: generate 7 auto topics about brand philosophy, decision-making, values
- Always use angle: "Behind the Scenes"

**`generate_community_engagement_topics` logic:**
- Fully auto-gen: 7 discussion-starter topics (questions, polls, debate prompts) relevant to the brand's ICP
- Angle: "Community"

**`generate_market_commentary_topics` logic:**
- Uses scraped_posts if provided, else generates from brand's market context
- 7 topics commenting on broader industry trends through the brand lens
- Angle: "Market Commentary"

**Files affected:**
- `scripts/bucket_generators.py` (new file)

---

#### Agent B: Pipeline Refactor (pipeline_runner.py)

Refactor `run_pipeline()` to use `bucket_generators.py` instead of the monolithic 21-topic Gemini prompt.

**Actions:**

- Import `bucket_generators` at top of file
- Replace Phase 1 (scrape 100 posts → 21 topics) with:
  - Phase 1: Scrape 50 posts (enough for 7 trending topics)
  - Phase 2: Read `content_types` from config
  - Phase 3: For each of the 3 content types, call the corresponding generator function
  - Combine all 3 × 7 = 21 topic dicts into a single ordered list (Mon-Sun, 3 per day, 1 from each bucket)
- The ordering: for each day, assign topic_position 1 = bucket[0], position 2 = bucket[1], position 3 = bucket[2]. So Mon gets trending_topic_1, education_topic_1, announcement_placeholder_1.
- Load `{output_dir}/{week_of}-bucket-inputs.json` before running generators (passed to generators that need it)
- Update content_json assembly loop to include `"bucket"` field
- Keep all existing Phase 4 (content generation), Phase 5 (image generation), Phase 6 (finalize) logic unchanged — they work on topic dicts regardless of source
- Update `TOPIC_POOL_PROMPT` → keep as legacy comment, but no longer used by default

**New orchestration in run_pipeline():**
```python
# Phase 2: Assemble topics by bucket
content_types = client_config.get_content_types(client_id)
bucket_size = client_config.get_bucket_size(client_id)

# Load any existing client inputs for this week
inputs_file = output_dir / f"{week_of}-bucket-inputs.json"
client_inputs = {}
if inputs_file.exists():
    client_inputs = json.loads(inputs_file.read_text())

all_bucket_topics = []
for bucket_type in content_types:
    if bucket_type == "trending":
        bucket_topics = bucket_generators.generate_trending_topics(config, week_of, day_dates, scraped_topics)
    elif bucket_type == "education":
        bucket_topics = bucket_generators.generate_education_topics(config, week_of, day_dates)
    elif bucket_type == "announcements":
        client_ann_text = client_inputs.get("announcements", {}).get("text", "")
        bucket_topics = bucket_generators.generate_announcement_placeholders(config, week_of, day_dates, client_ann_text)
    # ... etc for other types
    all_bucket_topics.append(bucket_topics)  # list of 3 lists of 7 topics each

# Interleave: Mon gets [bucket0[0], bucket1[0], bucket2[0]], Tue gets [bucket0[1], bucket1[1], bucket2[1]], etc.
topics = []
for day_idx in range(bucket_size):  # 0-6
    for bucket_topics in all_bucket_topics:
        if day_idx < len(bucket_topics):
            topics.append(bucket_topics[day_idx])
# Result: 21 topics in order [bucket0_day0, bucket1_day0, bucket2_day0, bucket0_day1, ...]
# Renumber topic_num 1–21
for i, t in enumerate(topics):
    t["topic_num"] = i + 1
```

**Files affected:**
- `scripts/pipeline_runner.py`

---

#### Agent C: Belief Journey Generation + Onboarding Updates

Create `clients/bobe/belief-journey.md` and `clients/_template/belief-journey.md`, update `onboard-client.md` command, and update `auto-onboard.yml` workflow.

**Actions:**

**`clients/_template/belief-journey.md` (new, template placeholder):**
```markdown
# {display_name} — Belief Journey

> Auto-generated during onboarding. Edit these belief stages to refine the education content strategy.
> Each stage represents a belief your target audience must hold before they are ready to become a customer.
> The pipeline uses these 7 stages to generate weekly education content topics.

---

## Belief Stage 1: Awareness of the Problem
**Belief needed:** "I have a real problem that is costing me something."
**Audience starting point:** They may not yet recognise the pain clearly.
**Content angle:** Surface the problem without selling. Make them feel seen.

## Belief Stage 2: [Fill in]
...
```

**`clients/bobe/belief-journey.md` (new, BoBe-specific):**
Generated by Claude reading `clients/bobe/context.md` and `clients/bobe/content-guidelines.md`. The 7 stages for BoBe:
1. Awareness — "I keep losing money trading emotionally"
2. Problem framing — "Manual trading is fundamentally broken for retail users"
3. Solution category — "Automation removes the emotion from trading"
4. Skepticism overcome — "Not all automation is a scam or black box"
5. Risk understanding — "Spot-only, no-leverage automation has a different risk profile"
6. Trust — "BoBe's on-chain transparency means I can verify, not just trust"
7. Action readiness — "I can start with a small amount and understand what's happening to my funds"

Each stage entry should include:
- Stage title
- The belief statement (as the audience should eventually hold it)
- Their starting belief (skepticism/misconception)
- The content angle (how to frame a post that moves them from starting → target)
- Example topic title for this week

**`onboard-client.md` — add Phase 3f (belief journey generation):**
After 3e (keywords.md), add:
```
**3f. Generate `clients/{client_id}/belief-journey.md`:**

Using all Q&A answers, write a belief-journey.md that maps the 7 belief stages
a prospect must hold before they become a customer. Follow this process:

1. Read the client's ICP: who they are, their pain points, desired outcome (from Q4)
2. Read the client's differentiators (Q5) and messaging pillars (Q8)
3. Think: what does a cold prospect believe right now? What must they believe by the time they buy?
4. Map 7 stages from cold-to-ready, each building on the last
5. For each stage: belief statement, starting misconception, content angle, example topic

The 7 stages should follow this arc:
Stage 1: Awareness (they have a problem)
Stage 2: Problem understanding (the problem is bigger than they thought)
Stage 3: Solution awareness (a category of solution exists)
Stage 4: Skepticism (why should they trust this solution?)
Stage 5: Differentiation (why this product specifically?)
Stage 6: Proof (can they verify the claims?)
Stage 7: Action (they're ready — what's the first step?)

Write the full file with all 7 stages before moving to Phase 4.
```

**`auto-onboard.yml` — add two new steps after "Write keywords.md":**

Step 1: Write content_types to config.json (from intake `content_types` field):
```yaml
- name: Write content_types to config.json
  env:
    INTAKE_JSON: ${{ github.event.inputs.intake_json }}
    CLIENT_ID: ${{ steps.parse.outputs.client_id }}
  run: |
    python3 - <<'PYEOF'
    import json, os
    intake = json.loads(os.environ["INTAKE_JSON"])
    client_id = os.environ["CLIENT_ID"]
    config_path = f"clients/{client_id}/config.json"
    with open(config_path) as f:
        config = json.load(f)
    content_types = intake.get("content_types", ["trending", "education", "announcements"])
    if len(content_types) != 3:
        content_types = ["trending", "education", "announcements"]
    config.setdefault("content", {})["content_types"] = content_types
    config["content"]["bucket_size"] = 7
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"content_types written: {content_types}")
    PYEOF
```

Step 2: Generate belief-journey.md via Gemini:
```yaml
- name: Generate belief-journey.md via Gemini
  env:
    INTAKE_JSON: ${{ github.event.inputs.intake_json }}
    CLIENT_ID: ${{ steps.parse.outputs.client_id }}
    GOOGLE_AI_API_KEY: ${{ secrets.GOOGLE_AI_API_KEY }}
  run: |
    python3 - <<'PYEOF'
    import json, os, sys
    from google import genai

    intake = json.loads(os.environ["INTAKE_JSON"])
    client_id = os.environ["CLIENT_ID"]
    api_key = os.environ.get("GOOGLE_AI_API_KEY", "")
    display_name = intake.get("display_name", client_id)

    audience = intake.get("audience", {})
    icp = f"Age: {audience.get('age_range','')}, Situation: {audience.get('situation','')}"
    pain_points = "\n".join(f"- {p}" for p in audience.get("pain_points", []))
    desired_outcome = audience.get("desired_outcome", "")
    differentiators = "\n".join(f"- {d}" for d in intake.get("differentiators", []))
    pillars = "\n".join(f"- {p}" for p in intake.get("voice", {}).get("messaging_pillars", []))
    description = intake.get("description", "")

    prompt = f"""You are a content strategist and conversion expert.

Product: {display_name}
Description: {description}
ICP: {icp}
Pain points:
{pain_points}
Desired outcome: {desired_outcome}
Differentiators:
{differentiators}
Messaging pillars:
{pillars}

Create a 7-stage belief journey for {display_name}. This maps the 7 beliefs a cold prospect must
progressively hold before they become a paying customer.

The 7 stages must follow this arc:
1. Awareness — they recognise they have a costly problem
2. Problem depth — the problem is bigger/more serious than they thought
3. Solution awareness — a category of solution exists
4. Skepticism — why should they trust this solution type?
5. Differentiation — why {display_name} specifically?
6. Proof — how can they verify the claims?
7. Action readiness — they are ready to take the first step

RULES:
- Never use em-dashes, en-dashes, or double-hyphens as punctuation
- Each stage must be specific to {display_name}'s ICP, not generic
- The language should match the tone: {intake.get("voice", {}).get("tone_description", "clear and educational")}

For EACH of the 7 stages, write this exact format:

## Belief Stage N: [Stage Name]
**Belief needed:** "Single sentence stating what the prospect must believe by end of this stage."
**Starting belief:** "What the cold prospect currently thinks (skepticism, misconception, or ignorance)."
**Content angle:** One sentence on how to frame a post that moves them from starting to needed belief.
**Example topic title:** A social media post title (max 80 chars) that serves this belief stage.

Return only the markdown content, no preamble."""

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        content = response.text.strip()
    except Exception as e:
        print(f"Warning: Gemini failed ({e}), writing placeholder belief journey")
        content = f"# {display_name} — Belief Journey\n\n> Auto-generation failed. Fill in manually.\n\n" + \
                  "\n\n".join([f"## Belief Stage {i}: [Stage {i}]\n**Belief needed:** \"\"\n**Starting belief:** \"\"\n**Content angle:** \"\"\n**Example topic title:** \"\"" for i in range(1, 8)])

    header = f"# {display_name} — Belief Journey\n\n> Auto-generated from intake data. Edit to refine.\n> Used by the Education content bucket to generate weekly belief-building topics.\n\n---\n\n"
    output = header + content
    path = f"clients/{client_id}/belief-journey.md"
    with open(path, "w") as f:
        f.write(output)
    print(f"belief-journey.md written ({len(output)} chars)")
    PYEOF
```

**Files affected:**
- `clients/_template/belief-journey.md` (new)
- `clients/bobe/belief-journey.md` (new)
- `.claude/commands/onboard-client.md`
- `.github/workflows/auto-onboard.yml`

---

#### Agent D: Dashboard Tab UI + Announcement Endpoint (web_viewer.py + build_static.py)

Restructure the dashboard from a flat grid into 3 tabs (one per configured bucket). Add announcement input UI to the Announcements tab. Add `/api/generate-announcement` endpoint.

**Actions:**

**`load_content()` in `web_viewer.py`**: Add `"bucket"` field to each topic dict. The bucket is read from column B (index 1, 0-based) of the workbook:
```python
topics[topic]["bucket"] = row[1] or "trending"  # New column B
# All existing column reads shift right by 1: day = row[2], topic = row[3], etc.
```

**New `load_bucket_inputs()` function**: Reads `{output_dir}/{week_of}-bucket-inputs.json` if it exists. Returns dict like `{"announcements": {"text": "...", "submitted_at": "..."}}`

**Dashboard HTML restructure** (the large HTML template string):
Replace the current `<main class="grid">` with a tab-based layout:

```html
<!-- Tab navigation bar -->
<div class="bucket-tabs">
  <button class="bucket-tab active" data-bucket="trending" onclick="switchBucket('trending')">
    📈 Trending
  </button>
  <button class="bucket-tab" data-bucket="education" onclick="switchBucket('education')">
    🎓 Education
  </button>
  <button class="bucket-tab" data-bucket="announcements" onclick="switchBucket('announcements')">
    📣 Announcements
  </button>
</div>

<!-- Announcements input panel (only visible on announcements tab) -->
<div class="announcement-input-panel" id="announcement-input-panel" style="display:none">
  <h3>Weekly Announcement</h3>
  <p>Paste your update below. The system will generate 7 different content angles from it.</p>
  <textarea id="announcement-text" placeholder="e.g. We updated the landing page to include a new yield calculator feature..." rows="4"></textarea>
  <button class="btn-generate-announcement" onclick="submitAnnouncement()">Generate 7 Content Angles</button>
  <div id="announcement-status"></div>
</div>

<!-- Content grid (filtered by active bucket) -->
<main class="grid" id="content-grid">
  {% for t in topics %}
  <div class="card" data-bucket="{{ t.bucket }}" id="card-{{ loop.index }}" style="display:none">
    <!-- existing card HTML unchanged -->
  </div>
  {% endfor %}
</main>
```

**JavaScript additions:**
```javascript
// Tab switching
function switchBucket(bucket) {
  // Update tab active states
  document.querySelectorAll('.bucket-tab').forEach(tab => {
    tab.classList.toggle('active', tab.dataset.bucket === bucket);
  });
  // Show/hide cards
  document.querySelectorAll('.card').forEach(card => {
    card.style.display = card.dataset.bucket === bucket ? '' : 'none';
  });
  // Show announcement input only on announcements tab
  const inputPanel = document.getElementById('announcement-input-panel');
  if (inputPanel) {
    inputPanel.style.display = bucket === 'announcements' ? 'block' : 'none';
  }
  // Save preference
  localStorage.setItem('active-bucket', bucket);
}

// Initialise to saved bucket or first tab
const savedBucket = localStorage.getItem('active-bucket') || 'trending';
switchBucket(savedBucket);

// Announcement generation
async function submitAnnouncement() {
  const text = document.getElementById('announcement-text').value.trim();
  if (!text) { alert('Please enter your announcement text.'); return; }

  const statusEl = document.getElementById('announcement-status');
  statusEl.textContent = 'Generating 7 content angles...';

  // Local Flask flow
  try {
    const resp = await fetch('/api/generate-announcement', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text, date: CURRENT_DATE})
    });
    const data = await resp.json();
    if (data.job_id) {
      // Poll for completion
      pollJobStatus(data.job_id, () => { statusEl.textContent = 'Done! Reload to see generated content.'; });
    } else if (data.success) {
      statusEl.textContent = 'Done! Reload to see content.';
      setTimeout(() => location.reload(), 2000);
    } else {
      statusEl.textContent = 'Error: ' + (data.error || 'Unknown error');
    }
  } catch(e) {
    statusEl.textContent = 'Error: ' + e.message;
  }
}
```

**CSS additions** (add to existing style block):
```css
.bucket-tabs {
  display: flex; gap: 8px; padding: 16px 24px 0;
  border-bottom: 2px solid #1e2d4a; margin-bottom: 0;
}
.bucket-tab {
  padding: 10px 20px; border: none; border-radius: 8px 8px 0 0;
  background: #111b32; color: #8a9bb5; cursor: pointer;
  font-size: 14px; font-weight: 600; transition: all 0.2s;
}
.bucket-tab.active {
  background: #1589dc; color: #fff;
}
.announcement-input-panel {
  margin: 20px 24px; padding: 20px; background: #111b32;
  border-radius: 12px; border: 1px solid #1e2d4a;
}
.announcement-input-panel textarea {
  width: 100%; background: #070a1b; color: #fff; border: 1px solid #1e2d4a;
  border-radius: 8px; padding: 12px; font-size: 14px; resize: vertical;
}
.btn-generate-announcement {
  margin-top: 12px; padding: 10px 20px; background: #1589dc;
  color: #fff; border: none; border-radius: 8px; cursor: pointer; font-weight: 600;
}
```

**New Flask endpoint** (`/api/generate-announcement`):
```python
@app.route("/api/generate-announcement", methods=["POST"])
def api_generate_announcement():
    """Generate 7 announcement content angles from client-submitted text."""
    data = request.get_json(force=True)
    text = (data.get("text") or "").strip()
    date_id = data.get("date", "")
    if not text:
        return jsonify({"success": False, "error": "text is required"}), 400

    # Resolve week_of from date_id
    week_of = date_id.replace("week:", "") if date_id.startswith("week:") else date_id[:10] if date_id else None
    if not week_of:
        return jsonify({"success": False, "error": "valid date required"}), 400

    job_id = str(uuid.uuid4())

    def _run():
        try:
            from bucket_generators import generate_announcement_placeholders
            import client_config as cc
            active_client = cc.get_active_client()
            config = cc.load_config(active_client)
            output_dir = cc.get_output_dir(active_client)

            # Save the input text
            inputs_file = output_dir / f"{week_of}-bucket-inputs.json"
            inputs = {}
            if inputs_file.exists():
                inputs = json.loads(inputs_file.read_text())
            inputs["announcements"] = {"text": text, "submitted_at": datetime.now().isoformat()}
            inputs_file.write_text(json.dumps(inputs, indent=2))

            # Generate 7 angles and update workbook
            from weekly_pipeline import get_week_of
            day_dates = {
                DAYS[i]: (datetime.strptime(week_of, "%Y-%m-%d") + timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range(7)
            }
            # Call the generator with the text
            bucket_topics = generate_announcement_placeholders(config, week_of, day_dates, announcement_text=text)

            # Generate full content for each announcement topic and save to workbook
            # (This uses the same per-topic Gemini generation as pipeline_runner Phase 4)
            # ... generation loop here (reuse call_gemini + CONTENT_GEN_PROMPT pattern)

            with _jobs_lock:
                _jobs[job_id] = {"status": "done"}
        except Exception as e:
            with _jobs_lock:
                _jobs[job_id] = {"status": "error", "error": str(e)}

    with _jobs_lock:
        _jobs[job_id] = {"status": "running"}
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"success": True, "job_id": job_id})
```

**`build_static.py`**: Mirror the tab-based layout. The static build pre-renders all tabs; JavaScript handles switching. The announcement input panel is present in static HTML but the "Generate" button calls the GitHub Actions workflow instead of the local Flask endpoint (same pattern as regen buttons). Add data attribute `data-live="true"` to distinguish live vs local.

**Files affected:**
- `scripts/web_viewer.py`
- `scripts/build_static.py`

---

#### Agent E: Intake Form + Content Strategy Section

Add the "Content Strategy" section to the intake form with 7 content type checkboxes (pick exactly 3).

**Actions:**

**`intake/index.html`**: Add new Section 10 (or insert between existing sections 8 and 9) titled "Content Strategy":

```html
<div class="section-card" id="section-content-strategy">
  <h2 class="section-title">
    <span class="section-num">10</span>
    Content Strategy
  </h2>
  <p class="section-desc">
    Choose exactly 3 content buckets for your weekly content plan. Each bucket produces 7 posts per week.
    Your selection determines what kinds of topics fill your content calendar.
  </p>

  <div class="field-wrapper">
    <label class="field-label">Content Buckets <span class="required">*</span></label>
    <p class="field-hint">Select exactly 3. Each bucket = 7 posts/week on Twitter and Telegram.</p>

    <div class="content-type-grid">
      <label class="content-type-option">
        <input type="checkbox" name="content_types" value="trending" checked>
        <div class="content-type-card">
          <span class="ct-icon">📈</span>
          <span class="ct-name">Trending</span>
          <span class="ct-desc">React to trending industry topics from X and Reddit, filtered by relevance</span>
        </div>
      </label>

      <label class="content-type-option">
        <input type="checkbox" name="content_types" value="education" checked>
        <div class="content-type-card">
          <span class="ct-icon">🎓</span>
          <span class="ct-name">Education</span>
          <span class="ct-desc">Belief-building content mapped to your buyer journey, designed to move leads toward purchase</span>
        </div>
      </label>

      <label class="content-type-option">
        <input type="checkbox" name="content_types" value="announcements" checked>
        <div class="content-type-card">
          <span class="ct-icon">📣</span>
          <span class="ct-name">Announcements</span>
          <span class="ct-desc">You input a weekly update, the system generates 7 content angles from it</span>
        </div>
      </label>

      <label class="content-type-option">
        <input type="checkbox" name="content_types" value="social_proof">
        <div class="content-type-card">
          <span class="ct-icon">⭐</span>
          <span class="ct-name">Social Proof</span>
          <span class="ct-desc">Community wins, user results, testimonials (auto-generated or from your input)</span>
        </div>
      </label>

      <label class="content-type-option">
        <input type="checkbox" name="content_types" value="behind_the_scenes">
        <div class="content-type-card">
          <span class="ct-icon">🔍</span>
          <span class="ct-name">Behind the Scenes</span>
          <span class="ct-desc">Team updates, process transparency, culture and decision-making (auto or client input)</span>
        </div>
      </label>

      <label class="content-type-option">
        <input type="checkbox" name="content_types" value="community_engagement">
        <div class="content-type-card">
          <span class="ct-icon">💬</span>
          <span class="ct-name">Community</span>
          <span class="ct-desc">Discussion starters, polls, audience questions designed to drive replies and engagement</span>
        </div>
      </label>

      <label class="content-type-option">
        <input type="checkbox" name="content_types" value="market_commentary">
        <div class="content-type-card">
          <span class="ct-icon">🌐</span>
          <span class="ct-name">Market Commentary</span>
          <span class="ct-desc">Industry analysis and macro perspectives filtered through your brand's lens</span>
        </div>
      </label>
    </div>
    <div class="field-error" id="error-content_types">Please select exactly 3 content buckets.</div>
    <div class="content-type-counter">
      <span id="ct-count">3</span> / 3 selected
    </div>
  </div>
</div>
```

**CSS additions** (in `intake/intake.css`):
```css
.content-type-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px; margin-top: 12px;
}
.content-type-option input { display: none; }
.content-type-card {
  display: flex; flex-direction: column; gap: 6px;
  padding: 14px; border: 2px solid #1e2d4a; border-radius: 10px;
  cursor: pointer; transition: all 0.2s; background: #070a1b;
}
.content-type-option input:checked + .content-type-card {
  border-color: #1589dc; background: #0d1829;
}
.ct-icon { font-size: 22px; }
.ct-name { font-weight: 700; color: #fff; font-size: 14px; }
.ct-desc { font-size: 12px; color: #8a9bb5; line-height: 1.4; }
.content-type-counter { margin-top: 10px; color: #8a9bb5; font-size: 13px; }
.content-type-counter span { color: #1589dc; font-weight: 700; }
```

**`intake/intake.js` additions:**

Add max-3 enforcement and count display:
```javascript
function initContentTypeSelector() {
  const checkboxes = document.querySelectorAll('input[name="content_types"]');
  const counter = document.getElementById('ct-count');

  checkboxes.forEach(cb => {
    cb.addEventListener('change', () => {
      const checked = Array.from(checkboxes).filter(c => c.checked);
      if (checked.length > 3) {
        cb.checked = false; // Revert the last selection
      }
      const currentCount = Array.from(checkboxes).filter(c => c.checked).length;
      if (counter) counter.textContent = currentCount;
    });
  });
}
```

Add to `validateForm()`:
```javascript
// content_types (exactly 3)
const contentTypesOk = getChecked('content_types').length === 3;
showError('content_types', !contentTypesOk);
if (!contentTypesOk) valid = false;
```

Add to `buildIntakeJSON()`:
```javascript
content_types: getChecked('content_types'),
```

Add `initContentTypeSelector()` to the `DOMContentLoaded` handler.

**Update progress bar**: Add new step for "Content Strategy" section in the progress bar HTML.

**Files affected:**
- `intake/index.html`
- `intake/intake.js`
- `intake/intake.css`

---

### Step 4: GitHub Actions — generate-announcement.yml

Create new workflow for live dashboard announcement generation. Follows the same pattern as `regenerate-item.yml`.

**Actions:**

Create `.github/workflows/generate-announcement.yml`:

```yaml
name: Generate Announcement Content

on:
  workflow_dispatch:
    inputs:
      client_id:
        description: 'Client ID'
        required: true
      week_of:
        description: 'Week start date YYYY-MM-DD'
        required: true
      announcement_text:
        description: 'Client announcement text (2 sentences to several paragraphs)'
        required: true
      mock:
        description: 'Dry run — no API calls'
        type: boolean
        default: false

concurrency:
  group: gh-pages-deploy
  cancel-in-progress: false

jobs:
  generate-announcement:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    permissions:
      contents: write

    steps:
      - name: Checkout main
        uses: actions/checkout@v4
        with:
          ref: main
          token: ${{ secrets.GITHUB_TOKEN }}
          fetch-depth: 0

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: pip install requests openpyxl google-genai python-dotenv jinja2 flask pillow

      - name: Create .env from secrets
        run: |
          echo "APIFY_API_TOKEN=${{ secrets.APIFY_API_TOKEN }}" >> .env
          echo "GOOGLE_AI_API_KEY=${{ secrets.GOOGLE_AI_API_KEY }}" >> .env
          echo "WAVESPEED_API_KEY=${{ secrets.WAVESPEED_API_KEY }}" >> .env
          echo "AIRTABLE_API_KEY=${{ secrets.AIRTABLE_API_KEY }}" >> .env
          echo "GH_REGEN_TOKEN=${{ secrets.GH_REGEN_TOKEN }}" >> .env

      - name: Save announcement input and generate content
        env:
          ANNOUNCEMENT_TEXT: ${{ github.event.inputs.announcement_text }}
          CLIENT_ID: ${{ github.event.inputs.client_id }}
          WEEK_OF: ${{ github.event.inputs.week_of }}
          MOCK: ${{ github.event.inputs.mock }}
        run: |
          ARGS="--client $CLIENT_ID --week-of $WEEK_OF --announcement-text \"$ANNOUNCEMENT_TEXT\""
          if [ "$MOCK" = "true" ]; then ARGS="$ARGS --mock"; fi
          python scripts/pipeline_runner.py $ARGS --mode announcement

      - name: Build static site
        run: |
          python scripts/build_static.py \
            --output dist \
            --include-admin \
            --client ${{ github.event.inputs.client_id }}

      - name: Copy admin panel to dist
        run: |
          mkdir -p dist/admin
          cp admin/index.html dist/admin/index.html
          cp admin/admin.css dist/admin/admin.css
          cp admin/admin.js dist/admin/admin.js

      - name: Deploy to GitHub Pages
        run: |
          cd dist
          git init
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add -A
          git commit -m "Generate announcement content: ${{ github.event.inputs.client_id }} ${{ github.event.inputs.week_of }}"
          git push -f https://x-access-token:${{ secrets.GITHUB_TOKEN }}@github.com/rtadik/bobe-content-dashboard.git HEAD:gh-pages
          cd ..
```

Also add `--mode announcement` flag to `pipeline_runner.py`'s argparser and handler: when `--mode announcement` is passed along with `--announcement-text`, it skips the full pipeline and only runs the announcement bucket generation for the specified week, then finalizes the workbook.

**Files affected:**
- `.github/workflows/generate-announcement.yml` (new)
- `scripts/pipeline_runner.py` (add `--mode` and `--announcement-text` flags)

---

### Step 5: Update weekly-pipeline.md Command

Update the `/weekly-pipeline` Claude command to reflect the 3-bucket structure.

**Actions:**

Update Phase 2 (Topic Pool Assembly):
- Replace "You need 21 topics total (3 per day × 7 days)" with "You need 21 topics total: 7 per bucket × 3 buckets"
- Replace the Evergreen Fallback Bank section with:
  1. **Trending bucket (7 topics)**: Scrape + rank scraped posts; use 7 most relevant; fill remaining with evergreen trending topics from keywords. All 7 go Mon–Sun (1 per day). Source: "Live" or "Evergreen"
  2. **Education bucket (7 topics)**: Read `clients/{active_client}/belief-journey.md`. Extract the 7 belief stages. Frame each as a topic title (max 80 chars). Assign one per day Mon–Sun. Source: "Belief Journey"
  3. **Announcement bucket (7 topics)**: Check if `outputs/content/{active_client}/{week_of}-bucket-inputs.json` exists and has `announcements.text`. If yes: generate 7 angle-topics from the text. If no: create 7 placeholder rows with status "Pending Input", no content generated.
- Update the topic schedule print format to include Bucket column:

```
| # | Bucket | Day | Date | Topic | Angle | Source |
|---|--------|-----|------|-------|-------|--------|
```

- Update Phase 3 workbook creation: note that workbook now has 15 columns including Bucket
- Keep all other phases (content generation, images, finalize) unchanged — they work on topics regardless of bucket

**Files affected:**
- `.claude/commands/weekly-pipeline.md`

---

### Step 6: BoBe Migration

Apply all schema changes to the existing BoBe client and generate its belief-journey.md.

**Actions:**

- Verify `clients/bobe/config.json` has `content_types` and `bucket_size` from Step 1 ✓
- Generate `clients/bobe/belief-journey.md` by running the onboard-client belief journey generation logic against BoBe's existing `context.md` and `content-guidelines.md`
- Validate: run `python -c "import sys; sys.path.insert(0,'scripts'); from client_config import load_config, get_content_types, get_belief_journey_path; c=get_content_types('bobe'); p=get_belief_journey_path('bobe'); print(c, p.exists())"`
- Verify the belief-journey.md has all 7 stages with correct structure
- Run a mock pipeline to confirm the 3-bucket structure works end to end:
  ```bash
  python scripts/pipeline_runner.py --client bobe --week-of 2026-03-02 --mock --skip-images --skip-airtable --skip-deploy
  ```
  Expect: 21 topics (7 trending + 7 education + 7 placeholder), 28 content items (14 trending + 14 education), 14 placeholder rows

**Files affected:**
- `clients/bobe/config.json` (verify Step 1 changes applied)
- `clients/bobe/belief-journey.md` (new, generated)

---

### Step 7: CLAUDE.md Update

Update CLAUDE.md to reflect all architectural changes.

**Actions:**

- Update "Weekly Pipeline Structure" section:
  - Change "21 topics per week (3 per day x 7 days)" to "21 topics per week: 7 per content bucket × 3 buckets"
  - Update workbook columns from 14 to 15 (add Bucket as column B)
  - Replace "Odd items (1,3,5...) = Twitter; Even items (2,4,6...) = Telegram" with the new interleaved structure
- Add "Content Buckets" section describing the 7 types and their generation logic
- Add `belief-journey.md` to the workspace structure diagram under each client folder
- Add `bucket_generators.py` to the Scripts table
- Add `generate-announcement.yml` to the GitHub Actions workflows list
- Update the Intake Form description to include the Content Strategy section
- Update `pipeline_runner.py` entry to note `--mode announcement` flag

**Files affected:**
- `CLAUDE.md`

---

## Connections & Dependencies

### Files That Reference This Area

- `scripts/airtable_sync.py` — reads Content sheet by column index; must be updated if Bucket column shifts indices
- `scripts/web_viewer.py` — `load_content()` reads by column index; needs update for +1 shift
- `scripts/build_static.py` — imports `load_content` from web_viewer; inherits fix automatically
- `admin/admin.js` — triggers `weekly-pipeline.yml` via GitHub API; unchanged (workflow input flags stay the same)
- `.claude/commands/view-content.md` — no changes needed; dashboard UI handles tabs

### Updates Needed for Consistency

- `scripts/airtable_sync.py`: Verify all column index reads and update for +1 shift from Bucket column
- `.claude/commands/onboard-client.md`: Phase 3f (belief journey) added, Phase 5d completion summary updated to include `belief-journey.md`
- `reference/airtable-client-setup.md`: Note that the Content sheet now has 15 columns (add Bucket to column mapping)

### Impact on Existing Workflows

- **`/weekly-pipeline` command**: Phase 2 changes significantly (3 buckets instead of flat 21). All other phases unchanged.
- **`/deploy` command**: No changes needed — `build_static.py` changes are internal.
- **`/onboard-client` command**: Adds Phase 3f (belief journey). All earlier phases unchanged.
- **`/view-content` command**: No changes needed — Flask dashboard handles tabs automatically.
- **GitHub Actions weekly-pipeline.yml**: No changes needed — `pipeline_runner.py` changes are internal.
- **Regen buttons**: No changes needed — they operate on individual rows by topic_index, unaffected by bucket grouping.
- **Existing BoBe workbooks**: Old workbooks (pre-plan) have 14 columns, no Bucket column. The updated `load_content()` should handle missing Bucket gracefully (default to "trending" if column B is a date or day string rather than a bucket type ID). Add a check: `if row[1] in ("Mon","Tue","Wed","Thu","Fri","Sat","Sun"): bucket = "trending"`.

---

## Validation Checklist

- [ ] `clients/bobe/config.json` has `content.content_types` and `content.bucket_size` fields
- [ ] `clients/_template/config.json` has the same new fields
- [ ] `client_config.get_content_types("bobe")` returns `["trending", "education", "announcements"]`
- [ ] `client_config.get_belief_journey_path("bobe").exists()` returns `True`
- [ ] `clients/bobe/belief-journey.md` has all 7 belief stages with required fields
- [ ] Mock pipeline run produces 21 topics with Bucket field set correctly (7 trending, 7 education, 7 announcements)
- [ ] Workbook Content sheet has 15 columns with "Bucket" as column B
- [ ] Flask dashboard (`/view-content`) shows 3 tabs; clicking each shows the correct 14 cards
- [ ] Announcements tab shows the input textarea and Generate button
- [ ] Submitting announcement text in Flask generates 7 content angle cards
- [ ] `intake/index.html` shows Content Strategy section with 7 checkboxes
- [ ] Selecting a 4th checkbox is blocked by JS enforcement
- [ ] Selecting fewer than 3 shows a validation error on form submit
- [ ] `buildIntakeJSON()` includes `content_types` array in output JSON
- [ ] `auto-onboard.yml` writes `content_types` to config.json and generates `belief-journey.md`
- [ ] `.github/workflows/generate-announcement.yml` triggers successfully (mock run)
- [ ] Old BoBe workbooks render correctly in dashboard (graceful bucket fallback)
- [ ] `CLAUDE.md` reflects all new files, scripts, and pipeline structure
- [ ] `airtable_sync.py` column indices correct after Bucket column insertion

---

## Success Criteria

The implementation is complete when:

1. Running `/weekly-pipeline` for BoBe produces a workbook with 14 rows of Trending content (7 topics × 2 platforms), 14 rows of Education content, and 14 placeholder rows for Announcements (status "Pending Input") — 42 rows total, correctly bucketed.
2. A client visiting the live dashboard sees 3 tabs, can input their weekly announcement text, and the system generates 7 angle variations with images via GitHub Actions (verified with a mock run of `generate-announcement.yml`).
3. A new client completing the intake form can select their 3 content buckets from 7 options, submit the form, and receive a `belief-journey.md` auto-generated in their client folder as part of the auto-onboard workflow.

---

## Notes

- **Backward compatibility for old workbooks**: Any workbook generated before this plan (14 columns, no Bucket column) will be read by the updated `load_content()` without errors because the bucket defaulting logic (`if row[1] in DAYS: bucket="trending"`) handles the old format. No migration of existing workbooks is required.
- **Announcement images**: The announcement generation endpoint generates content AND images for the 7 announcement topics, following the same image generation flow as the main pipeline. This means the first announcement submission for a week may take 3-5 minutes (14 images: 7 EN + 7 RU). Subsequent re-submissions (if client revises their announcement) regenerate content but reuse existing image slots.
- **Future: more than 3 buckets**: The architecture supports this — `bucket_size` can be changed from 7 to any number, and `content_types` can hold more than 3 items. The only hard assumption is that `len(content_types) × bucket_size = 21`. For now, enforced as 3 × 7.
- **Belief journey editing**: Clients (via admin or Rut directly) can edit `belief-journey.md` at any time. The changes take effect on the next pipeline run without any code changes needed.
- **Live dashboard announcement UI**: The "Generate" button on the static live dashboard needs the client's GitHub PAT in sessionStorage (same as regen buttons). Add a note to the UI: "You'll need your GitHub token to generate content. Same token you use for regenerating images."

---

## Implementation Notes

**Implemented:** 2026-02-26

### Summary

- Steps 1–7 fully executed across two sessions (second session resumed from context summary)
- Config schema updated in `_template/config.json` and `bobe/config.json` with `content_types` and `bucket_size`
- `client_config.py` extended with `get_content_types()`, `get_bucket_size()`, `get_belief_journey_path()`
- `weekly_pipeline.py` updated to 15-column schema (Bucket added as column B); `append_content_row()` and `finalize()` both support `mock` parameter for correct filename resolution
- `airtable_sync.py` updated to 15-column COLUMN_MAP with Bucket field
- `bucket_generators.py` created with 7 generator functions and `generate_bucket()` dispatcher
- `pipeline_runner.py` refactored for 3-bucket Phase 2; `mock_flag` moved outside try block so it's available in Phase 4 and 6
- `belief-journey.md` created for both `_template/` and `bobe/`
- `onboard-client.md` updated with Phase 3f belief-journey generation step
- `auto-onboard.yml` updated with content_types and belief-journey.md generation steps
- `generate-announcement.yml` GitHub Actions workflow created
- `web_viewer.py` and `build_static.py` updated with bucket tabs, announcement panel, `/api/generate-announcement` endpoint
- Intake form (`index.html`, `intake.css`, `intake.js`) updated with Section 10 content type selection (7 options, pick 3)
- `weekly-pipeline.md` command updated for 3-bucket Phase 2 instructions
- `CLAUDE.md` updated to reflect all structural changes

### Deviations from Plan

- `mock_flag` was defined inside the Phase 3 `try` block; moved outside to ensure it's in scope for Phase 4 `save-content` and Phase 6 `finalize` subprocess calls — both needed `--mock` flag for correct filename resolution
- `finalize()` in `weekly_pipeline.py` also needed a `mock` parameter added (not specified in plan but necessary for correctness)

### Issues Encountered

- **Mock workbook filename mismatch**: `create-workbook --mock` creates `{week_of}-mock-weekly-content.xlsx` but `save-content` and `finalize` were hardcoded to `{week_of}-weekly-content.xlsx`. Fixed by: (1) moving `mock_flag` variable outside the try block in `pipeline_runner.py`, (2) adding `mock` parameter to `append_content_row()` and `finalize()` in `weekly_pipeline.py`, (3) passing `args.mock` in the `save-content` and `finalize` action handlers.
- After fix, mock pipeline ran cleanly: 42/42 items, 0 errors, correct workbook filename throughout all phases.
