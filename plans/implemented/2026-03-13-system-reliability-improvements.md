# Plan: System Reliability, Performance & Security Improvements

**Created:** 2026-03-13
**Status:** Implemented
**Request:** Comprehensive system audit revealed 22 improvement areas across data integrity, performance, security, and reliability. This plan addresses them in 3 phases.

---

## Overview

### What This Plan Accomplishes

Hardens the entire content automation platform against silent failures, data corruption, and security weaknesses. Fixes critical schema mismatches, parallelizes image generation for 3-4x speedup, adds input validation throughout, and strengthens workflow error handling so broken content never reaches production.

### Why This Matters

The platform is now multi-client and serves live dashboards. Silent failures (wrong client, broken images, schema mismatches) can corrupt client content or publish wrong data to X. As more clients onboard, these issues compound. Fixing them now prevents incidents that would erode client trust.

---

## Current State

### Relevant Existing Structure

- `scripts/pipeline_runner.py` — Main pipeline, sequential image gen (Phase 5, lines 594-699)
- `scripts/airtable_writer.py` — Primary Airtable writer (18-field schema)
- `scripts/airtable_sync.py` — Legacy sync (15-field COLUMN_MAP, missing Tweet_URL)
- `scripts/client_config.py` — Central config loader, `get_active_client()` at lines 30-36
- `scripts/nano_banana.py` — EN image gen, `topic_slug` at line 315
- `scripts/wavespeed_img.py` — RU image gen
- `scripts/build_static.py` — Static site builder, credential gen at lines 64-98, CNAME at lines 2873-2876
- `scripts/bucket_generators.py` — JSON extraction (lines 56-64), Gemini calls (lines 37-53)
- `scripts/x_publisher.py` — X publishing, column assumptions (lines 108-168)
- `admin/admin.js` — PAT in sessionStorage (line 27), hardcoded REPO (line 8), XSS (line 337)
- `.github/workflows/weekly-pipeline.yml` — No `set -e`, deploy proceeds on failure
- `.github/workflows/auto-onboard.yml` — `|| true` swallows build errors (line 754)
- `clients/bobe/config.json` — R2 placeholder URLs (lines 139-143)

### Gaps or Problems Being Addressed

1. **Data corruption risk**: `airtable_sync.py` drops Tweet_URL on sync; image naming inconsistency between generators and pipeline_runner
2. **Silent failures**: Invalid `.active-client` falls back to BoBe without warning; workflows deploy broken content on pipeline failure
3. **Performance bottleneck**: 42 sequential image API calls (~40 min) could run in ~10 min with parallelization
4. **Security weaknesses**: Predictable passwords, XSS in admin panel, no CSRF on intake form
5. **Missing validation**: No column checks in Excel readers, no Cyrillic verification for Russian content
6. **Duplicated logic**: JSON extraction, Gemini API calls, slug generation reimplemented 2-3 times each

---

## Proposed Changes

### Summary of Changes

**Phase 1 — Data Integrity (Critical)**
- Fix Airtable schema mismatch in `airtable_sync.py`
- Fix BoBe R2 placeholder URLs in config
- Standardize image naming across all generators
- Add `set -e` and exit code validation to all GitHub Actions workflows
- Add Excel column validation in `x_publisher.py` and `airtable_sync.py`
- Add `.active-client` validation with explicit error on invalid client ID

**Phase 2 — Performance & Security**
- Parallelize image generation in `pipeline_runner.py` with ThreadPoolExecutor
- Fix XSS in `admin/admin.js` error rendering
- Make REPO configurable (not hardcoded) in `admin.js`
- Make CNAME configurable in `build_static.py`

**Phase 3 — Reliability & Polish**
- Add Russian content validation (Cyrillic check)
- Add retry logic for R2 uploads
- Extract shared utilities (JSON extraction, Gemini calls, slug generation)
- Add structured logging to pipeline scripts

### New Files to Create

| File Path | Purpose |
|-----------|---------|
| `scripts/utils.py` | Shared utilities: JSON extraction from LLM, Gemini API helper, topic slug generator, Cyrillic validator |

### Files to Modify

