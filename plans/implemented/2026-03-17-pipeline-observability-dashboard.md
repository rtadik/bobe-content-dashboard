# Plan: Pipeline Observability Dashboard

**Created:** 2026-03-17
**Status:** Implemented
**Request:** Build a visual pipeline status page that shows each phase as a node graph (like n8n), with per-topic drill-down, error details, and run history — for Rut's use only.

---

## Overview

### What This Plan Accomplishes

Instruments `pipeline_runner.py` to emit real-time status updates to a JSON file as it runs. A standalone HTML page reads that JSON and renders a visual node graph showing each pipeline phase (Scrape → Assemble → Content Gen → Image Gen → Finalize → Deploy), per-topic status within each phase, error details, and a history of the last 20 runs. Auto-refreshes every 3 seconds during active runs.

### Why This Matters

Right now pipeline failures are completely silent — Rut only discovers them by manually checking whether images or content are missing in the frontend. This gives him the same visibility n8n would provide (which phase failed, which topic failed, the actual error message) without adding another tool to maintain.

---

## Current State

### Relevant Existing Structure

| File | Relevance |
|------|-----------|
| `scripts/pipeline_runner.py` | Main pipeline orchestrator — 7 phases, sequential content gen, parallel image gen |
| `scripts/pipeline_runner.py:run_pipeline()` | Lines 311–777 — the function to instrument |
| `scripts/pipeline_runner.py:_gen_images_for_topic()` | Lines 634–712 — parallel image gen function |
| `scripts/pipeline_runner.py:run_regen_item()` | Lines 872–1078 — single-topic regen (also needs instrumentation) |
| `admin/index.html` | Existing admin panel — dark theme, design patterns to match |
| `admin/admin.css` | CSS variables and styling to reuse |
| `admin/admin.js` | Auth and GitHub API patterns |
| `scripts/build_static.py` | Static site builder — will NOT include this page (local only) |
| `outputs/` | Where pipeline-status.json will live |

### Gaps or Problems Being Addressed

1. **Zero observability**: Pipeline failures are silent. No logging, no status page, no alerts.
2. **No run history**: Can't see if last week's run succeeded or which topics failed.
3. **No per-topic visibility**: Can't tell which specific topic caused a failure or which phase it failed in.
4. **Debugging requires terminal access**: Must SSH/scroll terminal output to find errors.

---

## Proposed Changes

### Summary of Changes

- Create a `PipelineStatus` class that writes structured JSON status updates during pipeline execution
- Instrument all 6 phases of `pipeline_runner.py` with status writes (phase transitions + per-topic progress)
- Instrument `run_regen_item()` for single-topic regen tracking
- Create `admin/pipeline-status.html` — standalone visual status page with node graph, topic drill-down, and run history
- Create `admin/pipeline-status.css` — styles matching existing admin dark theme
- Create `admin/pipeline-status.js` — JSON polling, node rendering, run history management

### New Files to Create

| File Path | Purpose |
|-----------|---------|
| `scripts/pipeline_status.py` | `PipelineStatus` class — manages status JSON reads/writes, phase transitions, per-topic updates |
| `admin/pipeline-status.html` | Standalone HTML page — node graph + topic detail + run history |
| `admin/pipeline-status.css` | Dark theme styles matching admin panel design language |
| `admin/pipeline-status.js` | Client-side logic — JSON fetch, node rendering, auto-refresh, run selection |

### Files to Modify

| File Path | Changes |
|-----------|---------|
| `scripts/pipeline_runner.py` | Import `PipelineStatus`, call status methods at each phase start/end and per-topic completion |
| `CLAUDE.md` | Add pipeline-status.html to workspace structure, document the feature |

### Files to Delete

None.

---

## Design Decisions

### Key Decisions Made

1. **Standalone HTML page, not part of static build**: This is Rut's admin tool. It reads a local JSON file via fetch. Not deployed to Cloudflare Pages, not accessible to clients. Opened directly in browser from the local filesystem or via a simple `python -m http.server`.

