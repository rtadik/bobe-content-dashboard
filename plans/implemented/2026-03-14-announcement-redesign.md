# Plan: Redesign Announcements — Separate Tab, Loading States, Multi-Announcement Support

**Created:** 2026-03-14
**Status:** Implemented
**Request:** Redesign the announcement system: separate header tab, loading states on cards, multiple announcements per week, fix the broken generate button on the deployed dashboard.

---

## Overview

### What This Plan Accomplishes

Moves announcements out of the per-week bucket tabs into their own dedicated top-level tab that aggregates all announcements across weeks. Clients can submit multiple announcements per week (not just one), each generating 7 content angles. The generate button gets loading states directly on the placeholder cards, and generated content appears inline without a page refresh.

### Why This Matters

The current announcement flow is broken on the deployed static site (generate button shows errors), limited to one announcement per week, and buried inside each week's bucket tabs. Clients need a centralized place to manage all announcements and the ability to add multiple updates per week.

---

## Current State

### Relevant Existing Structure

| File | Role |
|------|------|
| `scripts/build_static.py` L1008-1023 | Bucket tabs (Trending, Education, Announcements, Blogs) + announcement input panel |
| `scripts/build_static.py` L1918-1987 | `submitAnnouncement()` JS — dispatches via worker or GH Actions |
| `scripts/build_static.py` L1496-1540 | `_dispatchViaWorker()` — generic workflow dispatch |
| `scripts/build_static.py` L3269-3440 | Static site builder — `date_options`, page rendering loop |
| `scripts/pipeline_runner.py` L1250-1280 | `--mode announcement` — saves text to `bucket-inputs.json`, generates 7 angles |
| `scripts/bucket_generators.py` L345-412 | `generate_announcement_placeholders()` — Gemini generates 7 angle topics |
| `scripts/airtable_writer.py` | Primary content store (18-field schema) |
| `.github/workflows/generate-announcement.yml` | GitHub Actions workflow for announcement generation |
| `scripts/web_viewer.py` L3576-3646 | Flask `/api/generate-announcement` endpoint |

### Gaps or Problems Being Addressed

1. **Generate button broken on deployed site** — `submitAnnouncement()` dispatches to `generate-announcement` workflow but the worker/GH API call fails silently or shows an error. The function passes `{ bucket: 'announcements', announcement_text: text }` but the workflow expects `announcement_text` as a direct input, not nested under `bucket`.
2. **No loading states** — After clicking generate, there's only a small text status message. No visual loading indicator on the placeholder cards.
3. **Single announcement per week** — `bucket-inputs.json` stores one `announcements.text` value; submitting a new one overwrites the previous.
4. **Announcements buried in week tabs** — Users must click into each week, then switch to the Announcements bucket tab, making it hard to see all announcements at a glance.
5. **No inline content display** — After generation completes, user must manually refresh the page. Generated content doesn't appear on the placeholder cards.

---

## Proposed Changes

### Summary of Changes

- Add a new **"Announcements" top-level header tab** before the week tabs
- Create a dedicated `announcements.html` page aggregating all announcements across weeks
- Remove the "Announcements" bucket tab from weekly pages (weeks show only Trending + Education)
- Support **multiple announcements per week** — each announcement gets its own card with input + generate button
- Add **loading spinner overlay** on announcement cards when generating
- After generation completes, **auto-reload** the page to show generated content inline
- Fix the `submitAnnouncement()` dispatch to correctly pass workflow inputs
- Update `pipeline_runner.py` to support multiple announcements per week (append, not overwrite)
- Update `bucket-inputs.json` schema to store an array of announcements

### New Files to Create

| File Path | Purpose |
|-----------|---------|
| None — all changes are modifications to existing files | |

### Files to Modify

| File Path | Changes |
|-----------|---------|
| `scripts/build_static.py` | Add Announcements header tab, new announcements page template, loading states, remove announcements from bucket tabs, fix `submitAnnouncement()` |
| `scripts/pipeline_runner.py` | Support multiple announcements (append to array in `bucket-inputs.json`) |
| `scripts/web_viewer.py` | Update Flask `/api/generate-announcement` to support announcement index |
| `.github/workflows/generate-announcement.yml` | Add `announcement_index` input for multi-announcement support |

