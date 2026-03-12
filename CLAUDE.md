# CLAUDE.md

This file is the single source of truth for how Claude should understand and operate within this workspace. It is automatically loaded at the start of every session.

---

## Project Overview

**BoBe** is a Web3 fintech platform where retail crypto users deposit assets into AI-driven automated trading strategies (DCA, grid bots) that generate on-chain USDT yield. Target users are age 20-35, hold $500-$20k in crypto, and are exhausted from emotional trading losses.

**The user** (Rut Adk) is BoBe's Strategic Marketing Lead and Growth Architect, an external partner responsible for acquisition systems, messaging clarity, funnel infrastructure, and ambassador expansion.

**This workspace** is a multi-client content automation platform. It scrapes trending topics, generates Twitter threads and Telegram posts, creates branded images, and packages everything into Excel workbooks for scheduling. Originally built for BoBe, it now supports multiple clients via config-driven architecture. Content is organized into **3 buckets** per week: Trending (scraped), Education (belief-journey), and Announcements (client input → 7 angles).

---

## Content Rules

- **NEVER use em-dashes** (`—` U+2014), en-dashes (`–` U+2013), or double-hyphens (`--`) as punctuation in generated content. Replace with commas, colons, or rephrase. The `---` tweet separator is the only exception (structural, not punctuation).
- Each client's tone, voice, and messaging rules are in `clients/{client_id}/content-guidelines.md` and `clients/{client_id}/config.json`.
- Default (BoBe) tone: transparent, educational, no hype, no guaranteed return claims.

---

## Workspace Structure

