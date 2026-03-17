# Plan: Autonomous Health Check & Auto-Fix System

**Created:** 2026-03-17
**Status:** Draft
**Request:** Build an aggressive auto-fix feedback loop that runs 3-5x daily, detects issues across the entire platform, fixes them autonomously, commits, deploys, and only escalates truly unfixable problems.

---

## Overview

### What This Plan Accomplishes

A fully autonomous monitoring and self-healing system that runs on a cron schedule via GitHub Actions. It audits every layer of the platform (APIs, content, images, Airtable, R2, config, deployment), auto-fixes what it can (retry uploads, re-sync records, regenerate broken content, rebuild/redeploy), commits all fixes, and creates GitHub Issues only for problems requiring human intervention.

### Why This Matters

Right now, failures are silent. If an R2 upload fails, an Airtable record is missing an image, a client config has a bad field, or a deploy is stale, nobody knows until someone manually checks. With 3-5 daily health checks and aggressive auto-fix, the platform becomes self-healing. Rut gets a daily summary instead of having to babysit infrastructure.

---

## Current State

### Relevant Existing Structure

- `scripts/pipeline_runner.py` — main pipeline, has try/except around most operations but no post-run validation
- `scripts/airtable_writer.py` — Airtable CRUD, `load_records()` can detect missing/incomplete records
- `scripts/r2_uploader.py` — has retry logic (3 attempts with backoff), `is_configured()` check
- `scripts/client_config.py` — config loader with `list_clients()`, `load_config()`, `get_api_key()`
- `scripts/build_static.py` — static site builder, imports from `web_viewer.py`
- `scripts/pipeline_status.py` — `PipelineStatus` class writes JSON status files
- `.github/workflows/` — 6 existing workflows, all use concurrency group `gh-pages-deploy`
- `admin/pipeline-status.html` — existing pipeline monitor (local only)

### Gaps or Problems Being Addressed

1. **No post-pipeline validation** — pipeline runs, logs errors, but never goes back to check what actually landed in Airtable/R2
2. **Silent failures** — R2 uploads, Airtable writes, image generation can fail without anyone noticing
3. **No config validation** — client configs can have missing fields, broken image paths, invalid API keys
4. **Stale deployments** — if a deploy fails or content changes without redeploy, the live site is out of date
5. **No cross-system consistency checks** — Airtable records may reference R2 images that don't exist, or vice versa
6. **Duplicate code** — `pipeline_runner.py` has its own `call_gemini()` and `extract_json()` instead of using `utils.py`
7. **No health history** — no way to see trends in system health over time

---

## Proposed Changes

### Summary of Changes

- New `scripts/health_check.py` — comprehensive audit + auto-fix engine (~800 lines)
- New `.github/workflows/health-check.yml` — cron workflow running 3x daily (8am, 2pm, 8pm UTC)
- New `.claude/commands/diagnose.md` — interactive `/diagnose` command for Claude Code sessions
- New `outputs/health/` directory for health reports and fix logs
- Modify `scripts/pipeline_runner.py` — add post-pipeline health check hook
- Modify `CLAUDE.md` — document new script, workflow, and command

### New Files to Create

| File Path | Purpose |
|-----------|---------|
| `scripts/health_check.py` | Main health check engine: 8 audit modules + auto-fix actions + report generation |
| `.github/workflows/health-check.yml` | Cron workflow: runs health_check.py 3x daily, commits fixes, redeploys if needed, opens Issues for escalation |
| `.claude/commands/diagnose.md` | `/diagnose` command for interactive health check during Claude Code sessions |

### Files to Modify

| File Path | Changes |
|-----------|---------|
| `scripts/pipeline_runner.py` | Add post-pipeline health check call at end of successful runs |
| `CLAUDE.md` | Add health_check.py to Scripts table, health-check.yml to Workflows section, /diagnose to Commands section |
| `.gitignore` | Add `outputs/health/` if not already covered |

### Files to Delete

None.

---

## Design Decisions

### Key Decisions Made

1. **GitHub Actions cron over local cron/launchd**: Runs in CI where all secrets are available, no dependency on Rut's machine being on. Free tier allows plenty of runs. Consistent environment.

2. **3x daily schedule (8am, 2pm, 8pm UTC)**: Covers morning, midday, evening. More than 3x would burn Actions minutes unnecessarily. Can be bumped to 5x later by adding 11am and 5pm slots.

