#!/usr/bin/env python3
"""
Static Site Builder

Multi-client: reads brand name from client config for page titles and footer.
Renders the content dashboard as static HTML files for deployment
to Cloudflare Pages or GitHub Pages. Zero hosting cost.
Includes bilingual EN/RU toggle matching the Flask dashboard.
Landing page + login page with per-client session auth.

Usage:
  python scripts/build_static.py                          # build all dates to dist/
  python scripts/build_static.py --output dist             # explicit output dir
  python scripts/build_static.py --date week:2026-02-16    # build single weekly date
  python scripts/build_static.py --client newclient        # build for a specific client
"""

import os
import sys
import json
import shutil
import hashlib
import argparse
from pathlib import Path

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent))

import client_config

from web_viewer import (
    load_content, resolve_image, list_available_dates, find_excel,
    CONTENT_DIR, IMAGES_DIR,
)

try:
    from jinja2 import Environment
except ImportError:
    print("jinja2 not installed. Run:  venv/bin/pip install jinja2")
    sys.exit(1)


def sanitize_date_id(date_id):
    """Convert date identifier to a safe filename.
    'week:2026-02-16' -> 'week-2026-02-16'
    """
    return date_id.replace(":", "-")


def date_display_label(date_id):
    """Human-readable label for a date identifier."""
    if date_id.startswith("week:"):
        return f"Week of {date_id[5:]}"
    return date_id


def generate_credentials():
    """Auto-generate credentials for all onboarded clients.

    Username: 'admin' for every client
    Password: '{client_id}123'  (e.g. bobe → bobe123)

    Reads all directories in clients/ (skips _template and any starting with _).
    No manual config or secrets required — credentials are derived from client IDs.

    Returns list of dicts: {username, password_hash, client_id, role, display_name}
    """
    clients_dir = Path(__file__).parent.parent / "clients"
    result = []

    for client_dir in sorted(clients_dir.iterdir()):
        if not client_dir.is_dir() or client_dir.name.startswith("_"):
            continue
        config_path = client_dir / "config.json"
        if not config_path.exists():
            continue
        with open(config_path) as f:
            config = json.load(f)
        client_id = config.get("client_id", client_dir.name)
        display_name = config.get("display_name", client_id)
        password = f"{client_id}123"
        result.append({
            "username": "admin",
            "password_hash": hashlib.sha256(password.encode()).hexdigest(),
            "client_id": client_id,
            "role": "client",
            "display_name": display_name,
        })

    print(f"  Credentials: {len(result)} client(s) auto-generated")
    return result


# ── Jinja2 HTML template — Dashboard content page ─────────────────────────────