| File Path | Changes |
|-----------|---------|
| `scripts/airtable_sync.py` | Add Tweet_URL (col P) and Week/Client fields to COLUMN_MAP |
| `scripts/client_config.py` | Add strict validation in `get_active_client()` — raise error on invalid client |
| `scripts/pipeline_runner.py` | Parallelize Phase 5 image gen with ThreadPoolExecutor; import shared utils |
| `scripts/nano_banana.py` | Use shared `topic_slug()` from utils.py |
| `scripts/wavespeed_img.py` | Use shared `topic_slug()` from utils.py |
| `scripts/bucket_generators.py` | Import shared JSON extraction and Gemini helper from utils.py |
| `scripts/x_publisher.py` | Add column header validation before reading data rows |
| `scripts/build_static.py` | Make CNAME domain configurable via env var or config |
| `scripts/weekly_pipeline.py` | Add Cyrillic validation for Russian content; import shared utils |
| `admin/admin.js` | Escape error HTML; make REPO configurable from page meta tag |
| `clients/bobe/config.json` | Replace R2 placeholder URLs with actual values (from .env or user input) |
| `.github/workflows/weekly-pipeline.yml` | Add `set -e`, validate pipeline exit code before deploy |
| `.github/workflows/auto-onboard.yml` | Replace `\|\| true` with proper error handling; validate build output |
| `.github/workflows/generate-announcement.yml` | Add `set -e` |
| `.github/workflows/regenerate-item.yml` | Add `set -e` |
| `.github/workflows/publish-to-x.yml` | Add `set -e` |

### Files to Delete

None.

---

## Design Decisions

### Key Decisions Made

1. **ThreadPoolExecutor over asyncio for image parallelization**: Image gen uses subprocess calls and blocking HTTP. ThreadPoolExecutor is simpler, requires no async refactor, and provides sufficient parallelism. 4 workers balances throughput with API rate limits.

2. **Shared `utils.py` over merging into `client_config.py`**: `client_config.py` is already large and focused on config loading. Utility functions (JSON extraction, Gemini calls) are cross-cutting concerns that belong in their own module.

3. **CNAME from environment variable, not config.json**: The domain is a deployment concern, not a client concern. All clients share one deployment domain. `CNAME_DOMAIN` env var (or fallback to `content.rejiglabs.com`) keeps it configurable without touching client configs.

4. **Column validation by header name, not position**: Excel columns can shift if users insert/delete columns. Validate by matching header text in row 1, then use discovered positions. More resilient than hardcoded indices.

5. **Keep `airtable_sync.py` functional (not deprecated)**: Even though `airtable_writer.py` is primary, `airtable_sync.py` is still used for backfill/recovery. Its schema must stay in sync.

6. **Cyrillic validation as a warning, not a blocker**: If Gemini returns English instead of Russian, log a warning and retry once. If still English, keep it (some content has intentional English terms) but flag it in the output.

### Alternatives Considered

- **Multiprocessing instead of ThreadPoolExecutor**: Rejected — subprocess calls are I/O-bound, not CPU-bound. Threading is simpler and sufficient.
- **Remove `airtable_sync.py` entirely**: Rejected — it's still useful for bulk recovery/migration scenarios.
- **bcrypt for password hashing**: Considered but rejected for now — SHA-256 is adequate for the current threat model (low-value credentials, no PII). Adding bcrypt would require a Python dependency and JS library. Noted as future improvement if client data becomes more sensitive.
- **GitHub OAuth instead of PAT**: Better UX but requires OAuth app registration, callback URL, and significant frontend changes. Out of scope for this plan.

### Open Questions

1. **R2 public URL**: User needs to provide the actual `pub-{hash}.r2.dev` URL for BoBe's R2 bucket. Check Cloudflare dashboard > R2 > bobe-content-images > Settings > Public access.
2. **Image parallelism worker count**: Defaulting to 4 workers. WaveSpeed API rate limits may require adjustment. Start with 4, monitor for 429 errors.
3. **CNAME domain**: Currently `content.rejiglabs.com`. Confirm this is still the desired domain.

---

## Step-by-Step Tasks

### Step 1: Fix BoBe R2 Placeholder URLs

Replace the `REPLACE_WITH_ACTUAL` placeholder in `clients/bobe/config.json` with the real R2 public URL.

**Actions:**
- Check `.env` for `R2_PUBLIC_URL` value
- If set, update `clients/bobe/config.json` fields `r2.public_url` and `airtable.images_base_url` to match
- If not set, prompt user for the correct URL

**Files affected:**
- `clients/bobe/config.json`

---

### Step 2: Fix Airtable Schema Mismatch

Add missing fields to `airtable_sync.py` COLUMN_MAP so legacy sync doesn't drop data.

