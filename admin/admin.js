/**
 * Content Pipeline Admin — GitHub API client
 *
 * Auth: GitHub PAT stored in sessionStorage only (cleared on tab close).
 * All API calls go directly to api.github.com — no intermediary server.
 */

const REPO = "rtadik/bobe-content-dashboard";
const API  = "https://api.github.com";

// Workflow file names in .github/workflows/
const PIPELINE_WORKFLOW = "weekly-pipeline.yml";
const ONBOARD_WORKFLOW  = "onboard-client.yml";

// Auto-refresh interval when a run is in progress (ms)
const POLL_INTERVAL = 30000;

let _pat          = null;
let _pollTimer    = null;
let _authedUser   = null;

// ── Session storage helpers ───────────────────────────────────────────────────

function savePat(pat) {
  _pat = pat;
  sessionStorage.setItem("admin_pat", pat);
}

function loadPat() {
  _pat = sessionStorage.getItem("admin_pat") || null;
  return _pat;
}

function clearPat() {
  _pat = null;
  sessionStorage.removeItem("admin_pat");
  _authedUser = null;
}

// ── GitHub API helpers ────────────────────────────────────────────────────────

async function ghFetch(path, options = {}) {
  const headers = {
    Authorization: `Bearer ${_pat}`,
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    ...options.headers,
  };
  const response = await fetch(`${API}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.message || `HTTP ${response.status}`);
  }
  return response.status === 204 ? null : response.json();
}

async function triggerWorkflow(workflow, inputs) {
  await ghFetch(`/repos/${REPO}/actions/workflows/${workflow}/dispatches`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ref: "main", inputs }),
  });
}

async function getWorkflowRuns(workflow, perPage = 5) {
  const data = await ghFetch(
    `/repos/${REPO}/actions/workflows/${workflow}/runs?per_page=${perPage}&exclude_pull_requests=true`
  );
  return data.workflow_runs || [];
}

// ── Auth ──────────────────────────────────────────────────────────────────────

async function connect(pat) {
  _pat = pat;
  try {
    const user = await ghFetch("/user");
    savePat(pat);
    _authedUser = user.login;
    setAuthed(true, user.login);
    showPipelineSection();
    showOnboardSection();
    showStatusSection();
    refreshStatus();
  } catch (err) {
    _pat = null;
    showAuthError(`Authentication failed: ${err.message}`);
  }
}

function disconnect() {
  clearPat();
  stopPolling();
  setAuthed(false);
  hideSections();
  document.getElementById("pat-input").value = "";
  hideMsg("auth-error");
}

function setAuthed(authed, username) {
  const badge = document.getElementById("auth-status");
  const disconnectBtn = document.getElementById("disconnect-btn");

  if (authed) {
    badge.textContent = `Connected as ${username}`;
    badge.className = "auth-badge connected";
    disconnectBtn.style.display = "inline-flex";
  } else {
    badge.textContent = "Not connected";
    badge.className = "auth-badge disconnected";
    disconnectBtn.style.display = "none";
  }
}

// ── Section visibility ────────────────────────────────────────────────────────

function showPipelineSection() { document.getElementById("section-pipeline").style.display = "block"; }
function showOnboardSection()  { document.getElementById("section-onboard").style.display = "block"; }
function showStatusSection()   { document.getElementById("section-status").style.display = "block"; }

function hideSections() {
  document.getElementById("section-pipeline").style.display = "none";
  document.getElementById("section-onboard").style.display = "none";
  document.getElementById("section-status").style.display = "none";
}

// ── Pipeline trigger ──────────────────────────────────────────────────────────

async function runPipeline() {
  const btn       = document.getElementById("pipeline-run-btn");
  const clientId  = document.getElementById("pipeline-client").value.trim() || "bobe";
  const weekOf    = document.getElementById("pipeline-week").value.trim();
  const skipImages   = document.getElementById("pipeline-skip-images").checked;
  const skipAirtable = document.getElementById("pipeline-skip-airtable").checked;
  const mock         = document.getElementById("pipeline-mock").checked;

  if (!clientId) {
    showMsg("pipeline-error", "Client ID is required.");
    return;
  }

  hideMsg("pipeline-error");
  hideMsg("pipeline-msg");
  btn.disabled = true;
  btn.textContent = "Triggering…";

  const inputs = {
    client_id:      clientId,
    week_of:        weekOf,
    skip_images:    String(skipImages),
    skip_airtable:  String(skipAirtable),
    mock:           String(mock),
  };

  try {
    await triggerWorkflow(PIPELINE_WORKFLOW, inputs);
    showMsg(
      "pipeline-msg",
      `Pipeline triggered for client "${clientId}"${weekOf ? ` (week: ${weekOf})` : " (current week)"}. ` +
      `Check Run Status below — it may take 30–60 seconds to appear.`
    );
    // Refresh status after a short delay to catch the new run
    setTimeout(() => { refreshStatus(); startPolling(); }, 5000);
  } catch (err) {
    const msg = err.message === "Not Found"
      ? "Failed to trigger pipeline: workflow not found. Make sure the repo's default branch is set to 'main' (not 'gh-pages') so GitHub Actions can index the workflow files."
      : `Failed to trigger pipeline: ${err.message}`;
    showMsg("pipeline-error", msg);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-icon">&#9654;</span> Run Pipeline';
  }
}

// ── Onboard trigger ───────────────────────────────────────────────────────────

async function runOnboard() {
  const btn = document.getElementById("onboard-run-btn");

  const clientId   = document.getElementById("onboard-id").value.trim();
  const displayName= document.getElementById("onboard-name").value.trim();
  const tagline    = document.getElementById("onboard-tagline").value.trim();
  const website    = document.getElementById("onboard-website").value.trim();
  const industry   = document.getElementById("onboard-industry").value.trim();
  const platforms  = document.getElementById("onboard-platforms").value.trim() || "twitter,telegram";
  const primary    = document.getElementById("onboard-primary").value.trim() || "#1a1a2e";
  const accent     = document.getElementById("onboard-accent").value.trim() || "#00aaff";
  const airtable   = document.getElementById("onboard-airtable").value.trim();

  // Validate required fields
  const missing = [];
  if (!clientId)    missing.push("Client ID");
  if (!displayName) missing.push("Display Name");
  if (!tagline)     missing.push("Tagline");
  if (!website)     missing.push("Website");
  if (!industry)    missing.push("Industry");

  if (missing.length) {
    showMsg("onboard-error", `Missing required fields: ${missing.join(", ")}`);
    return;
  }

  // Validate client ID format
  if (!/^[a-z0-9_-]+$/.test(clientId)) {
    showMsg("onboard-error", "Client ID must be lowercase letters, numbers, hyphens, or underscores only.");
    return;
  }

  hideMsg("onboard-error");
  hideMsg("onboard-msg");
  document.getElementById("onboard-next").style.display = "none";

  btn.disabled = true;
  btn.textContent = "Creating…";

  const inputs = {
    client_id:       clientId,
    display_name:    displayName,
    tagline:         tagline,
    website:         website,
    primary_color:   primary,
    accent_color:    accent,
    industry:        industry,
    platforms:       platforms,
    airtable_base_id:airtable,
  };

  try {
    await triggerWorkflow(ONBOARD_WORKFLOW, inputs);
    showMsg(
      "onboard-msg",
      `Onboarding workflow triggered for "${clientId}". The client directory will be committed to the repo in ~30 seconds.`
    );
    // Show next steps
    document.getElementById("onboard-next-cmd").textContent = `/onboard-client ${clientId}`;
    document.getElementById("onboard-next").style.display = "block";
    setTimeout(() => { refreshStatus(); startPolling(); }, 5000);
  } catch (err) {
    const msg = err.message === "Not Found"
      ? "Failed to trigger onboarding: workflow not found. Make sure the repo's default branch is set to 'main' (not 'gh-pages') so GitHub Actions can index the workflow files."
      : `Failed to trigger onboarding: ${err.message}`;
    showMsg("onboard-error", msg);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-icon">&#10133;</span> Create Client';
  }
}

// ── Run status ────────────────────────────────────────────────────────────────

async function refreshStatus() {
  document.getElementById("refresh-btn").disabled = true;
  try {
    const [pipelineRuns, onboardRuns] = await Promise.all([
      getWorkflowRuns(PIPELINE_WORKFLOW, 5),
      getWorkflowRuns(ONBOARD_WORKFLOW, 5),
    ]);
    renderRuns("pipeline-runs", pipelineRuns);
    renderRuns("onboard-runs", onboardRuns);

    // Start/stop auto-refresh based on whether any run is active
    const allRuns = [...pipelineRuns, ...onboardRuns];
    const hasActive = allRuns.some(r => r.status === "in_progress" || r.status === "queued");
    if (hasActive) {
      startPolling();
    } else {
      stopPolling();
    }
  } catch (err) {
    const errHtml = `<div class="runs-empty" style="color:var(--red)">Error: ${err.message}</div>`;
    document.getElementById("pipeline-runs").innerHTML = errHtml;
    document.getElementById("onboard-runs").innerHTML = errHtml;
  } finally {
    document.getElementById("refresh-btn").disabled = false;
  }
}

function renderRuns(containerId, runs) {
  const container = document.getElementById(containerId);
  if (!runs.length) {
    container.innerHTML = '<div class="runs-empty">No runs found</div>';
    return;
  }
  container.innerHTML = runs.map(run => {
    const badge   = getBadgeClass(run.status, run.conclusion);
    const label   = getBadgeLabel(run.status, run.conclusion);
    const started = run.created_at ? formatRelativeTime(run.created_at) : "";
    const duration= run.updated_at && run.created_at
      ? formatDuration(run.created_at, run.updated_at, run.status)
      : "";
    return `
      <div class="run-item">
        <div class="run-top">
          <span class="run-number">Run #${run.run_number}</span>
          <span class="run-badge ${badge}">${label}</span>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
          <span class="run-time">${started}${duration ? " · " + duration : ""}</span>
          <a href="${run.html_url}" target="_blank" rel="noopener" class="run-link">View logs ↗</a>
        </div>
      </div>`;
  }).join("");
}

function getBadgeClass(status, conclusion) {
  if (status === "completed") {
    return conclusion === "success" ? "success" :
           conclusion === "failure" ? "failure" :
           "cancelled";
  }
  if (status === "in_progress") return "running";
  if (status === "queued")      return "queued";
  return "cancelled";
}

function getBadgeLabel(status, conclusion) {
  if (status === "in_progress") return "Running";
  if (status === "queued")      return "Queued";
  if (status === "completed") {
    if (conclusion === "success")   return "Success";
    if (conclusion === "failure")   return "Failed";
    if (conclusion === "cancelled") return "Cancelled";
    return conclusion || "Done";
  }
  return status;
}

function formatRelativeTime(isoString) {
  const diff = (Date.now() - new Date(isoString).getTime()) / 1000;
  if (diff < 60)   return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400)return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function formatDuration(start, end, status) {
  if (status === "queued") return "";
  const secs = Math.round((new Date(end) - new Date(start)) / 1000);
  if (secs < 60)   return `${secs}s`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m ${secs % 60}s`;
  return `${Math.floor(secs / 3600)}h ${Math.floor((secs % 3600) / 60)}m`;
}

// ── Polling ───────────────────────────────────────────────────────────────────

function startPolling() {
  if (_pollTimer) return;
  document.getElementById("auto-refresh-indicator").style.display = "inline-flex";
  _pollTimer = setInterval(refreshStatus, POLL_INTERVAL);
}

function stopPolling() {
  if (_pollTimer) {
    clearInterval(_pollTimer);
    _pollTimer = null;
  }
  document.getElementById("auto-refresh-indicator").style.display = "none";
}

// ── Intake form link copy ─────────────────────────────────────────────────────

function copyIntakeLink() {
  const url = document.getElementById("intake-url").textContent.trim();
  const btn = document.getElementById("copy-intake-btn");
  navigator.clipboard.writeText(url).then(() => {
    btn.textContent = "✓ Copied!";
    btn.style.color = "var(--green)";
    btn.style.borderColor = "rgba(91,214,159,0.4)";
    setTimeout(() => {
      btn.innerHTML = "&#128203; Copy Link";
      btn.style.color = "";
      btn.style.borderColor = "";
    }, 2000);
  }).catch(() => {
    // Fallback for older browsers
    const range = document.createRange();
    range.selectNodeContents(document.getElementById("intake-url"));
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);
    btn.textContent = "Selected — Ctrl+C to copy";
    setTimeout(() => { btn.innerHTML = "&#128203; Copy Link"; }, 2500);
  });
}

