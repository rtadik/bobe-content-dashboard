# Plan: Deploy BoBe Content Dashboard as a Free Static Site

**Created:** 2026-02-18
**Status:** Implemented
**Request:** Deploy the content dashboard so the client can access it remotely, with zero extra costs.

---

## Overview

### What This Plan Accomplishes

Adds a static site build step to the content pipeline that renders the dashboard as self-contained HTML files + images, deployable to any free static hosting platform (Cloudflare Pages or GitHub Pages). The client gets a URL they can visit to view generated content — no server, no cold starts, no monthly bills.

### Why This Matters

Right now the dashboard only works locally via Flask (`/view-content`). The client can't see generated content without being on your machine. Deploying a static version gives them instant access while keeping costs at exactly zero — critical since this is a tool, not a revenue-generating product.

---

## Current State

### Relevant Existing Structure

| File/Folder | Relevance |
|-------------|-----------|
| `scripts/web_viewer.py` | Flask dashboard — HTML template and data loading logic we'll reuse. Already handles both daily (`YYYY-MM-DD-content.xlsx`) and weekly (`YYYY-MM-DD-weekly-content.xlsx`) files. Returns `week:YYYY-MM-DD` date identifiers for weekly content. `load_content()` auto-detects weekly workbooks (10 columns with "Day") vs daily (9 columns). |
| `scripts/weekly_pipeline.py` | Weekly pipeline orchestrator — generates 21 topics (3/day × 7 days) into weekly Excel workbooks |
| `outputs/content/*-content.xlsx` | Daily Excel files (topics + content) |
| `outputs/content/*-weekly-content.xlsx` | Weekly Excel files (topics + content with Day column) |
| `outputs/content/images/{date-type}/*.png` | Generated images in subdirectories (e.g., `images/2026-02-16-weekly/`, `images/2026-02-18-daily/`). ~500-650 KB each, up to 21 per weekly run. `resolve_image()` returns paths relative to `IMAGES_DIR`. |
| `outputs/content/*-approvals.json` | Local-only approval state (not needed in deployed version) |
| `.claude/commands/content-pipeline.md` | Daily pipeline — needs a new build step at the end |
| `.claude/commands/weekly-pipeline.md` | Weekly pipeline — needs a new build step at the end |
| `.claude/commands/view-content.md` | Local viewer command — stays unchanged |
| `.gitignore` | Currently excludes `outputs/content/*.xlsx` and `*.png` (flat only). Does NOT cover `outputs/content/images/**` subdirectories or `*.json` approval files — these gaps will be fixed as part of this plan. |

### Gaps or Problems Being Addressed

1. **Dashboard is local-only** — client can't access it without being on your machine
2. **Flask requires a running server** — can't just share a URL
3. **No deployment pipeline exists** — no way to push content to the web
4. **Current architecture assumes local filesystem** — threading, in-memory state, file writes are all incompatible with serverless platforms like Vercel

---

## Proposed Changes

### Summary of Changes

- Create `scripts/build_static.py` — renders the dashboard as static HTML files with a simplified template (no approval/regen features, just content viewing)
- Create `dist/` directory structure for the deployable static site
- Add a `/deploy` command that builds the static site and pushes to the deploy branch
- Add deployment config for the chosen hosting platform
- Update `/content-pipeline` to optionally build the static site after content generation
- Update `/weekly-pipeline` to optionally build the static site after finalize
- Update `CLAUDE.md` with deployment documentation

### New Files to Create

| File Path | Purpose |
|-----------|---------|
| `scripts/build_static.py` | Static site builder — reads Excel files, renders HTML, copies images to `dist/` |
| `.claude/commands/deploy.md` | `/deploy` command — build static site + push to deploy branch |
| `dist/.gitkeep` | Establish output directory for static site builds |

### Files to Modify

| File Path | Changes |
|-----------|---------|
| `.claude/commands/content-pipeline.md` | Add optional Phase 6 to build static site after content generation |
| `.claude/commands/weekly-pipeline.md` | Add optional Phase 7 to build static site after finalize |
| `.gitignore` | Add `dist/` directory exclusion from main branch (it gets its own branch) |
| `CLAUDE.md` | Document `/deploy` command, deployment architecture, hosting setup |