2. **JSON file in `outputs/pipeline-status.json`**: Keeps status data with other output artifacts. Gitignored (already covered by outputs/ patterns). Single file with array of runs (last 20, pruned on each new run).

3. **Separate `PipelineStatus` class in its own module**: Keeps instrumentation logic isolated from pipeline logic. Clean import, minimal changes to pipeline_runner.py. Each phase transition is one method call.

4. **Auto-refresh every 3 seconds during active runs, stop when complete**: Balances responsiveness with filesystem read frequency. Status badge shows "LIVE" during active runs.

5. **6 pipeline nodes matching actual phases**: Scrape → Assemble Buckets → Generate Content → Generate Images → Finalize → Deploy. Maps directly to pipeline_runner.py's run_pipeline() flow. Content gen and image gen nodes expand to show per-topic rows.

6. **Run history stored in same JSON file**: No database needed. Last 20 runs kept. Each run is self-contained with all phase and topic data. Old runs pruned on new pipeline start.

7. **Regen runs tracked separately**: When `run_regen_item()` executes, it creates a mini-run with type "regen" that shows which topic and what regen type (content/image_en/image_ru/content_ru).

8. **Announcement mode runs also tracked**: `--mode announcement` creates a run with type "announcement" showing the announcement-specific phases.

### Alternatives Considered

1. **Trigger.dev**: Would provide built-in visualization but requires migrating pipeline logic to Trigger.dev tasks. More infrastructure, more coupling. Rejected for now — can revisit later.

2. **Airtable-based status log**: Would work but adds API calls mid-pipeline (slowing it down) and requires Airtable to view status. Rejected — local JSON is faster and works offline.

3. **Terminal-only structured logging**: Cheaper to build but requires terminal access to see. Doesn't solve the "I only find out when content is missing" problem. Rejected as insufficient.

4. **WebSocket-based live updates**: More responsive than polling but requires a running server. Over-engineered for a single-user admin tool. Rejected.

### Open Questions

None — all design decisions are self-contained and don't require user input.

---

## Step-by-Step Tasks

### Step 1: Create `PipelineStatus` Module

Create `scripts/pipeline_status.py` — the core status tracking class.

**Design:**

```python
class PipelineStatus:
    """Tracks pipeline run status and writes to JSON file."""

    def __init__(self, client_id, week_of, mode="full", status_file=None):
        # Initialize run record with metadata
        # Load existing runs from JSON, append new run, prune to 20

    def start_phase(self, phase_name):
        # Mark phase as "running", record start time

    def complete_phase(self, phase_name, item_count=None):
        # Mark phase as "success", record end time and item count

    def fail_phase(self, phase_name, error_message):
        # Mark phase as "failed", record error

    def update_topic(self, phase_name, topic_index, topic_name, status, error=None):
        # Update per-topic status within a phase (for content gen and image gen)

    def complete_run(self):
        # Mark entire run as success/failed/partial based on phase statuses

    def fail_run(self, error_message):
        # Mark entire run as failed with top-level error

    def _write(self):
        # Write current state to JSON file (called after every update)

    def _load_runs(self):
        # Load existing runs from JSON file

    def _prune_runs(self, max_runs=20):
        # Keep only the last N runs
```

**JSON schema:**

