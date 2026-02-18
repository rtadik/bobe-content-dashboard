#!/usr/bin/env python3
"""
BoBe Content Dashboard — Flask web viewer
Reads the most recent (or specified) weekly Excel from outputs/content/
and serves a bilingual (EN/RU) visual dashboard at http://localhost:5001

Usage:
  python scripts/web_viewer.py                       # auto-loads latest weekly workbook
  python scripts/web_viewer.py week:2026-02-16       # loads specific week
"""

import sys
import re
import json
import time
import uuid
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CONTENT_DIR  = PROJECT_ROOT / "outputs" / "content"
IMAGES_DIR   = CONTENT_DIR / "images"

try:
    from flask import Flask, render_template_string, send_from_directory, request, jsonify
except ImportError:
    print("Flask not installed. Run:  venv/bin/pip install flask")
    sys.exit(1)

try:
    import openpyxl
except ImportError:
    print("openpyxl not installed. Run:  venv/bin/pip install openpyxl")
    sys.exit(1)

# Try to import image generator — graceful degradation if not available
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
try:
    from nano_banana import generate_image as gen_img, build_prompt, DEFAULT_REFERENCES
    HAS_GENERATOR = True
except Exception:
    HAS_GENERATOR = False

app = Flask(__name__)

# ── Async job tracking ────────────────────────────────────────────────────────
# { job_id: {"status": "running"|"done"|"error", "filename": str, "error": str} }
_jobs: dict = {}
_jobs_lock = threading.Lock()


# ── Excel discovery ───────────────────────────────────────────────────────────

def list_available_dates():
    dates = []
    # Weekly files only: YYYY-MM-DD-weekly-content.xlsx — prefix with "week:"
    for f in sorted(CONTENT_DIR.glob("*-weekly-content.xlsx"), reverse=True):
        m = re.match(r"(\d{4}-\d{2}-\d{2})-weekly-content\.xlsx", f.name)
        if m:
            dates.append(f"week:{m.group(1)}")
    return dates


def find_excel(date=None):
    if date and date.startswith("week:"):
        week_of = date[len("week:"):]
        p = CONTENT_DIR / f"{week_of}-weekly-content.xlsx"
        return p if p.exists() else None
    # Default: most recent weekly workbook
    dates = list_available_dates()
    if not dates:
        return None
    week_of = dates[0][len("week:"):]
    return CONTENT_DIR / f"{week_of}-weekly-content.xlsx"


# ── Image resolution ──────────────────────────────────────────────────────────

def resolve_image(raw_path, topic):
    """Return path relative to IMAGES_DIR of the best matching image, or None."""
    if not raw_path:
        return None

    # Strategy 1: exact path relative to project root
    candidate = PROJECT_ROOT / raw_path
    if candidate.exists():
        try:
            return str(candidate.relative_to(IMAGES_DIR))
        except ValueError:
            return candidate.name

    # Strategy 2: exact filename match — search recursively in IMAGES_DIR
    filename = Path(raw_path).name
    for png in sorted(IMAGES_DIR.glob("**/*.png")):
        if png.name == filename:
            return str(png.relative_to(IMAGES_DIR))
    if (CONTENT_DIR / filename).exists():
        return filename

    # Strategy 3: fuzzy slug match
    stem = Path(raw_path).stem
    parts = stem.split("_")
    slug_parts = [p for p in parts[1:] if p not in ("twitter", "telegram", "v2", "v1", "ru")]
    slug = "_".join(slug_parts)
    if slug:
        for png in sorted(IMAGES_DIR.glob("**/*.png")):
            if slug in png.name:
                return str(png.relative_to(IMAGES_DIR))

    # Strategy 4: derive slug from topic text
    topic_slug = re.sub(r"[^a-z0-9]+", "_", topic.lower())[:30].strip("_")
    for word in topic_slug.split("_"):
        if len(word) > 3:
            for png in sorted(IMAGES_DIR.glob("**/*.png")):
                if word in png.name.lower():
                    return str(png.relative_to(IMAGES_DIR))

    return None


# ── Approval state management ─────────────────────────────────────────────────

def get_approval_file(date):
    return CONTENT_DIR / f"{date}-approvals.json"


def load_approvals(date):
    f = get_approval_file(date)
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            return {}
    return {}


def save_approvals(date, approvals):
    f = get_approval_file(date)
    f.write_text(json.dumps(approvals, indent=2))


# ── Data loading ──────────────────────────────────────────────────────────────

