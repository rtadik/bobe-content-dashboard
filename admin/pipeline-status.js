/* Pipeline Status Monitor — client-side logic */

const STATUS_URL = '/api/pipeline-status';
const POLL_INTERVAL = 3000;

let allRuns = [];
let selectedRunId = null;
let selectedPhase = null;
let pollTimer = null;

// ── Phase metadata ────────────────────────────────────────────────────────
// Short label (fits in node), full description (shown in detail panel),
// and what "items" means for each phase.

const PHASE_META = {
  'Scrape Topics': {
    icon: '\u{1F50D}',
    label: 'Scrape',
    desc: 'Fetch trending topics from Twitter and Reddit via Apify API',
    unit: 'topics scraped',
  },
  'Assemble Buckets': {
    icon: '\u{1F4E6}',
    label: 'Assemble',
    desc: 'Combine Trending, Education, and Announcement buckets into 21 interleaved topics',
    unit: 'topics assembled',
  },
  'Generate Content': {
    icon: '\u{270D}\u{FE0F}',
    label: 'Content',
    desc: 'Generate bilingual Twitter threads and Telegram posts via Gemini API',
    unit: 'topics generated',
  },
  'Write to Airtable': {
    icon: '\u{1F4DD}',
    label: 'Airtable Write',
    desc: 'Write each content record (EN + RU) to the weekly Airtable table',
    unit: 'topics written',
  },
  'Generate Images': {
    icon: '\u{1F5BC}\u{FE0F}',
    label: 'Images',
    desc: 'Generate branded EN images via WaveSpeed GPT-Image-1.5',
    unit: 'images generated',
  },
  'Upload to R2': {
    icon: '\u{2601}\u{FE0F}',
    label: 'R2 Upload',
    desc: 'Upload generated images to Cloudflare R2 (S3-compatible CDN)',
    unit: 'images uploaded',
  },
  'Update Airtable Images': {
    icon: '\u{1F517}',
    label: 'Link Images',
    desc: 'Write R2 image URLs back to Airtable attachment fields',
    unit: 'records updated',
  },
  'Finalize': {
    icon: '\u{1F4CA}',
    label: 'Finalize',
    desc: 'Style and save the Excel workbook (opt-in via --export-excel)',
    unit: '',
  },
  'Deploy': {
    icon: '\u{1F680}',
    label: 'Deploy',
    desc: 'Build static HTML dashboard and deploy to Cloudflare Pages',
    unit: '',
  },
  'Translation': {
    icon: '\u{1F30D}',
    label: 'Translate',
    desc: 'Translate English content and image prompts to Russian via Gemini',
    unit: 'items translated',
  },
};

const STATUS_LABELS = {
  success: 'Completed',
  failed: 'Failed',
  running: 'In Progress',
  pending: 'Waiting',
  skipped: 'Skipped',
  partial: 'Partial',
};

const STATUS_ICONS = {
  success: '\u2713',
  failed: '\u2717',
  running: '\u21BB',
  pending: '\u2219',
  skipped: '\u2013',
};

const MODE_LABELS = {
  full: 'Full Pipeline',
  announcement: 'Announcement',
  regen: 'Regeneration',
  'content-only': 'Content Only',
  'images-approved': 'Approved Images',
};

// ── Fetch & poll ──────────────────────────────────────────────────────────

async function fetchStatus() {
  try {
    const resp = await fetch(STATUS_URL);
    if (!resp.ok) {
      if (resp.status === 404) { showEmpty(); return; }
      throw new Error(`HTTP ${resp.status}`);
    }
    const data = await resp.json();
    allRuns = data.runs || [];

    if (allRuns.length === 0) { showEmpty(); return; }

    hideEmpty();

    const latest = allRuns[allRuns.length - 1];
    if (!selectedRunId || selectedRunId === latest.run_id) {
      selectedRunId = latest.run_id;
    }

    renderRunHistory(allRuns);
    const run = allRuns.find(r => r.run_id === selectedRunId) || latest;
    renderRun(run);
    updatePolling(latest);
    updateTimestamp();
  } catch (err) {
    console.error('Fetch error:', err);
  }
}