```json
{
  "runs": [
    {
      "run_id": "2026-03-17T10-30-00_bobe_full",
      "client_id": "bobe",
      "week_of": "2026-03-17",
      "mode": "full",
      "status": "running",
      "started_at": "2026-03-17T10:30:00",
      "finished_at": null,
      "error": null,
      "phases": [
        {
          "name": "Scrape Topics",
          "status": "success",
          "started_at": "2026-03-17T10:30:00",
          "finished_at": "2026-03-17T10:31:15",
          "item_count": 7,
          "error": null,
          "topics": []
        },
        {
          "name": "Assemble Buckets",
          "status": "success",
          "started_at": "2026-03-17T10:31:15",
          "finished_at": "2026-03-17T10:31:16",
          "item_count": 21,
          "error": null,
          "topics": []
        },
        {
          "name": "Generate Content",
          "status": "running",
          "started_at": "2026-03-17T10:31:16",
          "finished_at": null,
          "item_count": null,
          "error": null,
          "topics": [
            {
              "index": 0,
              "name": "DCA Strategy Explained",
              "bucket": "trending",
              "status": "success",
              "error": null,
              "started_at": "2026-03-17T10:31:16",
              "finished_at": "2026-03-17T10:31:45"
            },
            {
              "index": 1,
              "name": "What is Grid Trading",
              "bucket": "education",
              "status": "failed",
              "error": "Gemini API timeout after 30s",
              "started_at": "2026-03-17T10:31:45",
              "finished_at": "2026-03-17T10:32:15"
            }
          ]
        },
        {
          "name": "Generate Images",
          "status": "pending",
          "started_at": null,
          "finished_at": null,
          "item_count": null,
          "error": null,
          "topics": []
        },
        {
          "name": "Finalize",
          "status": "pending",
          "started_at": null,
          "finished_at": null,
          "item_count": null,
          "error": null,
          "topics": []
        },
        {
          "name": "Deploy",
          "status": "pending",
          "started_at": null,
          "finished_at": null,
          "item_count": null,
          "error": null,
          "topics": []
        }
      ]
    }
  ]
}
```

**Actions:**

- Create `scripts/pipeline_status.py` with `PipelineStatus` class
- Status file default path: `outputs/pipeline-status.json`
- Thread-safe writes (use `threading.Lock`) since Phase 5 uses ThreadPoolExecutor
- Each method call triggers an immediate `_write()` to disk so the HTML page sees real-time updates
- `_write()` uses atomic write pattern (write to temp file, then rename) to prevent partial reads

**Files affected:**

- `scripts/pipeline_status.py` (new)

---

### Step 2: Instrument `pipeline_runner.py` — Phase Transitions

Add status tracking calls at each phase boundary in `run_pipeline()`.

**Actions:**

- Import `PipelineStatus` at top of file
- After CLI args are parsed (around line 1539), instantiate: `status = PipelineStatus(client_id, week_of, mode)`
- Pass `status` into `run_pipeline()` as a parameter (add optional `status=None` kwarg)
- Inside `run_pipeline()`, add calls at these points:

```
Phase 1 — Scrape (lines 346–368):
  status.start_phase("Scrape Topics")
  ... existing scrape code ...
  status.complete_phase("Scrape Topics", item_count=len(trending_topics))

Phase 2 — Assemble (lines 370–448):
  status.start_phase("Assemble Buckets")
  ... existing assembly code ...
  status.complete_phase("Assemble Buckets", item_count=len(all_topics))

Phase 3/4 — Content Gen (lines 467–622):
  status.start_phase("Generate Content")
  ... (per-topic instrumentation in Step 3) ...
  status.complete_phase("Generate Content", item_count=success_count)

Phase 5 — Image Gen (lines 624–717):
  status.start_phase("Generate Images")
  ... (per-topic instrumentation in Step 3) ...
  status.complete_phase("Generate Images", item_count=image_count)

Phase 6 — Finalize (lines 719–741):
  status.start_phase("Finalize")
  ... existing finalize code ...
  status.complete_phase("Finalize")

Phase 7 — Deploy (lines 742–758):
  status.start_phase("Deploy")
  ... existing deploy code ...
  status.complete_phase("Deploy")
```

- Wrap each phase in try/except that calls `status.fail_phase()` on error
- At end of `run_pipeline()`, call `status.complete_run()`
- In the outer exception handler, call `status.fail_run(str(e))`

**Files affected:**

- `scripts/pipeline_runner.py`

---

### Step 3: Instrument `pipeline_runner.py` — Per-Topic Progress

Add per-topic status updates inside the content generation loop and image generation function.

**Actions:**

