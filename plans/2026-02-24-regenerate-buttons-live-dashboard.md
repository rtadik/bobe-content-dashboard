# Plan: Regenerate Buttons + Approve-to-RU Flow — Local & Live Dashboard

**Created:** 2026-02-24
**Status:** Implemented
**Request:** Add regenerate content + image buttons to local Flask dashboard and the live GitHub Pages static dashboard. Clicking Approve on an EN image auto-switches the view to RU. Clients logged into the live site can regenerate items directly without needing the local dashboard. RU regenerate buttons are locked (disabled, with a lock icon) until EN is approved — approving EN unlocks them; removing EN approval re-locks them.

---

## Overview

### What This Plan Accomplishes

Adds per-topic regeneration capabilities to both the local Flask dashboard and the live GitHub Pages static site: (1) a "Regenerate Content" button to re-generate Twitter/Telegram copy for any topic, (2) existing regenerate-image buttons confirmed present locally, (3) an "Approve EN → auto-switch to RU → unlock RU regen buttons" UX flow, and (4) full parity on the live static dashboard using a new GitHub Actions workflow that runs targeted regeneration and redeploys. RU regenerate buttons (image and content) are locked with a lock icon until EN is approved per topic; approving EN unlocks them and removing EN approval re-locks them.

### Why This Matters

Clients currently must ask Rut to run scripts locally to tweak any generated item. With these changes, a logged-in client on the live dashboard can self-serve — regenerate an image or text that doesn't land right, approve EN content and be automatically prompted to review the Russian version, all without touching local tooling.

---

## Current State

### Relevant Existing Structure

**Local Flask (`scripts/web_viewer.py`)**
- `regenImage(idx)` JS + `/api/regenerate` POST endpoint — EN image regeneration ✓
- `regenRuImage(idx)` JS + `/api/regenerate-ru` POST endpoint — RU image regeneration ✓
- `approveImage(idx)` JS + `/api/approve` POST endpoint — EN image approval ✓
- `generateRussian(idx)` JS + `/api/generate-ru` POST endpoint — generate RU text ✓
- **MISSING:** `/api/regenerate-content` endpoint — no way to regenerate EN Twitter/Telegram text
- **MISSING:** Approve EN → auto-switch to RU language toggle
- **MISSING:** "Regenerate Content" button in the card HTML

**Static Site (`scripts/build_static.py`) — `STATIC_HTML` template**
- Shows EN/RU content and images ✓
- Language toggle (EN/RU) ✓
- Copy buttons ✓
- **MISSING:** All regeneration buttons (image + content)
- **MISSING:** Approve button
- **MISSING:** Any interactivity beyond copy/lightbox/lang toggle

**GitHub Actions (`.github/workflows/`)**
- `weekly-pipeline.yml` — full pipeline run ✓
- `onboard-client.yml` — client onboarding ✓
- **MISSING:** `regenerate-item.yml` — single-topic targeted regeneration

### Gaps or Problems Being Addressed

- Local dashboard has image regen but no text/content regen
- No UX flow for "review EN then switch to RU" after approving
- RU regenerate buttons are always enabled — there is no approval gate enforcing EN review before touching Russian content
- Static live dashboard is purely read-only — clients cannot regenerate anything
- No GitHub Actions workflow exists for targeted single-item regeneration

---

## Proposed Changes

### Summary of Changes

- Add `POST /api/regenerate-content` Flask route (regenerates EN Twitter + Telegram text via Gemini, updates Excel)
- Add "Regenerate Content" button + loading state to each card in `web_viewer.py` HTML
- Add "Approve EN → auto-switch to RU → unlock RU regen buttons" behavior in both local and static templates
- **RU regenerate buttons (image + content) start locked** (disabled + lock icon) on every card; they unlock only when EN is approved for that topic
- Removing EN approval re-locks the RU regenerate buttons
- Add regeneration UI (image + content) to `STATIC_HTML` in `build_static.py`, using GitHub Actions as the backend
- Create `.github/workflows/regenerate-item.yml` — targeted single-topic regen (image_en / image_ru / content)
- Add GitHub token auth flow to static dashboard (sessionStorage, one-time entry per session)
- Add run-status polling to static dashboard for GH Actions regen jobs

### New Files to Create

| File Path | Purpose |
|-----------|---------|
| `.github/workflows/regenerate-item.yml` | New GH Actions workflow: targeted single-topic regeneration (image EN, image RU, or content), rebuilds + deploys static site |

### Files to Modify

| File Path | Changes |
|-----------|---------|
| `scripts/web_viewer.py` | Add `/api/regenerate-content` route; add "Regenerate Content" button + JS to HTML template; add approve-EN → auto-switch-to-RU JS behavior |
| `scripts/build_static.py` | Add regen image + content buttons to `STATIC_HTML`; add GitHub token prompt UI; add GH Actions API call + polling JS; add approve-EN → switch-to-RU behavior |
| `CLAUDE.md` | Add `regenerate-item.yml` to workflow table; note static dashboard regeneration capability |

### Files to Delete (if any)

None.

---

## Design Decisions

### Key Decisions Made

1. **Static site uses GitHub Actions as the regen backend**: GitHub Pages is static and cannot call a local Python API. The existing admin panel already uses GH Actions API calls via a stored token. We extend the same pattern to the client dashboard. The client enters a "Regeneration Token" (GitHub PAT with `actions:write` scope) once per session; it is stored in sessionStorage.

2. **GitHub token prompt is non-blocking**: Regen buttons are always visible on the static site. On first click, if no token is stored, a modal prompts the user to enter one. The token is stored in sessionStorage (cleared on tab close, never in localStorage). After entering the token, the regeneration proceeds immediately.

3. **Content regen uses Gemini (same as RU translation)**: The existing `generate-ru` flow already calls `weekly_pipeline.translate_text_to_russian`. For EN content regen, we call Gemini with the content guidelines and topic, then save back to Excel. We reuse the `HAS_RU_GENERATOR` flag (which checks for Gemini availability) since it's the same dependency.

4. **Approve EN → auto-switch to RU → unlock RU regen is purely JS**: No backend call needed. After the `approveImage()` POST succeeds, the JS: (a) calls `setLang('ru')` to switch to RU view, and (b) calls `updateRuRegenState(idx)` to enable the RU regen buttons for that card. Removing approval calls the same function to re-lock them. This works in both Flask and static site.