def load_content(xlsx_path):
    """
    Read the Content sheet and return list of topic dicts grouped by topic.
    Supports 10-column (old weekly) and 14-column (bilingual weekly) workbooks.
    Each dict: {topic, date, day, img_prompt, image_filename, img_prompt_ru,
                image_filename_ru, twitter, telegram, twitter_ru, telegram_ru,
                hashtag_list, hashtag_list_ru}
    """
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    if "Content" not in wb.sheetnames:
        wb.close()
        return []

    ws = wb["Content"]
    topics = {}
    topic_order = []

    header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), ())
    num_cols = len([h for h in header_row if h])
    has_ru = num_cols >= 14

    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or not row[1]:
            continue

        if has_ru:
            (date, day, topic, platform, fmt, content, img_prompt, img_path, hashtags,
             content_ru, img_prompt_ru, img_path_ru, hashtags_ru, status) = row[:14]
        else:
            # Old 10-column weekly (graceful degradation — no RU fields)
            date, day, topic, platform, fmt, content, img_prompt, img_path, hashtags, status = row[:10]
            content_ru = img_prompt_ru = img_path_ru = hashtags_ru = ""

        if topic not in topics:
            topics[topic] = {
                "topic":            topic,
                "date":             str(date) if date else "",
                "day":              day or "",
                "img_prompt":       img_prompt or "",
                "raw_image_path":   img_path or "",
                "image_filename":   None,
                "img_prompt_ru":    img_prompt_ru or "",
                "raw_image_path_ru": img_path_ru or "",
                "image_filename_ru": None,
                "twitter":          None,
                "telegram":         None,
                "twitter_ru":       None,
                "telegram_ru":      None,
                "hashtags":         hashtags or "",
                "hashtags_ru":      hashtags_ru or "",
            }
            topic_order.append(topic)

        platform_lower = (platform or "").lower()
        if "twitter" in platform_lower:
            topics[topic]["twitter"] = content or ""
            if content_ru:
                topics[topic]["twitter_ru"] = content_ru or ""
        elif "telegram" in platform_lower:
            topics[topic]["telegram"] = content or ""
            if hashtags:
                topics[topic]["hashtags"] = hashtags
            if content_ru:
                topics[topic]["telegram_ru"] = content_ru or ""
            if hashtags_ru:
                topics[topic]["hashtags_ru"] = hashtags_ru

    wb.close()

    result = []
    for key in topic_order:
        t = topics[key]
        t["image_filename"]    = resolve_image(t["raw_image_path"],    t["topic"])
        t["image_filename_ru"] = resolve_image(t["raw_image_path_ru"], t["topic"])
        raw = t["hashtags"]
        t["hashtag_list"] = [h.strip() for h in str(raw).split(",") if h.strip()] if raw else []
        raw_ru = t["hashtags_ru"]
        t["hashtag_list_ru"] = [h.strip() for h in str(raw_ru).split(",") if h.strip()] if raw_ru else []
        result.append(t)

    return result