### Files to Delete

None.

---

## Design Decisions

### Key Decisions Made

1. **Announcements as a top-level header tab, not a bucket tab**: This gives announcements first-class visibility. The tab appears before all week tabs in the header, styled distinctly. Clicking it loads `announcements.html` which aggregates all announcements across all weeks.

2. **Multiple announcements stored as an array**: Change `bucket-inputs.json` from `{ "announcements": { "text": "..." } }` to `{ "announcements": [ { "text": "...", "created": "ISO-date", "status": "pending|generated" }, ... ] }`. Each announcement generates its own set of 7 angles, stored with a unique announcement index.

3. **Announcement cards with inline input**: Instead of a separate input panel at the top, each "empty slot" is a card with an embedded textarea and generate button. After generation, the card transforms to show the generated content (7 angle topics as sub-items). A "+" button adds a new announcement card.

4. **Loading overlay on cards**: When generate is clicked, the card gets a spinner overlay (reusing the existing `img-loading-overlay` pattern). The status bar also shows progress.

5. **Auto-reload after workflow completes**: The existing `_pollViaWorker` / `pollRegenCompletion` already auto-reloads the page. This will naturally show the generated content after the workflow finishes.

6. **Airtable storage**: Announcement records continue to use `bucket: "announcements"` in Airtable. Multiple announcements per week are differentiated by topic content (each announcement's 7 angles are distinct topics).

### Alternatives Considered

- **Keep announcements inside week tabs but add multi-support**: Rejected because the user explicitly wants announcements in a separate, centralized location.
- **Real-time inline content injection (no reload)**: Too complex — would require the static site to fetch from Airtable directly. The existing poll-and-reload pattern works well enough.
- **Separate Airtable table per announcement**: Over-engineered. One table per week with `bucket: announcements` records is sufficient.

### Open Questions

1. **Announcement grouping on the aggregated page**: Should the announcements page group by week, or show a flat chronological list? **Recommendation**: Group by week with week headers.
2. **Maximum announcements per week**: Should there be a limit? **Recommendation**: No hard limit, but the UI encourages deliberate use (max 3-4 per week is practical).

---

## Step-by-Step Tasks

### Step 1: Update `bucket-inputs.json` Schema

Change the announcements storage from a single object to an array of announcements.

**Actions:**
- In `scripts/pipeline_runner.py`, update the announcement mode to:
  - Read existing `bucket-inputs.json`
  - Append the new announcement text to an `announcements` array (instead of overwriting)
  - Each entry: `{ "text": "...", "created": "ISO-datetime", "index": N }`
- Add backward compatibility: if the existing file has `announcements.text` (old format), migrate it to array format on read

**Files affected:**
- `scripts/pipeline_runner.py` (announcement mode section, ~L1250-1280)

---

### Step 2: Add `announcement_index` to Workflow and Pipeline

Support targeting a specific announcement (by index) when generating content.

**Actions:**
- In `.github/workflows/generate-announcement.yml`, add `announcement_index` input (default: `0`)
- In `scripts/pipeline_runner.py`, accept `--announcement-index N` flag, pass it to `bucket_generators.generate_announcement_placeholders()`
- The 7 generated topics for announcement N should include the announcement index in their metadata (so they can be grouped on the page)

**Files affected:**
- `.github/workflows/generate-announcement.yml`
- `scripts/pipeline_runner.py`

---

### Step 3: Redesign the Static Site Header — Add Announcements Tab

Move announcements from the bucket tabs to a top-level header tab.

**Actions:**
- In `build_static.py` template HTML (~L992-997), add an "Announcements" tab before the week tabs:
  ```html
  <a class="week-tab announcements-tab{% if is_announcements_page %} active{% endif %}" href="announcements.html">Announcements</a>
  ```
- Style `.announcements-tab` with the accent color to distinguish it from week tabs
- Remove the "Announcements" button from the `.bucket-tabs` section (~L1012)
- Remove the `announcement-input-panel` div (~L1016-1023) from the weekly page template
- Remove the `data-bucket="announcements"` placeholder card (~L1040-1045)

**Files affected:**
- `scripts/build_static.py` (template HTML + CSS)

---

### Step 4: Remove Announcements from Weekly Bucket Tabs

Weekly pages should only show Trending and Education.

**Actions:**
- In `build_static.py` template, remove the Announcements bucket tab button (~L1012)
- In `switchBucket()` JS function, remove announcements handling
- Filter out `data-bucket="announcements"` cards from weekly pages during rendering (in the Python build logic)
- Update the topic card rendering to skip announcement-bucket topics on weekly pages

**Files affected:**
- `scripts/build_static.py` (template HTML, JS, and Python rendering logic)

---

### Step 5: Create Announcements Page Template and Build Logic

Build a dedicated `announcements.html` that aggregates all announcements across weeks.

**Actions:**
- In `build_static.py`, create a new template section for the announcements page
- The page layout:
  - Same header (logo, lang toggle, logout) with "Announcements" tab active
  - Week tabs still visible (for navigation back to weekly content)
  - Body: grouped by week, newest first
  - Each week section has a header ("Week N - dd/mm/yy") and shows:
    - Existing generated announcement cards (with images, content, regen buttons — same card format as weekly pages)
    - A "+ New Announcement" button that reveals an input card
  - The input card has: textarea, "Generate 7 Content Angles" button, loading overlay
- In the Python build logic (`build_static_site` function):
  - Collect all announcement-bucket topics from all weeks
  - Group them by week
  - Render `announcements.html` with this aggregated data
  - Pass `is_announcements_page=True` to the template

**Files affected:**
- `scripts/build_static.py` (new template, new Python build logic, CSS)

---

### Step 6: Add Loading States to Announcement Cards

When "Generate" is clicked, show a loading overlay on the card.

**Actions:**
- Add CSS for `.announcement-card .loading-overlay` (spinner + "Generating 7 angles..." text)
- In `submitAnnouncement()`, immediately add the loading overlay to the clicked card
- The overlay stays until the poll detects workflow completion and triggers a reload
- If the workflow fails, remove the overlay and show an error message on the card

**Files affected:**
- `scripts/build_static.py` (CSS + JS)

---

### Step 7: Fix `submitAnnouncement()` Dispatch

Fix the broken generate button on the deployed static site.

**Actions:**
- In `submitAnnouncement()` (~L1918-1987):
  - When dispatching via worker: change from `_dispatchViaWorker('generate-announcement', { bucket: 'announcements', announcement_text: text })` to pass `announcement_text` correctly
  - When dispatching via GH API: the workflow is `generate-announcement.yml` (not `weekly-pipeline.yml` as currently coded on L1947). Fix the workflow filename in the fetch URL.
  - Add `announcement_index` parameter to the dispatch
- Test both code paths (worker and direct GH API)

**Files affected:**
- `scripts/build_static.py` (JS `submitAnnouncement()` function)

---

### Step 8: Update Flask Endpoint for Multi-Announcement

Update the local Flask `/api/generate-announcement` to support multiple announcements.

**Actions:**
- In `web_viewer.py`, update the endpoint to accept optional `announcement_index` in the request body
- Pass `--announcement-index N` to the `pipeline_runner.py` subprocess call

**Files affected:**
- `scripts/web_viewer.py`

---

### Step 9: Update `web_viewer.py` to Exclude Announcements from Weekly View

The Flask dashboard should mirror the static site behavior.

**Actions:**
- In the Flask template rendering, filter out announcement-bucket topics from weekly pages
- Add a new `/announcements` route that renders the aggregated announcements view
- Add the Announcements header tab to the Flask template

**Files affected:**
- `scripts/web_viewer.py`

---

### Step 10: Test End-to-End

Verify the full flow works locally and on the deployed site.

**Actions:**
- Run `/view-content` locally and verify:
  - Announcements tab appears in header before week tabs
  - Clicking it shows the announcements page with grouped content
  - Weekly pages show only Trending + Education bucket tabs
  - "+ New Announcement" button reveals input card
  - Generate button shows loading overlay
  - After generation, content appears on reload
- Build static site and verify the same behavior
- Test the GitHub Actions workflow dispatch from the deployed site

**Files affected:**
- No files — testing only

---

## Connections & Dependencies

### Files That Reference This Area

- `scripts/web_viewer.py` — Flask dashboard mirrors static site structure
- `scripts/pipeline_runner.py` — Generates announcement content
- `scripts/bucket_generators.py` — Creates 7 angle topics from announcement text
- `scripts/airtable_writer.py` — Stores announcement records
- `.github/workflows/generate-announcement.yml` — Workflow trigger
- `.github/workflows/weekly-pipeline.yml` — Full pipeline also generates announcements

### Updates Needed for Consistency

- `CLAUDE.md` — Update workspace structure description (announcements tab, multi-announcement)
- Weekly pipeline skill — Update to note announcements are now on a separate tab
- Admin panel (`admin/index.html`) — May need updates if it references announcement bucket tabs

### Impact on Existing Workflows

- **Weekly pipeline**: Still generates announcement placeholders per week, but they display on the announcements page instead of in week tabs
- **`generate-announcement.yml`**: Gets a new `announcement_index` input (backward-compatible, defaults to 0)
- **`build_static.py`**: Major template changes — announcements page is new, weekly pages lose announcements bucket tab
- **Airtable schema**: No changes needed — announcement records already have `bucket: "announcements"` and can be filtered

---

## Validation Checklist

- [ ] Announcements header tab visible before week tabs on all pages
- [ ] Clicking Announcements tab loads `announcements.html` with all announcements grouped by week
- [ ] Weekly pages show only Trending and Education bucket tabs
- [ ] "+ New Announcement" button reveals input card with textarea
- [ ] Generate button shows loading spinner overlay on the card
- [ ] Workflow dispatches correctly (both worker and direct GH API paths)
- [ ] Multiple announcements per week are stored as array in `bucket-inputs.json`
- [ ] Generated content appears on the announcements page after reload
- [ ] EN/RU language toggle works on the announcements page
- [ ] Flask local dashboard mirrors the same behavior
- [ ] Existing weekly content (Trending, Education) unaffected
- [ ] CLAUDE.md updated to reflect new announcement architecture

---

## Success Criteria

The implementation is complete when:

1. A dedicated "Announcements" header tab exists and shows all announcements across all weeks, grouped by week
2. Clients can submit multiple announcements per week, each generating 7 content angles with loading states
3. Weekly content pages show only Trending and Education bucket tabs (no announcements)
4. The generate button works correctly on both the local Flask dashboard and the deployed static site

---

## Notes

- The `weekly-pipeline.yml` workflow still generates announcement placeholders during the full weekly run. These placeholders will appear as empty slots on the announcements page, ready for client input.
- The `blog` bucket tab should remain on weekly pages if it exists (this plan does not touch blogs).
- Future enhancement: allow clients to edit/delete submitted announcements before generation.
- The `_pollViaWorker` / `pollRegenCompletion` auto-reload mechanism handles the "show content after generation" requirement without needing real-time injection.

---

## Implementation Notes

**Implemented:** 2026-03-14

### Summary

All 10 steps executed. Announcements now have a dedicated header tab (pink accent, before week tabs) that loads `announcements.html` with content aggregated across all weeks, grouped by week (newest first). Each week section shows existing announcement cards + a "+ New Announcement" button that reveals an input card with textarea, generate button, and loading overlay. Multiple announcements per week are supported via array storage in `bucket-inputs.json`. The generate button correctly dispatches to `generate-announcement.yml` (was previously `weekly-pipeline.yml`). Weekly pages show only Trending, Education, and Blogs bucket tabs.

### Deviations from Plan

- **Step 9 (Flask dashboard)**: Kept minimal. Updated the `/api/generate-announcement` Flask endpoint with `announcement_index` support, but did not add a separate `/announcements` Flask route or modify the Flask HTML template. The Flask dashboard is a dev tool; the production dashboard is the static site. Full Flask parity can be done later if needed.
- **gh_repo/regen_worker_url detection**: Moved outside the per-date loop to avoid redundant git calls and to make variables available for the announcements page render.
- **Old announcement CSS removed**: Cleaned up `.announcement-input-panel`, `.btn-generate-announcement` CSS classes that are no longer used.

### Issues Encountered

None. Build test passed with 8 announcement topics across 3 weeks correctly aggregated.