5. **RU regen buttons show a lock icon when locked**: The button text is `🔒 Regenerate` when EN is not approved, with `disabled` attribute and reduced opacity. When EN is approved, the lock disappears and the button becomes `↻ Regenerate`. The lock state is per-card and tracked alongside the approval state.

6. **Regenerate-item workflow rebuilds full static site**: Rather than a partial update, the `regenerate-item.yml` workflow re-runs the targeted regen script, then runs `build_static.py` and redeploys to `gh-pages`. This keeps the deployment simple and consistent with the existing pipeline.

7. **Static site EN regen buttons are always enabled; RU regen buttons start locked**: EN image regen and EN content regen are available immediately. RU image regen is locked until EN is approved. This mirrors the existing `generateRussian()` flow in the Flask dashboard which already gates RU generation behind EN approval.

8. **One new GH Actions workflow, three regen types**: `regenerate-item.yml` accepts `regen_type` input: `image_en`, `image_ru`, or `content`. Each runs the appropriate script with `--topic-index` flag. This avoids separate workflows for each operation.

9. **New `pipeline_runner.py` flag `--regen-topic`**: Rather than building regen logic into the workflow script itself, we add a `--regen-topic INDEX --regen-type TYPE` flag to `pipeline_runner.py` which handles targeted regeneration, Excel update, and static rebuild.

### Alternatives Considered

- **Serverless proxy (Cloudflare Worker)**: Would avoid exposing GitHub token to clients, but adds new infrastructure and ongoing maintenance. Rejected — overkill for a small multi-client tool.
- **Pre-baked token in static HTML**: Hardcode a limited-scope GitHub token in the static site so clients don't need to enter anything. Rejected — security risk even with limited scope; token would be visible in source.
- **Regeneration via Airtable webhook**: Use Airtable to trigger regeneration. Rejected — not all clients use Airtable, and adds complexity.

### Open Questions (if any)

None — all design decisions are resolved. Implementation can proceed.

---

## Step-by-Step Tasks

### Step 1: Add `/api/regenerate-content` Flask route to `web_viewer.py`

Add a new async Flask endpoint that regenerates EN Twitter and Telegram content for a topic using Gemini, writes the result back to the Excel workbook, and returns a job ID for polling.

The endpoint follows the same async job pattern as `/api/regenerate` (starts a background thread, returns `job_id`, client polls `/api/regen-status/<job_id>`).

**Actions:**

- Read `scripts/web_viewer.py` lines around `@app.route("/api/generate-ru", methods=["POST"])` (line ~2482) to understand the async job pattern
- After the `/api/regenerate-ru` route (line ~2626), add a new route:

```python
@app.route("/api/regenerate-content", methods=["POST"])
def api_regenerate_content():
    """Regenerate EN Twitter + Telegram content for a topic using Gemini."""
    if not HAS_RU_GENERATOR:
        return jsonify({"success": False, "error": "Gemini not available"}), 503

    data = request.get_json(force=True)
    topic_index = data.get("topic_index")
    date = data.get("date", "")

    if topic_index is None:
        return jsonify({"success": False, "error": "topic_index required"}), 400

    xlsx = find_excel(date)
    if not xlsx:
        return jsonify({"success": False, "error": f"No workbook for date '{date}'"}), 404

    topics = load_content(xlsx)
    if topic_index < 0 or topic_index >= len(topics):
        return jsonify({"success": False, "error": "topic_index out of range"}), 400

    topic_data = topics[topic_index]

    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {"status": "running", "error": None, "content": None}

    def _do_regen():
        try:
            from weekly_pipeline import regenerate_topic_content
            result = regenerate_topic_content(
                xlsx_path=str(xlsx),
                topic_index=topic_index,
                client_id=_active_client,
            )
            with _jobs_lock:
                _jobs[job_id] = {"status": "done", "content": result, "error": None}
        except Exception as exc:
            with _jobs_lock:
                _jobs[job_id] = {"status": "error", "error": str(exc), "content": None}

    threading.Thread(target=_do_regen, daemon=True).start()
    return jsonify({"success": True, "job_id": job_id})
```

- Add `/api/content-regen-status/<job_id>` polling route (same pattern as `/api/regen-status/<job_id>`):

```python
@app.route("/api/content-regen-status/<job_id>")
def api_content_regen_status(job_id):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return jsonify({"status": "error", "error": "Unknown job"}), 404
    return jsonify(job)
```

**Files affected:**
- `scripts/web_viewer.py`

---

### Step 2: Add `regenerate_topic_content()` to `weekly_pipeline.py`

Add a new function to `scripts/weekly_pipeline.py` that regenerates EN Twitter + Telegram content for a specific topic row in the Excel workbook.

**Actions:**

- Read `scripts/weekly_pipeline.py` to understand how content is generated and how `append_content_row` / `update_ru_columns` work
- Add a new function `regenerate_topic_content(xlsx_path, topic_index, client_id)` that:
  1. Loads the Excel workbook
  2. Reads the topic name, date, day, platform rows for the given topic_index (rows = topic_index * 2 + 2 for Twitter and topic_index * 2 + 3 for Telegram, since topics are 2 rows each)
  3. Calls Gemini with the content guidelines to regenerate Twitter thread + Telegram post
  4. Writes the new content back to the Content sheet cells (column F = Content)
  5. Saves the workbook
  6. Returns `{"twitter": "...", "telegram": "..."}`

The Gemini prompt should load from `clients/{client_id}/content-guidelines.md` for brand-consistent output.

**Files affected:**
- `scripts/weekly_pipeline.py`

---

### Step 3: Add "Regenerate Content" button + RU locked regen buttons to Flask dashboard HTML

In `web_viewer.py`'s `HTML` string:
- Add "↻ Regen Content" button visible in EN mode only (like the image regen button)
- Add "🔒 Regenerate" RU image button in the RU image action bar, locked by default
- Add "🔒 Regen RU Content" button in RU mode on the card body, locked by default
- The existing `regen-ru-btn` for RU image regeneration already exists in the HTML — update it to start locked

**Actions:**

- In the card body, add a content-actions bar with a "↻ Regen Content" button per card (EN only):

```html
<!-- Content regen bar (EN only, local Flask) -->
<div class="content-regen-bar en-only" id="content-regen-bar-{{ loop.index }}">
  <span class="content-regen-label" id="content-regen-label-{{ loop.index }}">EN content</span>
  <button class="action-btn regen-btn" id="content-regen-btn-{{ loop.index }}"
          onclick="regenContent({{ loop.index }})">↻ Regen Content</button>
</div>
```