# ── HTML template ─────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BoBe Content Dashboard</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:        #0D1526;
    --surface:   #111B32;
    --surface2:  #162038;
    --border:    rgba(21,137,220,0.15);
    --blue:      #1589DC;
    --blue-dim:  rgba(21,137,220,0.12);
    --green:     #5BD69F;
    --green-dim: rgba(91,214,159,0.12);
    --yellow:    #E0C145;
    --yellow-dim:rgba(224,193,69,0.12);
    --pink:      #FF4FDA;
    --white:     #FFFFFF;
    --muted:     #6B82A8;
    --text:      #C8D8EE;
  }

  html, body {
    background: var(--bg);
    color: var(--white);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
    min-height: 100vh;
    line-height: 1.5;
  }

  /* ── Header ── */
  header {
    background: #080F1E;
    border-bottom: 1px solid var(--border);
    padding: 0 24px;
    height: 60px;
    display: flex;
    align-items: center;
    gap: 16px;
    position: sticky;
    top: 0;
    z-index: 200;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--blue);
    letter-spacing: 0.3px;
    white-space: nowrap;
  }

  .brand-dot { color: var(--pink); }

  .header-sep {
    width: 1px;
    height: 20px;
    background: var(--border);
  }

  .header-date {
    font-size: 0.85rem;
    color: var(--muted);
    white-space: nowrap;
  }

  .header-count {
    font-size: 0.78rem;
    background: var(--blue-dim);
    border: 1px solid rgba(21,137,220,0.25);
    color: var(--blue);
    padding: 2px 9px;
    border-radius: 20px;
    white-space: nowrap;
  }

  .spacer { flex: 1; }

  .date-select {
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 5px 10px;
    border-radius: 7px;
    font-size: 0.82rem;
    cursor: pointer;
    outline: none;
  }
  .date-select:hover { border-color: var(--blue); }

  /* ── Language toggle ── */
  .lang-toggle {
    display: flex;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
  }
  .lang-btn {
    background: none;
    border: none;
    color: var(--muted);
    padding: 5px 14px;
    cursor: pointer;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    transition: all 0.15s;
  }
  .lang-btn.active {
    background: var(--blue);
    color: #fff;
  }
  .lang-btn:hover:not(.active) { color: var(--text); }

  /* EN/RU visibility */
  .ru-only { display: none; }
  body.lang-ru .ru-only { display: block; }
  body.lang-ru .en-only { display: none; }

  /* ── Grid ── */
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
    gap: 24px;
    padding: 28px 24px;
    max-width: 1440px;
    margin: 0 auto;
  }

  @media (max-width: 500px) {
    .grid { grid-template-columns: 1fr; padding: 14px; gap: 16px; }
    header { padding: 0 14px; gap: 10px; }
  }

  /* ── Card ── */
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    transition: border-color 0.2s, box-shadow 0.2s;
  }
  .card:hover {
    border-color: rgba(21,137,220,0.35);
    box-shadow: 0 4px 32px rgba(21,137,220,0.08);
  }
  .card.is-approved {
    border-color: rgba(91,214,159,0.4);
  }
  .card.is-approved:hover {
    border-color: rgba(91,214,159,0.6);
    box-shadow: 0 4px 32px rgba(91,214,159,0.08);
  }

  /* ── Card image ── */
  .card-img {
    position: relative;
    width: 100%;
    aspect-ratio: 16 / 9;
    overflow: hidden;
    background: var(--surface2);
    cursor: pointer;
  }
  .card-img img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    transition: transform 0.3s ease;
  }
  .card-img:hover img { transform: scale(1.02); }
  .card-img .img-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(to bottom, transparent 60%, rgba(13,21,38,0.7) 100%);
    pointer-events: none;
  }
  .no-img {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 6px;
    color: var(--muted);
    font-size: 0.8rem;
  }
  .no-img-icon { font-size: 2rem; opacity: 0.3; }

  /* ── Loading overlay ── */
  .img-loading-overlay {
    position: absolute;
    inset: 0;
    background: rgba(13,21,38,0.88);
    display: none;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: 12px;
    z-index: 10;
    pointer-events: all;
  }
  .img-loading-overlay.active { display: flex; }
  .spinner {
    width: 38px;
    height: 38px;
    border: 3px solid rgba(21,137,220,0.2);
    border-top-color: var(--blue);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .spinner-label {
    font-size: 0.75rem;
    color: var(--muted);
    letter-spacing: 0.3px;
  }

  /* ── Image action bar ── */
  .image-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: #0A1221;
    border-bottom: 1px solid var(--border);
    min-height: 40px;
  }

  .img-status {
    flex: 1;
    font-size: 0.72rem;
    color: var(--muted);
    letter-spacing: 0.2px;
  }
  .img-status.approved {
    color: var(--green);
    font-weight: 500;
  }

  .action-btn {
    border: 1px solid transparent;
    padding: 4px 12px;
    border-radius: 7px;
    cursor: pointer;
    font-size: 0.75rem;
    font-weight: 500;
    transition: all 0.15s;
    white-space: nowrap;
  }
  .action-btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .approve-btn {
    background: var(--green-dim);
    border-color: rgba(91,214,159,0.25);
    color: var(--green);
  }
  .approve-btn:hover:not(:disabled) {
    background: rgba(91,214,159,0.2);
    border-color: rgba(91,214,159,0.4);
  }
  .approve-btn.approved {
    background: var(--green);
    border-color: var(--green);
    color: #0D1526;
  }
  .approve-btn.approved:hover:not(:disabled) {
    background: #4BC48F;
  }

  .regen-btn {
    background: rgba(255,79,218,0.07);
    border-color: rgba(255,79,218,0.2);
    color: var(--pink);
  }
  .regen-btn:hover:not(:disabled) {
    background: rgba(255,79,218,0.14);
    border-color: rgba(255,79,218,0.35);
  }

  /* ── Card body ── */
  .card-body {
    padding: 16px 18px 18px;
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .topic-title {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--white);
    line-height: 1.45;
  }

  /* ── Platform tabs ── */
  .tab-bar {
    display: flex;
    gap: 6px;
  }

  .tab {
    background: none;
    border: 1px solid var(--border);
    color: var(--muted);
    padding: 5px 14px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.78rem;
    font-weight: 500;
    letter-spacing: 0.3px;
    transition: all 0.15s;
    display: flex;
    align-items: center;
    gap: 5px;
  }
  .tab:hover:not(.active) {
    border-color: rgba(21,137,220,0.3);
    color: var(--text);
    background: var(--blue-dim);
  }
  .tab.active {
    background: var(--blue-dim);
    border-color: rgba(21,137,220,0.4);
    color: var(--blue);
  }
  .tab .platform-icon { font-size: 0.9rem; }

  /* ── Content panels ── */
  .panel { display: none; flex-direction: column; gap: 8px; }
  .panel.active { display: flex; }

  .content-box {
    background: #080F1E;
    border: 1px solid var(--border);
    border-radius: 9px;
    padding: 13px 14px;
    font-size: 0.8rem;
    line-height: 1.65;
    color: var(--text);
    white-space: pre-wrap;
    word-wrap: break-word;
    max-height: 220px;
    overflow-y: auto;
    font-family: inherit;
    scrollbar-width: thin;
    scrollbar-color: var(--border) transparent;
  }
  .content-box::-webkit-scrollbar { width: 4px; }
  .content-box::-webkit-scrollbar-track { background: transparent; }
  .content-box::-webkit-scrollbar-thumb {
    background: var(--border);
    border-radius: 4px;
  }

  .tweet-divider {
    border: none;
    border-top: 1px dashed rgba(21,137,220,0.2);
    margin: 6px 0;
  }

  .content-actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .char-count {
    font-size: 0.72rem;
    color: var(--muted);
  }

  .copy-btn {
    background: var(--blue);
    color: #fff;
    border: none;
    padding: 5px 14px;
    border-radius: 7px;
    cursor: pointer;
    font-size: 0.77rem;
    font-weight: 500;
    transition: background 0.15s, transform 0.1s;
  }
  .copy-btn:hover { background: #1070BB; }
  .copy-btn:active { transform: scale(0.97); }
  .copy-btn.copied { background: var(--green); color: #0D1526; }

  /* ── Hashtags ── */
  .hashtags {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    padding-top: 2px;
  }
  .tag {
    background: var(--yellow-dim);
    color: var(--yellow);
    border: 1px solid rgba(224,193,69,0.25);
    border-radius: 20px;
    padding: 2px 9px;
    font-size: 0.72rem;
    cursor: pointer;
    transition: background 0.15s;
    user-select: none;
  }
  .tag:hover { background: rgba(224,193,69,0.2); }
  .tag.tag-copied { background: var(--green-dim); color: var(--green); border-color: rgba(91,214,159,0.3); }

  /* ── Lightbox ── */
  #lightbox {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(8,15,30,0.93);
    z-index: 1000;
    align-items: center;
    justify-content: center;
    cursor: zoom-out;
    padding: 20px;
  }
  #lightbox.open { display: flex; }
  #lightbox img {
    max-width: 90vw;
    max-height: 85vh;
    border-radius: 10px;
    box-shadow: 0 8px 60px rgba(0,0,0,0.7);
    cursor: default;
  }
  #lightbox-close {
    position: absolute;
    top: 18px;
    right: 22px;
    background: none;
    border: none;
    color: var(--muted);
    font-size: 1.6rem;
    cursor: pointer;
    line-height: 1;
    padding: 4px 8px;
    border-radius: 6px;
  }
  #lightbox-close:hover { color: var(--white); background: var(--surface2); }

  /* ── Toast ── */
  #toast {
    position: fixed;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%) translateY(20px);
    background: #1A2540;
    border: 1px solid var(--border);
    color: var(--text);
    padding: 9px 18px;
    border-radius: 9px;
    font-size: 0.8rem;
    opacity: 0;
    transition: opacity 0.2s, transform 0.2s;
    pointer-events: none;
    z-index: 500;
    white-space: nowrap;
  }
  #toast.show {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
  #toast.error {
    border-color: rgba(255,79,218,0.3);
    color: #FF9EED;
  }

  /* ── Empty state ── */
  .empty {
    grid-column: 1 / -1;
    text-align: center;
    padding: 60px 20px;
    color: var(--muted);
  }
  .empty h2 { font-size: 1.1rem; margin-bottom: 8px; color: var(--text); }
  .empty code {
    background: var(--surface2);
    padding: 2px 7px;
    border-radius: 5px;
    font-size: 0.85rem;
    color: var(--blue);
  }

  /* ── Error banner ── */
  .error-banner {
    background: rgba(255,79,218,0.1);
    border: 1px solid rgba(255,79,218,0.25);
    color: #FF9EED;
    padding: 8px 18px;
    font-size: 0.82rem;
    text-align: center;
  }
