# CLAUDE.md

This file is the single source of truth for how Claude should understand and operate within this workspace. It is automatically loaded at the start of every session.

---

## Project Overview

**BoBe** is a Web3 fintech platform where retail crypto users deposit assets into AI-driven automated trading strategies (DCA, grid bots) that generate on-chain USDT yield. Target users are age 20-35, hold $500-$20k in crypto, and are exhausted from emotional trading losses.

**The user** (Rut Adk) is BoBe's Strategic Marketing Lead and Growth Architect, an external partner responsible for acquisition systems, messaging clarity, funnel infrastructure, and ambassador expansion.

**This workspace** automates BoBe's social media content creation: scraping trending crypto/DeFi topics, generating Twitter threads and Telegram posts, creating branded images, and packaging everything into Excel workbooks for scheduling.

---

## Content Rules

- **NEVER use em-dashes** (`—` U+2014), en-dashes (`–` U+2013), or double-hyphens (`--`) as punctuation in generated content. Replace with commas, colons, or rephrase. The `---` tweet separator is the only exception (structural, not punctuation).
- BoBe tone: transparent, educational, no hype, no guaranteed return claims.
- See `reference/content-guidelines.md` for full voice, messaging pillars, and platform-specific formatting rules.

---

## Workspace Structure

```
.
├── CLAUDE.md                 # This file
├── .env                      # API keys (gitignored)
├── .gitignore
├── .claude/
│   ├── commands/
│   │   ├── prime.md              # /prime — session initialization
│   │   ├── create-plan.md        # /create-plan — implementation planning
│   │   ├── implement.md          # /implement — execute plans
│   │   ├── content-pipeline.md   # /content-pipeline — daily content run
│   │   ├── weekly-pipeline.md    # /weekly-pipeline — weekly batch run
│   │   ├── view-content.md       # /view-content — launch dashboard
│   │   ├── deploy.md              # /deploy — build and deploy static dashboard
│   │   └── setup-content-automation.md  # /setup-content-automation — initial setup
│   └── skills/
│       ├── content-generator/    # Twitter/Telegram copy generation
│       ├── image-generator/      # Branded image generation via Gemini
│       ├── skill-creator/        # Create new Claude skills
│       └── mcp-integration/      # MCP server integration guidance
├── context/
│   ├── BoBe Context.md           # Organization overview, products, ICP, positioning
│   └── RT BoBe Info.md           # User's role, responsibilities, working style
├── plans/                        # Implementation plans (dated markdown files)
├── outputs/
│   └── content/
│       ├── {date}-content.xlsx          # Daily workbooks
│       ├── {date}-weekly-content.xlsx   # Weekly workbooks (21 topics, 42 content rows)
│       ├── {date}-approvals.json        # Image approval state (local only)
│       └── images/
│           ├── {date}-daily/            # Daily pipeline images
│           └── {date}-weekly/           # Weekly pipeline images
├── reference/
│   ├── content-guidelines.md     # BoBe voice, tone, messaging pillars, formatting
│   ├── bobe-keywords.md          # Keyword lists for topic scraping/filtering
│   ├── api-setup.md              # Apify + Google AI setup instructions
│   └── bobe-brand/               # Brand assets (logo, banners, color references)
├── scripts/
│   ├── apify_scraper.py          # Twitter + Reddit scraping via Apify API
│   ├── excel_manager.py          # Excel workbook creation and row management
│   ├── nano_banana.py            # Image generation via Google Gemini API
│   ├── weekly_pipeline.py        # Weekly pipeline orchestrator (workbook + content saving)
│   ├── web_viewer.py             # Flask dashboard server (localhost:5001)
│   └── build_static.py           # Static site builder for deployment
├── dist/                         # Static site build output (gitignored, deployed via /deploy)
└── venv/                         # Python virtual environment
```

---

## Commands

### /prime
Initialize a new session. Reads CLAUDE.md and context files, summarizes understanding, confirms readiness. **Run this at the start of every session.**

### /weekly-pipeline [week-of]
Fully automated weekly content pipeline. Scrapes trending topics (falls back to evergreen bank), assigns 21 topics across 7 days (3/day: 2 Twitter threads + 1 Telegram), generates all 42 content items and branded images, saves to weekly Excel workbook. Zero user input after triggering. Sends macOS notification on completion.

- Output: `outputs/content/{week-of}-weekly-content.xlsx`
- Images: `outputs/content/images/{week-of}-weekly/`
- Example: `/weekly-pipeline` or `/weekly-pipeline 2026-02-16`