- In the card body, add a RU content regen bar (RU only), locked by default:

```html
<!-- RU content regen bar (RU only, local Flask) -->
<div class="content-regen-bar ru-only" id="ru-content-regen-bar-{{ loop.index }}">
  <span class="content-regen-label" id="ru-content-regen-label-{{ loop.index }}">RU content</span>
  <button class="action-btn regen-btn" id="ru-content-regen-btn-{{ loop.index }}"
          onclick="regenRuContent({{ loop.index }})"
          disabled title="Approve EN content first">🔒 Regen RU Content</button>
</div>
```

- Update the **existing** RU image action bar in the HTML — the existing `regen-ru-{{ loop.index }}` button should start locked:

```html
<!-- RU image actions (already exists — update the button) -->
<div class="image-actions ru-only">
  <span class="img-status" style="font-size:0.72rem;color:var(--muted)">
    {% if t.image_filename_ru %}RU image{% else %}No RU image{% endif %}
  </span>
  <button class="action-btn regen-btn" id="regen-ru-{{ loop.index }}"
          onclick="regenRuImage({{ loop.index }})"
          disabled title="Approve EN content first">🔒 Regenerate</button>
</div>
```

- Place both content regen bars between the topic title and the platform tab-bar in the card body

- Add CSS for `.content-regen-bar` (a slim horizontal bar, same style as `.image-actions`):

```css
.content-regen-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
}
.content-regen-label {
  flex: 1;
  font-size: 0.72rem;
  color: var(--muted);
}
```

- Add a `updateRuRegenState(idx, isApproved)` JS helper that locks/unlocks all RU regen buttons for a card:

```javascript
function updateRuRegenState(idx, isApproved) {
  // RU image regen button
  const ruImgBtn = document.getElementById(`regen-ru-${idx}`);
  // RU content regen button
  const ruContentBtn = document.getElementById(`ru-content-regen-btn-${idx}`);

  [ruImgBtn, ruContentBtn].forEach(btn => {
    if (!btn) return;
    if (isApproved) {
      btn.disabled = false;
      btn.title = '';
      // Replace lock icon with regen icon if present
      btn.textContent = btn.textContent.replace('🔒 ', '↻ ');
    } else {
      btn.disabled = true;
      btn.title = 'Approve EN content first';
      // Add lock icon if not already present
      if (!btn.textContent.startsWith('🔒')) {
        btn.textContent = '🔒 ' + btn.textContent.replace('↻ ', '');
      }
    }
  });
}
```

- Also add a `/api/regenerate-ru-content` endpoint (same pattern as `/api/regenerate-content` but calls the RU translation pipeline for text only) and a `regenRuContent(idx)` JS function matching the `regenContent(idx)` pattern

- Add JS function `regenContent(idx)`:

```javascript
async function regenContent(idx) {
  if (!HAS_RU_GENERATOR) {
    showToast('Content generator not available (Gemini)', true);
    return;
  }
  const t = TOPICS[idx - 1];
  const btn = document.getElementById(`content-regen-btn-${idx}`);
  const label = document.getElementById(`content-regen-label-${idx}`);
  btn.disabled = true;
  btn.textContent = 'Regenerating...';
  label.textContent = 'Calling Gemini...';

  try {
    const startRes = await fetch('/api/regenerate-content', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date: CURRENT_DATE, topic_index: idx - 1 }),
    });
    const startData = await startRes.json();
    if (!startData.success) {
      showToast('Could not start: ' + (startData.error || 'Unknown'), true);
      btn.disabled = false; btn.textContent = '↻ Regen Content';
      label.textContent = 'EN content';
      return;
    }
    const jobId = startData.job_id;
    // Poll
    const deadline = Date.now() + 120000;
    let result = null;
    while (Date.now() < deadline) {
      await new Promise(r => setTimeout(r, 2500));
      const res = await fetch(`/api/content-regen-status/${jobId}`);
      const data = await res.json();
      if (data.status === 'done' || data.status === 'error') { result = data; break; }
    }
    if (result && result.status === 'done') {
      showToast('Content regenerated. Reloading...');
      setTimeout(() => location.reload(), 1200);
    } else {
      showToast('Regeneration failed: ' + (result?.error || 'Timeout'), true);
      btn.disabled = false; btn.textContent = '↻ Regen Content';
      label.textContent = 'EN content';
    }
  } catch (e) {
    showToast('Error: ' + e.message, true);
    btn.disabled = false; btn.textContent = '↻ Regen Content';
    label.textContent = 'EN content';
  }
}
```

**Files affected:**
- `scripts/web_viewer.py`

---

### Step 4: Add Approve EN → auto-switch to RU → lock/unlock RU regen buttons in Flask dashboard

After the approval POST succeeds in `approveImage()`, (a) switch language to RU and (b) call `updateRuRegenState()` to lock or unlock RU regen buttons for that card. Removing approval re-locks them.

**Actions:**

- In `web_viewer.py`'s `approveImage()` JS function, replace the existing `showToast(...)` line with:

```javascript
setApprovalUI(idx, newStatus);
updateRuRegenState(idx, newStatus === 'approved');

if (newStatus === 'approved') {
  setLang('ru');
  showToast('EN approved — RU controls unlocked');
} else {
  showToast('Approval removed — RU controls locked');
}
```

- On page load, restore lock state from existing approvals (the `loadApprovals()` call already runs on load — extend its callback to also call `updateRuRegenState(idx, isApproved)` for each topic after restoring approval UI):

```javascript
async function loadApprovals() {
  try {
    const res  = await fetch(`/api/approvals?date=${encodeURIComponent(CURRENT_DATE)}`);
    const data = await res.json();
    TOPICS.forEach((t, i) => {
      const entry = data[t.topic];
      const isApproved = entry && entry.status === 'approved';
      if (entry) setApprovalUI(i + 1, entry.status);
      updateRuRegenState(i + 1, isApproved);  // ← ADD THIS
      updateRuGenButton(i + 1);
    });
  } catch (e) {
    console.warn('Could not load approvals:', e);
    // Still initialise lock state (all locked on load if approvals unavailable)
    TOPICS.forEach((_, i) => updateRuRegenState(i + 1, false));
  }
}
```

- Ensure `updateRuRegenState()` is defined before `loadApprovals()` in the script

**Files affected:**
- `scripts/web_viewer.py`

---

### Step 5: Create `.github/workflows/regenerate-item.yml`