// ── UI helpers ────────────────────────────────────────────────────────────────

function showMsg(id, text) {
  const el = document.getElementById(id);
  if (el) { el.textContent = text; el.style.display = "block"; }
}

function hideMsg(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = "none";
}

function showAuthError(msg) {
  showMsg("auth-error", msg);
}

// ── Event wiring ──────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {

  // Restore session
  const stored = loadPat();
  if (stored) {
    connect(stored).catch(() => {
      clearPat();
      setAuthed(false);
    });
  }

  // Auth
  document.getElementById("connect-btn").addEventListener("click", () => {
    const pat = document.getElementById("pat-input").value.trim();
    if (!pat) {
      showAuthError("Please enter a GitHub PAT.");
      return;
    }
    hideMsg("auth-error");
    document.getElementById("connect-btn").textContent = "Connecting…";
    document.getElementById("connect-btn").disabled = true;
    connect(pat).finally(() => {
      document.getElementById("connect-btn").textContent = "Connect";
      document.getElementById("connect-btn").disabled = false;
    });
  });

  document.getElementById("pat-input").addEventListener("keydown", e => {
    if (e.key === "Enter") document.getElementById("connect-btn").click();
  });

  document.getElementById("disconnect-btn").addEventListener("click", disconnect);

  // Pipeline
  document.getElementById("pipeline-run-btn").addEventListener("click", runPipeline);

  // Onboard
  document.getElementById("onboard-run-btn").addEventListener("click", runOnboard);

  // Status refresh
  document.getElementById("refresh-btn").addEventListener("click", refreshStatus);
});