3. **Single Python script with module-based checks**: Each check category (API, Airtable, R2, Config, Images, Content, Deploy, Cross-system) is a function returning a standardized `CheckResult` list. This makes it easy to add new checks or disable categories.

4. **Fix-then-report pattern**: Each check function both detects AND fixes. It returns what it found and what it fixed. The report is generated after all fixes are applied.

5. **GitHub Issues for escalation only**: Auto-fixes are committed silently. Only truly unfixable problems (expired API key, Airtable schema mismatch, etc.) create a GitHub Issue. Issues are labeled `health-check` and deduplicated (won't create duplicates for the same problem).

6. **JSON report + markdown summary**: `outputs/health/` stores JSON reports (machine-readable for trends) and the workflow posts a markdown summary to the commit message. The `/diagnose` command reads the latest report.

7. **Concurrency group separate from deploy**: Health check uses `health-check` concurrency group (not `gh-pages-deploy`) so it doesn't block or get blocked by content pipelines. BUT if it needs to redeploy, it calls `build_static.py` and uses the deploy concurrency group for that step only.

8. **Post-pipeline hook**: After `pipeline_runner.py` completes successfully, it runs a lightweight subset of health checks (Airtable record completeness, R2 image existence) to catch issues immediately rather than waiting for the next cron run.

### Alternatives Considered

- **Cloudflare Worker cron**: Would work for HTTP health checks but can't run Python scripts, access Airtable/R2 with full credentials, or commit fixes. Rejected.
- **Local launchd/cron**: Requires Rut's machine to be on, can't access GitHub Secrets, harder to debug. Rejected.
- **Separate monitoring service (Uptime Robot, etc.)**: Only checks if site is up, can't audit content quality or fix things. Too limited. Rejected.
- **Single monolithic check**: Harder to maintain, can't run individual categories. Module approach is better.

### Open Questions

None — the aggressive auto-fix directive is clear. The system will fix everything it can and only escalate what it truly cannot.

---

## Step-by-Step Tasks

### Step 1: Create the Health Check Engine

Create `scripts/health_check.py` with the following architecture:

**Core structure:**

```python
# Severity levels
SEVERITY = {"critical": 0, "warning": 1, "info": 2}

class CheckResult:
    category: str        # e.g., "airtable", "r2", "config"
    check_name: str      # e.g., "missing_image_urls"
    severity: str        # "critical", "warning", "info"
    message: str         # Human-readable description
    auto_fixed: bool     # Whether the fix was applied
    fix_description: str # What was done to fix it (empty if not fixed)
    needs_escalation: bool  # True = create GitHub Issue

class HealthReport:
    timestamp: str
    client_id: str
    results: list[CheckResult]
    summary: dict  # counts by severity and category
    fixes_applied: int
    escalations: int
```

**8 audit modules:**

1. **`check_api_connectivity(client_id)`** — Test each API endpoint with a lightweight call:
   - Airtable: `GET /v0/meta/bases` (list bases)
   - R2: `head_object` on a known key (or `list_objects` with max_keys=1)
   - Gemini: `call_gemini("ping", client_id=client_id)` with a trivial prompt
   - Apify: `GET /v2/acts` (list actors)
   - WaveSpeed: `GET /api/v1/models` or similar lightweight endpoint
   - **Auto-fix**: None (can't fix expired keys). **Escalate**: Yes, with which key is broken.

2. **`check_client_configs()`** — Validate every client's config.json:
   - Required fields exist: `display_name`, `tagline`, `brand.primary_color`, `brand.accent_color`, `content.content_types` (array of 3), `content.bucket_size`
   - `brand/` directory has at least one image file
   - `content-guidelines.md`, `keywords.md`, `context.md`, `belief-journey.md` exist and are non-empty
   - `airtable.base_id` is set if `airtable.enabled` is true
   - API keys resolve via `get_api_key()` for required services
   - **Auto-fix**: Create missing files from `_template/` if template exists. Set defaults for missing optional fields. **Escalate**: Missing required fields that have no sensible default.

3. **`check_airtable_records(client_id, week_of)`** — Audit Airtable content completeness:
   - Load all records from the current week's table
   - Check each record has: Topic, Content (non-empty, non-fallback), Content_RU (non-empty, passes `is_cyrillic()`), Hashtags, Hashtags_RU, Platform, Format, Bucket, Status
   - Check image fields: `Image_URL_EN` and `Image_URL_RU` should have attachment format `[{"url": "..."}]`
   - Detect fallback content (prefix `[Fallback EN]` or `[Fallback RU]`)
   - Detect records stuck in "Draft" status for >48 hours
   - Count: should be 21 records (3 buckets x 7 topics)
   - **Auto-fix**: Regenerate fallback content by calling `call_gemini()` with the topic and updating the record. Re-push missing records from local data if available. **Escalate**: Entire table missing, schema mismatch.

4. **`check_r2_images(client_id, week_of)`** — Verify R2 image existence and accessibility:
   - For each Airtable record with an image URL, HTTP HEAD the R2 URL to verify it returns 200
   - Check both EN and RU image URLs
   - Detect URLs with stale cache-bust params (older than the record's last modified time)
   - **Auto-fix**: Re-upload from local file if it exists in `outputs/content/{client_id}/images/`. Re-generate image via `nano_banana.py`/`wavespeed_img.py` if local file also missing. Update Airtable record with new URL. **Escalate**: Image generation API is down (detected by check_api_connectivity).

5. **`check_cross_system_consistency(client_id, week_of)`** — Cross-reference Airtable, R2, and local files:
   - Every Airtable record's image URL should resolve in R2
   - Every R2 image for this week should be referenced by an Airtable record
   - If Excel exists, it should match Airtable record count
   - Local image files should have corresponding R2 uploads
   - **Auto-fix**: Upload orphaned local images to R2 and update Airtable. Delete orphaned R2 images (images with no Airtable reference) only if older than 7 days (safety buffer). **Escalate**: Count mismatches that can't be reconciled.

6. **`check_deployment_freshness(client_id)`** — Verify the live site matches current content:
   - Compare latest Airtable record timestamps with last deploy timestamp (from git log on gh-pages or Cloudflare Pages API)
   - Check that the live site returns HTTP 200 for key pages: landing, login, client dashboard
   - Verify CNAME/DNS is resolving correctly
   - **Auto-fix**: Trigger rebuild + redeploy via `build_static.py` + wrangler if content is newer than deploy. **Escalate**: Deploy command itself fails, DNS issues.

7. **`check_content_quality(client_id, week_of)`** — Basic content quality gates:
   - No em-dashes (`—`, `–`, `--`) in content (per CLAUDE.md rules)
   - Russian content passes `is_cyrillic()` threshold
   - Content length within expected ranges (Twitter: 200-1400 chars per thread, Telegram: 300-2000 chars)
   - Hashtags present and formatted correctly (start with #)
   - No duplicate topics within the same week
   - **Auto-fix**: Replace em-dashes with commas/colons. Regenerate content that fails Cyrillic check. **Escalate**: Systematic quality failures across many records.

8. **`check_workflow_health()`** — Audit GitHub Actions state:
   - Check recent workflow runs for failures via `gh api` or GitHub REST API
   - Detect workflows stuck in "in_progress" for >30 minutes
   - Check that required secrets are configured (via a canary: if API checks fail, the secret is likely missing/expired)
   - **Auto-fix**: Cancel stuck workflows via GitHub API. **Escalate**: Repeated workflow failures (same workflow failed 3+ times in 24h).

**Main orchestrator:**

```python
def run_health_check(client_id=None, week_of=None, categories=None, fix=True):
    """
    Run health checks for a client (or all clients).

    Args:
        client_id: Specific client or None for all clients
        week_of: Specific week or None for current week
        categories: List of check categories or None for all
        fix: Whether to apply auto-fixes (True for cron, can be False for dry-run)

    Returns:
        HealthReport with all results
    """
```

**CLI interface:**

```
python scripts/health_check.py                          # All clients, all checks, auto-fix ON
python scripts/health_check.py --client bobe            # Single client
python scripts/health_check.py --week-of 2026-03-17     # Specific week
python scripts/health_check.py --categories api,config  # Specific categories only
python scripts/health_check.py --dry-run                # Report only, no fixes
python scripts/health_check.py --post-pipeline          # Lightweight subset (Airtable + R2 only)
python scripts/health_check.py --json                   # Output JSON report to stdout
```

**Actions:**
- Create `scripts/health_check.py` with all 8 modules
- Create `outputs/health/` directory with `.gitkeep`
- Import from existing modules: `client_config`, `airtable_writer`, `r2_uploader`, `utils`

**Files affected:**
- `scripts/health_check.py` (new)
- `outputs/health/.gitkeep` (new)

---

### Step 2: Create the GitHub Actions Cron Workflow

Create `.github/workflows/health-check.yml`:

**Schedule:** `cron: '0 8,14,20 * * *'` (8am, 2pm, 8pm UTC = 3x daily)

**Also:** `workflow_dispatch` with inputs for manual triggering:
- `client_id` (optional, default: all)
- `categories` (optional, default: all)
- `dry_run` (boolean, default: false)

**Job structure:**

```yaml
name: Health Check & Auto-Fix

on:
  schedule:
    - cron: '0 8,14,20 * * *'
  workflow_dispatch:
    inputs:
      client_id:
        description: 'Client ID (blank for all)'
        required: false
        default: ''
      categories:
        description: 'Check categories (comma-separated, blank for all)'
        required: false
        default: ''
      dry_run:
        description: 'Dry run (report only, no fixes)'
        required: false
        type: boolean
        default: false

concurrency:
  group: health-check
  cancel-in-progress: true

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - checkout main (fetch-depth: 0)
      - setup Python 3.11
      - install dependencies
      - write .env from secrets
      - run health_check.py with --json flag, capture output
      - parse JSON report
      - if fixes were applied:
          - git add + commit changed files
          - push to main
      - if deployment needed (detected by check_deployment_freshness):
          - build static site
          - deploy via wrangler (needs CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_API_TOKEN secrets)
      - if escalations exist:
          - create/update GitHub Issue with label "health-check"
          - deduplicate: search for open issue with same title before creating new one
      - upload health report as artifact
```

**Key patterns (matching existing workflows):**
- `set -euo pipefail` in all shell steps
- `.env` created inline from secrets
- Concurrency group for deploy step only
- Artifact upload for reports

**New GitHub Secrets needed:**
- `CLOUDFLARE_ACCOUNT_ID` — for wrangler deploy (may already exist from /deploy setup)
- `CLOUDFLARE_API_TOKEN` — for wrangler deploy

**Actions:**
- Create `.github/workflows/health-check.yml`
- Verify Cloudflare secrets are documented in reference/github-actions-setup.md

**Files affected:**
- `.github/workflows/health-check.yml` (new)
- `reference/github-actions-setup.md` (modify — add Cloudflare secrets)

---

### Step 3: Create the /diagnose Command

Create `.claude/commands/diagnose.md`:

**Purpose:** When Rut opens a Claude Code session and runs `/diagnose`, Claude runs the health check interactively, shows results, and fixes issues on the spot.

**Behavior:**
1. Run `python scripts/health_check.py --json` and capture output
2. Also read latest report from `outputs/health/` if it exists (shows what the cron found)
3. Present a summary: X checks passed, Y warnings, Z critical, N auto-fixed
4. For each unfixed issue, explain what's wrong and fix it interactively
5. If everything is green, confirm the system is healthy

**Actions:**
- Create `.claude/commands/diagnose.md`

**Files affected:**
- `.claude/commands/diagnose.md` (new)

---

### Step 4: Add Post-Pipeline Health Check Hook

Modify `scripts/pipeline_runner.py` to run a lightweight health check after successful pipeline completion.

**Where:** After Phase 7 (Build Static Site), before the final "Pipeline complete" log message.

**What:** Call `health_check.run_health_check()` with:
- `categories=["airtable", "r2", "cross_system"]` (lightweight subset)
- `fix=True`
- Current client_id and week_of

**How:** Import and call directly (not subprocess), with try/except so health check failures don't fail the pipeline.

**Actions:**
- Add import of `health_check` module at top of pipeline_runner.py
- Add post-pipeline health check call after Phase 7
- Wrap in try/except with logging

**Files affected:**
- `scripts/pipeline_runner.py`

---

### Step 5: Implement Auto-Fix Actions

The auto-fix logic lives inside each check module in `health_check.py`. Here are the specific fix implementations:

**Content fixes:**
- Em-dash replacement: `re.sub(r'[—–]', ', ', content)` then update Airtable record via `airtable_writer.update_record()`
- Fallback content regeneration: Call `call_gemini()` with the original topic + guidelines, update Airtable record
- Failed Cyrillic: Re-translate EN content to RU via `call_gemini()` with translation prompt

**Image fixes:**
- Missing R2 image: Check local file first → `r2_uploader.upload_file()` → update Airtable attachment URL
- Missing local + R2: Re-generate via subprocess call to `nano_banana.py` or `wavespeed_img.py` → upload → update Airtable
- Broken attachment format: Re-wrap URL as `[{"url": "..."}]` and PATCH the record

**Sync fixes:**
- Missing Airtable records: If local data exists (Excel or previous JSON), push via `airtable_writer.write_record()`
- Orphaned R2 images: Log warning only (don't delete unless >7 days old and confirmed orphaned)

**Deploy fixes:**
- Stale deployment: Run `build_static.py` then `npx wrangler pages deploy dist`
- Failed deploy: Retry once, then escalate

**Config fixes:**
- Missing optional files: Copy from `clients/_template/` with client name substituted
- Missing `belief-journey.md`: Generate via Gemini using client's context.md and config.json

**Actions:**
- All fix logic is implemented within `health_check.py` (Step 1)
- This step is about being explicit on the fix implementations

**Files affected:**
- `scripts/health_check.py` (part of Step 1)

---

### Step 6: Implement GitHub Issue Escalation

Inside `health_check.py`, add an `escalate()` function:

```python
def escalate(results: list[CheckResult], repo: str = "rtadik/bobe-content-dashboard"):
    """Create or update GitHub Issues for unfixable problems."""
    # Group escalations by category
    # For each category with escalations:
    #   1. Search for open issue with title "Health Check: {category} issues"
    #   2. If exists, update body with latest findings
    #   3. If not, create new issue with label "health-check"
    # Uses `gh` CLI (available in GitHub Actions runners)
```

**Issue format:**
```markdown
## Health Check Alert: {category}

**Detected:** {timestamp}
**Client:** {client_id}
**Severity:** {highest severity in group}

### Issues Found

- {message 1}
- {message 2}

### What Was Tried

- {fix_description for each auto_fixed=False result}

### Manual Action Required

{specific instructions for what Rut needs to do}

---
*Auto-generated by health-check workflow*
```

**Labels:** `health-check`, `{severity}` (critical/warning)

**Actions:**
- Implement `escalate()` function in health_check.py
- Use `subprocess.run(["gh", "issue", ...])` for GitHub API calls

**Files affected:**
- `scripts/health_check.py` (part of Step 1)

---

### Step 7: Health Report Storage and History

Store reports in `outputs/health/`:

```
outputs/health/
├── .gitkeep
├── latest.json              # Symlink or copy of most recent report
├── 2026-03-17T08-00-00.json # Individual run reports
├── 2026-03-17T14-00-00.json
└── 2026-03-17T20-00-00.json
```

**Report JSON format:**
```json
{
  "timestamp": "2026-03-17T08:00:00Z",
  "duration_seconds": 45,
  "clients_checked": ["bobe"],
  "weeks_checked": ["2026-03-17"],
  "summary": {
    "total_checks": 42,
    "passed": 38,
    "warnings": 3,
    "critical": 1,
    "auto_fixed": 2,
    "escalated": 1
  },
  "results": [
    {
      "category": "airtable",
      "check_name": "missing_image_urls",
      "severity": "warning",
      "message": "3 records missing Image_URL_RU in Week-2026-03-17",
      "auto_fixed": true,
      "fix_description": "Re-uploaded 3 RU images from local files to R2, updated Airtable records",
      "needs_escalation": false
    }
  ],
  "fixes_log": [
    {
      "timestamp": "2026-03-17T08:01:23Z",
      "action": "r2_upload",
      "target": "bobe/2026-03-17/topic_slug_twitter_ru.png",
      "result": "success"
    }
  ]
}
```

**Retention:** Keep last 30 days of reports. The cron workflow cleans up older files.

**Actions:**
- Create `outputs/health/.gitkeep`
- Implement report writing in health_check.py
- Add cleanup logic for >30 day old reports
- Add `outputs/health/*.json` to `.gitignore` (reports are artifacts, not committed — only `latest.json` summary committed for /diagnose to read)

**Files affected:**
- `outputs/health/.gitkeep` (new)
- `.gitignore` (modify)
- `scripts/health_check.py` (part of Step 1)

---

### Step 8: Update Documentation

**CLAUDE.md updates:**
- Add `health_check.py` to Scripts table with description and flags
- Add `health-check.yml` to GitHub Actions section
- Add `/diagnose` to Commands section
- Add `outputs/health/` to Workspace Structure
- Add health check to Deployment section notes

**reference/github-actions-setup.md:**
- Add `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` to required secrets (if not already there)

**Actions:**
- Update CLAUDE.md Scripts table
- Update CLAUDE.md Commands section
- Update CLAUDE.md Workspace Structure
- Update CLAUDE.md GitHub Actions section
- Update CLAUDE.md Deployment section
- Update reference/github-actions-setup.md

**Files affected:**
- `CLAUDE.md`
- `reference/github-actions-setup.md`

---

## Connections & Dependencies

### Files That Reference This Area

- `scripts/pipeline_runner.py` — will be modified to call health check post-pipeline
- `scripts/airtable_writer.py` — imported by health_check.py for record operations
- `scripts/r2_uploader.py` — imported by health_check.py for image verification and re-upload
- `scripts/client_config.py` — imported by health_check.py for config validation
- `scripts/utils.py` — imported by health_check.py for `call_gemini()`, `is_cyrillic()`, `extract_json_from_llm()`
- `scripts/build_static.py` — called by health check for stale deploy fix
- `scripts/nano_banana.py` — called via subprocess for image regeneration
- `scripts/wavespeed_img.py` — called via subprocess for RU image regeneration

### Updates Needed for Consistency

- CLAUDE.md must reflect all new files and capabilities
- reference/github-actions-setup.md must include any new secrets
- The cron workflow must use the same Python version and dependency installation pattern as other workflows

### Impact on Existing Workflows

- **No interference with existing workflows**: Health check uses its own concurrency group (`health-check`), separate from `gh-pages-deploy`
- **Deploy step overlap**: When health check needs to redeploy, it uses wrangler directly (same as `/deploy`). The concurrency group prevents collision.
- **Post-pipeline hook**: Added with try/except so it cannot break an otherwise successful pipeline run
- **Git commits from CI**: Health check commits go to `main` branch, same as existing `publish-to-x.yml` pattern

---

## Validation Checklist

- [ ] `python scripts/health_check.py --dry-run --client bobe` runs without errors and produces a valid JSON report
- [ ] `python scripts/health_check.py --client bobe` detects and fixes at least one simulated issue (e.g., em-dash in content)
- [ ] `python scripts/health_check.py --post-pipeline --client bobe` runs the lightweight subset successfully
- [ ] `python scripts/health_check.py --json` outputs valid JSON to stdout
- [ ] Health report is written to `outputs/health/`
- [ ] `/diagnose` command works in Claude Code session and shows latest health status
- [ ] GitHub Actions workflow file passes `actionlint` or manual review
- [ ] Cron schedule is correct (3x daily)
- [ ] Escalation creates a properly formatted GitHub Issue with `health-check` label
- [ ] Post-pipeline hook in pipeline_runner.py doesn't break existing pipeline runs
- [ ] CLAUDE.md updated with new script, workflow, command, and directory
- [ ] No secrets are hardcoded; all use environment variables

---

## Success Criteria

The implementation is complete when:

1. `scripts/health_check.py` runs all 8 check categories, applies auto-fixes, and generates JSON + markdown reports
2. `.github/workflows/health-check.yml` runs on cron (3x daily) and via manual dispatch, commits fixes, redeploys when needed, and creates GitHub Issues for escalations
3. `/diagnose` command provides an interactive health summary in Claude Code sessions
4. `pipeline_runner.py` runs a lightweight health check after each successful pipeline execution
5. The system is fully autonomous — no human intervention needed for fixable issues

---

## Notes

- **Future enhancement**: Add a health dashboard page to the static site (like pipeline-status but for health trends). Could chart pass/fail rates over time using the stored JSON reports.
- **Future enhancement**: Slack/Telegram notifications for critical escalations instead of just GitHub Issues.
- **Future enhancement**: Predictive checks — e.g., API key expiration warnings before they actually expire.
- **Cost consideration**: GitHub Actions free tier gives 2,000 minutes/month. Each health check run should take 2-5 minutes. 3x daily = ~90 runs/month = ~270-450 minutes. Well within limits.
- **The duplicate code in pipeline_runner.py** (`call_gemini()`, `extract_json()`) should ideally be consolidated to use `utils.py`, but that's a separate refactor. Health check will import from `utils.py`.
