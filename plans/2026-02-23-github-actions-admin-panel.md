# Plan: GitHub Actions Admin Panel for Remote Pipeline Control

**Created:** 2026-02-23
**Status:** Draft
**Request:** Web-based admin panel on GitHub Pages with GitHub Actions backend — trigger weekly pipeline runs and onboard new clients from the live URL, with API keys stored as GitHub Secrets

---

## Overview

### What This Plan Accomplishes

Adds a password-protected admin panel at `https://rtadik.github.io/bobe-content-dashboard/admin/` that lets any authorized user trigger the full weekly content pipeline or onboard a new client from a browser — no Claude Code, no local machine required. GitHub Actions runs the pipeline on its servers, outputs are deployed automatically, and the admin panel shows live run status.

### Why This Matters

Currently all pipeline operations require running Claude Code locally, which ties the workflow to one machine and one person. A web-accessible admin panel means the pipeline can be triggered from anywhere — phone, tablet, or another team member's browser. It is the first step toward fully delegating pipeline execution to stakeholders other than the original developer.

---

## Current State

### Relevant Existing Structure

```
.github/                          ← does NOT exist yet
scripts/
  apify_scraper.py                ← CLI, runs standalone
  weekly_pipeline.py              ← CLI, workbook create/save/finalize
  nano_banana.py                  ← CLI, EN image generation
  wavespeed_img.py                ← CLI, RU image generation
  airtable_sync.py                ← CLI, Airtable push
  build_static.py                 ← CLI, static site builder
  client_config.py                ← config loader module
admin/                            ← does NOT exist yet
.claude/commands/weekly-pipeline.md  ← Claude-driven pipeline (interactive)
clients/bobe/config.json          ← airtable.enabled = true
.gitignore                        ← outputs/, dist/, .env all gitignored
```

**Git remote:** `origin → https://github.com/rtadik/bobe-content-dashboard.git`
**Active branch:** `Fork-#1` (working branch), `main`
**Deployed:** `gh-pages` branch → `https://rtadik.github.io/bobe-content-dashboard`

### Gaps or Problems Being Addressed

1. **No automated pipeline script** — content generation (Twitter/Telegram text) is currently done by Claude interactively. There is no standalone Python script that generates content text without Claude Code.
2. **No GitHub Actions workflows** — `.github/` directory does not exist.
3. **No admin panel** — no browser-accessible UI for triggering operations.
4. **Outputs are gitignored** — GH Actions runner must generate everything from scratch each run; it cannot read previously generated Excel files.

---

## Proposed Changes

### Summary of Changes

- Build `scripts/pipeline_runner.py`: a standalone end-to-end Python script that replaces Claude's interactive role in the pipeline by using the Gemini API to generate content (topics, Twitter threads, Telegram posts, RU translations). This is the core enabler — without it, GitHub Actions cannot run the full pipeline autonomously.
- Add `.github/workflows/weekly-pipeline.yml`: GitHub Actions workflow triggered via `workflow_dispatch` that runs `pipeline_runner.py`, deploys the static site, and syncs Airtable.
- Add `.github/workflows/onboard-client.yml`: GitHub Actions workflow that creates a new client directory from template inputs and commits it to the repo.
- Add `admin/index.html`: static HTML admin panel with GitHub PAT auth, pipeline trigger form, onboarding form, and live run status polling.
- Modify `scripts/build_static.py`: add `--include-admin` flag to copy `admin/index.html` → `dist/admin/index.html` during build (so the admin panel is deployed as part of the dashboard).
- Update `.claude/commands/deploy.md`: include admin panel copy step.
- Update `CLAUDE.md`: document new script, workflows, and admin panel.

### New Files to Create