### /content-pipeline [date]
Daily content pipeline. Scrapes Twitter + Reddit, presents top topics for user selection (2-3 picks), generates content and images for each, saves to daily Excel workbook.

- Output: `outputs/content/{date}-content.xlsx`
- Example: `/content-pipeline 2026-02-18`

### /view-content [date]
Launch the Flask content dashboard at **http://localhost:5001**. Shows topic cards with banner images, Twitter threads, Telegram posts, hashtags. Supports copy-to-clipboard, image lightbox, date switching. For weekly content, use `week:YYYY-MM-DD` format.

- Example: `/view-content 2026-02-18` or `/view-content week:2026-02-16`

### /deploy [date]
Build and deploy the static content dashboard for client access. Renders the dashboard as static HTML files, copies images, and deploys to Cloudflare Pages (or GitHub Pages). Your client gets a URL to view all generated content. Zero hosting cost.

- Requires one-time setup: Cloudflare account or GitHub Pages enabled. The `/deploy` command walks through first-time setup.
- Example: `/deploy` or `/deploy 2026-02-18`

### /create-plan [request]
Create a detailed implementation plan before making structural changes. Produces a dated markdown file in `plans/`.

- Example: `/create-plan add a competitor analysis command`

### /implement [plan-path]
Execute a plan created by /create-plan, step by step.

- Example: `/implement plans/2026-02-18-vercel-static-deployment.md`

### /setup-content-automation
One-time setup command. Implements the full content automation infrastructure from the initial plan.

---

## Scripts

| Script | Purpose | Key flags |
|--------|---------|-----------|
| `apify_scraper.py` | Scrape Twitter/Reddit via Apify for trending topics | `--platform`, `--keywords`, `--count`, `--days`, `--top`, `--output`, `--mock` |
| `excel_manager.py` | Create/manage Excel workbooks | `--action` (create, add-topics, add-content), `--date`, `--file` |
| `nano_banana.py` | Generate branded images via Gemini API | `--prompt`, `--output`, `--style` (minimal, tech, notification), `--mock` |
| `weekly_pipeline.py` | Weekly pipeline orchestrator | `--action` (create-workbook, save-content, finalize, scrape), `--week-of`, `--mock` |
| `web_viewer.py` | Flask dashboard server | Runs on localhost:5001, auto-detects daily vs weekly workbooks |
| `build_static.py` | Static site builder for deployment | `--output`, `--date` (repeatable) |

---

## Weekly Pipeline Structure

- 21 topics per week (3 per day x 7 days)
- Each topic gets both Twitter and Telegram versions = **42 content rows** in workbook
- JSON temp files: `/tmp/weekly_content_1.json` through `/tmp/weekly_content_42.json`
- Odd items (1,3,5...) = Twitter; Even items (2,4,6...) = Telegram
- Per day: topics 1-2 get Twitter thread format (5 tweets); topic 3 gets single tweet format
- Image styles: Pain Point → minimal, Education → tech, Transparency/Product → notification

---

## Skills

| Skill | Purpose |
|-------|---------|
| `content-generator` | Generate Twitter/Telegram copy from crypto topics, aligned with BoBe's tone |
| `image-generator` | Create branded images using Gemini API + BoBe mascot style |
| `skill-creator` | Create new Claude skills |
| `mcp-integration` | Integrate MCP servers into Claude workflows |

---

## API Requirements

| Service | Environment Variable | Purpose |
|---------|---------------------|---------|
| Apify | `APIFY_API_TOKEN` | Twitter + Reddit scraping |
| Google AI | `GOOGLE_AI_API_KEY` | Gemini image generation |

Store in `.env` (never commit). See `reference/api-setup.md` for setup.

**Python environment:** `venv/` with dependencies: `requests`, `openpyxl`, `google-genai`, `python-dotenv`, `flask`

---

## Deployment

The content dashboard can be deployed as a static site for client access:

- **Local viewing**: `/view-content` runs Flask on localhost:5001
- **Client access**: `/deploy` builds static HTML and deploys to Cloudflare Pages

The deployed dashboard is a read-only view of generated content. Content generation, image regeneration, and approval workflows remain local-only.

**Hosting**: Cloudflare Pages (free, unlimited bandwidth, no credit card required)
**Cost**: $0/month

---

## Pending Plans

| Plan | Status | Summary |
|------|--------|---------|
| `plans/2026-02-18-bobe-content-automation.md` | Implemented | Core content automation infrastructure |
| `plans/2026-02-18-vercel-static-deployment.md` | Implemented | Deploy dashboard as static site to Cloudflare Pages/GitHub Pages for client access |

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
