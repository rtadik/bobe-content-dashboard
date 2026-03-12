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

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent))

import client_config

from web_viewer import (
    load_content, load_content_from_airtable, resolve_image,
    list_available_dates, find_excel,
    CONTENT_DIR, IMAGES_DIR, HAS_AIRTABLE_WRITER,
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
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800;900&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg: #000e2b;
    --surface: rgba(255,255,255,0.04);
    --surface2: rgba(255,255,255,0.07);
    --border: rgba(255,255,255,0.08);
    --blue: #0055ff;
    --blue-hover: #0044cc;
    --blue-link: #0099ff;
    --blue-dim: rgba(0,85,255,0.1);
    --green: #5BD69F;
    --green-dim: rgba(91,214,159,0.1);
    --yellow: #f0c040;
    --yellow-dim: rgba(240,192,64,0.1);
    --white: #ffffff;
    --muted: #999999;
    --text: rgba(255,255,255,0.7);
  }

  html, body {
    background: var(--bg);
    color: var(--white);
    font-family: 'DM Sans', system-ui, -apple-system, sans-serif;
    min-height: 100vh;
    line-height: 1.5;
  }

  /* Header */
  header {
    background: rgba(0,14,43,0.85);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border);
    padding: 0 24px;
    height: 80px;
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

  .header-count {
    font-size: 0.78rem;
    background: var(--blue-dim);
    border: 1px solid rgba(0,85,255,0.2);
    color: var(--blue);
    padding: 2px 9px;
    border-radius: 20px;
    white-space: nowrap;
  }

  .spacer { flex: 1; }

  /* Week tabs — centered */
  .week-tabs {
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    gap: 6px;
    align-items: center;
  }
  .week-tab {
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--muted);
    padding: 6px 16px;
    border-radius: 8px;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
    white-space: nowrap;
    transition: all 0.15s;
  }
  .week-tab:hover:not(.active) { border-color: rgba(0,85,255,0.4); color: var(--text); }
  .week-tab.active {
    background: var(--blue-dim);
    border-color: rgba(0,85,255,0.5);
    color: var(--blue);
  }
  .week-tab.placeholder-tab {
    border-style: dashed;
    color: var(--muted);
  }
  .week-tab.placeholder-tab.active {
    border-style: solid;
    color: var(--blue);
  }
  .week-add-btn {
    background: none;
    border: 1px dashed rgba(0,85,255,0.4);
    color: rgba(0,85,255,0.7);
    padding: 4px 11px;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 500;
    line-height: 1.4;
    cursor: pointer;
    transition: all 0.15s;
    flex-shrink: 0;
  }
  .week-add-btn:hover { background: var(--blue-dim); border-color: var(--blue); color: var(--blue); }

  /* Placeholder week */
  .placeholder-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 24px;
    padding: 40px 24px;
    max-width: 1200px;
    margin: 0 auto;
  }
  .placeholder-card {
    background: var(--surface);
    border: 1px dashed rgba(255,255,255,0.1);
    border-radius: 24px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 56px 32px;
    gap: 12px;
    text-align: center;
    min-height: 300px;
    transition: border-color 0.2s;
  }
  .placeholder-card:hover { border-color: rgba(0,85,255,0.25); }
  .placeholder-icon { font-size: 2.2rem; opacity: 0.2; }
  .placeholder-label { font-size: 1rem; font-weight: 700; color: var(--muted); }
  .placeholder-hint { font-size: 0.82rem; color: var(--muted); opacity: 0.6; max-width: 260px; line-height: 1.5; }
  .generate-bucket-btn {
    background: var(--blue);
    border: none;
    color: #fff;
    padding: 9px 26px;
    border-radius: 10px;
    font-size: 0.86rem;
    font-weight: 600;
    cursor: pointer;
    font-family: inherit;
    transition: background 0.15s;
    margin-top: 4px;
  }
  .generate-bucket-btn:hover { background: var(--blue-hover); }
  .generate-bucket-btn:disabled { opacity: 0.55; cursor: not-allowed; }

  /* Add-week modal */
  .add-week-overlay {
    position: fixed; inset: 0;
    background: rgba(0,0,0,0.55);
    backdrop-filter: blur(4px);
    z-index: 900;
    display: none;
    align-items: center;
    justify-content: center;
  }
  .add-week-overlay.open { display: flex; }
  .add-week-box {
    background: #0d1a36;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 20px;
    padding: 32px;
    width: 360px;
    max-width: 92vw;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .add-week-box h3 { font-size: 1.05rem; font-weight: 700; }
  .add-week-box p { font-size: 0.84rem; color: var(--muted); line-height: 1.55; }
  .add-week-box input[type=date] {
    width: 100%;
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--white);
    padding: 9px 12px;
    border-radius: 9px;
    font-size: 0.88rem;
    font-family: inherit;
    color-scheme: dark;
  }
  .add-week-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 4px; }
  .add-week-actions button {
    padding: 8px 18px;
    border-radius: 9px;
    border: 1px solid var(--border);
    background: none;
    color: var(--muted);
    cursor: pointer;
    font-family: inherit;
    font-size: 0.84rem;
    font-weight: 500;
    transition: all 0.15s;
  }
  .add-week-actions .btn-confirm {
    background: var(--blue);
    border-color: var(--blue);
    color: #fff;
    font-weight: 600;
  }
  .add-week-actions .btn-confirm:hover { background: var(--blue-hover); }

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

  /* Client logo (top-left, replaces brand name) */
  .client-logo {
    height: 40px;
    width: auto;
    max-width: 140px;
    object-fit: contain;
    flex-shrink: 0;
  }

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
    border-radius: 24px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    transition: border-color 0.2s, box-shadow 0.2s;
    backdrop-filter: blur(8px);
  }
  .card:hover {
    border-color: rgba(0,85,255,0.35);
    box-shadow: 0 8px 40px rgba(0,85,255,0.12);
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
    border: 1px solid rgba(0,85,255,0.2);
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
    border-color: rgba(0,85,255,0.3);
    color: var(--text);
    background: var(--blue-dim);
  }
  .tab.active {
    background: var(--blue-dim);
    border-color: rgba(0,85,255,0.4);
    color: var(--blue);
  }
  .tab .platform-icon { font-size: 0.9rem; }

  /* Content panels */
  .panel { display: none; flex-direction: column; gap: 8px; }
  .panel.active { display: flex; }

  .content-box {
    background: rgba(0,0,0,0.3);
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
    border-top: 1px dashed rgba(0,85,255,0.2);
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
    border-radius: 10px;
    cursor: pointer;
    font-size: 0.77rem;
    font-weight: 500;
    transition: background 0.15s, transform 0.1s;
  }
  .copy-btn:hover { background: var(--blue-hover); }
  .copy-btn:active { transform: scale(0.97); }
  .copy-btn.copied { background: var(--green); color: #0D1526; }

  .publish-x-btn {
    padding: 5px 13px;
    border-radius: 7px;
    border: 1px solid rgba(29,161,242,0.4);
    background: rgba(29,161,242,0.1);
    color: #1DA1F2;
    font-size: 0.77rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
  }
  .publish-x-btn:hover:not(:disabled) {
    background: rgba(29,161,242,0.25);
    border-color: rgba(29,161,242,0.6);
  }
  .publish-x-btn.published {
    color: var(--green);
    border-color: rgba(91,214,159,0.4);
    background: rgba(91,214,159,0.1);
    cursor: default;
  }
  .publish-x-btn:disabled { opacity: 0.7; cursor: not-allowed; }

  /* Hashtags */
  .hashtags { display: flex; flex-wrap: wrap; gap: 5px; padding-top: 2px; }
  .tag {
    background: var(--yellow-dim);
    color: var(--yellow);
    border: 1px solid rgba(240,192,64,0.25);
    border-radius: 20px;
    padding: 2px 9px;
    font-size: 0.72rem;
    cursor: pointer;
    transition: background 0.15s;
    user-select: none;
  }
  .tag:hover { background: rgba(240,192,64,0.2); }
  .tag.tag-copied { background: var(--green-dim); color: var(--green); border-color: rgba(91,214,159,0.3); }

  /* Lightbox */
  #lightbox {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.9);
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
    background: rgba(0,14,43,0.95);
    backdrop-filter: blur(8px);
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

  /* Image loading overlay */
  .img-loading-overlay {
    display: none;
    position: absolute;
    inset: 0;
    background: rgba(0,14,43,0.82);
    z-index: 10;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: 10px;
    border-radius: 12px 12px 0 0;
  }
  .img-loading-overlay.active { display: flex; }
  .spinner {
    width: 32px; height: 32px;
    border: 3px solid rgba(0,85,255,0.2);
    border-top-color: var(--blue);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .spinner-label { font-size: 0.75rem; color: var(--muted); }

  /* Image action bars */
  .image-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 14px;
    background: rgba(255,255,255,0.02);
    border-bottom: 1px solid var(--border);
  }
  .img-status {
    flex: 1;
    font-size: 0.72rem;
    color: var(--muted);
  }
  .img-status.approved { color: var(--green); }
  .action-btn {
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 4px 11px;
    border-radius: 7px;
    cursor: pointer;
    font-size: 0.75rem;
    font-weight: 500;
    transition: all 0.15s;
    white-space: nowrap;
  }
  .action-btn:hover:not(:disabled) { border-color: rgba(0,85,255,0.4); color: var(--blue); }
  .action-btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .approve-btn.approved { background: var(--green-dim); border-color: rgba(91,214,159,0.3); color: var(--green); }
  .card.is-approved { border-color: rgba(91,214,159,0.25); }
  .regen-btn { color: var(--yellow); border-color: rgba(240,192,64,0.2); }
  .regen-btn:hover:not(:disabled) { border-color: rgba(240,192,64,0.5); color: var(--yellow); background: var(--yellow-dim); }

  /* Content regen bar */
  .content-regen-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 14px;
    background: rgba(240,192,64,0.04);
    border: 1px dashed rgba(240,192,64,0.15);
    border-radius: 9px;
    margin-bottom: 4px;
  }
  .content-regen-bar .regen-label {
    flex: 1;
    font-size: 0.78rem;
    color: var(--muted);
  }
  .content-regen-btn {
    background: var(--yellow-dim);
    border: 1px solid rgba(240,192,64,0.25);
    color: var(--yellow);
    padding: 5px 12px;
    border-radius: 7px;
    cursor: pointer;
    font-size: 0.77rem;
    font-weight: 500;
    transition: all 0.15s;
    white-space: nowrap;
  }
  .content-regen-btn:hover:not(:disabled) { background: rgba(240,192,64,0.15); border-color: rgba(240,192,64,0.4); }
  .content-regen-btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .content-regen-btn.triggering { background: rgba(0,85,255,0.1); border-color: rgba(0,85,255,0.3); color: var(--blue); }

  /* GitHub token modal */
  #gh-token-modal {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,14,43,0.88);
    z-index: 2000;
    align-items: center;
    justify-content: center;
    padding: 20px;
  }
  #gh-token-modal.open { display: flex; }
  .modal-box {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 28px 28px 24px;
    max-width: 440px;
    width: 100%;
    backdrop-filter: blur(8px);
  }
  .modal-box h3 { font-size: 1rem; font-weight: 600; margin-bottom: 8px; }
  .modal-box p { font-size: 0.8rem; color: var(--muted); margin-bottom: 16px; line-height: 1.55; }
  .modal-box input[type=password] {
    width: 100%;
    background: rgba(255,255,255,0.05);
    border: 1px solid var(--border);
    color: var(--white);
    padding: 9px 12px;
    border-radius: 10px;
    font-size: 0.85rem;
    margin-bottom: 14px;
    outline: none;
  }
  .modal-box input[type=password]:focus { border-color: #0099ff; }
  .modal-actions { display: flex; gap: 8px; justify-content: flex-end; }
  .btn-primary { background: #0055ff; color: #fff; border: none; padding: 8px 18px; border-radius: 22px; cursor: pointer; font-size: 0.83rem; font-weight: 500; transition: background 0.2s ease; }
  .btn-primary:hover { background: #0044cc; }
  .btn-secondary { background: none; border: 1px solid rgba(255,255,255,0.12); color: var(--muted); padding: 8px 14px; border-radius: 22px; cursor: pointer; font-size: 0.83rem; transition: all 0.2s ease; }

  /* RU loading modal */
  .ru-loading-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.7);
    backdrop-filter: blur(4px);
    z-index: 3000;
    align-items: center;
    justify-content: center;
  }
  .ru-loading-overlay.open { display: flex; }
  .ru-loading-box {
    background: #0d1a36;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 20px;
    padding: 36px 40px;
    max-width: 380px;
    width: 90%;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 18px;
    text-align: center;
  }
  .ru-loading-box p { font-size: 0.95rem; color: rgba(255,255,255,0.85); margin: 0; line-height: 1.5; }
  .ru-spinner {
    width: 40px; height: 40px;
    border: 3px solid rgba(255,255,255,0.12);
    border-top-color: #1589DC;
    border-radius: 50%;
    animation: ru-spin 0.8s linear infinite;
  }
  @keyframes ru-spin { to { transform: rotate(360deg); } }
  .ru-loading-box .btn-go-en {
    background: none;
    border: 1px solid rgba(255,255,255,0.2);
    color: rgba(255,255,255,0.65);
    padding: 8px 18px;
    border-radius: 22px;
    cursor: pointer;
    font-size: 0.82rem;
    transition: all 0.2s;
  }
  .ru-loading-box .btn-go-en:hover { background: rgba(255,255,255,0.08); color: #fff; }

  /* Regen status bar */
  #regen-status-bar {
    display: none;
    position: fixed;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(0,14,43,0.95);
    backdrop-filter: blur(8px);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 10px 18px;
    border-radius: 10px;
    font-size: 0.8rem;
    z-index: 600;
    display: none;
    align-items: center;
    gap: 10px;
    max-width: 440px;
    width: 90%;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
  }
  #regen-status-bar.show { display: flex; }
  #regen-status-bar .status-msg { flex: 1; }
  #regen-status-bar .dismiss-btn { background: none; border: none; color: var(--muted); cursor: pointer; font-size: 1rem; padding: 2px 6px; }

  /* Bucket tabs */
  .bucket-tabs {
    display: flex; gap: 8px; padding: 16px 24px 0;
    border-bottom: 2px solid rgba(255,255,255,0.06); margin-bottom: 0;
    flex-wrap: wrap;
  }
  .bucket-tab {
    padding: 10px 20px; border: none; border-radius: 8px 8px 0 0;
    background: rgba(255,255,255,0.04); color: var(--muted); cursor: pointer;
    font-size: 14px; font-weight: 600; transition: all 0.2s; font-family: inherit;
  }
  .bucket-tab.active { background: var(--blue); color: #fff; }
  .bucket-tab:hover:not(.active) { background: rgba(255,255,255,0.07); color: var(--text); }

  /* Announcement input panel */
  .announcement-input-panel {
    margin: 20px 24px; padding: 20px; background: rgba(255,255,255,0.04);
    border-radius: 12px; border: 1px solid var(--border);
  }
  .announcement-input-panel h3 { color: var(--white); margin: 0 0 8px; font-size: 16px; }
  .announcement-input-panel p { color: var(--muted); font-size: 13px; margin: 0 0 12px; }
  .announcement-input-panel textarea {
    width: 100%; box-sizing: border-box;
    background: rgba(0,0,0,0.3); color: var(--white); border: 1px solid var(--border);
    border-radius: 8px; padding: 12px; font-size: 14px; resize: vertical;
    font-family: inherit;
  }
  .announcement-input-panel textarea:focus { outline: none; border-color: var(--blue-link); }
  .btn-generate-announcement {
    margin-top: 12px; padding: 10px 20px; background: var(--blue);
    color: #fff; border: none; border-radius: 8px; cursor: pointer;
    font-weight: 600; font-size: 14px; transition: background 0.2s; font-family: inherit;
  }
  .btn-generate-announcement:hover { background: var(--blue-hover); }
  .btn-generate-announcement:disabled { opacity: 0.6; cursor: not-allowed; }
  #announcement-status { margin-top: 10px; font-size: 13px; color: var(--muted); }
</style>
</head>
<body>
{% autoescape false %}
<script>
(function() {
  var auth = sessionStorage.getItem('dash_auth');
  if (!auth) { window.location.replace('login.html'); return; }
  try {
    var session = JSON.parse(auth);
    var expectedClient = '{{ expected_client_id }}';
    if (session.role !== 'admin' && session.clientId !== expectedClient) {
      sessionStorage.removeItem('dash_auth');
      window.location.replace('login.html');
    }
  } catch(e) {
    sessionStorage.removeItem('dash_auth');
    window.location.replace('login.html');
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

<!-- GitHub Token Modal -->
<div id="gh-token-modal">
  <div class="modal-box">
    <h3>GitHub Token Required</h3>
    <p>To regenerate content or images, enter a GitHub Personal Access Token with <strong>Actions: write</strong> scope. It is stored in your browser session only.</p>
    <input type="password" id="gh-token-input" placeholder="ghp_..." autocomplete="off">
    <div class="modal-actions">
      <button class="btn-secondary" onclick="cancelGhModal()">Cancel</button>
      <button class="btn-primary" onclick="saveGhToken()">Save & Continue</button>
    </div>
  </div>
</div>

<!-- Regen status bar -->
<div id="regen-status-bar">
  <span class="status-msg" id="regen-status-msg">Workflow triggered...</span>
  <button class="dismiss-btn" onclick="dismissRegenStatus()" title="Dismiss">&#10005;</button>
</div>

<header>
  {% if client_logo_url %}
  <img src="{{ client_logo_url }}" alt="{{ brand_name }}" class="client-logo">
  {% else %}
  <div class="brand">{{ brand_name }}<span class="brand-dot">.</span></div>
  {% endif %}
  {% if topics %}
  <span class="header-count">{{ topics|length }} topic{{ 's' if topics|length != 1 else '' }}</span>
  {% endif %}
  {% set visible_tabs = date_options | selectattr('is_mock', 'equalto', false) | list %}
  {% if visible_tabs|length > 0 %}
  <div class="week-tabs">
    {% for opt in visible_tabs %}
    <a class="week-tab{% if opt.is_placeholder %} placeholder-tab{% endif %}{% if opt.date_id == current_date_id %} active{% endif %}" href="{{ opt.filename }}">{{ opt.label }}</a>
    {% endfor %}
    {% if gh_repo %}<button class="week-add-btn" onclick="openAddWeekModal()" title="Add new week">+</button>{% endif %}
  </div>
  {% endif %}
  <div class="spacer"></div>
  <div class="lang-toggle">
    <button class="lang-btn active" id="btn-en" onclick="setLang('en')">EN</button>
    <button class="lang-btn" id="btn-ru" onclick="setLang('ru')">RU</button>
  </div>
  <button class="logout-btn" onclick="logout()" title="Log out">Log out</button>
</header>

<!-- Bucket tab navigation -->
<div class="bucket-tabs" id="bucket-tabs">
  <button class="bucket-tab active" data-bucket="trending" onclick="switchBucket('trending')">&#128200; Trending</button>
  <button class="bucket-tab" data-bucket="education" onclick="switchBucket('education')">&#127891; Education</button>
  <button class="bucket-tab" data-bucket="announcements" onclick="switchBucket('announcements')">&#128227; Announcements</button>
</div>

<!-- Announcement input panel (shown only on announcements tab) -->
<div class="announcement-input-panel" id="announcement-input-panel" style="display:none">
  <h3>Weekly Announcement</h3>
  <p>Paste your weekly update below. The system will generate 7 different content angles from it (one per day).</p>
  <textarea id="announcement-text" rows="4" placeholder="e.g. We launched a new grid bot feature for ETH/USDT pairs..."></textarea>
  <button class="btn-generate-announcement" id="btn-gen-ann" onclick="submitAnnouncement()">Generate 7 Content Angles</button>
  <div id="announcement-status"></div>
</div>

{% if is_placeholder %}
<!-- Placeholder week — no content yet -->
<div class="placeholder-grid" id="placeholder-grid">
  <div class="placeholder-card" data-bucket="trending" id="ph-trending">
    <span class="placeholder-icon">&#128200;</span>
    <div class="placeholder-label">Trending Content</div>
    <div class="placeholder-hint">7 topics scraped from X and Reddit, tailored to this week's trends.</div>
    <button class="generate-bucket-btn" id="gen-btn-trending" onclick="generateWeek()">Generate</button>
  </div>
  <div class="placeholder-card" data-bucket="education" id="ph-education">
    <span class="placeholder-icon">&#127891;</span>
    <div class="placeholder-label">Education Content</div>
    <div class="placeholder-hint">7 belief-building posts from the buyer journey, generated for this week.</div>
    <button class="generate-bucket-btn" id="gen-btn-education" onclick="generateWeek()">Generate</button>
  </div>
  <div class="placeholder-card" data-bucket="announcements" id="ph-announcements">
    <span class="placeholder-icon">&#128227;</span>
    <div class="placeholder-label">Announcements</div>
    <div class="placeholder-hint">Add your weekly update above, then generate 7 content angles from it.</div>
    <button class="generate-bucket-btn" id="gen-btn-announcements" onclick="generateWeek()">Generate</button>
  </div>
</div>
{% else %}
<main class="grid">
{% if topics %}
  {% for t in topics %}
  <div class="card" id="card-{{ loop.index }}" data-bucket="{{ t.bucket or 'trending' }}">

    <!-- EN Image -->
    <div class="card-img en-only" {% if t.image_src %}data-src="{{ t.image_src }}"{% endif %}
         title="{% if t.image_src %}Click to enlarge{% endif %}">
      {% if t.image_src %}
      <img src="{{ t.image_src }}" alt="{{ t.topic }}" loading="lazy">
      <div class="img-overlay"></div>
      {% else %}
      <div class="no-img">
        <span class="no-img-icon">&#128444;</span>
        <span>No image generated</span>
      </div>
      {% endif %}
      <div class="img-loading-overlay" id="overlay-{{ loop.index }}">
        <div class="spinner"></div>
        <span class="spinner-label">Triggering workflow...</span>
      </div>
    </div>

    <!-- EN image action bar -->
    <div class="image-actions en-only">
      <span class="img-status" id="status-{{ loop.index }}">Pending review</span>
      <button class="action-btn approve-btn" id="approve-{{ loop.index }}"
              onclick="approveImage({{ loop.index }})">&#10003; Approve</button>
      <button class="action-btn regen-btn" id="regen-{{ loop.index }}"
              onclick="triggerRegen({{ loop.index }}, 'image_en')">&#8635; Regen Image</button>
    </div>

    <!-- RU Image -->
    <div class="card-img ru-only" {% if t.image_src_ru %}data-src="{{ t.image_src_ru }}"{% endif %}
         title="{% if t.image_src_ru %}Click to enlarge{% endif %}">
      {% if t.image_src_ru %}
      <img src="{{ t.image_src_ru }}" alt="{{ t.topic }}" loading="lazy">
      <div class="img-overlay"></div>
      {% else %}
      <div class="no-img">
        <span class="no-img-icon">&#128444;</span>
        <span>No Russian image</span>
      </div>
      {% endif %}
      <div class="img-loading-overlay" id="overlay-ru-{{ loop.index }}">
        <div class="spinner"></div>
        <span class="spinner-label">Triggering workflow...</span>
      </div>
    </div>

    <!-- RU image action bar (locked until EN approved) -->
    <div class="image-actions ru-only">
      <span class="img-status" style="font-size:0.72rem;color:var(--muted)">
        {% if t.image_filename_ru %}RU image{% else %}No RU image{% endif %}
      </span>
      <button class="action-btn regen-btn" id="regen-ru-{{ loop.index }}"
              onclick="triggerRegen({{ loop.index }}, 'image_ru')"
              disabled>&#128274; Regen Image</button>
    </div>

    <div class="card-body">
      <div class="topic-header">
        {% if t.day %}
        <span class="day-badge">{{ t.day }}</span>
        {% endif %}
        <h2 class="topic-title">{{ t.topic }}</h2>
      </div>

      <!-- EN content regen bar -->
      <div class="content-regen-bar en-only">
        <span class="regen-label" id="content-regen-label-{{ loop.index }}">Regenerate EN content via AI</span>
        <button class="content-regen-btn" id="content-regen-{{ loop.index }}"
                onclick="triggerRegen({{ loop.index }}, 'content')">&#8635; Regen Content</button>
      </div>

      <!-- RU content regen bar (locked until EN approved) -->
      <div class="content-regen-bar ru-only">
        <span class="regen-label" id="ru-content-regen-label-{{ loop.index }}">Approve EN first to unlock</span>
        <button class="content-regen-btn" id="ru-content-regen-{{ loop.index }}"
                onclick="triggerRegen({{ loop.index }}, 'content_ru')"
                disabled>&#128274; Regen RU Content</button>
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
            {% if x_publishing_enabled %}
              {% if t.status == 'Published' %}
              <button class="publish-x-btn published" id="publish-x-{{ loop.index }}" disabled>&#10003; Published</button>
              {% else %}
              <button class="publish-x-btn" id="publish-x-{{ loop.index }}" onclick="triggerPublishToX({{ loop.index }})">&#120143; Publish</button>
              {% endif %}
            {% endif %}
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
{% endif %}

<footer class="site-footer">Generated by {{ brand_name }} Content Pipeline</footer>

<!-- Add Week modal -->
<div class="add-week-overlay" id="add-week-modal">
  <div class="add-week-box">
    <h3>Create New Week</h3>
    <p>Select the Monday start date for the new week. The pipeline will generate all 3 content buckets and deploy when complete.</p>
    <input type="date" id="add-week-date">
    <div class="add-week-actions">
      <button onclick="cancelAddWeekModal()">Cancel</button>
      <button class="btn-confirm" onclick="confirmAddWeek()">Start Pipeline</button>
    </div>
  </div>
</div>

<!-- RU loading modal -->
<div class="ru-loading-overlay" id="ru-loading-modal">
  <div class="ru-loading-box">
    <div class="ru-spinner"></div>
    <p>Generating Russian content...<br><small style="opacity:0.6;font-size:0.8rem">This may take a few minutes.</small></p>
    <button class="btn-go-en" onclick="dismissRuModal()">Go back to English</button>
  </div>
</div>

<script>
// ── Constants (injected at build time) ────────────────────────────────────────
const GH_REPO           = '{{ gh_repo }}';
const GH_WORKFLOW       = 'regenerate-item.yml';
const GH_PUBLISH_WORKFLOW = 'publish-to-x.yml';
const WEEK_OF           = '{{ week_of }}';
const CLIENT_ID         = '{{ client_id }}';
const TOPIC_COUNT       = {{ topics|length }};
const GH_REGEN_TOKEN    = '{{ github_regen_token }}';
const REGEN_WORKER_URL  = '{{ regen_worker_url }}';

// ── Logout ────────────────────────────────────────────────────────────────────
function logout() {
  sessionStorage.removeItem('dash_auth');
  window.location.href = 'login.html';
}

// ── Language toggle ───────────────────────────────────────────────────────────
function setLang(lang) {
  document.body.classList.toggle('lang-ru', lang === 'ru');
  document.getElementById('btn-en').classList.toggle('active', lang === 'en');
  document.getElementById('btn-ru').classList.toggle('active', lang === 'ru');
  localStorage.setItem('content-dash-lang', lang);
  // Dismiss RU loading modal when switching back to English
  if (lang === 'en') {
    var m = document.getElementById('ru-loading-modal');
    if (m) m.classList.remove('open');
  }
}
(function(){ if(localStorage.getItem('content-dash-lang')==='ru') setLang('ru'); })();

// ── RU loading modal ──────────────────────────────────────────────────────────
function showRuModal() {
  var m = document.getElementById('ru-loading-modal');
  if (m) m.classList.add('open');
}
function dismissRuModal() {
  var m = document.getElementById('ru-loading-modal');
  if (m) m.classList.remove('open');
  setLang('en');
}

// ── Toast ─────────────────────────────────────────────────────────────────────
let toastTimer;
function showToast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'show';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.className = ''; }, 3000);
}

// ── Tab switching ─────────────────────────────────────────────────────────────
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

// ── Copy helpers ──────────────────────────────────────────────────────────────
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

document.querySelectorAll('.copy-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const text = btn.dataset.raw || '';
    copyText(text).then(() => flashCopy(btn, 'Copied ✓'));
  });
});

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