- **Content generation loop** (lines 475–622): Before each topic's Gemini call, add:
  ```python
  status.update_topic("Generate Content", topic_index, topic_name, "running")
  ```
  After successful generation + Airtable write:
  ```python
  status.update_topic("Generate Content", topic_index, topic_name, "success")
  ```
  In the per-topic except block:
  ```python
  status.update_topic("Generate Content", topic_index, topic_name, "failed", error=str(e))
  ```

- **Image generation function** `_gen_images_for_topic()` (lines 634–712): Same pattern but note this runs in threads — `PipelineStatus._write()` must be thread-safe (handled in Step 1 via Lock).
  ```python
  status.update_topic("Generate Images", topic_index, topic_name, "running")
  # ... image gen ...
  status.update_topic("Generate Images", topic_index, topic_name, "success")
  # or on error:
  status.update_topic("Generate Images", topic_index, topic_name, "failed", error=str(e))
  ```

- **Pass `status` to `_gen_images_for_topic()`**: Add it as a parameter. The ThreadPoolExecutor lambda/partial will capture it.

**Files affected:**

- `scripts/pipeline_runner.py`

---

### Step 4: Instrument Regen and Announcement Modes

Track `run_regen_item()` and announcement mode runs.

**Actions:**

- **`run_regen_item()`** (lines 872–1078): Create a status run with `mode="regen"` and a single phase:
  ```python
  status = PipelineStatus(client_id, week_of, mode="regen")
  status.start_phase(f"Regen {regen_type}")
  status.update_topic(f"Regen {regen_type}", topic_index, topic_name, "running")
  # ... regen logic ...
  status.update_topic(f"Regen {regen_type}", topic_index, topic_name, "success")
  status.complete_phase(f"Regen {regen_type}", item_count=1)
  status.complete_run()
  ```

- **Announcement mode** (lines 1254–1526): Create status run with `mode="announcement"` and phases matching the announcement flow (Content → Images → Translation based on `--phase` flag).

**Files affected:**

- `scripts/pipeline_runner.py`

---

### Step 5: Create `admin/pipeline-status.html`

The main status visualization page.

**Structure:**

```html
<!DOCTYPE html>
<html>
<head>
  <title>Pipeline Status</title>
  <link rel="stylesheet" href="pipeline-status.css">
</head>
<body>
  <header>
    <h1>Pipeline Monitor</h1>
    <div class="live-indicator">● LIVE</div>
    <div class="last-updated">Updated: --:--:--</div>
  </header>

  <main>
    <!-- Current/Selected Run Info Bar -->
    <section class="run-info">
      <span class="run-client">bobe</span>
      <span class="run-mode">full</span>
      <span class="run-week">Week of 2026-03-17</span>
      <span class="run-duration">2m 34s</span>
      <span class="run-status-badge">Running</span>
    </section>

    <!-- Node Graph — horizontal flow -->
    <section class="node-graph">
      <!-- 6 phase nodes connected by lines -->
      <div class="node" data-phase="Scrape Topics">
        <div class="node-icon">🔍</div>
        <div class="node-label">Scrape</div>
        <div class="node-status">7 topics</div>
        <div class="node-time">45s</div>
      </div>
      <div class="connector done"></div>
      <div class="node" data-phase="Assemble Buckets">...</div>
      <div class="connector done"></div>
      <div class="node active" data-phase="Generate Content">...</div>
      <div class="connector"></div>
      <div class="node" data-phase="Generate Images">...</div>
      <div class="connector"></div>
      <div class="node" data-phase="Finalize">...</div>
      <div class="connector"></div>
      <div class="node" data-phase="Deploy">...</div>
    </section>

    <!-- Topic Detail Panel — shown when a content/image node is selected -->
    <section class="topic-detail" id="topic-detail">
      <h2>Generate Content — 14/21 complete</h2>
      <div class="topic-grid">
        <!-- Per-topic rows with status indicators -->
        <div class="topic-row success">
          <span class="topic-index">#1</span>
          <span class="topic-bucket trending">Trending</span>
          <span class="topic-name">DCA Strategy Explained</span>
          <span class="topic-status">✓</span>
          <span class="topic-time">29s</span>
        </div>
        <div class="topic-row failed">
          <span class="topic-index">#2</span>
          <span class="topic-bucket education">Education</span>
          <span class="topic-name">What is Grid Trading</span>
          <span class="topic-status">✗</span>
          <span class="topic-time">30s</span>
          <div class="topic-error">Gemini API timeout after 30s</div>
        </div>
        <div class="topic-row running">
          <span class="topic-index">#3</span>
          <span class="topic-bucket announcement">Announcement</span>
          <span class="topic-name">New Feature Launch</span>
          <span class="topic-status">⟳</span>
          <span class="topic-time">12s...</span>
        </div>
        <!-- Pending topics shown as dimmed -->
      </div>
    </section>
  </main>

  <!-- Run History Sidebar -->
  <aside class="run-history">
    <h2>Run History</h2>
    <div class="run-list">
      <!-- Clickable run entries -->
      <div class="run-entry active">
        <span class="run-date">Mar 17, 10:30</span>
        <span class="run-type">full</span>
        <span class="run-result success">✓</span>
      </div>
      <div class="run-entry">
        <span class="run-date">Mar 17, 09:15</span>
        <span class="run-type">regen</span>
        <span class="run-result failed">✗</span>
      </div>
    </div>
  </aside>

  <script src="pipeline-status.js"></script>
</body>
</html>
```