New GitHub Actions workflow that accepts single-topic regeneration parameters, runs the targeted script, rebuilds the static site, and deploys.

**Actions:**

Create `.github/workflows/regenerate-item.yml` with:

```yaml
name: Regenerate Single Item

on:
  workflow_dispatch:
    inputs:
      client_id:
        description: 'Client ID (e.g. bobe)'
        required: true
        default: 'bobe'
      week_of:
        description: 'Week start date YYYY-MM-DD'
        required: true
      topic_index:
        description: 'Topic index (0-based, 0-20)'
        required: true
        default: '0'
      regen_type:
        description: 'What to regenerate'
        type: choice
        options:
          - image_en
          - image_ru
          - content
        required: true
        default: 'image_en'

jobs:
  regenerate:
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

      - name: Regenerate item
        run: |
          python scripts/pipeline_runner.py \
            --client ${{ github.event.inputs.client_id }} \
            --week-of ${{ github.event.inputs.week_of }} \
            --regen-topic ${{ github.event.inputs.topic_index }} \
            --regen-type ${{ github.event.inputs.regen_type }} \
            --skip-deploy

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
          git commit -m "Regen item: client=${{ github.event.inputs.client_id }} topic=${{ github.event.inputs.topic_index }} type=${{ github.event.inputs.regen_type }}"
          git push -f https://x-access-token:${{ secrets.GITHUB_TOKEN }}@github.com/rtadik/bobe-content-dashboard.git HEAD:gh-pages
          cd ..
```

**Files affected:**
- `.github/workflows/regenerate-item.yml` (new file)

---

### Step 6: Add `--regen-topic` / `--regen-type` flags to `pipeline_runner.py`

Extend `pipeline_runner.py` to accept targeted regeneration arguments. When `--regen-topic` is provided, skip the full pipeline and run only the targeted regeneration step.

**Actions:**

- Read `scripts/pipeline_runner.py` to understand its current CLI argument parsing
- Add `--regen-topic INT` and `--regen-type {image_en,image_ru,content}` arguments
- In `main()`, if `regen_topic` is set, branch to a new `run_regen_item()` function instead of the full pipeline:

```python
def run_regen_item(client_id, week_of, topic_index, regen_type, mock=False):
    """Regenerate a single item (image EN/RU or content) for a topic."""
    from weekly_pipeline import regenerate_topic_content
    # Determine week_of (default to current Monday if not given)
    if not week_of:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_of = week_start.strftime("%Y-%m-%d")

    output_dir = get_output_dir(client_id)
    xlsx_path = output_dir / f"{week_of}-weekly-content.xlsx"

    if not xlsx_path.exists():
        print(f"ERROR: Workbook not found: {xlsx_path}")
        sys.exit(1)

    if regen_type == "content":
        print(f"Regenerating EN content for topic index {topic_index}...")
        result = regenerate_topic_content(str(xlsx_path), topic_index, client_id, mock=mock)
        print(f"  Done: {result}")

    elif regen_type == "image_en":
        print(f"Regenerating EN image for topic index {topic_index}...")
        # Load topic data from workbook, call nano_banana
        from web_viewer import load_content
        topics = load_content(xlsx_path)
        if topic_index >= len(topics):
            print(f"ERROR: topic_index {topic_index} out of range (max {len(topics)-1})")
            sys.exit(1)
        t = topics[topic_index]
        images_dir = output_dir / "images" / f"{week_of}-weekly"
        images_dir.mkdir(parents=True, exist_ok=True)
        topic_slug = re.sub(r"[^a-z0-9]+", "_", t["topic"].lower())[:30].strip("_")
        platform = "twitter" if t.get("twitter") else "telegram"
        out_path = images_dir / f"{week_of}_{topic_slug}_{platform}.png"

        if not mock:
            import subprocess
            result = subprocess.run([
                "python", "scripts/nano_banana.py",
                "--prompt", t.get("img_prompt", t["topic"]),
                "--output", str(out_path),
                "--client", client_id,
            ], capture_output=True, text=True)
            print(result.stdout)
            if result.returncode != 0:
                print(f"ERROR: {result.stderr}")
                sys.exit(1)
        print(f"  EN image saved: {out_path}")

    elif regen_type == "image_ru":
        print(f"Regenerating RU image for topic index {topic_index}...")
        from web_viewer import load_content
        topics = load_content(xlsx_path)
        if topic_index >= len(topics):
            print(f"ERROR: topic_index {topic_index} out of range")
            sys.exit(1)
        t = topics[topic_index]
        images_dir = output_dir / "images" / f"{week_of}-weekly"
        images_dir.mkdir(parents=True, exist_ok=True)
        topic_slug = re.sub(r"[^a-z0-9]+", "_", t["topic"].lower())[:30].strip("_")
        platform = "twitter" if t.get("twitter_ru") else "telegram"
        out_path = images_dir / f"{week_of}_{topic_slug}_{platform}_ru.png"

        if not mock:
            import subprocess
            result = subprocess.run([
                "python", "scripts/wavespeed_img.py",
                "--prompt", t.get("img_prompt_ru", t.get("img_prompt", t["topic"])),
                "--output", str(out_path),
                "--client", client_id,
            ], capture_output=True, text=True)
            print(result.stdout)
            if result.returncode != 0:
                print(f"ERROR: {result.stderr}")
                sys.exit(1)
        print(f"  RU image saved: {out_path}")
```

**Files affected:**
- `scripts/pipeline_runner.py`

---

### Step 7: Update `STATIC_HTML` in `build_static.py` — add regen buttons and GH Actions UI

This is the largest change. Update the `STATIC_HTML` template in `build_static.py` to add:

1. **GitHub token modal** — Appears when any regen button is clicked and no token is stored. Simple modal with a password field and "Save Token" button.
2. **Regenerate Image buttons** — Below each image (EN and RU), styled like Flask dashboard
3. **Regenerate Content button** — In the card body, before platform tabs
4. **Approve button** — On EN image action bar (moves approval state to sessionStorage for static site)
5. **Approve → auto-switch to RU** — Same JS behavior as Flask
6. **GH Actions polling** — After triggering a regen workflow, shows a progress indicator and polls for completion using the GitHub API

**Actions:**

Add to `STATIC_HTML` CSS (after existing lightbox styles):

