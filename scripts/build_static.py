#!/usr/bin/env python3
"""
BoBe Static Site Builder

Renders the content dashboard as static HTML files for deployment
to Cloudflare Pages or GitHub Pages. Zero hosting cost.
Includes bilingual EN/RU toggle matching the Flask dashboard.

Usage:
  python scripts/build_static.py                          # build all dates to dist/
  python scripts/build_static.py --output dist             # explicit output dir
  python scripts/build_static.py --date week:2026-02-16    # build single weekly date
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent))

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


# ── Jinja2 HTML template ───────────────────────────────────────────────────────

STATIC_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BoBe Content Dashboard — {{ date_label }}</title>
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

  /* EN/RU visibility */
  .ru-only { display: none; }
  body.lang-ru .ru-only { display: block; }
  body.lang-ru .en-only { display: none; }

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

<!-- Lightbox -->
<div id="lightbox">
  <button id="lightbox-close" title="Close">&#10005;</button>
  <img id="lightbox-img" src="" alt="">
</div>

<!-- Toast -->
<div id="toast"></div>

<header>
  <div class="brand">BoBe<span class="brand-dot">.</span></div>
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

<footer class="site-footer">Generated by BoBe Content Pipeline</footer>

<script>
// Language toggle
function setLang(lang) {
  document.body.classList.toggle('lang-ru', lang === 'ru');
  document.getElementById('btn-en').classList.toggle('active', lang === 'en');
  document.getElementById('btn-ru').classList.toggle('active', lang === 'ru');
  localStorage.setItem('bobe-lang', lang);
}
(function(){ if(localStorage.getItem('bobe-lang')==='ru') setLang('ru'); })();

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


def build_site(output_dir, dates=None):
    """Build the static site into output_dir.

    Args:
        output_dir: Path to write the static site (e.g., dist/)
        dates: List of date identifiers to build, or None for all available
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

    # Build date-to-filename mapping for the date picker (across ALL available dates)
    date_options = []
    for d in all_dates:
        date_options.append({
            "date_id":  d,
            "filename": sanitize_date_id(d) + ".html",
            "label":    date_display_label(d),
        })

    # Set up Jinja2 environment
    env = Environment(autoescape=True)
    template = env.from_string(STATIC_HTML)

    images_out = output / "images"
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

        # Render the page
        html = template.render(
            topics=topics,
            date_label=date_display_label(date_id),
            current_date_id=date_id,
            date_options=date_options,
        )

        page_path = output / f"{safe_name}.html"
        page_path.write_text(html, encoding="utf-8")
        pages_built += 1
        print(f"  Built: {page_path.name} ({len(topics)} topics)")

    # Generate index.html that redirects to the most recent date
    latest = sanitize_date_id(build_dates[0])
    index_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="0; url={latest}.html">
<title>BoBe Content Dashboard</title>
</head>
<body>
<p>Redirecting to <a href="{latest}.html">latest content</a>...</p>
</body>
</html>"""
    (output / "index.html").write_text(index_html, encoding="utf-8")

    # Calculate total size
    total_size = sum(f.stat().st_size for f in output.rglob("*") if f.is_file())
    size_mb = total_size / (1024 * 1024)

    print(f"\n  Build complete:")
    print(f"    Pages:  {pages_built}")
    print(f"    Images: {len(images_copied)} (EN + RU)")
    print(f"    Total size: {size_mb:.1f} MB")
    print(f"    Output: {output.resolve()}")


def main():
    parser = argparse.ArgumentParser(description="BoBe Static Site Builder")
    parser.add_argument("--output", default="dist",
                        help="Output directory for the static site (default: dist)")
    parser.add_argument("--date", action="append", dest="dates",
                        help="Specific date(s) to build (can be repeated). Omit for all.")
    args = parser.parse_args()

    print("\nBoBe Static Site Builder")
    print("=" * 40)

    build_site(args.output, args.dates)


if __name__ == "__main__":
    main()
