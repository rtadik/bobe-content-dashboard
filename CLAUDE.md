# CLAUDE.md

This file is the single source of truth for how Claude should understand and operate within this workspace. It is automatically loaded at the start of every session.

---

## Project Overview

**BoBe** is a Web3 fintech platform where retail crypto users deposit assets into AI-driven automated trading strategies (DCA, grid bots) that generate on-chain USDT yield. Target users are age 20-35, hold $500-$20k in crypto, and are exhausted from emotional trading losses.

**The user** (Rut Adk) is BoBe's Strategic Marketing Lead and Growth Architect, an external partner responsible for acquisition systems, messaging clarity, funnel infrastructure, and ambassador expansion.

**This workspace** is a multi-client content automation platform. It scrapes trending topics, generates Twitter threads and Telegram posts, creates branded images, and packages everything into Excel workbooks for scheduling. Originally built for BoBe, it now supports multiple clients via config-driven architecture.

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
│       ├── weekly-pipeline.yml   # GH Actions: workflow_dispatch → pipeline_runner.py → deploy
│       └── onboard-client.yml    # GH Actions: workflow_dispatch → create client dir → commit
├── .claude/
│   ├── commands/
│   │   ├── prime.md              # /prime — session initialization
│   │   ├── create-plan.md        # /create-plan — implementation planning
│   │   ├── implement.md          # /implement — execute plans
│   │   ├── weekly-pipeline.md    # /weekly-pipeline — bilingual weekly batch run
│   │   ├── view-content.md       # /view-content — launch dashboard
│   │   ├── deploy.md             # /deploy — build and deploy static dashboard (includes admin panel)
│   │   ├── onboard-client.md     # /onboard-client — create new client config
│   │   ├── switch-client.md      # /switch-client — switch active client
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
├── clients/
│   ├── _template/                # Template for onboarding new clients
│   │   ├── config.json           # Placeholder config (copy and fill in)
│   │   ├── brand/README.md       # Brand asset instructions
│   │   ├── content-guidelines.md # Voice and messaging template
│   │   ├── keywords.md           # Keyword list template
│   │   └── context.md            # Business context template
│   └── bobe/                     # BoBe client (default)
│       ├── config.json           # Brand, keywords, tone, mascot, colors, style presets
│       ├── brand/                # Logo, banner examples, color references
│       ├── content-guidelines.md # Voice, tone, messaging pillars
│       ├── keywords.md           # Scraping/filtering keywords
│       └── context.md            # Business context and ICP
├── context/
│   ├── BoBe Context.md           # Organization overview (legacy, mirrored in clients/bobe/)
│   └── RT BoBe Info.md           # User's role, responsibilities, working style
├── plans/                        # Implementation plans (dated markdown files)
├── reference/
│   ├── api-setup.md              # All API setup instructions (Apify, Google AI, WaveSpeed, Airtable)
│   ├── airtable-client-setup.md  # Step-by-step Airtable setup guide for clients (token, base, config)
│   └── github-actions-setup.md   # GitHub Secrets, Pages, workflow permissions, PAT creation
├── outputs/
│   └── content/
│       └── {client_id}/          # Client-scoped output directory
│           ├── {date}-weekly-content.xlsx   # Weekly workbooks (14-col, bilingual)
│           ├── {date}-approvals.json        # Image approval state (local only)
│           └── images/
│               └── {date}-weekly/           # Weekly images (EN + RU, 42 total)
├── scripts/
│   ├── client_config.py          # Multi-client config loader (central module)
│   ├── apify_scraper.py          # Twitter + Reddit scraping via Apify API
│   ├── excel_manager.py          # Excel styling helpers (library only)
│   ├── nano_banana.py            # EN image generation via WaveSpeed GPT-Image-1.5
│   ├── wavespeed_img.py          # RU image generation via WaveSpeed Seedream 4.5
│   ├── weekly_pipeline.py        # Weekly pipeline orchestrator (14-col, bilingual)
│   ├── airtable_sync.py          # Push weekly content to client's Airtable base (opt-in)
│   ├── web_viewer.py             # Flask dashboard server (localhost:5001, EN/RU toggle)
│   └── build_static.py           # Static site builder for deployment (EN/RU toggle)
├── dist/                         # Static site build output (gitignored, deployed via /deploy)
└── venv/                         # Python virtual environment
```

---

## Commands

### /prime
Initialize a new session. Reads CLAUDE.md and context files, summarizes understanding, confirms readiness. **Run this at the start of every session.**

### /weekly-pipeline [week-of]
Fully automated bilingual weekly content pipeline for the active client. Scrapes trending topics (falls back to evergreen), assigns 21 topics across 7 days (3/day: 2 Twitter threads + 1 Telegram), generates all 42 content items in English AND Russian, generates 42 images (21 EN via GPT-Image-1.5 + 21 RU via Seedream 4.5), saves to weekly Excel workbook. Zero user input after triggering.

- Output: `outputs/content/{client_id}/{week-of}-weekly-content.xlsx` (14-column, bilingual)
- Images: `outputs/content/{client_id}/images/{week-of}-weekly/` (EN + RU images)
- Example: `/weekly-pipeline` or `/weekly-pipeline 2026-02-16`

### /view-content [week-of]
Launch the Flask content dashboard at **http://localhost:5001**. Shows topic cards with bilingual banner images, Twitter threads, Telegram posts, hashtags. Supports EN/RU language toggle, copy-to-clipboard, image lightbox, date switching. Use `week:YYYY-MM-DD` format.

- Example: `/view-content week:2026-02-16`

### /deploy [date]
Build and deploy the static content dashboard to GitHub Pages. Renders the dashboard as static HTML files, copies images, and pushes to the `gh-pages` branch of `rtadik/bobe-content-dashboard`. Your client gets a URL to view all generated content. Zero hosting cost.

- Live URL: https://rtadik.github.io/bobe-content-dashboard
- Requires one-time setup: enable GitHub Pages on the repo (Settings → Pages → branch: gh-pages). The `/deploy` command walks through this.
- Example: `/deploy` or `/deploy 2026-02-18`

### /create-plan [request]
Create a detailed implementation plan before making structural changes. Produces a dated markdown file in `plans/`.

- Example: `/create-plan add a competitor analysis command`

### /implement [plan-path]
Execute a plan created by /create-plan, step by step.

- Example: `/implement plans/2026-02-18-vercel-static-deployment.md`

### /onboard-client [client-name]
Create a new client configuration from the template. Conducts a full 18-question Q&A, then auto-drafts all four client files (`config.json`, `content-guidelines.md`, `context.md`, `keywords.md`) in one pass — no manual file editing required. Includes Airtable delivery setup as an optional final step.

- Example: `/onboard-client acmecrypto`

### /switch-client [client-id]
Switch the active client for all pipeline commands. Shows available clients and current selection.

- Example: `/switch-client bobe`

### /setup-content-automation
One-time setup command. Implements the full content automation infrastructure from the initial plan.

---

## Multi-Client Architecture

This workspace supports multiple clients via a config-driven architecture:

- **Client configs** live in `clients/{client_id}/` with `config.json`, `brand/`, `content-guidelines.md`, `keywords.md`, `context.md`
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
| `client_config.py` | Multi-client config loader (central module) | Import only: `load_config()`, `get_output_dir()`, `get_keywords()`, `get_airtable_config()`, `is_airtable_enabled()` |
| `apify_scraper.py` | Scrape Twitter/Reddit via Apify for trending topics | `--platform`, `--keywords`, `--count`, `--days`, `--top`, `--output`, `--mock`, `--client` |
| `excel_manager.py` | Excel styling library (no CLI) | Import only: `style_header_cell`, `style_data_cell`, color constants |
| `nano_banana.py` | Generate EN branded images via WaveSpeed GPT-Image-1.5 | `--prompt`, `--output`, `--style`, `--mock`, `--no-reference`, `--client` |
| `wavespeed_img.py` | Generate RU branded images via WaveSpeed Seedream 4.5 | `--prompt`, `--topic`, `--headline`, `--style`, `--output`, `--mock`, `--client` |
| `weekly_pipeline.py` | Weekly pipeline orchestrator (14-col bilingual workbook) | `--action` (scrape, create-workbook, save-content, finalize, sync-airtable), `--week-of`, `--mock`, `--client` |
| `pipeline_runner.py` | Standalone end-to-end pipeline (Gemini-powered, no Claude required) | `--client`, `--week-of`, `--mock`, `--skip-images`, `--skip-airtable`, `--skip-deploy` |
| `airtable_sync.py` | Push weekly content to client's Airtable base | `--week-of`, `--mock`, `--client` |
| `web_viewer.py` | Flask dashboard server with EN/RU toggle | Runs on localhost:5001, `--client` |
| `build_static.py` | Static site builder with EN/RU toggle + admin panel | `--output`, `--date`, `--include-admin`, `--client` |

---

## Weekly Pipeline Structure

- 21 topics per week (3 per day x 7 days)
- Each topic gets Twitter + Telegram in English AND Russian = **42 content rows** in workbook
- Workbook Content sheet: **14 columns** (Date, Day, Topic, Platform, Format, Content, Image Prompt, Image Path, Hashtags, Content_RU, Image_Prompt_RU, Image_Path_RU, Hashtags_RU, Status)
- JSON temp files: `/tmp/weekly_content_1.json` through `/tmp/weekly_content_42.json`
- Odd items (1,3,5...) = Twitter; Even items (2,4,6...) = Telegram
- Per day: topics 1-2 get Twitter thread format (5 tweets); topic 3 gets single tweet format
- Image styles: Pain Point → minimal, Education → tech, Transparency/Product → notification
- Images: 42 total — 21 EN via GPT-Image-1.5 (`nano_banana.py`) + 21 RU via Seedream 4.5 (`wavespeed_img.py`)
- RU image naming: append `_ru` before `.png` (e.g., `topic_slug_twitter_ru.png`)

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
| Airtable | `AIRTABLE_API_KEY` | Content delivery to client Airtable bases (optional, per client) |

Store in `.env` (never commit). See `reference/api-setup.md` for setup.

**Python environment:** `venv/` with dependencies: `requests`, `openpyxl`, `google-genai`, `python-dotenv`, `flask`

---

## Deployment

The content dashboard can be deployed as a static site for client access:

- **Local viewing**: `/view-content` runs Flask on localhost:5001
- **Client access**: `/deploy` builds static HTML + admin panel and deploys to GitHub Pages (`gh-pages` branch of `rtadik/bobe-content-dashboard`)
- **Remote pipeline**: `pipeline_runner.py` runs the full pipeline autonomously via GitHub Actions (Gemini-powered)

The deployed dashboard is a read-only view of generated content. The admin panel (`/admin/`) is write-capable via GitHub API.

**Hosting**: GitHub Pages (free, 100 GB/month bandwidth, no credit card required)
**Dashboard URL**: https://rtadik.github.io/bobe-content-dashboard
**Admin panel URL**: https://rtadik.github.io/bobe-content-dashboard/admin/
**Cost**: $0/month

### GitHub Actions

Two workflows in `.github/workflows/`:
- **`weekly-pipeline.yml`**: Triggered via `workflow_dispatch` (admin panel or GitHub UI). Runs `pipeline_runner.py`, builds static site with admin panel, deploys to `gh-pages`, uploads Excel as artifact.
- **`onboard-client.yml`**: Creates a new client directory from template inputs and commits it to the repo.

Setup: See `reference/github-actions-setup.md` for GitHub Secrets, permissions, and PAT creation.

---

## Pending Plans

| Plan | Status | Summary |
|------|--------|---------|
| `plans/2026-02-18-bobe-content-automation.md` | Implemented | Core content automation infrastructure |
| `plans/2026-02-18-vercel-static-deployment.md` | Implemented | Deploy dashboard as static site to Cloudflare Pages/GitHub Pages for client access |
| Russian language support + remove daily pipeline | Implemented | Bilingual EN/RU content generation, WaveSpeed Seedream 4.5 for RU images, EN/RU dashboard toggle, daily pipeline removed |
| `plans/2026-02-19-multi-client-platform.md` | Implemented | Multi-client architecture: config-driven client isolation, `/onboard-client`, `/switch-client`, all scripts refactored |
| `plans/2026-02-23-multi-client-scalability.md` | Implemented | Airtable content delivery, auto-drafted onboarding Q&A, config-driven platforms and image style mapping |
| `plans/2026-02-23-github-actions-admin-panel.md` | Implemented | Standalone `pipeline_runner.py`, GitHub Actions workflows, admin panel at `/admin/` |

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