```css
/* Regen & approve action bar */
.image-actions {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; background: #0A1221;
  border-bottom: 1px solid var(--border); min-height: 40px;
}
.img-status { flex: 1; font-size: 0.72rem; color: var(--muted); }
.img-status.approved { color: var(--green); font-weight: 500; }
.action-btn {
  border: 1px solid transparent; padding: 4px 12px; border-radius: 7px;
  cursor: pointer; font-size: 0.75rem; font-weight: 500;
  transition: all 0.15s; white-space: nowrap; font-family: inherit;
}
.action-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.approve-btn {
  background: var(--green-dim); border-color: rgba(91,214,159,0.25); color: var(--green);
}
.approve-btn.approved { background: var(--green); border-color: var(--green); color: #0D1526; }
.regen-btn {
  background: rgba(255,79,218,0.07); border-color: rgba(255,79,218,0.2); color: var(--pink);
}
.regen-btn:hover:not(:disabled) { background: rgba(255,79,218,0.14); border-color: rgba(255,79,218,0.35); }

/* Content regen bar */
.content-regen-bar {
  display: flex; align-items: center; gap: 8px; padding: 6px 0;
}
.content-regen-label { flex: 1; font-size: 0.72rem; color: var(--muted); }

/* Loading overlay on image */
.img-loading-overlay {
  position: absolute; inset: 0; background: rgba(13,21,38,0.88);
  display: none; align-items: center; justify-content: center;
  flex-direction: column; gap: 12px; z-index: 10;
}
.img-loading-overlay.active { display: flex; }
.spinner {
  width: 32px; height: 32px;
  border: 3px solid rgba(21,137,220,0.2); border-top-color: var(--blue);
  border-radius: 50%; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.spinner-label { font-size: 0.72rem; color: var(--muted); }

/* GitHub token modal */
#gh-token-modal {
  display: none; position: fixed; inset: 0; background: rgba(8,15,30,0.9);
  z-index: 2000; align-items: center; justify-content: center; padding: 20px;
}
#gh-token-modal.open { display: flex; }
.modal-box {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 14px; padding: 28px 28px; max-width: 380px; width: 100%;
  display: flex; flex-direction: column; gap: 16px;
}
.modal-title { font-size: 1rem; font-weight: 700; }
.modal-sub { font-size: 0.78rem; color: var(--muted); line-height: 1.55; }
.modal-sub a { color: var(--blue); }
.modal-input {
  background: #0A1221; border: 1px solid var(--border);
  color: #fff; padding: 10px 12px; border-radius: 8px;
  font-size: 0.85rem; font-family: monospace; width: 100%; outline: none;
}
.modal-input:focus { border-color: var(--blue); }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; }
.modal-cancel { background: none; border: 1px solid var(--border); color: var(--muted);
  padding: 7px 16px; border-radius: 7px; cursor: pointer; font-size: 0.8rem; font-family: inherit; }
.modal-save { background: var(--blue); border: none; color: #fff;
  padding: 7px 20px; border-radius: 7px; cursor: pointer; font-size: 0.8rem;
  font-weight: 600; font-family: inherit; }

/* Regen status banner */
#regen-status-bar {
  position: fixed; bottom: 0; left: 0; right: 0;
  background: #0A1221; border-top: 1px solid var(--border);
  padding: 10px 24px; display: none; align-items: center; gap: 12px; z-index: 300;
}
#regen-status-bar.show { display: flex; }
.regen-status-label { flex: 1; font-size: 0.82rem; color: var(--text); }
#regen-status-cancel { background: none; border: 1px solid var(--border); color: var(--muted);
  padding: 5px 12px; border-radius: 7px; cursor: pointer; font-size: 0.75rem; font-family: inherit; }
```

Add to card HTML (in `STATIC_HTML` for each topic in `{% for t in topics %}`):

After the EN image div and before RU image div, add an EN image action bar:
```html
<!-- EN image action bar -->
<div class="image-actions en-only">
  <span class="img-status" id="status-{{ loop.index }}">Pending review</span>
  <button class="action-btn approve-btn" id="approve-{{ loop.index }}"
          onclick="approveImage({{ loop.index }})">✓ Approve</button>
  <button class="action-btn regen-btn"
          onclick="triggerRegen({{ loop.index }}, 'image_en')">↻ Regen Image</button>
</div>
```

After the RU image div, add RU image action bar — button starts locked:
```html
<!-- RU image action bar -->
<div class="image-actions ru-only">
  <span class="img-status" style="font-size:0.72rem;color:var(--muted)">
    {% if t.image_filename_ru %}RU image{% else %}No RU image{% endif %}
  </span>
  <button class="action-btn regen-btn" id="ru-img-regen-{{ loop.index }}"
          onclick="triggerRegen({{ loop.index }}, 'image_ru')"
          disabled title="Approve EN content first">🔒 Regen RU Image</button>
</div>
```

Add loading overlays to both EN and RU image divs (same as Flask):
```html
<div class="img-loading-overlay" id="overlay-{{ loop.index }}">
  <div class="spinner"></div>
  <span class="spinner-label">Generating...</span>
</div>
```

In card-body, before platform tabs, add content regen bars — EN always enabled, RU starts locked:
```html
<!-- EN content regen (always enabled) -->
<div class="content-regen-bar en-only">
  <span class="content-regen-label">EN content</span>
  <button class="action-btn regen-btn" onclick="triggerRegen({{ loop.index }}, 'content')">↻ Regen Content</button>
</div>
<!-- RU content regen (locked until EN approved) -->
<div class="content-regen-bar ru-only">
  <span class="content-regen-label">RU content</span>
  <button class="action-btn regen-btn" id="ru-content-regen-{{ loop.index }}"
          onclick="triggerRegen({{ loop.index }}, 'content_ru')"
          disabled title="Approve EN content first">🔒 Regen RU Content</button>
</div>
```

Also add `content_ru` to the `regen_type` choice options in `regenerate-item.yml` (Step 5) and handle it in `pipeline_runner.py` (Step 6) to regenerate RU text only.