// ── Lightbox ──────────────────────────────────────────────────────────────────
const lightbox = document.getElementById('lightbox');
const lightImg = document.getElementById('lightbox-img');
const lbClose  = document.getElementById('lightbox-close');

document.querySelectorAll('.card-img[data-src]').forEach(el => {
  el.addEventListener('click', e => {
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

// ── Approval state (sessionStorage) ──────────────────────────────────────────
const APPROVAL_KEY = `approvals_${CLIENT_ID}_${WEEK_OF}`;

function loadApprovals() {
  try {
    return JSON.parse(sessionStorage.getItem(APPROVAL_KEY) || '{}');
  } catch(e) { return {}; }
}

function saveApprovals(data) {
  sessionStorage.setItem(APPROVAL_KEY, JSON.stringify(data));
}

function setApprovalUI(idx, status) {
  const statusEl   = document.getElementById(`status-${idx}`);
  const approveBtn = document.getElementById(`approve-${idx}`);
  const card       = document.getElementById(`card-${idx}`);
  if (!statusEl || !approveBtn) return;
  if (status === 'approved') {
    statusEl.textContent = 'Approved ✓';
    statusEl.className   = 'img-status approved';
    approveBtn.textContent = '✓ Approved';
    approveBtn.classList.add('approved');
    card && card.classList.add('is-approved');
  } else {
    statusEl.textContent = 'Pending review';
    statusEl.className   = 'img-status';
    approveBtn.textContent = '✓ Approve';
    approveBtn.classList.remove('approved');
    card && card.classList.remove('is-approved');
  }
}

// ── RU lock/unlock ────────────────────────────────────────────────────────────
function updateRuRegenState(idx, isApproved) {
  const ruImgBtn = document.getElementById(`regen-ru-${idx}`);
  const ruContentBtn = document.getElementById(`ru-content-regen-${idx}`);
  const ruContentLabel = document.getElementById(`ru-content-regen-label-${idx}`);
  if (ruImgBtn) {
    ruImgBtn.disabled = !isApproved;
    ruImgBtn.textContent = isApproved ? '\u21BB Regen Image' : '\\u{1F512} Regen Image';
  }
  if (ruContentBtn) {
    ruContentBtn.disabled = !isApproved;
    ruContentBtn.textContent = isApproved ? '\u21BB Regen RU Content' : '\\u{1F512} Regen RU Content';
  }
  if (ruContentLabel) {
    ruContentLabel.textContent = isApproved ? 'Regenerate RU content via AI' : 'Approve EN first to unlock';
  }
}

function approveImage(idx) {
  const approveBtn = document.getElementById(`approve-${idx}`);
  const isApproved = approveBtn.classList.contains('approved');
  const newStatus  = isApproved ? 'pending' : 'approved';

  const approvals = loadApprovals();
  approvals[idx] = newStatus;
  saveApprovals(approvals);

  setApprovalUI(idx, newStatus);
  updateRuRegenState(idx, newStatus === 'approved');
  if (newStatus === 'approved') {
    setLang('ru');
    showToast('Image approved ✓ — switched to Russian');
  } else {
    showToast('Approval removed');
  }
}

// Restore approval state on page load
(function() {
  const approvals = loadApprovals();
  for (let i = 1; i <= TOPIC_COUNT; i++) {
    const status = approvals[i] || 'pending';
    setApprovalUI(i, status);
    updateRuRegenState(i, status === 'approved');
  }
})();

// ── Cloudflare Worker dispatch helpers (Phase 4a) ─────────────────────────────

async function _dispatchViaWorker(workflow, extraInputs, btnIdx, regenType) {
  // Build button reference
  let btn = null;
  if (btnIdx !== null) {
    const btnId =
      regenType === 'image_en'   ? `regen-${btnIdx}` :
      regenType === 'image_ru'   ? `regen-ru-${btnIdx}` :
      regenType === 'content'    ? `content-regen-${btnIdx}` :
      regenType === 'content_ru' ? `ru-content-regen-${btnIdx}` :
      regenType === 'publish'    ? `publish-x-${btnIdx}` : null;
    btn = btnId ? document.getElementById(btnId) : null;
  }
  const origText = btn ? btn.textContent : '';
  if (btn) { btn.textContent = 'Triggering...'; btn.disabled = true; btn.classList.add('triggering'); }

  const label = regenType === 'announce' ? 'announcement pipeline' : `${regenType} regeneration`;
  showRegenStatus(`Triggering ${label}...`);

  try {
    const resp = await fetch(REGEN_WORKER_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        workflow,
        client_id: CLIENT_ID,
        week_of:   WEEK_OF,
        ...extraInputs,
      }),
    });

    const data = await resp.json().catch(() => ({}));
    if (resp.ok && data.ok) {
      showRegenStatus('Workflow started! This takes 2-5 min. Page will reload when done.');
      if (btn) { btn.textContent = 'Queued \u2713'; btn.classList.remove('triggering'); }
      _pollViaWorker(workflow + '.yml');
    } else if (resp.status === 401 || resp.status === 403) {
      showToast('Worker auth error. Contact admin.');
      if (btn) { btn.textContent = origText; btn.disabled = false; btn.classList.remove('triggering'); }
      dismissRegenStatus();
    } else {
      showToast('Worker error: ' + (data.error || resp.status));
      if (btn) { btn.textContent = origText; btn.disabled = false; btn.classList.remove('triggering'); }
      dismissRegenStatus();
    }
  } catch(e) {
    showToast('Network error: ' + e.message);
    if (btn) { btn.textContent = origText; btn.disabled = false; btn.classList.remove('triggering'); }
    dismissRegenStatus();
  }
}

async function _pollViaWorker(workflowFile) {
  const deadline = Date.now() + 10 * 60 * 1000; // 10 min
  await new Promise(r => setTimeout(r, 20000)); // wait 20s before first poll

  while (Date.now() < deadline) {
    try {
      const resp = await fetch(`${REGEN_WORKER_URL}/status?workflow=${encodeURIComponent(workflowFile)}`);
      const data = await resp.json().catch(() => ({}));
      if (data.status === 'completed') {
        if (data.conclusion === 'success') {
          showRegenStatus('Complete! Reloading page...');
          setTimeout(() => location.reload(), 2500);
        } else {
          showRegenStatus('Workflow finished with status: ' + data.conclusion + '. Check GitHub Actions for details.');
        }
        return;
      }
      if (data.status) {
        showRegenStatus('Workflow running... (' + data.status + ')');
      }
    } catch(e) { /* continue polling */ }
    await new Promise(r => setTimeout(r, 15000));
  }
  showRegenStatus('Workflow is taking longer than expected. Refresh manually when done.');
}

// ── GitHub token modal ────────────────────────────────────────────────────────
let _pendingRegenCb = null;

function getGhToken(callback) {
  const existing = GH_REGEN_TOKEN || sessionStorage.getItem('gh_pat');
  if (existing) { callback(existing); return; }
  _pendingRegenCb = callback;
  document.getElementById('gh-token-modal').classList.add('open');
  setTimeout(() => document.getElementById('gh-token-input').focus(), 100);
}

function cancelGhModal() {
  document.getElementById('gh-token-modal').classList.remove('open');
  document.getElementById('gh-token-input').value = '';
  _pendingRegenCb = null;
}

function saveGhToken() {
  const token = document.getElementById('gh-token-input').value.trim();
  if (!token) { showToast('Please enter a token'); return; }
  sessionStorage.setItem('gh_pat', token);
  document.getElementById('gh-token-modal').classList.remove('open');
  document.getElementById('gh-token-input').value = '';
  if (_pendingRegenCb) { const cb = _pendingRegenCb; _pendingRegenCb = null; cb(token); }
}

document.getElementById('gh-token-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') saveGhToken();
  if (e.key === 'Escape') cancelGhModal();
});