### Files to Delete (if any)

None.

---

## Design Decisions

### Key Decisions Made

1. **Static HTML over serverless Flask**: A static site costs nothing to host, has no cold starts, and works on any CDN. The dashboard is read-only for the client — they view content, copy text, and browse dates. Flask stays for local use only (`/view-content`), and the static export handles the deployed version.

2. **Cloudflare Pages as primary recommendation (GitHub Pages as alternative)**: Both are truly free with no credit card required. Cloudflare has unlimited bandwidth and no commercial use restriction. GitHub Pages has a 100 GB/month soft limit and is technically for non-commercial use, but is simpler if you already use GitHub. **Vercel Hobby is not recommended** — its free tier restricts non-commercial/personal use only, and BoBe is a commercial project.

3. **Separate `dist/` output directory with deploy branch**: The static site gets built into `dist/` locally, then pushed to a `gh-pages` or `deploy` branch. This keeps the main branch clean (no generated HTML in version control) and works natively with both Cloudflare Pages and GitHub Pages. The `dist/` directory itself stays gitignored on main.

4. **Image files copied alongside HTML (not base64-inlined)**: Each generated image is ~500-650 KB. Base64 would increase this by 33% and make the HTML file massive. Copying as separate files allows browser caching, lazy loading, and faster initial page load.

5. **One HTML file per date + index redirect**: `dist/index.html` redirects to the latest date. `dist/{date}.html` has the full dashboard for that date. The date picker links between static pages. Simple, no JavaScript routing needed.

6. **Strip approval/regeneration from deployed version**: The client doesn't need to approve images or trigger regeneration — that's your internal workflow. Removing these features from the static version simplifies the code and eliminates the need for any API endpoints or state management.

7. **Reuse data loading logic from web_viewer.py**: Import `load_content`, `resolve_image`, `list_available_dates`, and `IMAGES_DIR` from the existing viewer to avoid code duplication. Images are now in `outputs/content/images/` with subdirectories per date (e.g., `images/2026-02-16-weekly/`). `resolve_image()` returns paths relative to `IMAGES_DIR`, which the static builder mirrors into `dist/images/`.

### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|-----------------|
| Deploy Flask to Vercel serverless | Vercel Hobby is non-commercial only; requires Blob storage ($) for images; cold starts; ephemeral filesystem |
| Deploy Flask to Render free tier | 30+ second cold starts after 15 min inactivity; 512 MB RAM; service sleeps |
| Deploy Flask to Railway | Requires credit card after 30-day trial — not free |
| Deploy Flask to Fly.io | Requires credit card after 7-day trial — not free |
| Vercel Blob for image storage | Limited to ~250 MB on Hobby plan; adds complexity; still needs serverless Flask |
| Base64-encode images in HTML | 33% size increase; slower page loads; no browser caching |
| Store content in a database | Adds cost, complexity, and a dependency — overkill for a read-only content viewer |

### Open Questions (if any)

1. **Hosting platform preference**: Cloudflare Pages (unlimited bandwidth, no restrictions) vs GitHub Pages (simpler setup if already using GitHub). Both are free. Recommendation: Cloudflare Pages. Plan documents setup for both.

2. **Auto-deploy after pipeline**: Should `/content-pipeline` automatically build and deploy the static site at the end, or should deployment stay as a separate `/deploy` step? Plan implements both — auto-build with manual deploy.

3. **History depth**: Should the static site include all historical dates, or only the most recent N days? Recommendation: all available dates (total size is small — ~2 MB/day × 30 days = ~60 MB, well within limits).

---

## Step-by-Step Tasks

Execute these tasks in order during implementation.

### Step 1: Create the Static Site Builder Script

Create `scripts/build_static.py` that reads Excel content files and renders a static HTML dashboard.

**Actions:**