</style>
</head>
<body>

<!-- Lightbox -->
<div id="lightbox">
  <button id="lightbox-close" title="Close">✕</button>
  <img id="lightbox-img" src="" alt="">
</div>

<!-- Toast -->
<div id="toast"></div>

<header>
  <div class="brand">BoBe<span class="brand-dot">.</span></div>
  <div class="header-sep"></div>
  <div class="header-date">{{ date }}</div>
  {% if topics %}
  <span class="header-count">{{ topics|length }} topic{{ 's' if topics|length != 1 else '' }}</span>
  {% endif %}
  <div class="spacer"></div>
  {% if available_dates|length > 1 %}
  <form method="get" action="/" style="margin:0">
    <select class="date-select" name="date" onchange="this.form.submit()" title="Switch date">
      {% for d in available_dates %}
      <option value="{{ d }}"{% if d == date %} selected{% endif %}>{{ d }}</option>
      {% endfor %}
    </select>
  </form>
  {% endif %}
  <div class="lang-toggle">
    <button class="lang-btn active" id="btn-en" onclick="setLang('en')">EN</button>
    <button class="lang-btn" id="btn-ru" onclick="setLang('ru')">RU</button>
  </div>
</header>

{% if error %}
<div class="error-banner">{{ error }}</div>
{% endif %}