Add the GitHub token modal and status bar just before `</body>`:
```html
<!-- GitHub token modal -->
<div id="gh-token-modal">
  <div class="modal-box">
    <div class="modal-title">Connect GitHub to Regenerate</div>
    <div class="modal-sub">
      Enter a GitHub Personal Access Token with <strong>Actions: write</strong> permission.
      This is stored only for this session and cleared when you close the tab.
      <br><br>
      Ask your account manager for the token if you don't have one.
    </div>
    <input type="password" class="modal-input" id="gh-token-input" placeholder="ghp_xxxxxxxxxxxx">
    <div class="modal-actions">
      <button class="modal-cancel" onclick="cancelGhModal()">Cancel</button>
      <button class="modal-save" onclick="saveGhToken()">Save &amp; Continue</button>
    </div>
  </div>
</div>

<!-- Regen status bar -->
<div id="regen-status-bar">
  <div class="spinner" style="width:18px;height:18px;border-width:2px"></div>
  <span class="regen-status-label" id="regen-status-label">Triggering regeneration...</span>
  <button id="regen-status-cancel" onclick="dismissRegenStatus()">Dismiss</button>
</div>
```

Add JavaScript block after existing lightbox JS in `STATIC_HTML`:

```javascript
// ── Static dashboard config (injected at build time) ──────────────────────
const GH_REPO = 'rtadik/bobe-content-dashboard';
const GH_WORKFLOW = 'regenerate-item.yml';
const CURRENT_WEEK_OF = '{{ week_of }}';
const CLIENT_ID = '{{ client_id }}';

// ── Approval state (sessionStorage for static site) ───────────────────────
function loadApprovals() {
  const stored = sessionStorage.getItem('approvals_' + CURRENT_WEEK_OF) || '{}';
  try { return JSON.parse(stored); } catch { return {}; }
}
function saveApprovals(approvals) {
  sessionStorage.setItem('approvals_' + CURRENT_WEEK_OF, JSON.stringify(approvals));
}
function setApprovalUI(idx, status) {
  const statusEl = document.getElementById('status-' + idx);
  const approveBtn = document.getElementById('approve-' + idx);
  const card = document.getElementById('card-' + idx);
  if (!statusEl || !approveBtn) return;
  if (status === 'approved') {
    statusEl.textContent = 'Approved ✓';
    statusEl.className = 'img-status approved';
    approveBtn.textContent = '✓ Approved';
    approveBtn.classList.add('approved');
    if (card) card.classList.add('is-approved');
  } else {
    statusEl.textContent = 'Pending review';
    statusEl.className = 'img-status';
    approveBtn.textContent = '✓ Approve';
    approveBtn.classList.remove('approved');
    if (card) card.classList.remove('is-approved');
  }
}
// Restore approvals from session on load
(function() {
  const approvals = loadApprovals();
  const topics = document.querySelectorAll('.card');
  topics.forEach((_, i) => {
    const idx = i + 1;
    const card = document.getElementById('card-' + idx);
    if (!card) return;
    const topicEl = card.querySelector('.topic-title');
    if (!topicEl) return;
    const topic = topicEl.textContent.trim();
    if (approvals[topic] === 'approved') setApprovalUI(idx, 'approved');
  });
})();

// ── RU regen lock/unlock ─────────────────────────────────────────────────
function updateRuRegenState(idx, isApproved) {
  const ruImgBtn = document.getElementById('ru-img-regen-' + idx);
  const ruContentBtn = document.getElementById('ru-content-regen-' + idx);
  [ruImgBtn, ruContentBtn].forEach(btn => {
    if (!btn) return;
    if (isApproved) {
      btn.disabled = false;
      btn.title = '';
      btn.textContent = btn.textContent.replace('🔒 ', '↻ ');
    } else {
      btn.disabled = true;
      btn.title = 'Approve EN content first';
      if (!btn.textContent.startsWith('🔒')) {
        btn.textContent = '🔒 ' + btn.textContent.replace('↻ ', '');
      }
    }
  });
}

function approveImage(idx) {
  const approveBtn = document.getElementById('approve-' + idx);
  const card = document.getElementById('card-' + idx);
  const topicEl = card ? card.querySelector('.topic-title') : null;
  const topic = topicEl ? topicEl.textContent.trim() : '';
  const isApproved = approveBtn.classList.contains('approved');
  const newStatus = isApproved ? 'pending' : 'approved';
  setApprovalUI(idx, newStatus);
  updateRuRegenState(idx, newStatus === 'approved');
  // Persist in sessionStorage
  const approvals = loadApprovals();
  if (newStatus === 'approved') {
    approvals[topic] = 'approved';
    // Auto-switch to RU to review Russian version + RU controls now unlocked
    setLang('ru');
    showToast('EN approved — RU controls unlocked');
  } else {
    delete approvals[topic];
    showToast('Approval removed — RU controls locked');
  }
  saveApprovals(approvals);
}

// On page load: restore RU lock state from sessionStorage
(function() {
  const approvals = loadApprovals();
  const cards = document.querySelectorAll('.card');
  cards.forEach((_, i) => {
    const idx = i + 1;
    const card = document.getElementById('card-' + idx);
    if (!card) return;
    const topicEl = card.querySelector('.topic-title');
    const topic = topicEl ? topicEl.textContent.trim() : '';
    const isApproved = approvals[topic] === 'approved';
    if (isApproved) setApprovalUI(idx, 'approved');
    updateRuRegenState(idx, isApproved);
  });
})();

// ── GitHub token management ───────────────────────────────────────────────
let _pendingRegenIdx = null;
let _pendingRegenType = null;

function getGhToken() {
  return sessionStorage.getItem('gh_regen_token') || '';
}
function cancelGhModal() {
  document.getElementById('gh-token-modal').classList.remove('open');
  _pendingRegenIdx = null; _pendingRegenType = null;
}
function saveGhToken() {
  const token = document.getElementById('gh-token-input').value.trim();
  if (!token) { showToast('Please enter a token', true); return; }
  sessionStorage.setItem('gh_regen_token', token);
  document.getElementById('gh-token-modal').classList.remove('open');
  document.getElementById('gh-token-input').value = '';
  // Continue pending regen
  if (_pendingRegenIdx !== null) {
    const idx = _pendingRegenIdx;
    const type = _pendingRegenType;
    _pendingRegenIdx = null; _pendingRegenType = null;
    triggerRegen(idx, type);
  }
}

// ── GitHub Actions regen trigger ─────────────────────────────────────────
async function triggerRegen(cardIdx, regenType) {
  // Guard: RU regen types require EN approval (buttons should already be disabled,
  // but defend in depth in case JS is called directly)
  if (regenType === 'image_ru' || regenType === 'content_ru') {
    const approveBtn = document.getElementById('approve-' + cardIdx);
    if (!approveBtn || !approveBtn.classList.contains('approved')) {
      showToast('Approve EN content before regenerating Russian version', true);
      return;
    }
  }
  const token = getGhToken();
  if (!token) {
    _pendingRegenIdx = cardIdx;
    _pendingRegenType = regenType;
    document.getElementById('gh-token-modal').classList.add('open');
    document.getElementById('gh-token-input').focus();
    return;
  }
  // Find topic index (card index is 1-based, topic index is 0-based)
  const topicIdx = cardIdx - 1;
  showRegenStatus('Triggering regeneration on GitHub Actions...');
  try {
    const res = await fetch(
      `https://api.github.com/repos/${GH_REPO}/actions/workflows/${GH_WORKFLOW}/dispatches`,
      {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer ' + token,
          'Accept': 'application/vnd.github+json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ref: 'main',
          inputs: {
            client_id: CLIENT_ID,
            week_of: CURRENT_WEEK_OF,
            topic_index: String(topicIdx),
            regen_type: regenType,
          },
        }),
      }
    );
    if (res.status === 204) {
      showRegenStatus('Regeneration triggered. This takes 3-5 minutes. Refresh the page when done.');
      pollRegenCompletion(token);
    } else if (res.status === 401 || res.status === 403) {
      sessionStorage.removeItem('gh_regen_token');
      dismissRegenStatus();
      showToast('Invalid GitHub token — please re-enter', true);
      _pendingRegenIdx = cardIdx; _pendingRegenType = regenType;
      document.getElementById('gh-token-modal').classList.add('open');
    } else {
      const body = await res.text();
      showToast('GitHub error: ' + res.status + ' ' + body.slice(0, 80), true);
      dismissRegenStatus();
    }
  } catch (e) {
    showToast('Failed to reach GitHub: ' + e.message, true);
    dismissRegenStatus();
  }
}