| File Path | Purpose |
| --- | --- |
| `scripts/pipeline_runner.py` | End-to-end pipeline script: scrape → generate content via Gemini → images via WaveSpeed → Excel → Airtable → deploy |
| `.github/workflows/weekly-pipeline.yml` | GH Actions workflow: `workflow_dispatch` → run pipeline_runner.py → deploy to gh-pages |
| `.github/workflows/onboard-client.yml` | GH Actions workflow: `workflow_dispatch` → create client dir → commit to repo |
| `admin/index.html` | Static admin panel: auth, pipeline trigger, onboard form, run status |
| `admin/admin.css` | Styles for admin panel (dark theme, BoBe-aligned) |
| `admin/admin.js` | Admin panel logic: GitHub API calls, form handling, status polling |

### Files to Modify

| File Path | Changes |
| --- | --- |
| `scripts/build_static.py` | Add `--include-admin` flag; when set, copy `admin/` dir to `dist/admin/` |
| `.claude/commands/deploy.md` | Add admin copy step before pushing to gh-pages |
| `CLAUDE.md` | Document `pipeline_runner.py`, workflows, admin panel URL |
| `reference/api-setup.md` | Add GitHub Secrets setup section |

### Files to Delete

None.

---

## Design Decisions

### Key Decisions Made

1. **Gemini API for content generation (not Claude API)**: The workflow already uses `GOOGLE_AI_API_KEY` for RU translation. Reusing Gemini Flash for content generation avoids adding a new API key secret and keeps the cost low. Content quality from Gemini Flash is good enough for drafts that the user reviews before publishing. The Claude-driven pipeline (local) remains the gold standard for when quality matters most.

2. **GitHub PAT authentication in admin panel**: The admin panel stores the user's GitHub PAT in `sessionStorage` only (cleared on tab/browser close, never persisted to localStorage or sent to any server other than api.github.com). This avoids needing a backend auth service. The PAT needs `actions:write` scope to trigger workflows. The admin panel URL is public but without a valid PAT, no actions can be triggered.

3. **Single `pipeline_runner.py` script (not multi-step)**: Instead of chaining the existing scripts via shell in the workflow, one orchestrator script handles the full pipeline: it reads client config, calls Apify, generates content with Gemini, calls WaveSpeed for images, saves the Excel workbook, syncs Airtable, and builds the static site. This is easier to debug, log, and maintain.

4. **Outputs committed to repo during GH Actions run**: Since outputs are gitignored locally (to avoid bloating the repo with binary files), during a GH Actions run we commit only the Excel workbook and images to the `outputs/` path and then build + deploy the static site. Alternatively, the GH Actions build only creates `dist/` and pushes it to `gh-pages` without committing outputs to main — this keeps the repo clean. **Decision: GH Actions builds ephemeral outputs, builds dist/, pushes dist/ to gh-pages, and uploads the Excel workbook as a GitHub Actions artifact (downloadable from the Actions run page).**

5. **Admin panel is a static HTML file in the repo**: It lives in `admin/` on the main branch and gets copied to `dist/admin/` during each deploy. This means the admin panel is updated whenever the dashboard is redeployed.

6. **Onboarding workflow is config-only**: The GH Actions onboarding creates `clients/{id}/config.json` from form inputs and copies the template for the other files. It does NOT AI-draft `content-guidelines.md`, `keywords.md`, or `context.md` — that still requires running `/onboard-client` locally via Claude Code. The admin panel makes this clear with an instruction after onboarding: "Client folder created. Run `/onboard-client {id}` in Claude Code to draft content guidelines."

### Alternatives Considered

- **Separate backend (Vercel Functions, Railway)**: Would eliminate the GitHub PAT requirement but adds hosting complexity and cost. Rejected — GitHub Actions is free and already integrated with the repo.
- **Direct API call to Anthropic in GH Actions**: Could use Claude to generate content (better quality). Adds `ANTHROPIC_API_KEY` as a new secret; same cost profile as Gemini. Deferred — Gemini is simpler since it is already required; can upgrade to Claude API later by swapping the content generation module.
- **Committing outputs to main branch**: Would make outputs persistent in the repo. Rejected — Excel workbooks + 42 images per week would bloat the repo rapidly. Artifact upload (option chosen) keeps the repo clean.