<main class="grid">
{% if topics %}
  {% for t in topics %}
  <div class="card" id="card-{{ loop.index }}">

    <!-- EN Image -->
    <div class="card-img en-only" {% if t.image_filename %}data-src="/images/{{ t.image_filename }}"{% endif %}
         title="{% if t.image_filename %}Click to enlarge{% endif %}">
      {% if t.image_filename %}
      <img id="img-{{ loop.index }}" src="/images/{{ t.image_filename }}" alt="{{ t.topic }}" loading="lazy">
      <div class="img-overlay"></div>
      {% else %}
      <div class="no-img">
        <span class="no-img-icon">🖼</span>
        <span>No image generated</span>
      </div>
      {% endif %}
      <div class="img-loading-overlay" id="overlay-{{ loop.index }}">
        <div class="spinner"></div>
        <span class="spinner-label">Generating new image…</span>
      </div>
    </div>

    <!-- RU Image -->
    <div class="card-img ru-only" {% if t.image_filename_ru %}data-src="/images/{{ t.image_filename_ru }}"{% endif %}
         title="{% if t.image_filename_ru %}Click to enlarge{% endif %}">
      {% if t.image_filename_ru %}
      <img src="/images/{{ t.image_filename_ru }}" alt="{{ t.topic }}" loading="lazy">
      <div class="img-overlay"></div>
      {% else %}
      <div class="no-img">
        <span class="no-img-icon">🖼</span>
        <span>No Russian image</span>
      </div>
      {% endif %}
    </div>

    <!-- Image approval actions -->
    <div class="image-actions">
      <span class="img-status" id="status-{{ loop.index }}">Pending review</span>
      <button class="action-btn approve-btn" id="approve-{{ loop.index }}"
              onclick="approveImage({{ loop.index }})">✓ Approve</button>
      <button class="action-btn regen-btn" id="regen-{{ loop.index }}"
              onclick="regenImage({{ loop.index }})">↻ Regenerate</button>
    </div>

    <div class="card-body">
      <h2 class="topic-title">{{ t.topic }}</h2>

      <!-- Platform tabs -->
      <div class="tab-bar">
        <button class="tab active" data-tab="twitter-{{ loop.index }}">
          <span class="platform-icon">𝕏</span> Twitter
        </button>
        <button class="tab" data-tab="telegram-{{ loop.index }}">
          <span class="platform-icon">✈</span> Telegram
        </button>
      </div>

      <!-- Twitter panel -->
      <div class="panel active" id="twitter-{{ loop.index }}">
        <!-- EN Twitter -->
        <div class="en-only">
          {% if t.twitter %}
          {% set tweets = t.twitter.split('---') %}
          <div class="content-box" id="tw-box-{{ loop.index }}">{% for tweet in tweets %}{{ tweet.strip() }}{% if not loop.last %}
<hr class="tweet-divider">
{% endif %}{% endfor %}</div>
          <div class="content-actions">
            <span class="char-count">{{ t.twitter|length }} chars</span>
            <button class="copy-btn" data-raw="{{ t.twitter | e }}">Copy</button>
          </div>
          {% else %}
          <div class="content-box" style="color:var(--muted);font-style:italic;">No Twitter content</div>
          {% endif %}
        </div>
        <!-- RU Twitter -->
        <div class="ru-only">
          {% if t.twitter_ru %}
          {% set tweets_ru = t.twitter_ru.split('---') %}
          <div class="content-box" id="tw-box-ru-{{ loop.index }}">{% for tweet in tweets_ru %}{{ tweet.strip() }}{% if not loop.last %}