function updatePolling(latestRun) {
  const isActive = latestRun && latestRun.status === 'running';
  const indicator = document.getElementById('live-indicator');

  if (isActive && !pollTimer) {
    pollTimer = setInterval(fetchStatus, POLL_INTERVAL);
    indicator.classList.add('active');
  } else if (!isActive && pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
    indicator.classList.remove('active');
  }
}

function updateTimestamp() {
  document.getElementById('last-updated').textContent =
    `Last refresh: ${new Date().toLocaleTimeString()}`;
}

// ── Render ────────────────────────────────────────────────────────────────

function showEmpty() {
  document.getElementById('empty-state').style.display = '';
  document.getElementById('run-info').style.display = 'none';
  document.getElementById('node-graph').style.display = 'none';
  document.getElementById('topic-detail').style.display = 'none';
}

function hideEmpty() {
  document.getElementById('empty-state').style.display = 'none';
  document.getElementById('run-info').style.display = '';
  document.getElementById('node-graph').style.display = '';
}

function renderRun(run) {
  renderRunInfo(run);
  renderNodeGraph(run);
  if (selectedPhase) {
    const phase = run.phases.find(p => p.name === selectedPhase);
    if (phase && phase.topics && phase.topics.length > 0) {
      renderTopicDetail(phase);
    } else if (phase) {
      renderPhaseInfo(phase);
    }
  }
}

// ── Run info bar ──────────────────────────────────────────────────────────

function renderRunInfo(run) {
  document.getElementById('ri-client').textContent = run.client_id;
  document.getElementById('ri-mode').textContent = MODE_LABELS[run.mode] || run.mode;
  document.getElementById('ri-week').textContent = `Week of ${run.week_of}`;

  const dur = formatDuration(run.started_at, run.finished_at);
  document.getElementById('ri-duration').textContent = run.status === 'running'
    ? `Running for ${dur}` : `Duration: ${dur}`;

  const badge = document.getElementById('ri-status');
  badge.textContent = STATUS_LABELS[run.status] || run.status;
  badge.className = `run-status-badge ${run.status}`;

  // Progress summary
  const total = run.phases.length;
  const done = run.phases.filter(p => p.status === 'success' || p.status === 'skipped').length;
  const failed = run.phases.filter(p => p.status === 'failed').length;
  const progress = document.getElementById('ri-progress');
  if (run.status === 'running') {
    progress.textContent = `${done}/${total} phases complete`;
    progress.style.display = '';
  } else if (failed > 0) {
    progress.textContent = `${failed} phase${failed > 1 ? 's' : ''} failed`;
    progress.style.display = '';
  } else {
    progress.style.display = 'none';
  }

  const errEl = document.getElementById('ri-error');
  if (run.error) {
    errEl.textContent = run.error;
    errEl.style.display = '';
  } else {
    errEl.style.display = 'none';
  }
}

// ── Node graph ────────────────────────────────────────────────────────────