- Create `scripts/build_static.py` with the following functionality:
  - Import `load_content`, `resolve_image`, `list_available_dates`, `find_excel`, `CONTENT_DIR`, `IMAGES_DIR` from `web_viewer.py`
  - Define a simplified HTML template (based on `web_viewer.py`'s template but with these changes):
    - Remove the approval bar (approve/regenerate buttons, status line)
    - Remove the image loading overlay and regeneration JS
    - Remove all `/api/*` fetch calls
    - Keep: tab switching, copy-to-clipboard, hashtag copy, lightbox, date picker
    - Change date picker from `<form>` to `<select>` with `onchange="window.location=..."` linking to the sanitized filename
    - Show "Day" badge (Mon, Tue, etc.) on cards when present (weekly content includes a `day` field)
    - Add a small footer: "Generated by BoBe Content Pipeline"
  - **Date identifier handling**: `web_viewer.py` uses `week:YYYY-MM-DD` for weekly files. Since `:` is invalid in filenames, sanitize to `week-YYYY-MM-DD.html` for static output. Build a mapping: `{date_id: filename}` (e.g., `{"week:2026-02-16": "week-2026-02-16.html", "2026-02-18": "2026-02-18.html"}`)
  - **Image directory structure**: Images are now stored in `outputs/content/images/` with subdirectories per date/type (e.g., `images/2026-02-16-weekly/`, `images/2026-02-18-daily/`). The `resolve_image()` function returns paths relative to `IMAGES_DIR` (e.g., `2026-02-16-weekly/filename.png`). The static builder must preserve this subdirectory structure when copying to `dist/images/`.
  - `build_site(output_dir, dates=None)` function:
    - If `dates` is None, build for all available dates (both daily and weekly)
    - For each date: render `{sanitized_date}.html` with content from that date's Excel
    - Copy referenced images to `{output_dir}/images/` preserving subdirectory structure (use `shutil.copytree` or iterate `IMAGES_DIR.glob("**/*.png")` and recreate parent dirs)
    - Also check `CONTENT_DIR` root for backward-compatible flat images (older daily runs stored PNGs directly in `outputs/content/`)
    - Generate `index.html` that redirects to the most recent date page (first in the list)
  - CLI interface: `python scripts/build_static.py [--output dist] [--date 2026-02-18] [--date week:2026-02-16]`

- The script should:
  - Use Jinja2's `Environment` and `Template` directly (not Flask) to keep dependencies minimal
  - Handle both daily and weekly Excel formats (already handled by imported `load_content()`)
  - Handle missing images gracefully (show "No image" placeholder like the Flask version)
  - Print a summary: number of pages built (daily + weekly), total images copied, output directory size

**Files affected:**

- `scripts/build_static.py` (create)

**Template changes from web_viewer.py's HTML (specific removals):**

```
REMOVE:
- .image-actions div (approve-btn, regen-btn, img-status)
- .img-loading-overlay div
- All CSS for: .approve-btn, .regen-btn, .img-status, .img-loading-overlay, .spinner, .action-btn
- JS functions: approveImage(), regenImage(), pollJob(), loadApprovals(), setApprovalUI()
- JS variables: HAS_GENERATOR
- const TOPICS and CURRENT_DATE can stay (needed for lightbox)

KEEP:
- Full card layout with image, tabs, content, hashtags
- Tab switching JS
- Copy-to-clipboard JS
- Hashtag copy JS
- Lightbox JS
- Toast notification JS
- Date picker (converted from form to links)
- All card/grid/responsive CSS
- Empty state

ADD:
- Day badge on cards: if topic has a `day` field (weekly content), show it as a small
  chip/badge next to the topic title (e.g., "Mon" in a colored pill)
- Footer: "Generated by BoBe Content Pipeline" in muted text

MODIFY:
- Date picker: <select> with form submit → <select> with onchange="window.location"
  linking to sanitized filename (e.g., "week-2026-02-16.html" or "2026-02-18.html")
- Date display labels: show "Week of 2026-02-16" for weekly dates, plain date for daily
- Image src: "/images/filename" → "images/filename" (relative path)
- Remove .card.is-approved CSS class and logic
```

---

### Step 2: Create the dist/ Output Directory and Fix .gitignore

**Actions:**

- Create `dist/` directory with `.gitkeep`
- Update `.gitignore`:
  - Add `dist/` (the static site lives on its own deploy branch, not main)
  - Add `outputs/content/images/` (images subdirectory is not currently gitignored — the existing `outputs/content/*.png` pattern only matches flat files, not files in subdirectories)
  - Add `outputs/content/*.json` (approval JSON files are not currently gitignored)

**Files affected:**

- `dist/.gitkeep` (create)
- `.gitignore` (modify — add `dist/`, `outputs/content/images/`, `outputs/content/*.json`)

---

### Step 3: Create the /deploy Command

Create `.claude/commands/deploy.md` that orchestrates static site building and deployment.

**Actions:**

- Create the command file with this workflow:
  1. Build the static site: `python scripts/build_static.py --output dist`
  2. Verify the build (check files exist, report size)
  3. Deploy to the hosting platform:
     - **For Cloudflare Pages (via Wrangler CLI):**
       ```bash
       npx wrangler pages deploy dist --project-name bobe-content
       ```
     - **For GitHub Pages (via git):**
       ```bash
       cd dist && git init && git add -A && git commit -m "Deploy {date}" && git push -f origin main:gh-pages
       ```
     - **For manual upload:** Just tell user to drag `dist/` folder to Cloudflare Pages dashboard
  4. Report the live URL to the user

**Files affected:**

- `.claude/commands/deploy.md` (create)

**Command content:**

```markdown
# Deploy

> Build and deploy the BoBe content dashboard to the web

## Variables

date: $ARGUMENTS (optional — build only a specific date, defaults to all available dates)

---

## Instructions

### Step 1 — Build the static site

```bash
cd "/Users/rt/Claude Code/bobe-image-content-gen" && ./venv/bin/python scripts/build_static.py --output dist
```

If a specific date was provided:
```bash
cd "/Users/rt/Claude Code/bobe-image-content-gen" && ./venv/bin/python scripts/build_static.py --output dist --date {date}
```

### Step 2 — Verify the build

Check the build output:
- Confirm `dist/index.html` exists
- Confirm at least one `dist/{date}.html` exists
- Confirm `dist/images/` contains the expected images
- Report total file count and size

### Step 3 — Deploy

**Option A: Cloudflare Pages (recommended)**
```bash
npx wrangler pages deploy dist --project-name bobe-content
```

**Option B: GitHub Pages**
Ensure the repo has GitHub Pages enabled on the `gh-pages` branch, then:
```bash
cd "/Users/rt/Claude Code/bobe-image-content-gen/dist" && git init && git add -A && git commit -m "Deploy content dashboard" && git push -f git@github.com:USER/REPO.git main:gh-pages
```

**Option C: Manual upload**
Tell the user to:
1. Go to https://dash.cloudflare.com → Pages → Create a project → Upload assets
2. Drag the `dist/` folder
3. Deploy

### Step 4 — Report

Tell the user:
- Build successful: X pages, Y images, Z total size
- Deployed to: [URL]
- Share this URL with your client
```

---

### Step 4: Update Content Pipeline Command

Add an optional Phase 6 to `/content-pipeline` that builds the static site after content generation.

**Actions:**

- Add a new phase at the end of `.claude/commands/content-pipeline.md`:

```markdown
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
```

**Files affected:**

- `.claude/commands/content-pipeline.md` (modify — add Phase 6 after Phase 5)

---

### Step 4b: Update Weekly Pipeline Command

Add an optional Phase 7 to `/weekly-pipeline` that builds the static site after finalize.

**Actions:**

- Add a new phase at the end of `.claude/commands/weekly-pipeline.md` (after Phase 6: Finalize):

```markdown
### Phase 7: Build Static Dashboard (Optional)

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
```

**Files affected:**

- `.claude/commands/weekly-pipeline.md` (modify — add Phase 7 after Phase 6)

---

### Step 5: Update CLAUDE.md

Document the new deployment capability.

**Actions:**

Add to the Commands section:

```markdown
### /deploy [date]

**Purpose:** Build and deploy the static content dashboard for client access.

Renders the dashboard as static HTML files, copies images, and deploys to Cloudflare Pages (or GitHub Pages). Your client gets a URL to view all generated content. Zero hosting cost.

Requires one-time setup: Cloudflare account or GitHub Pages enabled. The `/deploy` command walks through first-time setup.

Example: `/deploy` or `/deploy 2026-02-18`
```

Add to the workspace structure tree (under `scripts/`):

```
    ├── build_static.py    # Static site builder for deployment
```

Add `dist/` to the key directories table:

```markdown
| `dist/`          | Static site build output (gitignored on main, deployed via `/deploy`) |
```

Add `deploy.md` to the commands tree:

```
    │   │   └── deploy.md          # /deploy — build and deploy static dashboard
```

Add a new section:

```markdown
## Deployment

The content dashboard can be deployed as a static site for client access:

- **Local viewing**: `/view-content` — runs Flask on localhost:5001
- **Client access**: `/deploy` — builds static HTML and deploys to Cloudflare Pages

The deployed dashboard is a read-only view of generated content. Content generation, image regeneration, and approval workflows remain local-only.

**Hosting**: Cloudflare Pages (free, unlimited bandwidth, no credit card required)
**Cost**: $0/month
```

**Files affected:**

- `CLAUDE.md` (modify)

---

### Step 6: One-Time Hosting Setup Documentation

Create a reference document for setting up the hosting platform.

**Actions:**

- This step is NOT a file to create during implementation — instead, the `/deploy` command should guide the user through first-time setup if not already configured.
- The `/deploy` command should detect if this is the first deployment (no Cloudflare project exists) and walk through setup.

**First-time setup steps (documented in the /deploy command):**

For Cloudflare Pages:
1. Create free Cloudflare account at https://dash.cloudflare.com
2. Go to Workers & Pages → Create → Pages → Upload assets
3. Upload the `dist/` folder
4. Choose a project name (e.g., `bobe-content`)
5. Get the URL: `https://bobe-content.pages.dev`
6. For subsequent deploys, either re-upload or use Wrangler CLI

For GitHub Pages:
1. Create a public repo (or use the existing one)
2. Go to Settings → Pages → Source: Deploy from branch `gh-pages`
3. Push the `dist/` contents to `gh-pages` branch
4. Get the URL: `https://username.github.io/repo-name`

---

### Step 7: Validate the Full Workflow

**Actions:**

- Build the static site from existing content: `python scripts/build_static.py --output dist`
- Open `dist/index.html` in a browser and verify:
  - Redirects to latest date page
  - All content cards render correctly
  - Images display properly
  - Tab switching works (Twitter/Telegram)
  - Copy buttons work
  - Lightbox works
  - Date picker links work (if multiple dates)
  - No console errors (no broken API calls to localhost)
- Verify image paths are relative with subdirectories (e.g., `images/2026-02-16-weekly/filename.png`, not `/images/...`)
- Verify `dist/images/` preserves subdirectory structure (e.g., `dist/images/2026-02-16-weekly/`, `dist/images/2026-02-18-daily/`)
- Check total `dist/` size is reasonable (~15-20 MB for current content including weekly images)

**Files affected:**

- No files changed — this is a validation step

---

## Connections & Dependencies

### Files That Reference This Area

| File | Reference |
|------|-----------|
| `CLAUDE.md` | Documents all commands, workspace structure, and workflows |
| `.claude/commands/content-pipeline.md` | Gets a new optional Phase 6 |
| `.claude/commands/weekly-pipeline.md` | Gets a new optional Phase 7 |
| `.claude/commands/view-content.md` | Unchanged — stays as the local viewer |
| `scripts/web_viewer.py` | `build_static.py` imports data-loading functions from this (already handles daily + weekly) |

### Updates Needed for Consistency

- `CLAUDE.md` must document `/deploy`, `dist/`, and the deployment architecture
- `.gitignore` must include `dist/`
- `/content-pipeline` should mention the deployment option
- `/weekly-pipeline` should mention the deployment option

### Impact on Existing Workflows

| Workflow | Impact |
|----------|--------|
| `/prime` | No change — additive documentation in CLAUDE.md |
| `/content-pipeline` | Minor addition — optional Phase 6 build step |
| `/weekly-pipeline` | Minor addition — optional Phase 7 build step |
| `/view-content` | No change — local Flask viewer continues to work independently |
| `/create-plan` | No change |
| `/implement` | No change |

---

## Validation Checklist

How to verify the implementation is complete and correct:

- [ ] `scripts/build_static.py` exists and runs without errors
- [ ] `python scripts/build_static.py --output dist` produces a valid static site
- [ ] `dist/index.html` redirects to the most recent date
- [ ] `dist/2026-02-18.html` renders daily content topic cards with images
- [ ] Weekly content pages (e.g., `dist/week-2026-02-16.html`) render with day badges (Mon, Tue, etc.)
- [ ] Images display correctly with relative subdirectory paths (e.g., `images/2026-02-16-weekly/filename.png`)
- [ ] Tab switching (Twitter/Telegram) works in static HTML
- [ ] Copy-to-clipboard works for content and hashtags
- [ ] Lightbox image zoom works
- [ ] Date picker links navigate between date pages
- [ ] No JavaScript errors in browser console (no broken `/api/*` calls)
- [ ] No approval/regeneration UI elements visible
- [ ] `.claude/commands/deploy.md` exists with clear instructions
- [ ] `.claude/commands/content-pipeline.md` has Phase 6
- [ ] `.claude/commands/weekly-pipeline.md` has Phase 7
- [ ] `CLAUDE.md` documents `/deploy` command and deployment architecture
- [ ] `dist/` is in `.gitignore`
- [ ] Total `dist/` size is reasonable (~15-20 MB for current daily + weekly content)

---

## Success Criteria

The implementation is complete when:

1. Running `python scripts/build_static.py --output dist` produces a complete, self-contained static website from the existing Excel content files
2. Opening `dist/index.html` in a browser shows a fully functional read-only dashboard identical to the Flask version (minus approval/regen features)
3. The `/deploy` command exists and provides clear deployment instructions for Cloudflare Pages and GitHub Pages
4. The client can access the dashboard at a public URL after deployment
5. Total cost of hosting: $0/month

---

## Notes

### Cost Breakdown

| Component | Cost |
|-----------|------|
| Cloudflare Pages hosting | Free (unlimited bandwidth) |
| GitHub Pages hosting (alternative) | Free (100 GB/month) |
| Custom domain (optional) | Free if using `.pages.dev` or `.github.io` subdomain |
| SSL certificate | Free (included by both platforms) |
| **Total** | **$0/month** |

### Size Projections

Weekly pipeline generates 21 images (~600 KB each = ~12.6 MB/week). Daily generates ~3 images (~1.8 MB/day).

| Timeframe | Est. Total Size (weekly mode) | Within Limits? |
|-----------|-------------------------------|----------------|
| 1 week (21 topics) | ~13 MB | Yes |
| 1 month (4 weeks) | ~55 MB | Yes |
| 6 months | ~330 MB | Yes |
| 1 year | ~660 MB | Yes (GitHub Pages limit: 1 GB site) |

### Future Enhancements

1. **Custom domain**: Point `content.bobe.app` (or similar) at the static site — free on both Cloudflare and GitHub Pages
2. **Auto-deploy via GitHub Actions**: Push to main triggers a build + deploy automatically
3. **Password protection**: Cloudflare Access (free for up to 50 users) can gate the site behind a login
4. **Content archiving**: If size grows beyond limits after a year, add a `--keep-days 90` flag to `build_static.py` to only include recent content

### Dependencies Added

- `jinja2` — already installed as a Flask dependency, so no new packages needed
- No new API keys or paid services required

---

## Implementation Notes

**Implemented:** 2026-02-18

### Summary

All 7 steps executed successfully. The static site builder (`scripts/build_static.py`) was created, importing data-loading functions from `web_viewer.py` and rendering a simplified Jinja2 template. The first build produced 2 pages (1 daily, 1 weekly) with 24 images totaling 13 MB. All pipeline commands updated with optional build phases, CLAUDE.md documented, and `.gitignore` gaps fixed.

### Deviations from Plan

None. All steps executed as specified.

### Issues Encountered

None.