**Actions:**

- Create the HTML file with semantic structure
- No external dependencies (no React, no charting library — pure HTML/CSS/JS)
- Responsive layout: node graph on top, topic detail below, run history as a right sidebar (collapses to bottom on narrow screens)

**Files affected:**

- `admin/pipeline-status.html` (new)

---

### Step 6: Create `admin/pipeline-status.css`

Dark theme matching existing admin panel design language.

**Design specifications:**

- Reuse admin CSS variables: `--bg: #0D1526`, `--primary: #1589DC`, `--accent: #00aaff`, `--success: #5BD69F`, `--warning: #E0C145`, `--error: #FF5A5A`
- System fonts + SF Mono/Fira Code for monospace
- Node states:
  - **Pending**: dim outline, gray fill (`#1a2236`)
  - **Running**: pulsing border animation, blue glow (`--primary`)
  - **Success**: solid green border + fill tint (`--success` at 15% opacity)
  - **Failed**: solid red border + fill tint (`--error` at 15% opacity)
  - **Partial**: solid yellow border + fill tint (`--warning` at 15% opacity)
- Connectors: horizontal lines between nodes, colored based on completion
- Topic rows: alternating subtle backgrounds, bucket badges color-coded (trending=blue, education=green, announcement=orange)
- Run history entries: compact list items, highlight selected run
- Live indicator: pulsing green dot when auto-refresh is active
- Responsive: flexbox layout, nodes wrap to 2 rows on mobile

**Actions:**

- Create `admin/pipeline-status.css` with all styles
- Match the admin panel's visual language closely

**Files affected:**

- `admin/pipeline-status.css` (new)

---

### Step 7: Create `admin/pipeline-status.js`

Client-side logic for the status page.

**Key functions:**

```javascript
// Core
async function fetchStatus()        // GET pipeline-status.json, parse, render
function selectRun(runId)           // Switch displayed run (from history)
function renderNodeGraph(run)       // Draw 6 phase nodes with current statuses
function renderTopicDetail(phase)   // Show per-topic breakdown for selected phase
function renderRunHistory(runs)     // Populate sidebar with clickable run entries

// Auto-refresh
function startPolling()             // setInterval(fetchStatus, 3000) when run is active
function stopPolling()              // clearInterval when run completes
function isRunActive(run)           // Check if status === "running"

// UI helpers
function formatDuration(start, end) // Human-readable duration (e.g., "2m 34s")
function formatTime(iso)            // Format timestamp for display
function getPhaseIcon(phaseName)    // Return icon for each phase type
function getBucketColor(bucket)     // Return color for bucket type
```