function renderNodeGraph(run) {
  const container = document.getElementById('node-graph');
  container.innerHTML = '';

  run.phases.forEach((phase, idx) => {
    if (idx > 0) {
      const conn = document.createElement('div');
      conn.className = 'connector';
      const prev = run.phases[idx - 1].status;
      if (prev === 'success' || prev === 'skipped') conn.classList.add('done');
      else if (prev === 'running') conn.classList.add('active');
      container.appendChild(conn);
    }

    const meta = PHASE_META[phase.name] || { icon: '\u2699\uFE0F', label: phase.name, desc: '', unit: 'items' };
    const node = document.createElement('div');
    node.className = `node ${phase.status}`;
    if (phase.name === selectedPhase) node.classList.add('selected');

    // Build status line: count + unit, or status label
    let statusLine = STATUS_LABELS[phase.status] || phase.status;
    if (phase.status === 'success' && phase.item_count != null && meta.unit) {
      statusLine = `${phase.item_count} ${meta.unit}`;
    } else if (phase.status === 'running' && phase.topics && phase.topics.length > 0) {
      const done = phase.topics.filter(t => t.status === 'success').length;
      const total = phase.topics.length;
      statusLine = `${done}/${total}`;
    } else if (phase.status === 'skipped' && phase.error) {
      statusLine = 'Skipped';
    }

    const timeText = phase.started_at ? formatDuration(phase.started_at, phase.finished_at) : '';

    // Progress bar for running phases with topics
    let progressBar = '';
    if (phase.topics && phase.topics.length > 0) {
      const done = phase.topics.filter(t => t.status === 'success' || t.status === 'skipped').length;
      const total = phase.topics.length;
      const pct = total > 0 ? Math.round((done / total) * 100) : 0;
      progressBar = `<div class="node-progress"><div class="node-progress-fill ${phase.status}" style="width:${pct}%"></div></div>`;
    }

    node.innerHTML = `
      <div class="node-icon">${meta.icon}</div>
      <div class="node-label">${esc(meta.label)}</div>
      <div class="node-status">${esc(statusLine)}</div>
      ${progressBar}
      ${timeText ? `<div class="node-time">${esc(timeText)}</div>` : ''}
    `;

    // Tooltip on hover
    node.title = meta.desc;

    node.addEventListener('click', () => {
      if (selectedPhase === phase.name) {
        selectedPhase = null;
        document.getElementById('topic-detail').style.display = 'none';
        node.classList.remove('selected');
      } else {
        selectedPhase = phase.name;
        document.querySelectorAll('.node').forEach(n => n.classList.remove('selected'));
        node.classList.add('selected');
        if (phase.topics && phase.topics.length > 0) {
          renderTopicDetail(phase);
        } else {
          renderPhaseInfo(phase);
        }
      }
    });

    container.appendChild(node);
  });
}

// ── Phase info (no topics) ────────────────────────────────────────────────

function renderPhaseInfo(phase) {
  const panel = document.getElementById('topic-detail');
  panel.style.display = '';
  const meta = PHASE_META[phase.name] || { desc: '', unit: '' };

  const title = document.getElementById('topic-detail-title');
  title.textContent = phase.name;

  const grid = document.getElementById('topic-grid');
  let statusLabel = STATUS_LABELS[phase.status] || phase.status;
  let detail = meta.desc;

  if (phase.status === 'skipped' && phase.error) {
    detail = `Skipped: ${phase.error}`;
  } else if (phase.status === 'failed' && phase.error) {
    detail = `Error: ${phase.error}`;
  }

  const dur = phase.started_at ? formatDuration(phase.started_at, phase.finished_at) : 'N/A';

  grid.innerHTML = `
    <div class="phase-info-card">
      <div class="phase-info-row">
        <span class="phase-info-label">Status</span>
        <span class="phase-info-value status-${phase.status}">${esc(statusLabel)}</span>
      </div>
      <div class="phase-info-row">
        <span class="phase-info-label">Duration</span>
        <span class="phase-info-value">${esc(dur)}</span>
      </div>
      ${phase.item_count != null ? `
      <div class="phase-info-row">
        <span class="phase-info-label">Output</span>
        <span class="phase-info-value">${phase.item_count} ${esc(meta.unit || 'items')}</span>
      </div>` : ''}
      <div class="phase-info-row">
        <span class="phase-info-label">Description</span>
        <span class="phase-info-value">${esc(detail)}</span>
      </div>
    </div>
  `;
}

// ── Topic detail panel ────────────────────────────────────────────────────