STATIC_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ brand_name }} Content Dashboard — {{ date_label }}</title>
<link rel="icon" type="image/jpeg" href="../../favicon.jpg">
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

  /* Header */
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

  .header-sep { width: 1px; height: 20px; background: var(--border); }

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

  /* Language toggle */
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
  .lang-btn.active { background: var(--blue); color: #fff; }
  .lang-btn:hover:not(.active) { color: var(--text); }

  /* Logout button */
  .logout-btn {
    background: none;
    border: 1px solid var(--border);
    color: var(--muted);
    padding: 5px 12px;
    border-radius: 7px;
    cursor: pointer;
    font-size: 0.75rem;
    transition: all 0.15s;
    font-family: inherit;
  }
  .logout-btn:hover { border-color: var(--blue); color: var(--text); }

  /* EN/RU visibility */
  .ru-only { display: none !important; }
  body.lang-ru .ru-only { display: block !important; }
  body.lang-ru .en-only { display: none !important; }

  /* Grid */
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

  /* Card */
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

  /* Card image */
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

  /* Card body */
  .card-body {
    padding: 16px 18px 18px;
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .topic-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .day-badge {
    background: var(--blue-dim);
    border: 1px solid rgba(21,137,220,0.25);
    color: var(--blue);
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.3px;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .topic-title {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--white);
    line-height: 1.45;
  }

  /* Platform tabs */
  .tab-bar { display: flex; gap: 6px; }

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

  /* Content panels */
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
  .content-box::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }

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

  .char-count { font-size: 0.72rem; color: var(--muted); }

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

  /* Hashtags */
  .hashtags { display: flex; flex-wrap: wrap; gap: 5px; padding-top: 2px; }
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

  /* Lightbox */
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

  /* Toast */
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
  #toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }

  /* Empty state */
  .empty {
    grid-column: 1 / -1;
    text-align: center;
    padding: 60px 20px;
    color: var(--muted);
  }
  .empty h2 { font-size: 1.1rem; margin-bottom: 8px; color: var(--text); }

  /* Footer */
  .site-footer {
    text-align: center;
    padding: 20px 24px 28px;
    font-size: 0.72rem;
    color: var(--muted);
    letter-spacing: 0.2px;
  }
</style>
</head>
<body>
{% autoescape false %}
<script>
(function() {
  var auth = sessionStorage.getItem('dash_auth');
  if (!auth) { window.location.replace('../../login.html'); return; }
  try {
    var session = JSON.parse(auth);
    var expectedClient = '{{ expected_client_id }}';
    if (session.role !== 'admin' && session.clientId !== expectedClient) {
      sessionStorage.removeItem('dash_auth');
      window.location.replace('../../login.html');
    }
  } catch(e) {
    sessionStorage.removeItem('dash_auth');
    window.location.replace('../../login.html');
  }
})();
</script>
{% endautoescape %}

<!-- Lightbox -->
<div id="lightbox">
  <button id="lightbox-close" title="Close">&#10005;</button>
  <img id="lightbox-img" src="" alt="">
</div>

<!-- Toast -->
<div id="toast"></div>

<header>
  <div class="brand">{{ brand_name }}<span class="brand-dot">.</span></div>
  <div class="header-sep"></div>
  <div class="header-date">{{ date_label }}</div>
  {% if topics %}
  <span class="header-count">{{ topics|length }} topic{{ 's' if topics|length != 1 else '' }}</span>
  {% endif %}
  <div class="spacer"></div>
  {% if date_options|length > 1 %}
  <select class="date-select" onchange="window.location=this.value" title="Switch date">
    {% for opt in date_options %}
    <option value="{{ opt.filename }}"{% if opt.date_id == current_date_id %} selected{% endif %}>{{ opt.label }}</option>
    {% endfor %}
  </select>
  {% endif %}
  <div class="lang-toggle">
    <button class="lang-btn active" id="btn-en" onclick="setLang('en')">EN</button>
    <button class="lang-btn" id="btn-ru" onclick="setLang('ru')">RU</button>
  </div>
  <button class="logout-btn" onclick="logout()" title="Log out">Log out</button>
</header>

<main class="grid">
{% if topics %}
  {% for t in topics %}
  <div class="card" id="card-{{ loop.index }}">

    <!-- EN Image -->
    <div class="card-img en-only" {% if t.image_filename %}data-src="images/{{ t.image_filename }}"{% endif %}
         title="{% if t.image_filename %}Click to enlarge{% endif %}">
      {% if t.image_filename %}
      <img src="images/{{ t.image_filename }}" alt="{{ t.topic }}" loading="lazy">
      <div class="img-overlay"></div>
      {% else %}
      <div class="no-img">
        <span class="no-img-icon">&#128444;</span>
        <span>No image generated</span>
      </div>
      {% endif %}
    </div>

    <!-- RU Image -->
    <div class="card-img ru-only" {% if t.image_filename_ru %}data-src="images/{{ t.image_filename_ru }}"{% endif %}
         title="{% if t.image_filename_ru %}Click to enlarge{% endif %}">
      {% if t.image_filename_ru %}
      <img src="images/{{ t.image_filename_ru }}" alt="{{ t.topic }}" loading="lazy">
      <div class="img-overlay"></div>
      {% else %}
      <div class="no-img">
        <span class="no-img-icon">&#128444;</span>
        <span>No Russian image</span>
      </div>
      {% endif %}
    </div>

    <div class="card-body">
      <div class="topic-header">
        {% if t.day %}
        <span class="day-badge">{{ t.day }}</span>
        {% endif %}
        <h2 class="topic-title">{{ t.topic }}</h2>
      </div>

      <!-- Platform tabs -->
      <div class="tab-bar">
        <button class="tab active" data-tab="twitter-{{ loop.index }}">
          <span class="platform-icon">&#120143;</span> Twitter
        </button>
        <button class="tab" data-tab="telegram-{{ loop.index }}">
          <span class="platform-icon">&#9992;</span> Telegram
        </button>
      </div>

      <!-- Twitter panel -->
      <div class="panel active" id="twitter-{{ loop.index }}">
        <!-- EN Twitter -->
        <div class="en-only">
          {% if t.twitter %}
          {% set tweets = t.twitter.split('---') %}
          <div class="content-box">{% for tweet in tweets %}{{ tweet.strip() }}{% if not loop.last %}
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
          <div class="content-box">{% for tweet in tweets_ru %}{{ tweet.strip() }}{% if not loop.last %}
<hr class="tweet-divider">
{% endif %}{% endfor %}</div>
          <div class="content-actions">
            <span class="char-count">{{ t.twitter_ru|length }} chars</span>
            <button class="copy-btn" data-raw="{{ t.twitter_ru | e }}">Copy</button>
          </div>
          {% else %}
          <div class="content-box" style="color:var(--muted);font-style:italic;">&#1053;&#1077;&#1090; &#1082;&#1086;&#1085;&#1090;&#1077;&#1085;&#1090;&#1072; &#1076;&#1083;&#1103; Twitter</div>
          {% endif %}
        </div>
      </div>

      <!-- Telegram panel -->
      <div class="panel" id="telegram-{{ loop.index }}">
        <!-- EN Telegram -->
        <div class="en-only">
          {% if t.telegram %}
          <div class="content-box">{{ t.telegram }}</div>
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
          <div class="content-box">{{ t.telegram_ru }}</div>
          <div class="content-actions">
            <span class="char-count">{{ t.telegram_ru|length }} chars</span>
            <button class="copy-btn" data-raw="{{ t.telegram_ru | e }}">Copy</button>
          </div>
          {% else %}
          <div class="content-box" style="color:var(--muted);font-style:italic;">&#1053;&#1077;&#1090; &#1082;&#1086;&#1085;&#1090;&#1077;&#1085;&#1090;&#1072; &#1076;&#1083;&#1103; Telegram</div>
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
    <h2>No content found</h2>
    <p>No content is available for this date.</p>
  </div>
{% endif %}
</main>

<footer class="site-footer">Generated by {{ brand_name }} Content Pipeline</footer>

<script>
// Logout
function logout() {
  sessionStorage.removeItem('dash_auth');
  window.location.href = '../../login.html';
}

// Language toggle
function setLang(lang) {
  document.body.classList.toggle('lang-ru', lang === 'ru');
  document.getElementById('btn-en').classList.toggle('active', lang === 'en');
  document.getElementById('btn-ru').classList.toggle('active', lang === 'ru');
  localStorage.setItem('content-dash-lang', lang);
}
(function(){ if(localStorage.getItem('content-dash-lang')==='ru') setLang('ru'); })();

// Toast
let toastTimer;
function showToast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'show';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.className = ''; }, 3000);
}