```
.
├── CLAUDE.md                 # This file
├── .env                      # API keys (gitignored)
├── .active-client            # Current active client ID (gitignored, default: bobe)
├── .gitignore
├── .github/
│   └── workflows/
│       ├── weekly-pipeline.yml        # GH Actions: workflow_dispatch → pipeline_runner.py → deploy
│       ├── generate-announcement.yml  # GH Actions: client announcement input → 7 content angles → deploy
│       ├── regenerate-item.yml        # GH Actions: regen single topic item (image/content) → deploy
│       ├── publish-to-x.yml           # GH Actions: publish Twitter thread to X → commit xlsx → deploy
│       ├── onboard-client.yml         # GH Actions: workflow_dispatch → create client dir → commit
│       └── auto-onboard.yml           # GH Actions: intake form submit → create client config → deploy
├── .claude/
│   ├── commands/
│   │   ├── prime.md                   # /prime — session initialization
│   │   ├── create-plan.md             # /create-plan — implementation planning
│   │   ├── implement.md               # /implement — execute plans
│   │   ├── weekly-pipeline.md         # /weekly-pipeline — bilingual weekly batch run
│   │   ├── view-content.md            # /view-content — launch dashboard
│   │   ├── deploy.md                  # /deploy — build and deploy static dashboard (includes admin panel)
│   │   ├── onboard-client.md          # /onboard-client — create new client config via Q&A
│   │   ├── onboard-from-intake.md     # /onboard-from-intake — generate config from intake JSON
│   │   ├── switch-client.md           # /switch-client — switch active client
│   │   └── setup-content-automation.md  # /setup-content-automation — initial setup
│   └── skills/
│       ├── content-generator/    # Twitter/Telegram copy generation (client-aware)
│       ├── image-generator/      # Branded image generation (client-aware)
│       ├── skill-creator/        # Create new Claude skills
│       └── mcp-integration/      # MCP server integration guidance
├── admin/
│   ├── index.html                # Password-protected admin panel UI
│   ├── admin.css                 # Dark theme styles
│   └── admin.js                  # GitHub API calls, auth, status polling
├── intake/
│   ├── index.html                # Client self-serve intake form (9 sections, contextual tips)
│   ├── intake.css                # Dark theme styles + tip box + progress bar
│   ├── intake.js                 # Form logic: tips, validation, EmailJS send, JSON download
│   ├── intake-config.example.js  # Template for EmailJS config (committed, safe to share)
│   └── intake-config.js          # EmailJS API keys + dashboard URL (gitignored — Rut fills once)
├── clients/
│   ├── intake/                   # Received intake JSONs (gitignored — may contain PII)
│   │   └── .gitkeep
│   ├── _template/                # Template for onboarding new clients
│   │   ├── config.json           # Placeholder config (copy and fill in)
│   │   ├── brand/README.md       # Brand asset instructions
│   │   ├── content-guidelines.md # Voice and messaging template
│   │   ├── keywords.md           # Keyword list template
│   │   ├── context.md            # Business context template
│   │   └── belief-journey.md     # 7-stage buyer belief journey template (Education bucket source)
│   └── bobe/                     # BoBe client (default)
│       ├── config.json           # Brand, keywords, tone, mascot, colors, style presets
│       ├── brand/                # Logo, banner examples, color references
│       ├── content-guidelines.md # Voice, tone, messaging pillars
│       ├── keywords.md           # Scraping/filtering keywords
│       ├── context.md            # Business context and ICP
│       └── belief-journey.md     # BoBe-specific 7-stage belief journey (auto-generated at onboarding)
├── context/
│   ├── BoBe Context.md           # Organization overview (legacy, mirrored in clients/bobe/)
│   └── RT BoBe Info.md           # User's role, responsibilities, working style
├── plans/                        # Implementation plans (dated markdown files)
├── reference/
│   ├── api-setup.md              # All API setup instructions (Apify, Google AI, WaveSpeed, Airtable)
│   ├── airtable-client-setup.md  # Step-by-step Airtable setup guide for clients (token, base, config)
│   ├── emailjs-setup.md          # EmailJS one-time setup for intake form credential emails
│   └── github-actions-setup.md   # GitHub Secrets, Pages, workflow permissions, PAT creation
├── outputs/
│   └── content/
│       └── {client_id}/          # Client-scoped output directory
│           ├── {date}-weekly-content.xlsx      # Weekly workbooks (15-col, bilingual, 3-bucket)
│           ├── {date}-bucket-inputs.json       # Announcement text input (written on dashboard submit)
│           ├── {date}-approvals.json           # Image approval state (local only)
│           └── images/
│               └── {date}-weekly/              # Weekly images (EN + RU, 42 total)
├── scripts/
│   ├── client_config.py          # Multi-client config loader (central module)
│   ├── apify_scraper.py          # Twitter + Reddit scraping via Apify API
│   ├── excel_manager.py          # Excel styling helpers (library only)
│   ├── nano_banana.py            # EN image generation via WaveSpeed GPT-Image-1.5
│   ├── wavespeed_img.py          # RU image generation via WaveSpeed Seedream 4.5
│   ├── weekly_pipeline.py        # Weekly pipeline orchestrator (15-col, bilingual, 3-bucket)
│   ├── bucket_generators.py      # 3-bucket topic generators (trending, education, announcements + 4 more)
│   ├── airtable_sync.py          # Push weekly content to client's Airtable base (opt-in)
│   ├── web_viewer.py             # Flask dashboard server (localhost:5001, EN/RU toggle, bucket tabs)
│   └── build_static.py           # Static site builder for deployment (EN/RU toggle, bucket tabs)
├── dist/                         # Static site build output (gitignored, deployed via /deploy)
└── venv/                         # Python virtual environment
```

---

## Commands

### /prime
Initialize a new session. Reads CLAUDE.md and context files, summarizes understanding, confirms readiness. **Run this at the start of every session.**

### /weekly-pipeline [week-of]
Fully automated bilingual weekly content pipeline for the active client. Assembles 21 topics across 3 buckets (7 Trending, 7 Education, 7 Announcements), generates all 42 content items in English AND Russian, generates 42 images (21 EN via GPT-Image-1.5 + 21 RU via Seedream 4.5), saves to weekly Excel workbook. Zero user input after triggering. Announcement topics are placeholders until the client submits input via the dashboard.

- Output: `outputs/content/{client_id}/{week-of}-weekly-content.xlsx` (15-column, bilingual, 3-bucket)
- Images: `outputs/content/{client_id}/images/{week-of}-weekly/` (EN + RU images)
- Example: `/weekly-pipeline` or `/weekly-pipeline 2026-02-16`

### /view-content [week-of]
Launch the Flask content dashboard at **http://localhost:5001**. Shows topic cards with bilingual banner images, Twitter threads, Telegram posts, hashtags. Supports EN/RU language toggle, copy-to-clipboard, image lightbox, date switching. Use `week:YYYY-MM-DD` format.

- Example: `/view-content week:2026-02-16`

### /deploy [date]
Build and deploy the static content dashboard to GitHub Pages. Renders the dashboard as static HTML files, copies images, and pushes to the `gh-pages` branch of `rtadik/bobe-content-dashboard`. Your client gets a URL to view all generated content. Zero hosting cost.