### Open Questions

None — design is clear enough to implement.

---

## Step-by-Step Tasks

### Step 1: Create `scripts/pipeline_runner.py`

This is the most important file — it makes the pipeline autonomous. It mirrors the logic of `.claude/commands/weekly-pipeline.md` but runs as a single Python script using Gemini API for content generation.

**Actions:**

- Create `scripts/pipeline_runner.py` with the following structure:
  ```
  main()
    → parse args: --client, --week-of, --mock, --skip-images, --skip-airtable
    → load client config
    → calculate week_of (default: Monday of current week)
    → Phase 1: scrape topics via apify_scraper.py (subprocess)
    → Phase 2: assemble 21-topic pool (Gemini: rank + fill evergreen)
    → Phase 3: create workbook (weekly_pipeline.py --action create-workbook)
    → Phase 4: generate 42 content items (Gemini: EN content + RU translation)
             → save each item (weekly_pipeline.py --action save-content)
    → Phase 5: generate 42 images (nano_banana.py + wavespeed_img.py subprocess)
    → Phase 6: finalize workbook (weekly_pipeline.py --action finalize)
    → Phase 6.5: Airtable sync (airtable_sync.py subprocess, if enabled)
    → Phase 7: build static site (build_static.py subprocess)
    → Phase 8: deploy to gh-pages (git force push)
    → Print summary
  ```