function renderTopicDetail(phase) {
  const panel = document.getElementById('topic-detail');
  panel.style.display = '';
  const meta = PHASE_META[phase.name] || { desc: '', unit: '' };

  const completed = phase.topics.filter(t => t.status === 'success').length;
  const failed = phase.topics.filter(t => t.status === 'failed').length;
  const total = phase.topics.length;

  const title = document.getElementById('topic-detail-title');
  let summary = `${phase.name}: ${completed}/${total} succeeded`;
  if (failed > 0) summary += `, ${failed} failed`;
  title.textContent = summary;

  const grid = document.getElementById('topic-grid');
  grid.innerHTML = '';

  // Description bar
  if (meta.desc) {
    const descRow = document.createElement('div');
    descRow.className = 'topic-detail-desc';
    descRow.textContent = meta.desc;
    grid.appendChild(descRow);
  }

  // Header row
  const header = document.createElement('div');
  header.className = 'topic-row topic-header';
  header.innerHTML = `
    <span class="topic-index">#</span>
    <span class="topic-bucket">Bucket</span>
    <span class="topic-name">Topic</span>
    <span class="topic-status-icon">Status</span>
    <span class="topic-time">Time</span>
  `;
  grid.appendChild(header);

  // Sort by index
  const sorted = [...phase.topics].sort((a, b) => a.index - b.index);

  sorted.forEach(topic => {
    const row = document.createElement('div');
    row.className = 'topic-row';

    const statusIcon = STATUS_ICONS[topic.status] || '\u2219';
    const bucketClass = (topic.bucket || '').toLowerCase().replace(/\s/g, '');
    const duration = topic.started_at ? formatDuration(topic.started_at, topic.finished_at) : '';

    // Truncate long topic names for display, full name in title
    const displayName = topic.name.length > 50 ? topic.name.slice(0, 47) + '...' : topic.name;

    row.innerHTML = `
      <span class="topic-index">${topic.index + 1}</span>
      <span class="topic-bucket ${esc(bucketClass)}">${esc(capitalize(topic.bucket || '?'))}</span>
      <span class="topic-name" title="${esc(topic.name)}">${esc(displayName)}</span>
      <span class="topic-status-icon ${topic.status}">${statusIcon}</span>
      <span class="topic-time">${esc(duration || '-')}</span>
      ${topic.error ? `<div class="topic-error">${esc(topic.error)}</div>` : ''}
    `;

    grid.appendChild(row);
  });
}

// ── Run history ───────────────────────────────────────────────────────────

function renderRunHistory(runs) {
  const list = document.getElementById('run-list');
  list.innerHTML = '';

  if (runs.length === 0) {
    list.innerHTML = '<div class="run-empty">No runs recorded</div>';
    return;
  }

  const reversed = [...runs].reverse();

  reversed.forEach(run => {
    const entry = document.createElement('div');
    entry.className = `run-entry${run.run_id === selectedRunId ? ' active' : ''}`;

    const dateStr = run.started_at ? formatShortDate(run.started_at) : '?';
    const resultIcon = STATUS_ICONS[run.status] || '\u2219';
    const modeLabel = MODE_LABELS[run.mode] || run.mode;
    const dur = formatDuration(run.started_at, run.finished_at);
    const phaseSummary = run.phases
      ? `${run.phases.filter(p => p.status === 'success').length}/${run.phases.length} phases`
      : '';

    entry.innerHTML = `
      <div class="run-entry-main">
        <span class="run-date">${esc(dateStr)}</span>
        <span class="run-result ${run.status}">${resultIcon}</span>
      </div>
      <div class="run-entry-meta">
        <span class="run-type">${esc(modeLabel)}</span>
        <span class="run-client-tag">${esc(run.client_id)}</span>
        <span class="run-dur">${esc(dur)}</span>
      </div>
    `;

    entry.addEventListener('click', () => {
      selectedRunId = run.run_id;
      selectedPhase = null;
      document.getElementById('topic-detail').style.display = 'none';
      renderRunHistory(allRuns);
      const selected = allRuns.find(r => r.run_id === run.run_id);
      if (selected) renderRun(selected);
    });

    list.appendChild(entry);
  });
}

// ── Helpers ───────────────────────────────────────────────────────────────

function formatDuration(startIso, endIso) {
  if (!startIso) return '-';
  const start = new Date(startIso);
  const end = endIso ? new Date(endIso) : new Date();
  const secs = Math.max(0, Math.round((end - start) / 1000));

  if (secs === 0) return '<1s';
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  const remSecs = secs % 60;
  if (mins < 60) return `${mins}m ${remSecs}s`;
  const hrs = Math.floor(mins / 60);
  const remMins = mins % 60;
  return `${hrs}h ${remMins}m`;
}

function formatShortDate(iso) {
  const d = new Date(iso);
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return `${months[d.getMonth()]} ${d.getDate()}, ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function pad(n) { return String(n).padStart(2, '0'); }

function capitalize(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

function esc(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// ── Init ──────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  fetchStatus();
  // Slow poll (10s) to catch new runs even when idle
  setInterval(() => { if (!pollTimer) fetchStatus(); }, 10000);
});