<hr class="tweet-divider">
{% endif %}{% endfor %}</div>
          <div class="content-actions">
            <span class="char-count">{{ t.twitter_ru|length }} chars</span>
            <button class="copy-btn" data-raw="{{ t.twitter_ru | e }}">Copy</button>
          </div>
          {% else %}
          <div class="content-box" style="color:var(--muted);font-style:italic;">Нет контента для Twitter</div>
          {% endif %}
        </div>
      </div>

      <!-- Telegram panel -->
      <div class="panel" id="telegram-{{ loop.index }}">
        <!-- EN Telegram -->
        <div class="en-only">
          {% if t.telegram %}
          <div class="content-box" id="tg-box-{{ loop.index }}">{{ t.telegram }}</div>
          <div class="content-actions">
            <span class="char-count">{{ t.telegram|length }} chars</span>
            <button class="copy-btn" data-raw="{{ t.telegram | e }}">Copy</button>
          </div>
          {% else %}
          <div class="content-box" style="color:var(--muted);font-style:italic;">No Telegram content</div>
          {% endif %}
        </div>
        <!-- RU Telegram -->
        <div class="ru-only">
          {% if t.telegram_ru %}
          <div class="content-box" id="tg-box-ru-{{ loop.index }}">{{ t.telegram_ru }}</div>
          <div class="content-actions">
            <span class="char-count">{{ t.telegram_ru|length }} chars</span>
            <button class="copy-btn" data-raw="{{ t.telegram_ru | e }}">Copy</button>
          </div>
          {% else %}
          <div class="content-box" style="color:var(--muted);font-style:italic;">Нет контента для Telegram</div>
          {% endif %}
        </div>
      </div>

      <!-- EN Hashtags -->
      {% if t.hashtag_list %}
      <div class="en-only">
        <div class="hashtags">
          {% for tag in t.hashtag_list %}
          <span class="tag" data-tag="{{ tag }}" title="Click to copy">{{ tag }}</span>
          {% endfor %}
        </div>
      </div>
      {% endif %}

      <!-- RU Hashtags -->
      {% if t.hashtag_list_ru %}
      <div class="ru-only">
        <div class="hashtags">
          {% for tag in t.hashtag_list_ru %}
          <span class="tag" data-tag="{{ tag }}" title="Click to copy">{{ tag }}</span>
          {% endfor %}
        </div>
      </div>
      {% endif %}

    </div>
  </div>
  {% endfor %}

{% else %}
  <div class="empty">
    <h2>No content found for {{ date }}</h2>
    <p>Run <code>/weekly-pipeline</code> to generate content first.</p>
  </div>
{% endif %}
</main>

<script>
// ── Topic data embedded from server ────────────────────────────────────────
const TOPICS       = {{ topics_json | safe }};
const CURRENT_DATE = {{ date_json | safe }};
const HAS_GENERATOR = {{ has_generator | safe }};

// ── Language toggle ──────────────────────────────────────────────────────────
function setLang(lang) {
  document.body.classList.toggle('lang-ru', lang === 'ru');
  document.getElementById('btn-en').classList.toggle('active', lang === 'en');
  document.getElementById('btn-ru').classList.toggle('active', lang === 'ru');
  localStorage.setItem('bobe-lang', lang);
}
// Restore language preference on load
(function(){ if(localStorage.getItem('bobe-lang')==='ru') setLang('ru'); })();

// ── Toast ───────────────────────────────────────────────────────────────────
let toastTimer;
function showToast(msg, isError = false) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'show' + (isError ? ' error' : '');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.className = ''; }, 3000);
}

// ── Tab switching ────────────────────────────────────────────────────────────
document.querySelectorAll('.tab-bar').forEach(bar => {
  bar.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const card = tab.closest('.card-body');
      const target = tab.dataset.tab;
      bar.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      card.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById(target).classList.add('active');
    });
  });
});

// ── Copy buttons ─────────────────────────────────────────────────────────────
function flashCopy(el, successLabel) {
  const orig = el.textContent;
  el.textContent = successLabel;
  el.classList.add('copied');
  setTimeout(() => { el.textContent = orig; el.classList.remove('copied'); }, 2000);
}

function copyText(text) {
  if (navigator.clipboard) {
    return navigator.clipboard.writeText(text);
  }
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  document.execCommand('copy');
  document.body.removeChild(ta);
  return Promise.resolve();
}

document.querySelectorAll('.copy-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const text = btn.dataset.raw || '';
    copyText(text).then(() => flashCopy(btn, 'Copied ✓')).catch(() => flashCopy(btn, 'Copied ✓'));
  });
});

// ── Hashtag copy ─────────────────────────────────────────────────────────────
document.querySelectorAll('.tag').forEach(tag => {
  tag.addEventListener('click', () => {
    copyText(tag.dataset.tag).then(() => {
      const orig = tag.textContent;
      tag.textContent = '✓';
      tag.classList.add('tag-copied');
      setTimeout(() => { tag.textContent = orig; tag.classList.remove('tag-copied'); }, 1500);
    });
  });
});

// ── Lightbox ─────────────────────────────────────────────────────────────────
const lightbox = document.getElementById('lightbox');
const lightImg  = document.getElementById('lightbox-img');
const lbClose   = document.getElementById('lightbox-close');