- **Gemini content generation** (replaces Claude's interactive role):
  - Use `google-genai` SDK (already installed in venv)
  - Model: `gemini-2.0-flash` (fast, low cost, supports long context)
  - Phase 2 prompt: given client config + scraped topics, return JSON list of 21 topic objects with `{topic, angle, source, day, date}`
  - Phase 4 prompt per topic: given client config + topic, return JSON with `{content, image_prompt, hashtags, content_ru, image_prompt_ru, hashtags_ru}`
  - Parse JSON from Gemini response; fall back to evergreen stubs if parse fails
  - Enforce content rules in prompt: no em-dashes, char limits per platform

- **Logging**: print progress with phase headers and item counts (same format as `/weekly-pipeline` command output)

- **CLI flags**:
  - `--client {id}` — client to run for (default: reads `.active-client` or `bobe`)
  - `--week-of YYYY-MM-DD` — week start date (default: Monday of current week)
  - `--mock` — dry run, no API calls
  - `--skip-images` — skip image generation (useful for content-only runs)
  - `--skip-airtable` — skip Airtable sync
  - `--skip-deploy` — skip static site build and deployment

**Files affected:**

- `scripts/pipeline_runner.py` (new)

---

### Step 2: Create `.github/workflows/weekly-pipeline.yml`

**Actions:**

- Create `.github/` and `.github/workflows/` directories
- Create `.github/workflows/weekly-pipeline.yml`:

```yaml
name: Weekly Content Pipeline

on:
  workflow_dispatch:
    inputs:
      client_id:
        description: 'Client ID (e.g. bobe)'
        required: true
        default: 'bobe'
      week_of:
        description: 'Week start date YYYY-MM-DD (optional, defaults to current Monday)'
        required: false
        default: ''
      skip_images:
        description: 'Skip image generation'
        type: boolean
        default: false
      skip_airtable:
        description: 'Skip Airtable sync'
        type: boolean
        default: false

jobs:
  run-pipeline:
    runs-on: ubuntu-latest
    timeout-minutes: 120

    steps:
      - name: Checkout main branch
        uses: actions/checkout@v4
        with:
          ref: Fork-#1   # working branch; change to main when merged
          token: ${{ secrets.GITHUB_TOKEN }}
          fetch-depth: 0  # needed for gh-pages push

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install requests openpyxl google-genai python-dotenv jinja2 flask pillow

      - name: Create .env from secrets
        run: |
          echo "APIFY_API_TOKEN=${{ secrets.APIFY_API_TOKEN }}" >> .env
          echo "GOOGLE_AI_API_KEY=${{ secrets.GOOGLE_AI_API_KEY }}" >> .env
          echo "WAVESPEED_API_KEY=${{ secrets.WAVESPEED_API_KEY }}" >> .env
          echo "AIRTABLE_API_KEY=${{ secrets.AIRTABLE_API_KEY }}" >> .env

      - name: Set active client
        run: echo "${{ github.event.inputs.client_id }}" > .active-client

      - name: Run pipeline
        run: |
          ARGS="--client ${{ github.event.inputs.client_id }}"
          if [ -n "${{ github.event.inputs.week_of }}" ]; then
            ARGS="$ARGS --week-of ${{ github.event.inputs.week_of }}"
          fi
          if [ "${{ github.event.inputs.skip_images }}" = "true" ]; then
            ARGS="$ARGS --skip-images"
          fi
          if [ "${{ github.event.inputs.skip_airtable }}" = "true" ]; then
            ARGS="$ARGS --skip-airtable"
          fi
          python scripts/pipeline_runner.py $ARGS --skip-deploy

      - name: Build static site
        run: python scripts/build_static.py --output dist --client ${{ github.event.inputs.client_id }}

      - name: Copy admin panel to dist
        run: |
          mkdir -p dist/admin
          cp admin/index.html dist/admin/index.html
          cp admin/admin.css dist/admin/admin.css
          cp admin/admin.js dist/admin/admin.js

      - name: Deploy to GitHub Pages (gh-pages branch)
        run: |
          cd dist
          git init
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add -A
          git commit -m "Deploy content dashboard $(date +%Y-%m-%d)"
          git push -f https://x-access-token:${{ secrets.GITHUB_TOKEN }}@github.com/rtadik/bobe-content-dashboard.git HEAD:gh-pages
          cd ..

      - name: Upload Excel workbook as artifact
        uses: actions/upload-artifact@v4
        with:
          name: weekly-content-${{ github.event.inputs.client_id }}-${{ github.run_id }}
          path: outputs/content/${{ github.event.inputs.client_id }}/*.xlsx
          retention-days: 30
```

**Files affected:**

- `.github/workflows/weekly-pipeline.yml` (new)

---

### Step 3: Create `.github/workflows/onboard-client.yml`

**Actions:**

- Create `.github/workflows/onboard-client.yml`:

```yaml
name: Onboard New Client

on:
  workflow_dispatch:
    inputs:
      client_id:
        description: 'Client ID (lowercase, no spaces, e.g. acmecorp)'
        required: true
      display_name:
        description: 'Brand display name (e.g. Acme Corp)'
        required: true
      tagline:
        description: 'One-line brand tagline'
        required: true
      website:
        description: 'Website URL (e.g. acmecorp.com)'
        required: true
      primary_color:
        description: 'Primary brand color hex (e.g. #1a1a2e)'
        required: false
        default: '#1a1a2e'
      accent_color:
        description: 'Accent color hex (e.g. #00aaff)'
        required: false
        default: '#00aaff'
      industry:
        description: 'Industry / niche (e.g. DeFi, SaaS, ecommerce)'
        required: true
      platforms:
        description: 'Platforms (comma-separated: twitter,telegram)'
        required: false
        default: 'twitter,telegram'
      airtable_base_id:
        description: 'Airtable Base ID (optional, e.g. appXXXXXXXXXX)'
        required: false
        default: ''

jobs:
  onboard:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          ref: Fork-#1
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Create client directory from template
        run: |
          CLIENT_ID="${{ github.event.inputs.client_id }}"
          CLIENT_DIR="clients/${CLIENT_ID}"

          if [ -d "$CLIENT_DIR" ]; then
            echo "ERROR: Client '${CLIENT_ID}' already exists."
            exit 1
          fi

          # Copy template
          cp -r clients/_template "${CLIENT_DIR}"

          # Fill config.json with provided values
          python3 - <<'PYEOF'
          import json, os, sys

          client_id = os.environ.get("CLIENT_ID", "${{ github.event.inputs.client_id }}")
          display_name = "${{ github.event.inputs.display_name }}"
          tagline = "${{ github.event.inputs.tagline }}"
          website = "${{ github.event.inputs.website }}"
          primary_color = "${{ github.event.inputs.primary_color }}"
          accent_color = "${{ github.event.inputs.accent_color }}"
          industry = "${{ github.event.inputs.industry }}"
          platforms_str = "${{ github.event.inputs.platforms }}"
          platforms = [p.strip() for p in platforms_str.split(",") if p.strip()]
          airtable_base_id = "${{ github.event.inputs.airtable_base_id }}"

          config_path = f"clients/{client_id}/config.json"
          with open(config_path) as f:
              config = json.load(f)

          config["client_id"] = client_id
          config["display_name"] = display_name
          config["tagline"] = tagline
          config["website"] = website
          config["brand"]["primary_color"] = primary_color
          config["brand"]["accent_color"] = accent_color
          config["content"]["platforms"] = platforms

          if airtable_base_id:
              config["airtable"]["enabled"] = True
              config["airtable"]["base_id"] = airtable_base_id

          with open(config_path, "w") as f:
              json.dump(config, f, indent=2)

          print(f"Config written for {client_id}")
          PYEOF
        env:
          CLIENT_ID: ${{ github.event.inputs.client_id }}

      - name: Commit new client directory
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add clients/${{ github.event.inputs.client_id }}/
          git commit -m "Onboard client: ${{ github.event.inputs.client_id }} (${{ github.event.inputs.display_name }})"
          git push origin Fork-#1
```

**Files affected:**

- `.github/workflows/onboard-client.yml` (new)

---

### Step 4: Create `admin/index.html`

The admin panel is a clean dark-themed single-page HTML app with three sections:
1. **Connect** — GitHub PAT input (stored in sessionStorage only)
2. **Weekly Pipeline** — trigger form with client_id, week_of, options
3. **Onboard Client** — form with all onboarding fields
4. **Run Status** — shows last 5 workflow runs for each workflow with status + log link

**Actions:**

- Create `admin/index.html` with:
  - Meta charset, viewport, links to `admin.css` and `admin.js`
  - Header: "Content Pipeline Admin" with BoBe branding
  - **Auth section**: GitHub PAT input + "Connect" button. On connect: call `GET /user` to validate PAT; show username if valid; store PAT in `sessionStorage`. Clear button to disconnect.
  - **Weekly Pipeline section** (hidden until authed):
    - Client ID input (default: bobe)
    - Week Of input (YYYY-MM-DD, optional)
    - Checkboxes: Skip Images, Skip Airtable
    - "Run Pipeline" button → calls `POST /repos/rtadik/bobe-content-dashboard/actions/workflows/weekly-pipeline.yml/dispatches`
    - Shows "Triggered! Check Run Status below."
  - **Onboard Client section** (hidden until authed):
    - Fields: Client ID, Display Name, Tagline, Website, Primary Color, Accent Color, Industry, Platforms, Airtable Base ID (optional)
    - "Create Client" button → calls `POST .../onboard-client.yml/dispatches`
    - Note after submit: "Client folder created. Run /onboard-client {id} in Claude Code to draft content guidelines."
  - **Run Status section** (hidden until authed):
    - "Refresh Status" button
    - Two tables: "Weekly Pipeline Runs" and "Onboard Runs"
    - Shows: run number, status (queued/in_progress/completed), conclusion (success/failure), started at, link to run
    - Auto-refresh every 30s when a run is in_progress

- Create `admin/admin.css`: dark navy theme, form layouts, status badges (green/yellow/red)
- Create `admin/admin.js`: all GitHub API calls, sessionStorage auth handling, status polling

**Security note in admin panel**: Add visible note — "Your GitHub PAT is stored only in this browser tab's session memory. It is sent directly to api.github.com and nowhere else. Close this tab to clear it."

**Files affected:**

- `admin/index.html` (new)
- `admin/admin.css` (new)
- `admin/admin.js` (new)

---

### Step 5: Modify `scripts/build_static.py`

Add `--include-admin` flag. When set, after building `dist/`, copy the `admin/` directory to `dist/admin/`.

**Actions:**

- Add to argparse: `--include-admin` flag (boolean, default False)
- After the main build loop, if `--include-admin`:
  ```python
  admin_src = Path(__file__).parent.parent / "admin"
  admin_dst = output_dir / "admin"
  if admin_src.exists():
      shutil.copytree(admin_src, admin_dst, dirs_exist_ok=True)
      print(f"Admin panel copied to {admin_dst}")
  ```

**Files affected:**

- `scripts/build_static.py`

---

### Step 6: Update `.claude/commands/deploy.md`

Add a step before pushing to gh-pages: copy `admin/` to `dist/admin/` (or use `--include-admin` flag with build_static.py).

**Actions:**

Update Step 1 to use `--include-admin`:
```bash
cd "/Users/rt/Claude Code/bobe-image-content-gen" && ./venv/bin/python scripts/build_static.py --output dist --include-admin
```

**Files affected:**

- `.claude/commands/deploy.md`

---

### Step 7: Configure GitHub Secrets

This step requires the user to perform a one-time action in the GitHub repository settings.

**Actions:**

- Document in `reference/github-actions-setup.md` (new reference file):
  ```
  # GitHub Actions Setup

  ## Required Secrets
  Go to: https://github.com/rtadik/bobe-content-dashboard/settings/secrets/actions

  Add these secrets (values from your .env file):
  - APIFY_API_TOKEN
  - GOOGLE_AI_API_KEY
  - WAVESPEED_API_KEY
  - AIRTABLE_API_KEY

  ## Required for Admin Panel Auth
  The admin panel uses YOUR GitHub PAT to trigger workflows.
  Create a PAT at: https://github.com/settings/tokens
  Required scope: actions:write
  Store it in your password manager — you'll enter it in the admin panel UI each session.

  ## GitHub Pages Setup (if not already done)
  1. Go to https://github.com/rtadik/bobe-content-dashboard/settings/pages
  2. Source: Deploy from a branch → Branch: gh-pages / root
  3. Save
  ```

**Files affected:**

- `reference/github-actions-setup.md` (new)

---

### Step 8: Update `CLAUDE.md`

**Actions:**

- Add `pipeline_runner.py` to the Scripts table
- Add admin panel URL to the Deployment section
- Add GitHub Actions section under Commands
- Update Workspace Structure to include `.github/workflows/` and `admin/`

**Files affected:**

- `CLAUDE.md`

---

### Step 9: Validate

**Actions:**

- Run `python scripts/pipeline_runner.py --mock --client bobe` locally to verify the script runs without errors
- Verify `dist/admin/index.html` exists after running `build_static.py --include-admin`
- Commit everything and push to Fork-#1
- Enable GitHub Pages on the repo if not already done
- Run a `/deploy` locally to push the admin panel live
- Test admin panel: open `https://rtadik.github.io/bobe-content-dashboard/admin/`
- Enter a GitHub PAT with `actions:write` scope → verify authentication
- Trigger a mock pipeline run (add `--mock` support to the workflow input) and verify it appears in Run Status

**Files affected:**

- All newly created files (validation only)

---

## Connections & Dependencies

### Files That Reference This Area

- `.claude/commands/deploy.md` — updated to use `--include-admin`
- `.claude/commands/weekly-pipeline.md` — can reference `pipeline_runner.py` as the GH Actions equivalent
- `reference/api-setup.md` — should link to `reference/github-actions-setup.md`
- `CLAUDE.md` — updated to document new structure

### Updates Needed for Consistency

- `CLAUDE.md` Scripts table: add `pipeline_runner.py`
- `CLAUDE.md` Workspace Structure: add `.github/workflows/` and `admin/`
- `CLAUDE.md` Deployment section: add admin panel URL
- `reference/api-setup.md`: add link to GitHub Actions setup guide

### Impact on Existing Workflows

- `/deploy` command: now uses `--include-admin` flag, so the admin panel is always deployed with the dashboard
- `/weekly-pipeline` (local Claude Code): unchanged — still the primary pipeline for quality-critical runs
- `pipeline_runner.py` (new): the GH Actions equivalent — uses Gemini for content instead of Claude; use when triggering from admin panel or when automating unattended runs

---

## Validation Checklist

- [ ] `scripts/pipeline_runner.py` runs with `--mock` flag without errors
- [ ] `scripts/pipeline_runner.py` generates a valid Excel workbook with 42 rows (non-mock test)
- [ ] `.github/workflows/weekly-pipeline.yml` YAML is valid (check with `yamllint` or GitHub UI)
- [ ] `.github/workflows/onboard-client.yml` YAML is valid
- [ ] `admin/index.html` opens in browser and shows the auth form
- [ ] GitHub PAT authentication succeeds and shows user name
- [ ] "Run Pipeline" button triggers a workflow (visible in GitHub Actions tab)
- [ ] Run Status section shows workflow runs and updates on refresh
- [ ] `build_static.py --include-admin` copies admin panel to `dist/admin/`
- [ ] Admin panel is accessible at `https://rtadik.github.io/bobe-content-dashboard/admin/` after deploy
- [ ] GitHub Secrets documented in `reference/github-actions-setup.md`
- [ ] `CLAUDE.md` updated

---

## Success Criteria

The implementation is complete when:

1. A user can open `https://rtadik.github.io/bobe-content-dashboard/admin/`, enter their GitHub PAT, and trigger a full weekly pipeline run for any configured client — without opening Claude Code or a terminal.
2. The triggered pipeline runs on GitHub Actions, generates 42 content rows + 42 images, syncs to Airtable, deploys the updated dashboard, and the admin panel shows the run as "completed/success".
3. A user can create a new client directory from the admin panel's onboard form, and it appears in `clients/` after the workflow completes.

---

## Notes

**Content quality note**: `pipeline_runner.py` uses Gemini Flash to generate Twitter threads and Telegram posts. The output quality is high but differs slightly from Claude-generated content (which is more consistent with brand voice). The local `/weekly-pipeline` command (Claude-driven) remains the gold standard for important weeks. Use `pipeline_runner.py` / admin panel for routine runs or when away from the local machine.

**Limitations of admin panel onboarding**: The GH Actions onboard workflow creates the config and template files but does not AI-draft `content-guidelines.md`, `keywords.md`, or `context.md` with client-specific content. After triggering onboard from the admin panel, run `/onboard-client {id}` locally in Claude Code to complete the content guidelines setup.

**Branch note**: Workflows reference `Fork-#1` as the working branch. When this branch is merged to `main`, update the `ref:` field in both workflow files to `main`.

**`GITHUB_TOKEN` permissions**: The `gh-pages` push in `weekly-pipeline.yml` uses `secrets.GITHUB_TOKEN` with `x-access-token`. This requires the repo's Actions settings to grant "Read and write permissions" to `GITHUB_TOKEN`. Set at: `https://github.com/rtadik/bobe-content-dashboard/settings/actions` → Workflow permissions → "Read and write permissions".

**Estimated effort**: Steps 1 (pipeline_runner.py) and 4 (admin panel) are the most involved. Steps 2–3 (workflows) and 5–8 (config/docs) are straightforward. Total: a solid session of implementation.