// ── Regen status bar ──────────────────────────────────────────────────────────
function showRegenStatus(msg) {
  const bar = document.getElementById('regen-status-bar');
  document.getElementById('regen-status-msg').textContent = msg;
  bar.classList.add('show');
}

function dismissRegenStatus() {
  document.getElementById('regen-status-bar').classList.remove('show');
}

// ── Trigger regeneration via GitHub Actions API ───────────────────────────────
function triggerRegen(idx, regenType) {
  // Guard: RU types require EN to be approved
  if (regenType === 'image_ru' || regenType === 'content_ru') {
    const approvals = loadApprovals();
    if (approvals[idx] !== 'approved') {
      showToast('Approve the EN image first to unlock RU regeneration');
      return;
    }
  }

  if (!GH_REPO || GH_REPO === '') {
    showToast('GitHub repo not configured — contact admin');
    return;
  }

  // Show RU loading modal for RU regen types
  if (regenType === 'image_ru' || regenType === 'content_ru') {
    showRuModal();
  }

  // Worker path: no PAT needed
  if (REGEN_WORKER_URL) {
    _dispatchViaWorker('regenerate-item', { topic_index: String(idx - 1), regen_type: regenType }, idx, regenType);
    return;
  }

  getGhToken(async function(token) {
    const btn = document.getElementById(
      regenType === 'image_en' ? `regen-${idx}` :
      regenType === 'image_ru' ? `regen-ru-${idx}` :
      regenType === 'content'  ? `content-regen-${idx}` :
                                 `ru-content-regen-${idx}`
    );
    const origText = btn ? btn.textContent : '';
    if (btn) { btn.textContent = 'Triggering...'; btn.disabled = true; btn.classList.add('triggering'); }

    showRegenStatus(`Triggering ${regenType} regeneration for topic ${idx}...`);

    try {
      const resp = await fetch(
        `https://api.github.com/repos/${GH_REPO}/actions/workflows/${GH_WORKFLOW}/dispatches`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'application/vnd.github+json',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            ref: 'main',
            inputs: {
              client_id:   CLIENT_ID,
              week_of:     WEEK_OF,
              topic_index: String(idx - 1),
              regen_type:  regenType,
            },
          }),
        }
      );

      if (resp.status === 204) {
        showRegenStatus('Workflow started! This takes 2-5 min. Refresh the page when done.');
        if (btn) { btn.textContent = 'Queued ✓'; btn.classList.remove('triggering'); }
        pollRegenCompletion(token);
      } else if (resp.status === 401 || resp.status === 403) {
        sessionStorage.removeItem('gh_pat');
        showToast('Token invalid or expired. Please try again.', true);
        if (btn) { btn.textContent = origText; btn.disabled = false; btn.classList.remove('triggering'); }
        dismissRegenStatus();
        var ruModal = document.getElementById('ru-loading-modal');
        if (ruModal) ruModal.classList.remove('open');
      } else {
        const err = await resp.text();
        showToast('GitHub API error: ' + resp.status);
        if (btn) { btn.textContent = origText; btn.disabled = false; btn.classList.remove('triggering'); }
        dismissRegenStatus();
        var ruModal = document.getElementById('ru-loading-modal');
        if (ruModal) ruModal.classList.remove('open');
        console.error('GH API error', resp.status, err);
      }
    } catch(e) {
      showToast('Network error: ' + e.message);
      if (btn) { btn.textContent = origText; btn.disabled = false; btn.classList.remove('triggering'); }
      dismissRegenStatus();
      var ruModal = document.getElementById('ru-loading-modal');
      if (ruModal) ruModal.classList.remove('open');
    }
  });
}