async function pollRegenCompletion(token, maxWaitMs = 360000) {
  const deadline = Date.now() + maxWaitMs;
  // Wait a few seconds for GH to register the run
  await new Promise(r => setTimeout(r, 6000));
  while (Date.now() < deadline) {
    try {
      const res = await fetch(
        `https://api.github.com/repos/${GH_REPO}/actions/workflows/${GH_WORKFLOW}/runs?per_page=1`,
        { headers: { 'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json' } }
      );
      const data = await res.json();
      const run = data.workflow_runs && data.workflow_runs[0];
      if (run) {
        if (run.status === 'completed') {
          if (run.conclusion === 'success') {
            showRegenStatus('Done! Refreshing page in 3s...');
            setTimeout(() => location.reload(), 3000);
          } else {
            showRegenStatus('Regeneration finished with status: ' + run.conclusion + '. Check GitHub Actions for details.');
          }
          return;
        } else {
          showRegenStatus('Running on GitHub Actions (' + run.status + ')… Refresh page when done or wait.');
        }
      }
    } catch (e) { /* ignore poll errors */ }
    await new Promise(r => setTimeout(r, 15000));
  }
  showRegenStatus('Timed out waiting. Refresh the page manually when done.');
}

function showRegenStatus(msg) {
  const bar = document.getElementById('regen-status-bar');
  document.getElementById('regen-status-label').textContent = msg;
  bar.classList.add('show');
}
function dismissRegenStatus() {
  document.getElementById('regen-status-bar').classList.remove('show');
}
```

Note: The `STATIC_HTML` template also needs `{{ week_of }}` and `{{ client_id }}` variables injected at build time. Update `build_static.py`'s `dashboard_template.render(...)` call to include these.

**Files affected:**
- `scripts/build_static.py`

---

### Step 8: Update `build_static.py` render call to inject `week_of` and `client_id`

In `build_static.py`'s `build_site()` function, the `dashboard_template.render(...)` call needs two new variables:

```python
html = dashboard_template.render(
    topics=topics,
    date_label=date_display_label(date_id),
    current_date_id=date_id,
    date_options=date_options,
    brand_name=_display_name,
    expected_client_id=active_client,
    week_of=date_id[5:] if date_id.startswith("week:") else date_id,  # ADD THIS
    client_id=active_client,  # ADD THIS
)
```

**Files affected:**
- `scripts/build_static.py`

---

### Step 9: Update `CLAUDE.md`

Update the GitHub Actions section to document `regenerate-item.yml`, and add a note that the static client dashboard supports regeneration.

**Actions:**

In the `### GitHub Actions` section under `## Deployment`, add:

```markdown
- **`regenerate-item.yml`**: Triggered via client dashboard or admin panel. Regenerates a single topic's image (EN or RU) or text content, rebuilds static site, and deploys. Inputs: `client_id`, `week_of`, `topic_index`, `regen_type` (image_en / image_ru / content).
```

In the `## Deployment` section, add a note under "Credentials":

```markdown
**Regeneration on live dashboard**: Clients can regenerate images and content from the live dashboard using a GitHub PAT with `actions:write` scope. Token is entered once per session (never stored permanently). Triggers `regenerate-item.yml` via GitHub Actions API.
```

**Files affected:**
- `CLAUDE.md`

---

### Step 10: Test and validate

After implementing all steps, validate locally and then deploy.

**Actions:**

**Local Flask testing:**
1. Run `python scripts/web_viewer.py` and open http://localhost:5001
2. Click "↻ Regen Content" on any card — should show spinner, then reload with new content
3. Click "↻ Regen Image" — existing functionality, verify still works
4. Click "✓ Approve" on an EN image — should show "EN approved" toast and auto-switch to RU tab
5. Switch back to EN, unapprove — should return to EN mode

**Static site build testing:**
1. Run `python scripts/build_static.py --output dist`
2. Open `dist/dashboard/bobe/week-2026-02-16.html` in a browser (or serve with `python -m http.server -d dist 8080`)
3. Log in with `admin` / `bobe123`
4. Verify regen buttons appear on cards
5. Click "↻ Regen Image" — token modal should appear
6. Enter an invalid token — should show error
7. Verify "✓ Approve" button switches to RU view after click

**GitHub Actions testing:**
1. Check that `regenerate-item.yml` appears in GitHub Actions UI
2. Manually trigger it with a valid `client_id`, `week_of`, `topic_index`, `regen_type`
3. Confirm it runs to completion and deploys updated site

**Files affected:**
- None (validation only)

---

## Connections & Dependencies

### Files That Reference This Area

- `scripts/pipeline_runner.py` — gains `--regen-topic` / `--regen-type` flags
- `scripts/weekly_pipeline.py` — gains `regenerate_topic_content()` function
- `scripts/web_viewer.py` — gains content regen endpoint + approve→RU behavior
- `scripts/build_static.py` — gains full regen UI in static template
- `.github/workflows/regenerate-item.yml` — new workflow
- `CLAUDE.md` — updated docs