- Live URL: https://content.rejiglabs.com
- Requires one-time setup: enable GitHub Pages on the repo (Settings → Pages → branch: gh-pages). The `/deploy` command walks through this.
- Example: `/deploy` or `/deploy 2026-02-18`

### /create-plan [request]
Create a detailed implementation plan before making structural changes. Produces a dated markdown file in `plans/`. Once the plan is fully implemented, move it to `plans/implemented/`.

- Example: `/create-plan add a competitor analysis command`

### /implement [plan-path]
Execute a plan created by /create-plan, step by step. After successful implementation, move the plan file to `plans/implemented/`.

- Example: `/implement plans/2026-02-24-scalability-saas-plan.md`

### /onboard-client [client-name]
Create a new client configuration from the template. Conducts a full 18-question Q&A, then auto-drafts all four client files (`config.json`, `content-guidelines.md`, `context.md`, `keywords.md`) in one pass — no manual file editing required. Includes Airtable delivery setup as an optional final step.

- Example: `/onboard-client acmecrypto`

### /onboard-from-intake [path]
Read a completed client intake JSON (downloaded from the intake form) and generate all four config files + write credentials in one pass. No Q&A required. After running, execute `/deploy` to publish updated credentials.

- Example: `/onboard-from-intake clients/intake/acmecrypto-intake.json`

### /switch-client [client-id]
Switch the active client for all pipeline commands. Shows available clients and current selection.

- Example: `/switch-client bobe`

### /setup-content-automation
One-time setup command. Implements the full content automation infrastructure from the initial plan.

---

## Multi-Client Architecture

This workspace supports multiple clients via a config-driven architecture:

- **Client configs** live in `clients/{client_id}/` with `config.json`, `brand/`, `content-guidelines.md`, `keywords.md`, `context.md`, `belief-journey.md`
- **Active client** is stored in `.active-client` (gitignored). Default: `bobe`
- **All scripts** accept `--client {id}` to override the active client
- **`scripts/client_config.py`** is the central module that all scripts import for client-specific values
- **Outputs** are namespaced under `outputs/content/{client_id}/`
- **Onboarding**: Use `/onboard-client` to create a new client from `clients/_template/` (full Q&A + auto-draft)
- **Switching**: Use `/switch-client` to change the active client
- **Airtable delivery**: Opt-in per client — set `airtable.enabled: true` and `airtable.base_id` in `config.json`, add `AIRTABLE_API_KEY` to `.env`. See `reference/airtable-client-setup.md` for full setup guide.

---

## Scripts

| Script | Purpose | Key flags |
|--------|---------|-----------|
| `client_config.py` | Multi-client config loader (central module) | Import only: `load_config()`, `get_output_dir()`, `get_keywords()`, `get_content_types()`, `get_bucket_size()`, `get_belief_journey_path()`, `is_airtable_enabled()` |
| `apify_scraper.py` | Scrape Twitter/Reddit via Apify for trending topics | `--platform`, `--keywords`, `--count`, `--days`, `--top`, `--output`, `--mock`, `--client` |
| `excel_manager.py` | Excel styling library (no CLI) | Import only: `style_header_cell`, `style_data_cell`, color constants |
| `nano_banana.py` | Generate EN branded images via WaveSpeed GPT-Image-1.5; uploads to R2 if configured | `--prompt`, `--output`, `--style`, `--mock`, `--no-reference`, `--no-r2`, `--client` |
| `wavespeed_img.py` | Generate RU branded images via WaveSpeed Seedream 4.5; uploads to R2 if configured | `--prompt`, `--topic`, `--headline`, `--style`, `--output`, `--mock`, `--no-r2`, `--client` |
| `weekly_pipeline.py` | Weekly pipeline orchestrator (15-col bilingual workbook, 3-bucket) | `--action` (scrape, create-workbook, save-content, finalize, sync-airtable), `--week-of`, `--mock`, `--client` |
| `bucket_generators.py` | 3-bucket topic generators dispatched by type | Import only: `generate_bucket(type, config, week_of, ...)`, `BUCKET_DISPLAY_NAMES` |
| `pipeline_runner.py` | Standalone end-to-end pipeline (Gemini-powered); writes directly to Airtable + R2; Excel is opt-in | `--client`, `--week-of`, `--mock`, `--skip-images`, `--skip-airtable`, `--skip-deploy`, `--export-excel`, `--mode {full,announcement}`, `--announcement-text`, `--regen-topic INT`, `--regen-type {image_en,image_ru,content,content_ru}` |
| `airtable_sync.py` | Push weekly Excel content to client's Airtable base (batch; legacy — pipeline_runner writes inline) | `--week-of`, `--mock`, `--client` |
| `airtable_writer.py` | Inline Airtable write/update module used by pipeline_runner (18-field schema, per-item writes) | Import only: `get_or_create_table()`, `write_record()`, `update_image_urls()`, `load_records()`, `list_week_tables()`, `records_to_topics()` |
| `r2_uploader.py` | Cloudflare R2 image upload module (S3-compatible, boto3) | Import only: `upload_bytes()`, `upload_file()`, `make_key()`, `is_configured()`; CLI `--test` mode |
| `x_publisher.py` | Publish Twitter thread to X via OAuth 1.0a; updates Excel Status + Tweet_URL cols | `--client`, `--week-of`, `--topic-index`, `--mock` |
| `web_viewer.py` | Flask dashboard server with EN/RU toggle and bucket tabs | Runs on localhost:5001, `--client`; `/api/generate-announcement`, `/api/publish-to-x` endpoints |
| `build_static.py` | Static site builder with EN/RU toggle, bucket tabs, admin panel | `--output`, `--date`, `--include-admin`, `--client` |