document.querySelectorAll('.card-img[data-src]').forEach(el => {
  el.addEventListener('click', (e) => {
    if (e.target.closest('.img-loading-overlay')) return;
    lightImg.src = el.dataset.src;
    lightbox.classList.add('open');
    document.body.style.overflow = 'hidden';
  });
});

function closeLightbox() {
  lightbox.classList.remove('open');
  document.body.style.overflow = '';
  lightImg.src = '';
}

lbClose.addEventListener('click', closeLightbox);
lightbox.addEventListener('click', e => { if (e.target === lightbox) closeLightbox(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeLightbox(); });

// ── Approval state ───────────────────────────────────────────────────────────
function setApprovalUI(idx, status) {
  const statusEl  = document.getElementById(`status-${idx}`);
  const approveBtn = document.getElementById(`approve-${idx}`);
  const card      = document.getElementById(`card-${idx}`);
  if (!statusEl || !approveBtn) return;

  if (status === 'approved') {
    statusEl.textContent = 'Approved ✓';
    statusEl.className   = 'img-status approved';
    approveBtn.textContent = '✓ Approved';
    approveBtn.classList.add('approved');
    card.classList.add('is-approved');
  } else {
    statusEl.textContent = 'Pending review';
    statusEl.className   = 'img-status';
    approveBtn.textContent = '✓ Approve';
    approveBtn.classList.remove('approved');
    card.classList.remove('is-approved');
  }
}

async function loadApprovals() {
  try {
    const res  = await fetch(`/api/approvals?date=${encodeURIComponent(CURRENT_DATE)}`);
    const data = await res.json();
    TOPICS.forEach((t, i) => {
      const entry = data[t.topic];
      if (entry) setApprovalUI(i + 1, entry.status);
    });
  } catch (e) {
    console.warn('Could not load approvals:', e);
  }
}

async function approveImage(idx) {
  const t        = TOPICS[idx - 1];
  const approveBtn = document.getElementById(`approve-${idx}`);
  const isApproved = approveBtn.classList.contains('approved');
  const newStatus  = isApproved ? 'pending' : 'approved';

  try {
    await fetch('/api/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date: CURRENT_DATE, topic: t.topic, status: newStatus }),
    });
    setApprovalUI(idx, newStatus);
    showToast(newStatus === 'approved' ? 'Image approved ✓' : 'Approval removed');
  } catch (e) {
    showToast('Could not save approval', true);
  }
}

// ── Regeneration (async + polling) ───────────────────────────────────────────
async function regenImage(idx) {
  if (!HAS_GENERATOR) {
    showToast('Image generator not available — check GOOGLE_AI_API_KEY', true);
    return;
  }

  const t          = TOPICS[idx - 1];
  const overlay    = document.getElementById(`overlay-${idx}`);
  const approveBtn = document.getElementById(`approve-${idx}`);
  const regenBtn   = document.getElementById(`regen-${idx}`);
  const imgEl      = document.getElementById(`img-${idx}`);
  const cardImg    = imgEl ? imgEl.closest('.card-img') : null;

  overlay.classList.add('active');
  approveBtn.disabled = true;
  regenBtn.disabled   = true;

  try {
    const startRes = await fetch('/api/regenerate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        date:       CURRENT_DATE,
        topic:      t.topic,
        img_prompt: t.img_prompt || '',
        style:      'tech',
      }),
    });
    const startData = await startRes.json();
    if (!startData.success) {
      showToast('Could not start generation: ' + (startData.error || 'Unknown'), true);
      return;
    }

    const jobId = startData.job_id;
    const result = await pollJob(jobId);

    if (result.status === 'done') {
      if (imgEl) imgEl.src = `/images/${result.filename}?t=${Date.now()}`;
      if (cardImg) cardImg.dataset.src = `/images/${result.filename}`;
      TOPICS[idx - 1].image_filename = result.filename;
      setApprovalUI(idx, 'pending');
      showToast('New image generated — please review');
    } else {
      showToast('Generation failed: ' + (result.error || 'Unknown error'), true);
    }
  } catch (e) {
    showToast('Generation failed: ' + e.message, true);
  } finally {
    overlay.classList.remove('active');
    approveBtn.disabled = false;
    regenBtn.disabled   = false;
  }
}

async function pollJob(jobId, intervalMs = 3000, maxWaitMs = 300000) {
  const deadline = Date.now() + maxWaitMs;
  while (Date.now() < deadline) {
    await new Promise(r => setTimeout(r, intervalMs));
    const res  = await fetch(`/api/regen-status/${jobId}`);
    const data = await res.json();
    if (data.status === 'done' || data.status === 'error') return data;
  }
  return { status: 'error', error: 'Timed out waiting for generation' };
}