### Updates Needed for Consistency

- `CLAUDE.md` Scripts table: add `regenerate_topic_content` to `weekly_pipeline.py` description
- `CLAUDE.md` GitHub Actions section: add `regenerate-item.yml`
- `reference/github-actions-setup.md`: optionally note the new workflow and the limited-scope PAT setup for clients

### Impact on Existing Workflows

- Local Flask dashboard: no breaking changes. Existing approve/regen image/generate-RU flows unchanged. Content regen is additive.
- Static site build: no breaking changes. New UI elements added but all existing static behavior preserved.
- `pipeline_runner.py`: no breaking changes to existing `--client`, `--week-of`, `--mock`, `--skip-images` flags. New flags only activate when provided.

---

## Validation Checklist

- [ ] `/api/regenerate-content` Flask route returns `job_id` on valid request
- [ ] `regenerate_topic_content()` in `weekly_pipeline.py` updates the Excel workbook
- [ ] "↻ Regen Content" button appears in Flask dashboard for each card (EN only)
- [ ] "🔒 Regen RU Image" and "🔒 Regen RU Content" buttons appear in Flask dashboard, disabled with lock icon on page load
- [ ] Clicking "✓ Approve" in Flask dashboard: switches language to RU, unlocks both RU regen buttons (lock icon removed, buttons enabled)
- [ ] Removing approval in Flask dashboard: re-locks RU regen buttons (lock icon restored, buttons disabled)
- [ ] Page reload in Flask dashboard: RU buttons remain locked/unlocked according to saved approval state
- [ ] `regenerate-item.yml` appears in GitHub Actions UI and can be triggered manually
- [ ] `pipeline_runner.py --regen-topic 0 --regen-type image_en` runs without error
- [ ] Static site build (`build_static.py`) completes without errors
- [ ] Static dashboard HTML shows "🔒 Regen RU Image" and "🔒 Regen RU Content" disabled on load
- [ ] GitHub token modal appears on first regen click when no token stored
- [ ] Valid token stored in sessionStorage triggers GH Actions dispatch (HTTP 204)
- [ ] Approving EN on static dashboard: switches to RU view, unlocks RU regen buttons, persists in sessionStorage
- [ ] Removing EN approval on static dashboard: re-locks RU regen buttons
- [ ] Clicking a locked RU regen button (if somehow enabled) shows toast "Approve EN content first"
- [ ] `CLAUDE.md` updated with new workflow and regeneration capability

---

## Success Criteria

The implementation is complete when:

1. **Local Flask**: A "↻ Regen Content" button regenerates EN Twitter + Telegram text for any topic via Gemini, updates the workbook, and the dashboard reloads with new content. RU regen buttons (image + content) show a lock icon and are disabled on page load. Clicking Approve switches to RU and unlocks them. Removing approval re-locks them.

2. **Live static dashboard**: Regen buttons exist on every card. EN regen buttons (image + content) are always enabled. RU regen buttons (image + content) start with a lock icon and are disabled. Approving EN unlocks them, auto-switches to RU, and persists approval in sessionStorage. Clicking any unlocked regen button triggers the `regenerate-item.yml` GitHub Actions workflow via GitHub API (prompting for a token once per session).

3. **Consistency**: Both local and live dashboards share the same lock/unlock behavior and approve→RU-switch UX. The gate is enforced both via disabled buttons and via a JS guard in `triggerRegen()`.

---

## Notes

- **Token guidance for clients**: Rut should create a GitHub Fine-Grained Personal Access Token scoped to `rtadik/bobe-content-dashboard` with only `Actions: write` permission, then share it with each client. This is the least-privilege approach.
- **Future improvement**: A serverless webhook (Cloudflare Worker / Vercel Edge Function) could proxy the GitHub Actions call so clients never see a token at all. Out of scope for now.
- **Content regen model**: Uses the same Gemini model (`gemini-2.0-flash` or whatever `weekly_pipeline.py` currently uses). The `regenerate_topic_content()` function should load the client's `content-guidelines.md` and `context.md` for brand-consistent output.
- **Image filename on regen**: When an image is regenerated remotely (via GH Actions), the new image is saved with a `_v2`, `_v3` etc. suffix to avoid overwriting the original and to ensure the static site rebuild picks up the newest file.

---

## Implementation Notes

**Implemented:** 2026-02-24

### Summary

- Added `regenerate_topic_content()` to `weekly_pipeline.py` — reads workbook, calls Gemini to regenerate EN Twitter+Telegram content for a given topic index, writes back to Excel
- Added three Flask API routes to `web_viewer.py`: `/api/regenerate-content`, `/api/content-regen-status/<job_id>`, `/api/regenerate-ru-content`
- Added `.content-regen-bar` CSS + EN/RU content regen bar HTML + `updateRuRegenState()`, `regenContent()`, `regenRuContent()` JS to Flask dashboard
- Updated `approveImage()` to call `updateRuRegenState()` and `setLang('ru')` on approval; updated `loadApprovals()` to restore lock state
- RU image regen button now starts `disabled` with `🔒` prefix; `updateRuRegenState()` toggles it
- Created `.github/workflows/regenerate-item.yml` with 4 regen types via `workflow_dispatch`
- Added `run_regen_item()` + `--regen-topic`/`--regen-type` CLI flags to `pipeline_runner.py`
- Updated `STATIC_HTML` in `build_static.py`: full regen CSS, image action bars (EN: approve + regen, RU: locked regen), content regen bars, GitHub token modal, regen status bar, full JS block with `triggerRegen()`, `pollRegenCompletion()`, `updateRuRegenState()`, `approveImage()`, and approval persistence via `sessionStorage`
- Updated `build_static.py` render call to inject `week_of`, `client_id`, `gh_repo` (auto-detected from git remote)
- Updated `CLAUDE.md` with new workflow and live dashboard regeneration capability

### Deviations from Plan

- `gh_repo` is auto-detected from `git remote get-url origin` at build time rather than being a required CLI argument — no user action needed for standard setups
- `updateRuRegenState()` uses unicode escapes for lock/cycle symbols in the static HTML JS block to avoid encoding issues in the Python string
- Approval persistence on static site uses `sessionStorage` keyed `approvals_{client_id}_{week_of}` (per plan design)

### Issues Encountered

None — all steps executed cleanly.