---

## Weekly Pipeline Structure

- 21 topics per week = **3 buckets × 7 topics** (1 topic per bucket per day, interleaved)
  - **Bucket 1: Trending** — 7 scraped/relevant topics from X and Reddit
  - **Bucket 2: Education** — 7 belief-building topics from `clients/{client_id}/belief-journey.md`
  - **Bucket 3: Announcements** — client inputs ONE text update → Gemini generates 7 content angles
- Each topic gets Twitter + Telegram in English AND Russian = **42 content items**
- **Primary storage**: Airtable (18-field schema: Date, Bucket, Day, Topic, Platform, Format, Content, Image_Prompt, Image_URL_EN, Hashtags, Content_RU, Image_Prompt_RU, Image_URL_RU, Hashtags_RU, Status, Tweet_URL, Week, Client). Written inline per item during Phase 4.
- **Image storage**: Cloudflare R2 (S3-compatible). R2 URLs stored in `Image_URL_EN`/`Image_URL_RU` Airtable fields.
- **Excel workbook** (opt-in via `--export-excel`): 16 columns (Date, Bucket, Day, Topic, Platform, Format, Content, Image Prompt, Image Path, Hashtags, Content_RU, Image_Prompt_RU, Image_Path_RU, Hashtags_RU, Status, Tweet_URL). Tweet_URL col (P) written by `x_publisher.py`; backward-compatible.
- Interleaved day order: Mon = [Trending#1, Education#1, Announcement#1], Tue = [Trending#2, Education#2, Announcement#2], etc.
- Per day: topics 1-2 (positions 1 and 2 in the day) get Twitter thread format (5 tweets); topic 3 gets single tweet format
- Image styles: Pain Point → minimal, Education → tech, Announcement → notification
- Images: 42 total — 21 EN via GPT-Image-1.5 (`nano_banana.py`) + 21 RU via Seedream 4.5 (`wavespeed_img.py`)
- RU image naming: append `_ru` before `.png` (e.g., `topic_slug_twitter_ru.png`)
- **Announcement flow**: Dashboard Announcements tab shows a textarea. Client types update → submits → Flask `/api/generate-announcement` (local) or `generate-announcement.yml` (live) generates 7 angles and rebuilds workbook/site
- **Bucket config**: Each client's `config.json` has `content.content_types` (array of 3 type IDs) and `content.bucket_size` (default 7)
- **`belief-journey.md`**: Auto-generated at onboarding from intake data by reading ICP/pain points/product; maps 7 buyer belief stages from awareness to action readiness

---

## Skills

| Skill | Purpose |
|-------|---------|
| `content-generator` | Generate Twitter/Telegram copy from topics, using active client's tone and config |
| `image-generator` | Create branded images using WaveSpeed APIs + client's mascot/brand config |
| `skill-creator` | Create new Claude skills |
| `mcp-integration` | Integrate MCP servers into Claude workflows |

---

## API Requirements

| Service | Environment Variable | Purpose |
|---------|---------------------|---------|
| Apify | `APIFY_API_TOKEN` | Twitter + Reddit scraping |
| Google AI | `GOOGLE_AI_API_KEY` | Gemini text translation (RU content) |
| WaveSpeed | `WAVESPEED_API_KEY` | GPT-Image-1.5 (EN) + Seedream 4.5 (RU) image generation |
| Airtable | `AIRTABLE_API_KEY` | Primary content store — written inline per item (optional, per client) |
| Cloudflare R2 | `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_PUBLIC_URL` | Image cloud storage (S3-compatible, 10GB free, zero egress). See `reference/r2-setup.md` |
| X (Twitter) | `{CLIENT_ID_UPPER}_X_API_KEY`, `_X_API_SECRET`, `_X_ACCESS_TOKEN`, `_X_ACCESS_TOKEN_SECRET` | Direct publishing to X (optional, per client). See `reference/x-api-setup.md` |
| EmailJS | `intake/intake-config.js` | Credential email delivery from intake form (not an env var — stored in gitignored JS file) |

Store in `.env` (never commit). See `reference/api-setup.md` for setup.

**Python environment:** `venv/` with dependencies: `requests`, `openpyxl`, `google-genai`, `python-dotenv`, `flask`, `boto3`

---

## Deployment

The content dashboard can be deployed as a static site for client access:

- **Local viewing**: `/view-content` runs Flask on localhost:5001
- **Client access**: `/deploy` builds static HTML + admin panel and deploys to GitHub Pages (`gh-pages` branch of `rtadik/bobe-content-dashboard`)
- **Remote pipeline**: `pipeline_runner.py` runs the full pipeline autonomously via GitHub Actions (Gemini-powered); writes content to Airtable and images to Cloudflare R2

The deployed dashboard has a landing page, login form, and per-client auth. Clients log in with their credentials and see only their own content. The admin panel (`/admin/`) is write-capable via GitHub API.

**Hosting**: Cloudflare Pages (free tier — unlimited requests, 500 builds/month, no credit card required)
**Landing page**: https://content.rejiglabs.com/
**Login page**: https://content.rejiglabs.com/login.html
**BoBe dashboard**: https://content.rejiglabs.com/dashboard/bobe/
**Admin panel URL**: https://content.rejiglabs.com/admin/
**Fallback URL**: https://bobe-content-dashboard.pages.dev (no DNS needed)
**Cost**: $0/month
**Note**: Migrated from GitHub Pages on 2026-03-12 (GitHub Actions disabled on rtadik account). Deploy via `npx wrangler pages deploy dist --project-name bobe-content-dashboard`.

**Credentials**: Auto-generated from client IDs — no manual config or secrets required. Username: `admin`, password: `{client_id}123` (e.g. `bobe123`). New clients get credentials automatically on next deploy.

### GitHub Actions

Six workflows in `.github/workflows/`:
- **`weekly-pipeline.yml`**: Triggered via `workflow_dispatch` (admin panel or GitHub UI). Runs `pipeline_runner.py` (writes to Airtable + R2), builds static site with admin panel, deploys to `gh-pages`, uploads pipeline outputs as artifact.
- **`generate-announcement.yml`**: Triggered from the live dashboard's Announcements tab (or GitHub UI). Accepts `client_id`, `week_of`, `announcement_text`. Runs `pipeline_runner.py --mode announcement`, rebuilds and deploys static site.
- **`regenerate-item.yml`**: Triggered by the live dashboard's Regen buttons (via GitHub API from the client's browser, using a PAT). Regenerates a single topic item (image_en, image_ru, content, or content_ru), rebuilds and redeploys the static site. Inputs: `client_id`, `week_of`, `topic_index` (0-based), `regen_type`.
- **`publish-to-x.yml`**: Triggered by the live dashboard's "Publish to X" button (via GitHub API using a PAT). Runs `x_publisher.py`, commits updated xlsx (Status=Published, Tweet_URL col), rebuilds and redeploys static site. Inputs: `client_id`, `week_of`, `topic_index`. Requires `BOBE_X_*` GitHub Secrets.
- **`onboard-client.yml`**: Creates a new client directory from template inputs and commits it to the repo.
- **`auto-onboard.yml`**: Triggered by the Cloudflare Worker when a client submits the intake form. Parses the intake JSON, creates all client config files including `belief-journey.md` and `content_types`, commits to main, rebuilds and deploys the static site. Zero manual steps required.