// Tab switching
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

// Copy helpers
function copyText(text) {
  if (navigator.clipboard) return navigator.clipboard.writeText(text);
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

function flashCopy(el, label) {
  const orig = el.textContent;
  el.textContent = label;
  el.classList.add('copied');
  setTimeout(() => { el.textContent = orig; el.classList.remove('copied'); }, 2000);
}

// Copy buttons
document.querySelectorAll('.copy-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const text = btn.dataset.raw || '';
    copyText(text).then(() => flashCopy(btn, 'Copied ✓'));
  });
});

// Hashtag copy
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

// Lightbox
const lightbox = document.getElementById('lightbox');
const lightImg = document.getElementById('lightbox-img');
const lbClose  = document.getElementById('lightbox-close');

document.querySelectorAll('.card-img[data-src]').forEach(el => {
  el.addEventListener('click', () => {
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
</script>
</body>
</html>"""


# ── Landing page template (placeholder) ───────────────────────────────────────

LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ brand_name }} Content Platform</title>
<link rel="icon" type="image/jpeg" href="favicon.jpg">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0D1526; --surface: #111B32; --border: rgba(21,137,220,0.15);
    --blue: #1589DC; --pink: #FF4FDA; --muted: #6B82A8; --text: #C8D8EE;
  }
  html, body {
    background: var(--bg); color: #fff;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
    min-height: 100vh; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
  }
  .placeholder-badge {
    position: fixed; top: 14px; right: 16px;
    background: rgba(224,193,69,0.1); border: 1px solid rgba(224,193,69,0.25);
    color: #E0C145; font-size: 0.65rem; padding: 3px 10px; border-radius: 20px;
    letter-spacing: 0.5px; font-weight: 600;
  }
  .hero {
    display: flex; flex-direction: column; align-items: center;
    gap: 20px; text-align: center; padding: 40px 24px; max-width: 480px;
  }
  .eyebrow {
    font-size: 0.72rem; font-weight: 700; letter-spacing: 2px;
    color: var(--muted); text-transform: uppercase;
  }
  .brand-name {
    font-size: 3.5rem; font-weight: 800; letter-spacing: -1px; line-height: 1;
    color: var(--blue);
  }
  .brand-dot { color: var(--pink); }
  .tagline {
    font-size: 1rem; color: var(--text); line-height: 1.6; max-width: 340px;
  }
  .login-btn {
    margin-top: 8px;
    background: var(--blue); color: #fff; border: none;
    padding: 13px 36px; border-radius: 10px; font-size: 0.95rem;
    font-weight: 600; cursor: pointer; text-decoration: none;
    transition: background 0.15s, transform 0.1s;
    display: inline-block;
  }
  .login-btn:hover { background: #1070BB; }
  .login-btn:active { transform: scale(0.98); }
  .site-footer {
    position: fixed; bottom: 18px;
    font-size: 0.68rem; color: var(--muted); letter-spacing: 0.2px;
  }
</style>
</head>
<body>
<span class="placeholder-badge">Placeholder Design</span>
<div class="hero">
  <p class="eyebrow">Content Platform</p>
  <h1 class="brand-name">{{ brand_name }}<span class="brand-dot">.</span></h1>
  <p class="tagline">Your weekly content, organized and ready to publish.</p>
  <a href="login.html" class="login-btn">Log In</a>
</div>
<footer class="site-footer">{{ brand_name }} Content Platform</footer>
</body>
</html>"""


# ── Login page template ────────────────────────────────────────────────────────

LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Log In — {{ brand_name }}</title>
<link rel="icon" type="image/jpeg" href="favicon.jpg">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0D1526; --surface: #111B32; --surface2: #162038;
    --border: rgba(21,137,220,0.15); --blue: #1589DC; --pink: #FF4FDA;
    --muted: #6B82A8; --text: #C8D8EE; --red: #FF6B6B;
  }
  html, body {
    background: var(--bg); color: #fff;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
    min-height: 100vh; display: flex; flex-direction: column;
    align-items: center; justify-content: center; padding: 24px;
  }
  .card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 16px; padding: 36px 32px; width: 100%; max-width: 380px;
    display: flex; flex-direction: column; gap: 24px;
  }
  .card-header { display: flex; flex-direction: column; gap: 6px; }
  .back-link {
    font-size: 0.75rem; color: var(--muted); text-decoration: none;
    display: flex; align-items: center; gap: 4px; margin-bottom: 8px;
    transition: color 0.15s;
  }
  .back-link:hover { color: var(--text); }
  .card-title { font-size: 1.35rem; font-weight: 700; }
  .card-subtitle { font-size: 0.8rem; color: var(--muted); }
  .field { display: flex; flex-direction: column; gap: 6px; }
  .field label { font-size: 0.78rem; font-weight: 600; color: var(--text); letter-spacing: 0.2px; }
  .field input {
    background: var(--surface2); border: 1px solid var(--border);
    color: #fff; padding: 10px 14px; border-radius: 9px; font-size: 0.9rem;
    outline: none; transition: border-color 0.15s;
    font-family: inherit;
  }
  .field input:focus { border-color: var(--blue); }
  .error-msg {
    background: rgba(255,107,107,0.1); border: 1px solid rgba(255,107,107,0.3);
    color: var(--red); font-size: 0.78rem; padding: 9px 13px; border-radius: 8px;
    display: none;
  }
  .error-msg.show { display: block; }
  .submit-btn {
    background: var(--blue); color: #fff; border: none;
    padding: 12px; border-radius: 9px; font-size: 0.92rem;
    font-weight: 600; cursor: pointer; width: 100%;
    transition: background 0.15s; font-family: inherit;
  }
  .submit-btn:hover { background: #1070BB; }
  .submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }
  .site-footer {
    margin-top: 28px; font-size: 0.68rem; color: var(--muted);
  }
</style>
</head>
<body>
<div class="card">
  <div class="card-header">
    <a href="index.html" class="back-link">&#8592; Back</a>
    <h1 class="card-title">Welcome back</h1>
    <p class="card-subtitle">Log in to access your content dashboard</p>
  </div>
  <div class="field">
    <label for="username">Username</label>
    <input type="text" id="username" placeholder="Enter username" autocomplete="username" autocapitalize="none">
  </div>
  <div class="field">
    <label for="password">Password</label>
    <input type="password" id="password" placeholder="Enter password" autocomplete="current-password">
  </div>
  <div class="error-msg" id="error-msg">Incorrect username or password.</div>
  <button class="submit-btn" id="login-btn" onclick="handleLogin()">Log In</button>
</div>
<footer class="site-footer">{{ brand_name }} Content Platform</footer>

<script>
// Credentials map injected at build time (SHA-256 hashed passwords only)
const CREDENTIALS = {{ credentials_json }};

async function sha256(message) {
  const msgBuffer = new TextEncoder().encode(message);
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

async function handleLogin() {
  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value;
  const btn = document.getElementById('login-btn');
  const errEl = document.getElementById('error-msg');

  if (!username || !password) {
    errEl.textContent = 'Please enter both username and password.';
    errEl.classList.add('show');
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Checking...';
  errEl.classList.remove('show');

  try {
    const hash = await sha256(password);
    const match = CREDENTIALS.find(c => c.username === username && c.password_hash === hash);

    if (!match) {
      errEl.textContent = 'Incorrect username or password.';
      errEl.classList.add('show');
      btn.disabled = false;
      btn.textContent = 'Log In';
      return;
    }

    // Store session
    sessionStorage.setItem('dash_auth', JSON.stringify({
      clientId: match.client_id,
      username: match.username,
      role: match.role,
      display_name: match.display_name
    }));

    // Redirect based on role
    if (match.role === 'admin') {
      window.location.href = 'admin/';
    } else {
      window.location.href = 'dashboard/' + match.client_id + '/';
    }
  } catch (err) {
    errEl.textContent = 'Login error. Please try again.';
    errEl.classList.add('show');
    btn.disabled = false;
    btn.textContent = 'Log In';
  }
}

// Allow Enter key to submit
document.addEventListener('keydown', e => {
  if (e.key === 'Enter') handleLogin();
});
</script>
</body>
</html>"""


def build_site(output_dir, dates=None, credentials=None, active_client="bobe"):
    """Build the static site into output_dir.

    Args:
        output_dir: Path to write the static site (e.g., dist/)
        dates: List of date identifiers to build, or None for all available
        credentials: List of credential dicts from load_credentials()
        active_client: Client ID for scoped output paths
    """
    output = Path(output_dir)

    # Clean previous build
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    # Discover available dates
    all_dates = list_available_dates()
    if not all_dates:
        print("No weekly content files found in outputs/content/")
        return

    build_dates = dates if dates else all_dates

    # Verify requested dates exist
    for d in build_dates:
        if d not in all_dates:
            print(f"  Warning: date '{d}' not found, skipping")
    build_dates = [d for d in build_dates if d in all_dates]

    if not build_dates:
        print("No valid dates to build.")
        return

    # Dashboard subdirectory for this client
    client_dash_dir = output / "dashboard" / active_client
    client_dash_dir.mkdir(parents=True, exist_ok=True)

    # Images go inside the client dashboard dir
    images_out = client_dash_dir / "images"

    # Build date-to-filename mapping for the date picker (across ALL available dates)
    # Filenames are relative within the client dashboard dir
    date_options = []
    for d in all_dates:
        date_options.append({
            "date_id":  d,
            "filename": sanitize_date_id(d) + ".html",
            "label":    date_display_label(d),
        })

    # Set up Jinja2 environments
    env = Environment(autoescape=True)       # for content dashboard pages
    plain_env = Environment(autoescape=False)  # for landing + login pages

    dashboard_template = env.from_string(STATIC_HTML)
    landing_template = plain_env.from_string(LANDING_HTML)
    login_template = plain_env.from_string(LOGIN_HTML)

    images_copied = set()
    pages_built = 0

    for date_id in build_dates:
        xlsx = find_excel(date_id)
        if not xlsx:
            print(f"  Warning: no Excel file for '{date_id}', skipping")
            continue

        topics = load_content(xlsx)
        safe_name = sanitize_date_id(date_id)

        # Copy EN and RU images for this date's topics
        for t in topics:
            for img_key in ("image_filename", "image_filename_ru"):
                img_rel = t.get(img_key)
                if not img_rel:
                    continue

                src = IMAGES_DIR / img_rel
                if not src.exists():
                    src = CONTENT_DIR / img_rel
                if not src.exists():
                    continue

                dst = images_out / img_rel
                if str(dst) not in images_copied:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(src), str(dst))
                    images_copied.add(str(dst))

        # Render the dashboard page (with auth guard)
        html = dashboard_template.render(
            topics=topics,
            date_label=date_display_label(date_id),
            current_date_id=date_id,
            date_options=date_options,
            brand_name=_display_name,
            expected_client_id=active_client,
        )

        page_path = client_dash_dir / f"{safe_name}.html"
        page_path.write_text(html, encoding="utf-8")
        pages_built += 1
        print(f"  Built: dashboard/{active_client}/{page_path.name} ({len(topics)} topics)")

    # Copy favicon if available
    favicon_src = Path(__file__).parent.parent / "reference" / "favicon.jpg"
    if favicon_src.exists():
        shutil.copy2(str(favicon_src), str(output / "favicon.jpg"))

    # Generate dist/dashboard/{client_id}/index.html — redirect to latest date
    latest_page = sanitize_date_id(build_dates[0]) + ".html"
    client_index_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="0; url={latest_page}">
<title>{_display_name} Dashboard</title>
</head>
<body>
<p>Redirecting to <a href="{latest_page}">latest content</a>...</p>
</body>
</html>"""
    (client_dash_dir / "index.html").write_text(client_index_html, encoding="utf-8")

    # Generate dist/index.html — landing page
    landing_html = landing_template.render(brand_name=_display_name)
    (output / "index.html").write_text(landing_html, encoding="utf-8")
    print(f"  Built: index.html (landing page)")

    # Generate dist/login.html — login page with baked-in credentials
    creds_for_js = credentials or []
    credentials_json = json.dumps(creds_for_js, ensure_ascii=False)
    login_html = login_template.render(
        brand_name=_display_name,
        credentials_json=credentials_json,
    )
    (output / "login.html").write_text(login_html, encoding="utf-8")
    creds_count = len(creds_for_js)
    print(f"  Built: login.html ({creds_count} credential(s) baked in)")

    # Calculate total size
    total_size = sum(f.stat().st_size for f in output.rglob("*") if f.is_file())
    size_mb = total_size / (1024 * 1024)

    print(f"\n  Build complete:")
    print(f"    Pages:  {pages_built}")
    print(f"    Images: {len(images_copied)} (EN + RU)")
    print(f"    Total size: {size_mb:.1f} MB")
    print(f"    Output: {output.resolve()}")
    print(f"\n  URL structure:")
    print(f"    /             → Landing page")
    print(f"    /login.html   → Login form")
    print(f"    /dashboard/{active_client}/  → Client dashboard")


_display_name = "Brand"  # module-level default, set in main()


def main():
    global _display_name, CONTENT_DIR, IMAGES_DIR

    parser = argparse.ArgumentParser(description="Static Site Builder")
    parser.add_argument("--output", default="dist",
                        help="Output directory for the static site (default: dist)")
    parser.add_argument("--date", action="append", dest="dates",
                        help="Specific date(s) to build (can be repeated). Omit for all.")
    parser.add_argument("--include-admin", action="store_true", default=False,
                        help="Copy admin/ panel to dist/admin/ after building")
    client_config.add_client_arg(parser)
    args = parser.parse_args()

    active_client = client_config.resolve_client(args)
    config = client_config.load_config(active_client)
    _display_name = config.get("display_name", active_client)

    # Update content dirs to client-scoped paths
    CONTENT_DIR = client_config.get_output_dir(active_client)
    IMAGES_DIR = CONTENT_DIR / "images"

    # Also update the web_viewer module's global vars for find_excel/list_available_dates
    import web_viewer
    web_viewer.CONTENT_DIR = CONTENT_DIR
    web_viewer.IMAGES_DIR = IMAGES_DIR

    # Auto-generate credentials from onboarded clients (username: admin, password: {client_id}123)
    credentials = generate_credentials()

    print(f"\n{_display_name} Static Site Builder")
    print(f"Client: {active_client}")
    print("=" * 40)

    build_site(args.output, args.dates, credentials=credentials, active_client=active_client)

    # Copy admin panel if requested
    if args.include_admin:
        admin_src = Path(__file__).parent.parent / "admin"
        admin_dst = Path(args.output) / "admin"
        if admin_src.exists():
            shutil.copytree(str(admin_src), str(admin_dst), dirs_exist_ok=True)
            print(f"  Admin panel copied to {admin_dst}")
        else:
            print("  Warning: admin/ directory not found, skipping --include-admin")

    # Copy intake form (always — no flag required)
    intake_src = Path(__file__).parent.parent / "intake"
    if intake_src.exists():
        intake_dst = Path(args.output) / "intake"
        shutil.copytree(str(intake_src), str(intake_dst), dirs_exist_ok=True)
        # Never deploy intake-config.js — it contains EmailJS API keys
        config_in_dist = intake_dst / "intake-config.js"
        if config_in_dist.exists():
            config_in_dist.unlink()
        print(f"  Intake form copied to {intake_dst}")


if __name__ == "__main__":
    main()