// ── Init ─────────────────────────────────────────────────────────────────────
loadApprovals();
</script>
</body>
</html>"""


# ── Approval API routes ────────────────────────────────────────────────────────

@app.route("/api/approvals")
def api_get_approvals():
    date = request.args.get("date", "")
    return jsonify(load_approvals(date))


@app.route("/api/approve", methods=["POST"])
def api_approve():
    data   = request.get_json(force=True)
    date   = data.get("date", "")
    topic  = data.get("topic", "")
    status = data.get("status", "approved")

    if not date or not topic:
        return jsonify({"success": False, "error": "date and topic required"}), 400

    approvals = load_approvals(date)
    approvals[topic] = {"status": status}
    save_approvals(date, approvals)
    return jsonify({"success": True})


@app.route("/api/regenerate", methods=["POST"])
def api_regenerate():
    """Start an async EN image regeneration job (Gemini). Returns a job_id immediately."""
    if not HAS_GENERATOR:
        return jsonify({"success": False, "error": "Image generator not available. Check GOOGLE_AI_API_KEY and google-genai install."}), 503

    data       = request.get_json(force=True)
    date       = data.get("date", "")
    topic      = data.get("topic", "")
    img_prompt = data.get("img_prompt", "")
    style      = data.get("style", "tech")

    if not date or not topic:
        return jsonify({"success": False, "error": "date and topic required"}), 400

    topic_slug   = re.sub(r"[^a-z0-9]+", "_", topic.lower())[:30].strip("_")
    timestamp    = int(time.time())
    date_slug    = date.replace("week:", "")
    subdir       = f"{date_slug}-weekly"
    filename     = f"{subdir}/{date_slug}_{topic_slug}_regen_{timestamp}.png"
    regen_dir    = IMAGES_DIR / subdir
    regen_dir.mkdir(parents=True, exist_ok=True)
    output_path  = str(IMAGES_DIR / filename)
    job_id       = str(uuid.uuid4())

    with _jobs_lock:
        _jobs[job_id] = {"status": "running", "filename": None, "error": None}

    def _run():
        try:
            prompt = img_prompt if img_prompt else build_prompt(topic=topic, style=style)
            gen_img(prompt, output_path, DEFAULT_REFERENCES)
            approvals = load_approvals(date)
            approvals[topic] = {"status": "pending", "image": filename}
            save_approvals(date, approvals)
            with _jobs_lock:
                _jobs[job_id] = {"status": "done", "filename": filename, "error": None}
        except Exception as e:
            with _jobs_lock:
                _jobs[job_id] = {"status": "error", "filename": None, "error": str(e)}

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"success": True, "job_id": job_id})


@app.route("/api/regen-status/<job_id>")
def api_regen_status(job_id):
    """Poll for job completion."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        return jsonify({"status": "unknown"}), 404
    return jsonify(job)


# ── Flask routes ───────────────────────────────────────────────────────────────

@app.route("/images/<path:filename>")
def serve_image(filename):
    if (IMAGES_DIR / filename).exists():
        return send_from_directory(str(IMAGES_DIR), filename)
    return send_from_directory(str(CONTENT_DIR), filename)


@app.route("/")
def index():
    date_param      = request.args.get("date")
    available_dates = list_available_dates()
    error           = None

    if not available_dates:
        return render_template_string(
            HTML,
            topics=[], date="—", available_dates=[],
            topics_json="[]", date_json='""',
            has_generator="true" if HAS_GENERATOR else "false",
            error="No weekly content Excel files found in outputs/content/",
        )

    selected = date_param if date_param in available_dates else available_dates[0]
    xlsx     = find_excel(selected)

    if not xlsx:
        error  = f"No Excel file found for {selected}"
        topics = []
    else:
        topics = load_content(xlsx)

    topics_json = json.dumps([
        {
            "topic":             t["topic"],
            "img_prompt":        t.get("img_prompt", ""),
            "img_prompt_ru":     t.get("img_prompt_ru", ""),
            "image_filename":    t.get("image_filename", ""),
            "image_filename_ru": t.get("image_filename_ru", ""),
            "date":              t.get("date", ""),
        }
        for t in topics
    ])

    return render_template_string(
        HTML,
        topics=topics,
        date=selected,
        available_dates=available_dates,
        topics_json=topics_json,
        date_json=json.dumps(selected),
        has_generator="true" if HAS_GENERATOR else "false",
        error=error,
    )


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    print(f"\n  BoBe Content Dashboard")
    print(f"  Content dir : {CONTENT_DIR}")
    dates = list_available_dates()
    print(f"  Found dates : {', '.join(dates) if dates else 'none'}")
    print(f"  Generator   : {'available' if HAS_GENERATOR else 'unavailable (check GOOGLE_AI_API_KEY)'}")
    print(f"\n  → http://localhost:5001\n")
    print("  Press Ctrl+C to stop.\n")
    app.run(host="127.0.0.1", port=5001, debug=False, threaded=True)