**Behavior:**

1. On page load: fetch `outputs/pipeline-status.json`, render latest run, populate history
2. If latest run is active: start polling every 3 seconds, show LIVE indicator
3. Click a node: expand topic detail panel for that phase (only for Content Gen and Image Gen)
4. Click a history entry: switch to that run's data, stop polling if viewing old run
5. When active run completes: stop polling, flash "Complete" notification, update node states
6. If JSON file not found (404): show "No pipeline runs yet" empty state

**Serving the page:**

The page needs to fetch `outputs/pipeline-status.json` via HTTP. Two approaches:

- **Option A (recommended)**: Add a `/pipeline-status` route to `web_viewer.py` (Flask) that serves the admin page and the JSON endpoint. Accessible at `http://localhost:5001/pipeline-status`.
- **Option B**: Run `python -m http.server 8080` from the project root. Page at `http://localhost:8080/admin/pipeline-status.html`.

Going with **Option A** — add a Flask route so it works alongside the existing `/view-content` dashboard. The route serves the HTML page, and a `/api/pipeline-status` endpoint serves the JSON data.

**Actions:**

- Create `admin/pipeline-status.js` with all rendering and polling logic
- Add Flask routes in `web_viewer.py`:
  - `GET /pipeline-status` → serve `admin/pipeline-status.html`
  - `GET /api/pipeline-status` → serve `outputs/pipeline-status.json`

**Files affected:**

- `admin/pipeline-status.js` (new)
- `scripts/web_viewer.py` (add 2 routes)

---

### Step 8: Add Flask Routes to `web_viewer.py`

Add endpoints to serve the pipeline status page and its data.

**Actions:**

- Add route `GET /pipeline-status` that returns `admin/pipeline-status.html` with CSS/JS assets
- Add route `GET /api/pipeline-status` that reads and returns `outputs/pipeline-status.json`
- If JSON doesn't exist yet, return `{"runs": []}` with 200 status
- Static file serving for `admin/pipeline-status.css` and `admin/pipeline-status.js` (Flask already serves static files — may need to add admin/ as a static folder or use send_from_directory)

**Files affected:**

- `scripts/web_viewer.py`

---

### Step 9: Ensure `outputs/pipeline-status.json` is Gitignored

Verify the gitignore already covers this file.

**Actions:**

- Check `.gitignore` for `outputs/` pattern
- If not already covered, add `outputs/pipeline-status.json` to `.gitignore`

**Files affected:**

- `.gitignore` (if needed)

---

### Step 10: Update CLAUDE.md

Document the new feature in the workspace reference.

**Actions:**

- Add `pipeline_status.py` to the Scripts table with description: "Pipeline run status tracker — writes real-time JSON status during pipeline execution"
- Add `admin/pipeline-status.html` to the Workspace Structure section under `admin/`
- Add a note in the "Deployment" section that pipeline status is local-only (not deployed)
- Mention `/pipeline-status` route in the Flask dashboard description

**Files affected:**

- `CLAUDE.md`

---

## Connections & Dependencies

### Files That Reference This Area

| File | Relationship |
|------|-------------|
| `scripts/pipeline_runner.py` | Primary file being instrumented — imports PipelineStatus |
| `scripts/web_viewer.py` | Serves the status page — new routes added |
| `scripts/build_static.py` | NOT affected — status page is local only, not included in static builds |
| `admin/admin.js` | NOT affected — admin panel remains independent |
| `.github/workflows/weekly-pipeline.yml` | Works automatically — pipeline_runner.py writes status JSON whether run locally or via GitHub Actions (though the HTML page only works locally) |

### Updates Needed for Consistency

- CLAUDE.md Scripts table: add `pipeline_status.py`
- CLAUDE.md Workspace Structure: add `admin/pipeline-status.html`, `admin/pipeline-status.css`, `admin/pipeline-status.js`
- CLAUDE.md: note the `/pipeline-status` route on `web_viewer.py`