// ── Trigger X publish via GitHub Actions API ──────────────────────────────────
function triggerPublishToX(idx) {
  if (!GH_REPO || GH_REPO === '') {
    showToast('GitHub repo not configured — contact admin');
    return;
  }

  // Worker path: no PAT needed
  if (REGEN_WORKER_URL) {
    _dispatchViaWorker('publish-to-x', { topic_index: String(idx - 1) }, idx, 'publish');
    return;
  }

  getGhToken(async function(token) {
    const btn = document.getElementById(`publish-x-${idx}`);
    const origText = btn ? btn.textContent : '';
    if (btn) { btn.textContent = 'Publishing...'; btn.disabled = true; btn.classList.add('triggering'); }

    showRegenStatus('Triggering X publish workflow...');

    try {
      const resp = await fetch(
        `https://api.github.com/repos/${GH_REPO}/actions/workflows/${GH_PUBLISH_WORKFLOW}/dispatches`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'application/vnd.github+json',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            ref: 'main',
            inputs: {
              client_id:   CLIENT_ID,
              week_of:     WEEK_OF,
              topic_index: String(idx - 1),
            },
          }),
        }
      );

      if (resp.status === 204) {
        showRegenStatus('Publish workflow started! This takes 2-3 min. Refresh to see Published status.');
        if (btn) { btn.textContent = 'Queued ✓'; btn.classList.remove('triggering'); }
        pollRegenCompletion(token);
      } else if (resp.status === 401 || resp.status === 403) {
        sessionStorage.removeItem('gh_pat');
        showToast('Token invalid or expired. Please try again.', true);
        if (btn) { btn.textContent = origText; btn.disabled = false; btn.classList.remove('triggering'); }
        dismissRegenStatus();
      } else {
        const err = await resp.text();
        showToast('GitHub API error: ' + resp.status);
        if (btn) { btn.textContent = origText; btn.disabled = false; btn.classList.remove('triggering'); }
        dismissRegenStatus();
        console.error('GH API error', resp.status, err);
      }
    } catch(e) {
      showToast('Network error: ' + e.message);
      if (btn) { btn.textContent = origText; btn.disabled = false; btn.classList.remove('triggering'); }
      dismissRegenStatus();
    }
  });
}