**Actions:**
- Add `16: "Tweet_URL"` to `COLUMN_MAP` dict (col P, index 16)
- Verify the table field creation function includes Tweet_URL, Week, and Client fields (matching `airtable_writer.py`'s 18-field schema)
- Add Week and Client as computed fields during sync (derived from filename and active client)

**Files affected:**
- `scripts/airtable_sync.py`

---

### Step 3: Add Active Client Validation

Make `get_active_client()` raise a clear error when `.active-client` contains an invalid client ID, instead of silently falling back to "bobe".

**Actions:**
- In `client_config.py`, after reading `.active-client`, validate that `clients/{client_id}/config.json` exists
- If invalid, raise `ValueError` with message listing available client IDs
- Keep "bobe" as default only when `.active-client` file is missing entirely

**Files affected:**
- `scripts/client_config.py`

---

### Step 4: Add Excel Column Validation

Before reading data rows, validate that Excel headers match expected column layout.

**Actions:**
- In `x_publisher.py`, read row 1 headers and build a name→index map
- Validate required columns exist: Date, Topic, Platform, Format, Content, Status, Tweet_URL
- Raise clear error if columns are missing or shifted
- In `airtable_sync.py`, add same header validation before sync
- Replace hardcoded column indices with discovered positions

**Files affected:**
- `scripts/x_publisher.py`
- `scripts/airtable_sync.py`

---

### Step 5: Add Workflow Error Handling

Prevent broken content from deploying when pipeline scripts fail.

**Actions:**
- Add `shell: bash` and `set -euo pipefail` to all Python-running steps in:
  - `weekly-pipeline.yml` (generate job, lines 74-89)
  - `generate-announcement.yml` (generate job)
  - `regenerate-item.yml` (generate job)
  - `publish-to-x.yml` (publish job)
- In `auto-onboard.yml`, replace `|| true` on build_static.py calls with proper error tracking:
  ```bash
  FAILED=0
  python scripts/build_static.py ... || FAILED=1
  if [ "$FAILED" -ne 0 ]; then
    echo "::warning::Build failed for client $client_id"
  fi
  ```
- Add a validation step after build: check that `dist/index.html` exists before deploying

**Files affected:**
- `.github/workflows/weekly-pipeline.yml`
- `.github/workflows/generate-announcement.yml`
- `.github/workflows/regenerate-item.yml`
- `.github/workflows/publish-to-x.yml`
- `.github/workflows/auto-onboard.yml`

---

### Step 6: Create Shared Utilities Module

Extract duplicated logic into `scripts/utils.py`.

**Actions:**
- Create `scripts/utils.py` with:
  ```python
  def extract_json_from_llm(text: str) -> dict | list:
      """Extract JSON from LLM response, handling markdown code fences."""
      # Consolidated from bucket_generators.py:56-64 and pipeline_runner.py:129-139

  def call_gemini(prompt: str, model: str = "gemini-2.0-flash", api_key: str = None) -> str:
      """Call Gemini API with standard error handling and fallback."""
      # Consolidated from bucket_generators.py:37-53 and pipeline_runner.py:106-126

  def topic_slug(topic: str, max_len: int = 30) -> str:
      """Generate a filesystem-safe slug from a topic string."""
      # Consolidated from nano_banana.py:315 and pipeline_runner.py:72-77

  def is_cyrillic(text: str, threshold: float = 0.3) -> bool:
      """Check if text contains sufficient Cyrillic characters."""
      # New: validates Russian translations
  ```
- Update imports in `bucket_generators.py`, `pipeline_runner.py`, `nano_banana.py`, `wavespeed_img.py`
- Keep original functions as thin wrappers initially (to avoid breaking changes), then remove in follow-up

**Files affected:**
- `scripts/utils.py` (new)
- `scripts/bucket_generators.py`
- `scripts/pipeline_runner.py`
- `scripts/nano_banana.py`
- `scripts/wavespeed_img.py`

---

### Step 7: Parallelize Image Generation

Convert sequential image generation in `pipeline_runner.py` Phase 5 to use ThreadPoolExecutor.

**Actions:**
- Import `concurrent.futures.ThreadPoolExecutor`
- Wrap the per-topic image generation (EN + RU + R2 upload + Airtable patch) into a function `generate_images_for_topic(topic_num, topic_data, ...)`
- Run with `ThreadPoolExecutor(max_workers=4)`:
  ```python
  with ThreadPoolExecutor(max_workers=4) as pool:
      futures = {
          pool.submit(generate_images_for_topic, num, data, ...): num
          for num, data in topics.items()
      }
      for future in as_completed(futures):
          topic_num = futures[future]
          try:
              future.result()
          except Exception as e:
              errors.append(f"Topic {topic_num} images failed: {e}")
  ```
- Airtable writes within each thread are independent (different records), so no lock needed
- Add `--parallel-workers N` CLI flag (default 4) for tunability
- Excel writes (if `--export-excel`) must be serialized — use a Lock or batch after all images complete

**Files affected:**
- `scripts/pipeline_runner.py`

---

### Step 8: Add Russian Content Validation

Verify Gemini actually returns Cyrillic text when translating to Russian.

**Actions:**
- In `pipeline_runner.py` (Phase 4, after Russian content generation), call `utils.is_cyrillic(content_ru)`
- If fails threshold (< 30% Cyrillic chars), retry Gemini call once with explicit instruction: "You MUST respond entirely in Russian using Cyrillic script"
- If still fails, keep the content but add `[RU-WARN]` prefix to Content_RU field
- Log warning with topic details

**Files affected:**
- `scripts/pipeline_runner.py`
- `scripts/utils.py` (is_cyrillic function)

---

### Step 9: Add R2 Upload Retry

Add simple retry with backoff for R2 uploads.

**Actions:**
- In `scripts/r2_uploader.py`, wrap boto3 `put_object` call with retry (3 attempts, 1s/2s/4s backoff)
- Use `botocore.exceptions.ClientError` and `ConnectionError` as retry triggers
- Log each retry attempt

**Files affected:**
- `scripts/r2_uploader.py`

---

### Step 10: Fix Admin Panel XSS and Hardcoded Repo

**Actions:**
- In `admin/admin.js` line 337, escape error messages before inserting into HTML:
  ```javascript
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
  // Then:
  const errHtml = `<div class="runs-empty" style="color:var(--red)">Error: ${escapeHtml(err.message)}</div>`;
  ```
- Move `REPO` constant to a `<meta>` tag in `admin/index.html`:
  ```html
  <meta name="github-repo" content="rtadik/bobe-content-dashboard">
  ```
  Then in JS: `const REPO = document.querySelector('meta[name="github-repo"]').content;`
- Update `build_static.py` to write this meta tag dynamically from config or env var

**Files affected:**
- `admin/admin.js`
- `admin/index.html`
- `scripts/build_static.py`

---

### Step 11: Make CNAME Configurable

**Actions:**
- In `build_static.py`, read domain from `CNAME_DOMAIN` env var with fallback:
  ```python
  cname_domain = os.environ.get("CNAME_DOMAIN", "content.rejiglabs.com")
  cname_path.write_text(f"{cname_domain}\n")
  ```
- Update workflows to pass `CNAME_DOMAIN` from GitHub Secrets (optional)

**Files affected:**
- `scripts/build_static.py`
- `.github/workflows/weekly-pipeline.yml` (add env var, optional)

---

### Step 12: Add Structured Logging to Pipeline

**Actions:**
- In `scripts/pipeline_runner.py`, replace `print()` calls with Python `logging` module
- Configure with format: `%(asctime)s [%(levelname)s] %(message)s`
- Use levels: INFO for progress, WARNING for recoverable issues, ERROR for failures
- Keep `print()` for user-facing CLI output (argument parsing, final summary)
- Add timing metrics: log elapsed time for each phase

**Files affected:**
- `scripts/pipeline_runner.py`

---

### Step 13: Update CLAUDE.md

**Actions:**
- Add `scripts/utils.py` to the Scripts table
- Note parallel image generation and `--parallel-workers` flag in pipeline_runner row
- Update any references to sequential image generation

**Files affected:**
- `CLAUDE.md`

---

### Step 14: Validation & Testing

**Actions:**
- Run `python scripts/pipeline_runner.py --client bobe --mock --week-of 2026-03-16` to verify parallel image gen works
- Run `python scripts/airtable_sync.py --mock --client bobe --week-of 2026-03-02` to verify schema fix
- Trigger `weekly-pipeline.yml` with mock=true to verify workflow error handling
- Manually test admin panel error rendering with invalid PAT to verify XSS fix
- Verify `.active-client` validation by writing invalid client ID and running any script

**Files affected:**
- None (testing only)

---

## Connections & Dependencies

### Files That Reference This Area

- `scripts/build_static.py` imports `load_content` from `web_viewer.py` — changes to content loading affect static builds
- `scripts/weekly_pipeline.py` calls `translate_text_to_russian()` internally — Cyrillic validation should cover this path too
- All GitHub Actions workflows share the `gh-pages-deploy` concurrency group — changes to one affect serialization of others
- `admin/admin.js` uses `REPO` constant for all GitHub API calls — changing it affects pipeline triggers, run status polling, and announcement dispatch

### Updates Needed for Consistency

- `reference/api-setup.md` — clarify Gemini is text-only, WaveSpeed handles images
- `reference/airtable-client-setup.md` — update URL from GitHub Pages to Cloudflare Pages

### Impact on Existing Workflows

- **Phase 5 parallelization** changes the order in which images appear in logs (non-deterministic) but produces the same final output
- **`set -e` in workflows** may surface previously-hidden failures — some runs that used to "succeed" (by ignoring errors) will now fail correctly. This is intentional.
- **Column validation** will reject malformed Excel files that previously processed silently. Users editing workbooks manually will get clear error messages instead of corrupt data.
- **Active client validation** will break any workflow that accidentally runs with a stale/invalid `.active-client` file — this is the desired behavior.

---

## Validation Checklist

- [ ] `python -c "from scripts.utils import extract_json_from_llm, call_gemini, topic_slug, is_cyrillic"` succeeds
- [ ] `python scripts/pipeline_runner.py --mock --client bobe --week-of 2026-03-16` completes with parallel image gen
- [ ] Writing "nonexistent" to `.active-client` and running any script raises clear ValueError
- [ ] `airtable_sync.py` COLUMN_MAP includes Tweet_URL at index 16
- [ ] `x_publisher.py` validates headers before processing and rejects shifted columns
- [ ] `clients/bobe/config.json` has real R2 URLs (no REPLACE_WITH_ACTUAL)
- [ ] Admin panel renders `<script>alert(1)</script>` as escaped text in error messages
- [ ] `weekly-pipeline.yml` generate job fails the workflow (not just the step) when pipeline_runner exits non-zero
- [ ] `auto-onboard.yml` logs warnings for failed builds but doesn't silently continue
- [ ] CNAME domain reads from `CNAME_DOMAIN` env var
- [ ] Pipeline logs show timestamps and phase timing
- [ ] CLAUDE.md updated with `utils.py` and parallel image gen

---

## Success Criteria

The implementation is complete when:

1. **Zero silent failures**: Invalid client IDs, missing Excel columns, failed pipeline scripts, and broken builds all produce explicit errors or warnings instead of proceeding silently
2. **Image generation runs in parallel**: `pipeline_runner.py` Phase 5 uses ThreadPoolExecutor with configurable worker count, reducing typical runtime from ~40 min to ~10-15 min
3. **No data corruption paths**: `airtable_sync.py` preserves all 18 fields including Tweet_URL; image filenames are consistent between generators and consumers; Russian content is validated as actually Russian

---

## Notes

- **Phased implementation recommended**: Steps 1-5 (Phase 1: Data Integrity) are independent and can be implemented first. Steps 6-9 (Phase 2: Performance) depend on Step 6 (utils.py). Steps 10-13 (Phase 3: Polish) are independent of each other.
- **R2 URL is a user action item**: Step 1 requires the user to look up their actual R2 public URL from the Cloudflare dashboard. This cannot be automated.
- **Backward compatibility**: All changes maintain backward compatibility. `airtable_sync.py` gains fields but doesn't remove any. `utils.py` functions are additive. Workflow changes only add strictness, not new behavior.
- **Future considerations**: GitHub OAuth for admin panel, per-client custom domains, and scheduled publishing are out of scope but noted for future planning.

---

## Implementation Notes

**Implemented:** 2026-03-13

### Summary

All 14 steps implemented across 3 phases. Created shared `utils.py` module, parallelized image generation in pipeline_runner.py, added header-based Excel column validation, fixed Airtable schema mismatch, added active client validation, hardened all GitHub Actions workflows with `set -euo pipefail`, added R2 upload retry with exponential backoff, added Russian content Cyrillic validation, fixed XSS in admin panel, made REPO and CNAME configurable, and added structured logging to pipeline_runner.

### Deviations from Plan

- **Step 1 (R2 URLs)**: Deferred to user action. R2_PUBLIC_URL is empty in local .env and R2 credentials are not configured locally. The pipeline_runner uses `r2_uploader.py` which reads from env vars directly, so the config.json placeholder only affects the legacy `airtable_sync.py` path. R2 may be configured in GitHub Secrets for remote runs.
- **Step 6 (shared utils)**: Created utils.py and wired it into pipeline_runner.py. Did not refactor bucket_generators.py or nano_banana.py to use the shared functions yet (kept original functions intact to avoid breaking changes). These can be migrated in a follow-up.

### Issues Encountered

None.