### Impact on Existing Workflows

- **pipeline_runner.py**: Minimal impact. Status calls are additive — they don't change existing logic. If PipelineStatus fails, the pipeline continues (all status calls wrapped in try/except to be non-blocking).
- **run_regen_item()**: Same — additive status tracking.
- **web_viewer.py**: Two new routes added. No existing routes affected.
- **GitHub Actions runs**: Status JSON will be written to the runner's filesystem but won't be accessible from the local HTML page. This is fine — the status page is designed for local pipeline runs. GitHub Actions status is already visible in GitHub's UI.

---

## Validation Checklist

- [ ] `python scripts/pipeline_runner.py --client bobe --week-of 2026-03-17 --mock` creates `outputs/pipeline-status.json` with correct structure
- [ ] Status JSON updates in real-time during pipeline execution (check timestamps, per-topic progress)
- [ ] `python scripts/web_viewer.py` starts Flask server and `/pipeline-status` loads the HTML page
- [ ] Node graph renders 6 phases with correct status colors (pending/running/success/failed)
- [ ] Clicking "Generate Content" or "Generate Images" node shows per-topic breakdown
- [ ] Auto-refresh works: page updates every 3 seconds during active run, stops when complete
- [ ] Run history shows last N runs, clicking a run switches the view
- [ ] Regen runs (`--regen-topic`) create separate entries in run history
- [ ] Thread-safe: image gen phase (ThreadPoolExecutor) doesn't corrupt the JSON file
- [ ] Pipeline still works correctly if `outputs/pipeline-status.json` is deleted or missing
- [ ] Status tracking is non-blocking: if PipelineStatus throws, pipeline continues normally
- [ ] CLAUDE.md updated with new files and routes

---

## Success Criteria

The implementation is complete when:

1. Running `pipeline_runner.py` (any mode: full, announcement, regen) automatically writes real-time status to `outputs/pipeline-status.json`
2. Opening `http://localhost:5001/pipeline-status` shows a visual node graph with phase statuses, per-topic drill-down, error messages, and run history
3. The status page auto-refreshes during active runs and stops when the run completes
4. Existing pipeline behavior is completely unchanged — status tracking is additive and non-blocking

---

## Notes

- **Future enhancement**: Could add browser notifications when a run completes or fails (using Notification API). Not in scope for v1.
- **Future enhancement**: Could add a "Trigger Run" button on the status page (POST to Flask to start pipeline_runner.py as subprocess). Not in scope for v1 — run triggering stays in terminal or admin panel.
- **Future enhancement**: If Trigger.dev is adopted later, the status JSON format could be adapted to also receive webhook updates from Trigger.dev runs, giving a unified view.
- **GitHub Actions runs**: The status page won't show GitHub Actions runs since the JSON is local. GitHub's own run UI covers that. If needed later, we could add a GitHub API polling mode to the status page.

---

## Implementation Notes

**Implemented:** 2026-03-18

### Summary

- Created `scripts/pipeline_status.py` with thread-safe `PipelineStatus` class (atomic JSON writes, threading.Lock)
- Instrumented all 6 phases of `run_pipeline()` with start/complete/fail tracking
- Added per-topic progress tracking in Phase 4 (content gen) and Phase 5 (image gen)
- Instrumented regen mode, announcement mode, content-only mode, and images-approved mode
- Created `admin/pipeline-status.html` + CSS + JS with visual node graph, topic drill-down, and run history
- Added 4 Flask routes to `web_viewer.py`: `/pipeline-status`, `/pipeline-status.css`, `/pipeline-status.js`, `/api/pipeline-status`
- Added `outputs/pipeline-status.json` to `.gitignore`
- Updated CLAUDE.md with new files, routes, and implemented plan entry

### Deviations from Plan

- Added `skip_phase()` method to PipelineStatus (not in original plan) for cleaner handling of skipped phases (--skip-images, --skip-deploy, mock mode)
- Slow background polling (10s) added even when no active run, to detect new runs starting

### Issues Encountered

None.