async function pollRegenCompletion(token) {
  if (REGEN_WORKER_URL) { _pollViaWorker(GH_WORKFLOW); return; }
  const deadline = Date.now() + 10 * 60 * 1000; // 10 min
  await new Promise(r => setTimeout(r, 20000)); // wait 20s before first poll

  while (Date.now() < deadline) {
    try {
      const resp = await fetch(
        `https://api.github.com/repos/${GH_REPO}/actions/workflows/${GH_WORKFLOW}/runs?per_page=5`,
        { headers: { 'Authorization': `Bearer ${token}`, 'Accept': 'application/vnd.github+json' } }
      );
      const data = await resp.json();
      const run  = data.workflow_runs && data.workflow_runs[0];
      if (run && run.status === 'completed') {
        if (run.conclusion === 'success') {
          showRegenStatus('Regeneration complete! Reloading page...');
          setTimeout(() => location.reload(), 2500);
        } else {
          showRegenStatus('Workflow finished with status: ' + run.conclusion + '. Check GitHub Actions for details.');
        }
        return;
      }
      if (run) {
        showRegenStatus('Workflow running... (' + (run.status || 'in_progress') + ')');
      }
    } catch(e) { /* continue polling */ }
    await new Promise(r => setTimeout(r, 15000));
  }
  showRegenStatus('Workflow is taking longer than expected. Refresh manually when done.');
}

// ── Bucket tab switching ───────────────────────────────────────────────────────
function switchBucket(bucket) {
  document.querySelectorAll('.bucket-tab').forEach(function(tab) {
    tab.classList.toggle('active', tab.dataset.bucket === bucket);
  });
  document.querySelectorAll('.card').forEach(function(card) {
    var cardBucket = card.dataset.bucket || 'trending';
    card.style.display = cardBucket === bucket ? '' : 'none';
  });
  // Show/hide placeholder cards
  document.querySelectorAll('.placeholder-card').forEach(function(card) {
    var cardBucket = card.dataset.bucket || 'trending';
    card.style.display = cardBucket === bucket ? '' : 'none';
  });
  var inputPanel = document.getElementById('announcement-input-panel');
  if (inputPanel) {
    inputPanel.style.display = bucket === 'announcements' ? 'block' : 'none';
  }
  try { localStorage.setItem('active-bucket', bucket); } catch(e) {}
}

// Initialise bucket on load
(function() {
  var saved = '';
  try { saved = localStorage.getItem('active-bucket') || ''; } catch(e) {}
  var firstBucket = 'trending';
  var allBuckets = new Set(['trending','education','announcements']);
  document.querySelectorAll('.card').forEach(function(c) { if(c.dataset.bucket) allBuckets.add(c.dataset.bucket); });
  switchBucket(saved && allBuckets.has(saved) ? saved : firstBucket);
})();

// ── Add week / placeholder generate ───────────────────────────────────────────
function openAddWeekModal() {
  const modal = document.getElementById('add-week-modal');
  if (!modal) return;
  // Default to next Monday after current WEEK_OF
  try {
    const base = WEEK_OF ? new Date(WEEK_OF + 'T00:00:00') : new Date();
    base.setDate(base.getDate() + 7);
    document.getElementById('add-week-date').value = base.toISOString().slice(0, 10);
  } catch(e) {}
  modal.classList.add('open');
}

function cancelAddWeekModal() {
  const modal = document.getElementById('add-week-modal');
  if (modal) modal.classList.remove('open');
}

function confirmAddWeek() {
  const d = document.getElementById('add-week-date').value;
  if (!d) { showToast('Please select a week start date.'); return; }
  cancelAddWeekModal();
  _triggerWeeklyPipeline(d);
}

function generateWeek() {
  if (!GH_REPO) { showToast('GitHub repo not configured'); return; }
  // Disable all generate buttons to prevent double-trigger
  document.querySelectorAll('.generate-bucket-btn').forEach(b => {
    b.disabled = true; b.textContent = 'Queued \u2713';
  });
  _triggerWeeklyPipeline(WEEK_OF);
}