**Live dashboard regeneration**: Clients on the deployed dashboard can regenerate images and content directly. On first use, they enter a GitHub PAT with `Actions: write` scope (stored in `sessionStorage` for the session). Approving an EN image auto-switches the view to Russian and unlocks the RU regen buttons. After triggering, the workflow runs (~2-5 min) and the page auto-reloads when complete.

Setup: See `reference/github-actions-setup.md` for GitHub Secrets, permissions, and PAT creation.

---

## Plans

Implemented plans are archived in `plans/implemented/`. Active (pending) plans live in `plans/`. When a plan is fully implemented, move it to `plans/implemented/`.

### Implemented (archived in `plans/implemented/`)

| Plan | Summary |
|------|---------|
| `2026-02-18-bobe-content-automation.md` | Core content automation infrastructure |
| `2026-02-18-vercel-static-deployment.md` | Deploy dashboard as static site to Cloudflare Pages/GitHub Pages for client access |
| Russian language support + remove daily pipeline | Bilingual EN/RU content generation, WaveSpeed Seedream 4.5 for RU images, EN/RU dashboard toggle, daily pipeline removed |
| `2026-02-19-multi-client-platform.md` | Multi-client architecture: config-driven client isolation, `/onboard-client`, `/switch-client`, all scripts refactored |
| `2026-02-23-multi-client-scalability.md` | Airtable content delivery, auto-drafted onboarding Q&A, config-driven platforms and image style mapping |
| `2026-02-23-github-actions-admin-panel.md` | Standalone `pipeline_runner.py`, GitHub Actions workflows, admin panel at `/admin/` |
| `2026-02-23-landing-login-client-dashboard.md` | Landing page (placeholder), login form with SHA-256 auth, per-client dashboard routing under `/dashboard/{client_id}/` |
| `2026-02-23-client-intake-form.md` | Self-serve client intake form at `/intake/`, EmailJS credential delivery, `/onboard-from-intake` command, `credentials.json` auto-write |
| `2026-02-24-regenerate-buttons-live-dashboard.md` | Regen buttons (content + images) on local Flask dashboard and live static site; EN approval auto-switches to RU and unlocks RU regen; GitHub Actions `regenerate-item.yml` as backend for live regen |
| `2026-02-24-auto-onboard-on-intake-submit.md` | Cloudflare Worker proxy triggers `auto-onboard.yml` on intake form submit; creates client dir, commits to main, rebuilds and deploys site automatically |
| `2026-02-26-three-bucket-content-strategy.md` | 3-bucket content strategy: Trending (7 scraped), Education (7 from belief-journey.md), Announcements (client input → 7 angles). 15-col workbook, bucket tabs on dashboard, intake content type selection, belief-journey.md auto-generated at onboarding |
| Direct X (Twitter) publishing | One-click publish from dashboard (local Flask + live static site via GitHub Actions). Per-client OAuth 1.0a credentials. Duplicate prevention. Excel Status + Tweet_URL cols (16). See `reference/x-api-setup.md` |
| `2026-03-05-cloudflare-r2-airtable-primary-store.md` | Cloudflare R2 for image storage + Airtable as primary content store. pipeline_runner writes inline per item. Excel demoted to opt-in (`--export-excel`). Dashboard and static build read from Airtable first, fall back to Excel. |
| `2026-02-24-scalability-saas-plan.md` | Per-client API key isolation (`get_api_key()` in client_config.py), deployment serialization (concurrency groups in workflows, split generate/deploy jobs), per-client login pages, Cloudflare Worker proxy for regen buttons. |
| Logo fix + client logo upload | Strengthened EN image prompts to enforce logo fidelity. Added `logo_url` field to intake form + auto-onboard workflow (downloads logo to brand/ on onboarding). `nano_banana.py` falls back to `logo_url` if local file missing. |

### Pending (active plans in `plans/`)

_No active plans._

---

## Session Workflow

1. **Start**: Run `/prime` to load context
2. **Work**: Use commands or direct Claude with tasks
3. **Plan changes**: Use `/create-plan` before significant additions
4. **Execute**: Use `/implement` to execute plans
5. **Maintain**: Claude updates CLAUDE.md as the workspace evolves

---

## Maintain This File

After any workspace change, Claude must check whether CLAUDE.md needs updating. If a new command, script, output type, or workflow is added, update the relevant section here. This file must always reflect the current state of the workspace.