function _triggerWeeklyPipeline(weekOf) {
  if (!GH_REPO) { showToast('GitHub repo not configured'); return; }
  if (REGEN_WORKER_URL) {
    _dispatchViaWorker('weekly-pipeline', { week_of: weekOf }, null, 'pipeline');
    showRegenStatus('Weekly pipeline started. New content will appear when complete (~5-10 min).');
    return;
  }
  getGhToken(async function(token) {
    try {
      const resp = await fetch(
        `https://api.github.com/repos/${GH_REPO}/actions/workflows/weekly-pipeline.yml/dispatches`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'application/vnd.github+json',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ ref: 'main', inputs: { client_id: CLIENT_ID, week_of: weekOf } }),
        }
      );
      if (resp.status === 204) {
        showRegenStatus('Weekly pipeline started. New content will appear when complete (~5-10 min).');
        pollRegenCompletion(token);
      } else if (resp.status === 401 || resp.status === 403) {
        sessionStorage.removeItem('gh_pat');
        showToast('Token invalid or expired. Please try again.');
        document.querySelectorAll('.generate-bucket-btn').forEach(b => { b.disabled = false; b.textContent = 'Generate'; });
      } else {
        showToast('GitHub API error: ' + resp.status);
        document.querySelectorAll('.generate-bucket-btn').forEach(b => { b.disabled = false; b.textContent = 'Generate'; });
      }
    } catch(e) {
      showToast('Network error: ' + e.message);
      document.querySelectorAll('.generate-bucket-btn').forEach(b => { b.disabled = false; b.textContent = 'Generate'; });
    }
  });
}

// ── Announcement generation (via GitHub Actions) ───────────────────────────────
async function submitAnnouncement() {
  var text = (document.getElementById('announcement-text') || {}).value;
  if (!text || !text.trim()) {
    alert('Please enter your announcement text first.');
    return;
  }
  var btn = document.getElementById('btn-gen-ann');
  var statusEl = document.getElementById('announcement-status');
  if (btn) { btn.disabled = true; btn.textContent = 'Generating...'; }
  if (statusEl) statusEl.textContent = 'Preparing to trigger workflow...';

  if (!GH_REPO || GH_REPO === '') {
    if (statusEl) statusEl.textContent = 'GitHub repo not configured. Contact admin.';
    if (btn) { btn.disabled = false; btn.textContent = 'Generate 7 Content Angles'; }
    return;
  }

  // Worker path: no PAT needed
  if (REGEN_WORKER_URL) {
    if (statusEl) statusEl.textContent = 'Triggering announcement pipeline...';
    _dispatchViaWorker('generate-announcement', { bucket: 'announcements', announcement_text: text.trim() }, null, 'announce');
    if (btn) { btn.textContent = 'Queued \u2713'; }
    return;
  }

  getGhToken(async function(token) {
    try {
      if (statusEl) statusEl.textContent = 'Triggering announcement pipeline...';
      const resp = await fetch(
        'https://api.github.com/repos/' + GH_REPO + '/actions/workflows/weekly-pipeline.yml/dispatches',
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
              week_of:   WEEK_OF,
              bucket:    'announcements',
              announcement_text: text.trim(),
            },
          }),
        }
      );

      if (resp.status === 204) {
        if (statusEl) statusEl.textContent = 'Workflow triggered! Generating 7 content angles (2-5 min). Refresh when done.';
        if (btn) { btn.textContent = 'Queued ✓'; }
        showRegenStatus('Announcement pipeline started. Refresh in a few minutes.');
        pollRegenCompletion(token);
      } else if (resp.status === 401 || resp.status === 403) {
        sessionStorage.removeItem('gh_pat');
        if (statusEl) statusEl.textContent = 'Token invalid or expired. Please try again.';
        if (btn) { btn.disabled = false; btn.textContent = 'Generate 7 Content Angles'; }
      } else {
        const err = await resp.text();
        if (statusEl) statusEl.textContent = 'GitHub API error: ' + resp.status;
        if (btn) { btn.disabled = false; btn.textContent = 'Generate 7 Content Angles'; }
        console.error('GH API error', resp.status, err);
      }
    } catch(e) {
      if (statusEl) statusEl.textContent = 'Network error: ' + e.message;
      if (btn) { btn.disabled = false; btn.textContent = 'Generate 7 Content Angles'; }
    }
  });
}
</script>
</body>
</html>"""


# ── Landing page template ──────────────────────────────────────────────────────

LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Content · Rejig Labs</title>
<link rel="icon" type="image/jpeg" href="favicon.jpg">
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800;900&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #000e2b;
    --surface: rgba(255,255,255,0.04);
    --surface2: rgba(255,255,255,0.07);
    --border: rgba(255,255,255,0.08);
    --blue: #0055ff;
    --blue-hover: #0044cc;
    --blue-link: #0099ff;
    --blue-dim: rgba(0,85,255,0.1);
    --green: #5BD69F;
    --green-dim: rgba(91,214,159,0.1);
    --yellow: #f0c040;
    --yellow-dim: rgba(240,192,64,0.1);
    --white: #ffffff;
    --muted: #999999;
    --text: rgba(255,255,255,0.7);
  }
  html, body {
    background: var(--bg); color: #fff;
    font-family: 'DM Sans', system-ui, -apple-system, sans-serif;
    min-height: 100vh; display: flex; flex-direction: column;
  }
  /* Background orbs */
  .bg-orb {
    position: fixed;
    border-radius: 50%;
    pointer-events: none;
    z-index: 0;
    filter: blur(80px);
  }
  .bg-orb-1 {
    width: 700px; height: 700px;
    background: radial-gradient(circle, rgba(0,85,255,0.12) 0%, transparent 70%);
    top: -200px; left: 50%; transform: translateX(-50%);
  }
  .bg-orb-2 {
    width: 400px; height: 400px;
    background: radial-gradient(circle, rgba(0,153,255,0.08) 0%, transparent 70%);
    bottom: 0; right: -100px;
  }
  nav, .hero-wrap, footer { position: relative; z-index: 1; }
  /* Navbar */
  nav {
    background: rgba(0,14,43,0.85);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border);
    padding: 0 32px;
    height: 80px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky; top: 0; z-index: 100;
  }
  .nav-brand {
    font-size: 1.2rem; font-weight: 800; color: #ffffff;
    letter-spacing: 0.3px; text-decoration: none;
  }
  .nav-brand .brand-sep { color: var(--muted); font-weight: 400; padding: 0 2px; }
  .nav-brand .brand-studio { color: var(--muted); font-weight: 600; }
  .nav-login {
    background: none; border: 1px solid rgba(255,255,255,0.12);
    color: var(--blue); padding: 7px 20px; border-radius: 22px;
    font-size: 0.85rem; font-weight: 600; cursor: pointer;
    text-decoration: none; transition: all 0.2s ease;
  }
  .nav-login:hover { background: var(--blue-dim); border-color: var(--blue); }
  /* Hero */
  .hero-wrap {
    flex: 1; display: flex; align-items: center; justify-content: center;
    padding: 60px 24px;
  }
  .hero {
    display: flex; flex-direction: column; align-items: center;
    gap: 24px; text-align: center; max-width: 560px;
  }
  .eyebrow {
    font-size: 0.72rem; font-weight: 700; letter-spacing: 3px;
    color: var(--blue-link); text-transform: uppercase;
  }
  .hero-title {
    font-size: clamp(2.5rem, 6vw, 4.5rem); font-weight: 800; letter-spacing: -2px; line-height: 1.05;
    color: #fff;
  }
  .hero-title .accent { color: var(--blue); }
  .hero-sub {
    font-size: 1rem; color: var(--text); line-height: 1.7; max-width: 420px;
  }
  .hero-actions { display: flex; gap: 12px; margin-top: 4px; }
  .btn-primary {
    background: #0055ff; color: #fff; border: none;
    padding: 14px 40px; border-radius: 22px; font-size: 0.95rem;
    font-weight: 700; cursor: pointer; text-decoration: none;
    transition: background 0.2s ease, transform 0.1s; display: inline-block;
  }
  .btn-primary:hover { background: #0044cc; }
  .btn-primary:active { transform: scale(0.98); }
  /* Features */
  .features {
    display: flex; gap: 12px; flex-wrap: wrap; justify-content: center;
    margin-top: 8px;
  }
  .feature-pill {
    background: var(--surface); border: 1px solid rgba(255,255,255,0.12);
    color: var(--text); font-size: 0.78rem; padding: 6px 14px;
    border-radius: 20px; white-space: nowrap;
  }
  /* Footer */
  footer {
    text-align: center; padding: 20px 24px;
    font-size: 0.68rem; color: var(--muted);
  }
</style>
</head>
<body>
<div class="bg-orb bg-orb-1"></div>
<div class="bg-orb bg-orb-2"></div>
<nav>
  <a class="nav-brand" href="#">Content<span class="brand-sep"> · </span><span class="brand-studio">Rejig Labs</span></a>
  <a href="login.html" class="nav-login">Log In</a>
</nav>
<div class="hero-wrap">
  <div class="hero">
    <p class="eyebrow">Content Platform</p>
    <h1 class="hero-title">Your weekly content,<br><span class="accent">ready to publish.</span></h1>
    <p class="hero-sub">Bilingual Twitter threads, Telegram posts, and branded images — generated, organized, and delivered every week.</p>
    <div class="hero-actions">
      <a href="login.html" class="btn-primary">Log In to Dashboard</a>
    </div>
    <div class="features">
      <span class="feature-pill">EN + RU Content</span>
      <span class="feature-pill">Twitter &amp; Telegram</span>
      <span class="feature-pill">Branded Images</span>
      <span class="feature-pill">Weekly Delivery</span>
    </div>
  </div>
</div>
<footer>Content · Rejig Labs</footer>
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
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800;900&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #000e2b;
    --surface: rgba(255,255,255,0.04);
    --surface2: rgba(255,255,255,0.07);
    --border: rgba(255,255,255,0.08);
    --blue: #0055ff;
    --blue-hover: #0044cc;
    --blue-link: #0099ff;
    --blue-dim: rgba(0,85,255,0.1);
    --white: #ffffff;
    --muted: #999999;
    --text: rgba(255,255,255,0.7);
    --red: #FF6B6B;
  }
  html, body {
    background: var(--bg); color: #fff;
    font-family: 'DM Sans', system-ui, -apple-system, sans-serif;
    min-height: 100vh; display: flex; flex-direction: column;
    align-items: center; justify-content: center; padding: 24px;
  }
  /* Background orbs */
  .bg-orb {
    position: fixed;
    border-radius: 50%;
    pointer-events: none;
    z-index: 0;
    filter: blur(80px);
  }
  .bg-orb-1 {
    width: 700px; height: 700px;
    background: radial-gradient(circle, rgba(0,85,255,0.12) 0%, transparent 70%);
    top: -200px; left: 50%; transform: translateX(-50%);
  }
  .bg-orb-2 {
    width: 400px; height: 400px;
    background: radial-gradient(circle, rgba(0,153,255,0.08) 0%, transparent 70%);
    bottom: 0; right: -100px;
  }
  .card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 24px; padding: 36px 32px; width: 100%; max-width: 380px;
    display: flex; flex-direction: column; gap: 24px;
    backdrop-filter: blur(8px);
    position: relative; z-index: 1;
  }
  .card-header { display: flex; flex-direction: column; gap: 6px; }
  .back-link {
    font-size: 0.75rem; color: var(--muted); text-decoration: none;
    display: flex; align-items: center; gap: 4px; margin-bottom: 8px;
    transition: color 0.2s ease;
  }
  .back-link:hover { color: var(--text); }
  .card-title { font-size: 1.35rem; font-weight: 700; }
  .card-subtitle { font-size: 0.8rem; color: var(--muted); }
  .field { display: flex; flex-direction: column; gap: 6px; }
  .field label { font-size: 0.78rem; font-weight: 600; color: var(--text); letter-spacing: 0.2px; }
  .field input {
    background: rgba(255,255,255,0.05); border: 1px solid var(--border);
    color: #fff; padding: 10px 14px; border-radius: 10px; font-size: 0.9rem;
    outline: none; transition: border-color 0.2s ease;
    font-family: inherit;
  }
  .field input:focus { border-color: #0099ff; }
  .error-msg {
    background: rgba(255,107,107,0.1); border: 1px solid rgba(255,107,107,0.3);
    color: var(--red); font-size: 0.78rem; padding: 9px 13px; border-radius: 8px;
    display: none;
  }
  .error-msg.show { display: block; }
  .submit-btn {
    background: #0055ff; color: #fff; border: none;
    padding: 12px; border-radius: 22px; font-size: 0.92rem;
    font-weight: 600; cursor: pointer; width: 100%;
    transition: background 0.2s ease; font-family: inherit;
  }
  .submit-btn:hover { background: #0044cc; }
  .submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }
  .site-footer {
    margin-top: 28px; font-size: 0.68rem; color: var(--muted);
    position: relative; z-index: 1;
  }
</style>
</head>
<body>
<div class="bg-orb bg-orb-1"></div>
<div class="bg-orb bg-orb-2"></div>
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


# ── Per-client login page template ────────────────────────────────────────────
# This is identical to LOGIN_HTML but with:
#   - Relative favicon path (../../favicon.jpg from dashboard/{client_id}/)
#   - Back link going to ../../index.html (root landing page)
#   - CREDENTIALS contains only this client's credential (credential isolation)
#   - After login, redirect to ./ (the client's own dashboard directory)

PER_CLIENT_LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Log In — {{ brand_name }}</title>
<link rel="icon" type="image/jpeg" href="../../favicon.jpg">
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800;900&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #000e2b;
    --surface: rgba(255,255,255,0.04);
    --surface2: rgba(255,255,255,0.07);
    --border: rgba(255,255,255,0.08);
    --blue: #0055ff;
    --blue-hover: #0044cc;
    --blue-link: #0099ff;
    --blue-dim: rgba(0,85,255,0.1);
    --white: #ffffff;
    --muted: #999999;
    --text: rgba(255,255,255,0.7);
    --red: #FF6B6B;
  }
  html, body {
    background: var(--bg); color: #fff;
    font-family: 'DM Sans', system-ui, -apple-system, sans-serif;
    min-height: 100vh; display: flex; flex-direction: column;
    align-items: center; justify-content: center; padding: 24px;
  }
  .bg-orb {
    position: fixed;
    border-radius: 50%;
    pointer-events: none;
    z-index: 0;
    filter: blur(80px);
  }
  .bg-orb-1 {
    width: 700px; height: 700px;
    background: radial-gradient(circle, rgba(0,85,255,0.12) 0%, transparent 70%);
    top: -200px; left: 50%; transform: translateX(-50%);
  }
  .bg-orb-2 {
    width: 400px; height: 400px;
    background: radial-gradient(circle, rgba(0,153,255,0.08) 0%, transparent 70%);
    bottom: 0; right: -100px;
  }
  .card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 24px; padding: 36px 32px; width: 100%; max-width: 380px;
    display: flex; flex-direction: column; gap: 24px;
    backdrop-filter: blur(8px);
    position: relative; z-index: 1;
  }
  .card-header { display: flex; flex-direction: column; gap: 6px; }
  .back-link {
    font-size: 0.75rem; color: var(--muted); text-decoration: none;
    display: flex; align-items: center; gap: 4px; margin-bottom: 8px;
    transition: color 0.2s ease;
  }
  .back-link:hover { color: var(--text); }
  .card-title { font-size: 1.35rem; font-weight: 700; }
  .card-subtitle { font-size: 0.8rem; color: var(--muted); }
  .field { display: flex; flex-direction: column; gap: 6px; }
  .field label { font-size: 0.78rem; font-weight: 600; color: var(--text); letter-spacing: 0.2px; }
  .field input {
    background: rgba(255,255,255,0.05); border: 1px solid var(--border);
    color: #fff; padding: 10px 14px; border-radius: 10px; font-size: 0.9rem;
    outline: none; transition: border-color 0.2s ease;
    font-family: inherit;
  }
  .field input:focus { border-color: #0099ff; }
  .error-msg {
    background: rgba(255,107,107,0.1); border: 1px solid rgba(255,107,107,0.3);
    color: var(--red); font-size: 0.78rem; padding: 9px 13px; border-radius: 8px;
    display: none;
  }
  .error-msg.show { display: block; }
  .submit-btn {
    background: #0055ff; color: #fff; border: none;
    padding: 12px; border-radius: 22px; font-size: 0.92rem;
    font-weight: 600; cursor: pointer; width: 100%;
    transition: background 0.2s ease; font-family: inherit;
  }
  .submit-btn:hover { background: #0044cc; }
  .submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }
  .site-footer {
    margin-top: 28px; font-size: 0.68rem; color: var(--muted);
    position: relative; z-index: 1;
  }
</style>
</head>
<body>
<div class="bg-orb bg-orb-1"></div>
<div class="bg-orb bg-orb-2"></div>
<div class="card">
  <div class="card-header">
    <a href="../../index.html" class="back-link">&#8592; Back</a>
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
// Credentials: only this client's credential is baked in (credential isolation)
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

    // Redirect to this client's dashboard (same directory)
    window.location.href = './';
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


def build_site(output_dir, dates=None, credentials=None, active_client="bobe", clean=True):
    """Build the static site into output_dir.

    Args:
        output_dir: Path to write the static site (e.g., dist/)
        dates: List of date identifiers to build, or None for all available
        credentials: List of credential dicts from load_credentials()
        active_client: Client ID for scoped output paths
        clean: Wipe output_dir before building (set False for multi-client sequential builds)
    """
    output = Path(output_dir)
    github_regen_token = ""  # Phase 4a: inject via Cloudflare Worker proxy, not static HTML

    # Clean previous build (skip when building multiple clients sequentially)
    if clean and output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

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

    # Copy client logo to dashboard dir and record relative URL for template
    client_logo_url = ""
    _client_cfg = client_config.load_config(active_client)
    _logo_rel = _client_cfg.get("brand", {}).get("logo_path", "")
    if _logo_rel:
        _logo_src = Path(__file__).parent.parent / "clients" / active_client / _logo_rel
        if _logo_src.exists():
            _logo_dst_name = "client-logo" + _logo_src.suffix
            shutil.copy2(str(_logo_src), str(client_dash_dir / _logo_dst_name))
            client_logo_url = _logo_dst_name

    # Images go inside the client dashboard dir
    images_out = client_dash_dir / "images"

    # Build date-to-filename mapping (Week N labels; oldest real week = Week 1)
    from datetime import datetime, timedelta
    date_options = []
    week_num = 1
    for d in all_dates:
        if d.startswith("week:"):
            date_str = datetime.strptime(d[5:], "%Y-%m-%d").strftime("%d/%m/%y")
            label = f"Week {week_num} - {date_str}"
            week_num += 1
        else:
            label = d
        date_options.append({
            "date_id":       d,
            "filename":      sanitize_date_id(d) + ".html",
            "label":         label,
            "is_mock":       False,
            "is_placeholder": False,
        })

    # Append a placeholder tab for the upcoming week (latest real week + 7 days)
    latest_week = next((d for d in reversed(all_dates) if d.startswith("week:")), None)
    placeholder_date_id = None
    if latest_week:
        latest_date_str = latest_week[5:]
        next_week_date = (datetime.strptime(latest_date_str, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")
        placeholder_date_id = f"week:{next_week_date}"
        placeholder_filename = f"week-{next_week_date}.html"
        date_options.append({
            "date_id":       placeholder_date_id,
            "filename":      placeholder_filename,
            "label":         f"Week {week_num}",
            "is_mock":       False,
            "is_placeholder": True,
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
        topics = []
        # Try Airtable first for week: dates
        if date_id.startswith("week:") and HAS_AIRTABLE_WRITER:
            at_cfg = _client_cfg.get("airtable", {})
            if at_cfg.get("enabled"):
                topics = load_content_from_airtable(date_id, active_client)

        if not topics:
            # Fall back to local Excel
            xlsx = find_excel(date_id)
            if not xlsx:
                print(f"  Warning: no content for '{date_id}' (no Airtable data and no Excel file), skipping")
                continue
            topics = load_content(xlsx)
        elif not any(t.get("image_filename") for t in topics):
            # Airtable loaded content but has no image URLs (e.g. R2 not configured).
            # Supplement image filenames from local Excel if available.
            xlsx = find_excel(date_id)
            if xlsx:
                try:
                    excel_topics = load_content(xlsx)
                    img_map = {et["topic"]: et for et in excel_topics}
                    for t in topics:
                        if t["topic"] in img_map:
                            et = img_map[t["topic"]]
                            t["image_filename"]    = et.get("image_filename")
                            t["image_filename_ru"] = et.get("image_filename_ru")
                except Exception as _img_e:
                    print(f"  Warning: could not merge Excel image paths: {_img_e}")

        safe_name = sanitize_date_id(date_id)

        # Copy EN and RU images for topics with local file paths (skip R2 URLs)
        for t in topics:
            # Ensure image_src is set for static build (relative prefix, not /images/)
            fn = t.get("image_filename")
            fn_ru = t.get("image_filename_ru")
            t["image_src"] = fn if (fn and fn.startswith("http")) else (f"images/{fn}" if fn else "")
            t["image_src_ru"] = fn_ru if (fn_ru and fn_ru.startswith("http")) else (f"images/{fn_ru}" if fn_ru else "")

            for img_key in ("image_filename", "image_filename_ru"):
                img_rel = t.get(img_key)
                if not img_rel or img_rel.startswith("http"):
                    continue  # Skip R2 URLs — they load directly in the browser

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

        # Derive week_of from date_id (e.g. 'week:2026-02-16' -> '2026-02-16')
        week_of_str = date_id.split(":")[-1] if ":" in date_id else date_id

        # Detect GitHub repo from env or git remote
        gh_repo = os.environ.get("GH_REPO", "")
        if not gh_repo:
            try:
                import subprocess as _sp
                remote = _sp.check_output(
                    ["git", "remote", "get-url", "origin"],
                    stderr=_sp.DEVNULL, text=True, cwd=str(Path(__file__).parent.parent)
                ).strip()
                # Parse 'https://github.com/owner/repo.git' or 'git@github.com:owner/repo.git'
                if "github.com" in remote:
                    if remote.startswith("https://"):
                        gh_repo = remote.replace("https://github.com/", "").removesuffix(".git")
                    else:
                        gh_repo = remote.split("github.com:")[-1].removesuffix(".git")
            except Exception:
                pass

        regen_worker_url = os.environ.get("REGEN_WORKER_URL", "")

        # Render the dashboard page (with auth guard)
        html = dashboard_template.render(
            topics=topics,
            date_label=date_display_label(date_id),
            current_date_id=date_id,
            date_options=date_options,
            brand_name=_display_name,
            expected_client_id=active_client,
            week_of=week_of_str,
            client_id=active_client,
            gh_repo=gh_repo,
            github_regen_token=github_regen_token,
            regen_worker_url=regen_worker_url,
            client_logo_url=client_logo_url,
            x_publishing_enabled=client_config.is_x_publishing_enabled(active_client),
            is_placeholder=False,
        )

        page_path = client_dash_dir / f"{safe_name}.html"
        page_path.write_text(html, encoding="utf-8")
        pages_built += 1
        print(f"  Built: dashboard/{active_client}/{page_path.name} ({len(topics)} topics)")

    # Build placeholder week page (upcoming week with Generate buttons per bucket)
    if placeholder_date_id and latest_week:
        ph_week_of = placeholder_date_id[5:]
        ph_html = dashboard_template.render(
            topics=[],
            date_label=date_options[-1]["label"],
            current_date_id=placeholder_date_id,
            date_options=date_options,
            brand_name=_display_name,
            expected_client_id=active_client,
            week_of=ph_week_of,
            client_id=active_client,
            gh_repo=gh_repo,
            github_regen_token=github_regen_token,
            regen_worker_url=regen_worker_url,
            client_logo_url=client_logo_url,
            x_publishing_enabled=client_config.is_x_publishing_enabled(active_client),
            is_placeholder=True,
        )
        ph_page_path = client_dash_dir / f"week-{ph_week_of}.html"
        ph_page_path.write_text(ph_html, encoding="utf-8")
        pages_built += 1
        print(f"  Built: dashboard/{active_client}/{ph_page_path.name} (placeholder)")

    # Copy favicon if available
    favicon_src = Path(__file__).parent.parent / "reference" / "favicon.jpg"
    if favicon_src.exists():
        shutil.copy2(str(favicon_src), str(output / "favicon.jpg"))

    # Generate dist/dashboard/{client_id}/index.html — redirect to latest (newest) date
    latest_page = sanitize_date_id(build_dates[-1]) + ".html"
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

    # Generate per-client login pages: dist/dashboard/{client_id}/login.html
    # Each page only contains that client's own credential (credential isolation).
    # This prevents any client from seeing other clients' hashed credentials in source.
    per_client_login_template = plain_env.from_string(PER_CLIENT_LOGIN_HTML)
    all_creds = credentials or []
    clients_dir_for_login = Path(__file__).parent.parent / "clients"
    for client_dir in sorted(clients_dir_for_login.iterdir()):
        if not client_dir.is_dir() or client_dir.name.startswith("_"):
            continue
        client_cfg_path = client_dir / "config.json"
        if not client_cfg_path.exists():
            continue
        with open(client_cfg_path) as _f:
            _cfg = json.load(_f)
        _cid = _cfg.get("client_id", client_dir.name)
        _dname = _cfg.get("display_name", _cid)
        # Filter to only this client's credential
        client_cred = [c for c in all_creds if c.get("client_id") == _cid]
        if not client_cred:
            continue
        client_login_html = per_client_login_template.render(
            brand_name=_dname,
            credentials_json=json.dumps(client_cred, ensure_ascii=False),
        )
        client_login_dir = output / "dashboard" / _cid
        client_login_dir.mkdir(parents=True, exist_ok=True)
        (client_login_dir / "login.html").write_text(client_login_html, encoding="utf-8")
        print(f"  Built: dashboard/{_cid}/login.html (1 credential baked in)")

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
    parser.add_argument("--no-clean", action="store_true", default=False,
                        help="Don't wipe output dir before building (use for multi-client sequential builds)")
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

    build_site(args.output, args.dates, credentials=credentials, active_client=active_client,
               clean=not args.no_clean)

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

        # Inline intake-config.js into the deployed HTML so EmailJS works on the live site.
        # The external file is deleted — keys are embedded in the page instead of a named file.
        config_src = intake_src / "intake-config.js"
        config_in_dist = intake_dst / "intake-config.js"
        intake_html_path = intake_dst / "index.html"

        if config_src.exists() and intake_html_path.exists():
            config_content = config_src.read_text(encoding="utf-8")
            html = intake_html_path.read_text(encoding="utf-8")
            inline_tag = f'<script src="intake-config.js" onerror="window.INTAKE_CONFIG=null"></script>'
            replacement = f'<script>\n{config_content}\n</script>'
            if inline_tag in html:
                html = html.replace(inline_tag, replacement)
                intake_html_path.write_text(html, encoding="utf-8")
                print(f"  Intake form copied to {intake_dst} (EmailJS config inlined)")
            else:
                print(f"  Intake form copied to {intake_dst} (warning: could not find config script tag to inline)")
        else:
            if not config_src.exists():
                print(f"  Intake form copied to {intake_dst} (warning: intake-config.js not found — email delivery will fail on live site)")
            else:
                print(f"  Intake form copied to {intake_dst}")

        # Always remove the standalone config file from dist — config is inlined above
        if config_in_dist.exists():
            config_in_dist.unlink()

    # Write CNAME for custom domain (GitHub Pages)
    cname_path = Path(args.output) / "CNAME"
    cname_path.write_text("content.rejiglabs.com\n")
    print(f"  CNAME written: content.rejiglabs.com")


if __name__ == "__main__":
    main()
