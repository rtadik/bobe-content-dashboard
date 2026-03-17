#!/usr/bin/env python3
"""
Baserow Client Module

Abstracts Baserow REST API operations for client settings, content approvals,
and image style preferences. Used by pipeline_runner.py, web_viewer.py, and
build_static.py.

Tables:
  - Client_Settings: API keys, brand overrides, setup state
  - Content_Approvals: Per-topic approval state (content/image/translation)
  - Image_Style_Preferences: 4 style variants per client, 1 selected

Requires BASEROW_API_TOKEN and BASEROW_DATABASE_ID in .env.
Falls back gracefully if Baserow is unreachable.
"""

import os
import json
import logging
import requests
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("baserow")

# Load .env if not already loaded
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

BASE_URL = os.environ.get("BASEROW_URL", "https://api.baserow.io")
API_TOKEN = os.environ.get("BASEROW_API_TOKEN", "")
DATABASE_ID = os.environ.get("BASEROW_DATABASE_ID", "")

# Table IDs — populated by setup_tables() or set manually after table creation
# These can also be set via env vars for portability
TABLE_IDS = {
    "client_settings": int(os.environ.get("BASEROW_TABLE_CLIENT_SETTINGS", "0")),
    "content_approvals": int(os.environ.get("BASEROW_TABLE_CONTENT_APPROVALS", "0")),
    "image_style_preferences": int(os.environ.get("BASEROW_TABLE_IMAGE_STYLE_PREFS", "0")),
}


def is_configured() -> bool:
    """Return True if Baserow API token and at least one table ID are set."""
    return bool(API_TOKEN and any(TABLE_IDS.values()))


def _headers() -> dict:
    return {
        "Authorization": f"Token {API_TOKEN}",
        "Content-Type": "application/json",
    }


def _api(method: str, url: str, data: dict = None, timeout: int = 15) -> dict:
    """Make an API call to Baserow. Returns response JSON or empty dict on error."""
    try:
        resp = requests.request(
            method,
            f"{BASE_URL}{url}",
            headers=_headers(),
            json=data,
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}
    except requests.RequestException as e:
        logger.warning(f"Baserow API error: {e}")
        return {}


# ── Table Setup ───────────────────────────────────────────────────────────────

CLIENT_SETTINGS_FIELDS = [
    {"name": "client_id", "type": "text"},
    {"name": "display_name", "type": "text"},
    {"name": "google_ai_api_key", "type": "text"},
    {"name": "wavespeed_api_key", "type": "text"},
    {"name": "wavespeed_ru_api_key", "type": "text"},
    {"name": "airtable_api_key", "type": "text"},
    {"name": "airtable_base_id", "type": "text"},
    {"name": "apify_api_token", "type": "text"},
    {"name": "x_api_key", "type": "text"},
    {"name": "x_api_secret", "type": "text"},
    {"name": "x_access_token", "type": "text"},
    {"name": "x_access_token_secret", "type": "text"},
    {"name": "logo_url", "type": "url"},
    {"name": "primary_color", "type": "text"},
    {"name": "accent_color", "type": "text"},
    {"name": "tone_override", "type": "long_text"},
    {"name": "setup_complete", "type": "boolean"},
    {"name": "selected_style_id", "type": "text"},
    {"name": "created_at", "type": "date", "date_format": "ISO"},
    {"name": "updated_at", "type": "date", "date_format": "ISO"},
]

CONTENT_APPROVALS_FIELDS = [
    {"name": "client_id", "type": "text"},
    {"name": "week_of", "type": "text"},
    {"name": "topic_index", "type": "number", "number_decimal_places": 0},
    {"name": "platform", "type": "text"},
    {"name": "content_status", "type": "single_select", "select_options": [
        {"value": "pending", "color": "yellow"},
        {"value": "approved", "color": "green"},
        {"value": "rejected", "color": "red"},
        {"value": "regenerating", "color": "blue"},
    ]},
    {"name": "image_status", "type": "single_select", "select_options": [
        {"value": "waiting", "color": "light-gray"},
        {"value": "pending", "color": "yellow"},
        {"value": "approved", "color": "green"},
        {"value": "rejected", "color": "red"},
        {"value": "regenerating", "color": "blue"},
    ]},
    {"name": "translation_status", "type": "single_select", "select_options": [
        {"value": "pending", "color": "yellow"},
        {"value": "completed", "color": "green"},
        {"value": "skipped", "color": "light-gray"},
    ]},
    {"name": "content_approved_at", "type": "date", "date_format": "ISO"},
    {"name": "image_approved_at", "type": "date", "date_format": "ISO"},
    {"name": "notes", "type": "long_text"},
]

IMAGE_STYLE_PREFS_FIELDS = [
    {"name": "client_id", "type": "text"},
    {"name": "style_preset", "type": "text"},
    {"name": "sample_image_url", "type": "url"},
    {"name": "sample_prompt", "type": "long_text"},
    {"name": "selected", "type": "boolean"},
    {"name": "created_at", "type": "date", "date_format": "ISO"},
]


def _create_table(name: str, fields: list) -> int:
    """Create a Baserow table and return its ID. Returns 0 on failure."""
    if not DATABASE_ID:
        logger.warning("BASEROW_DATABASE_ID not set, cannot create tables")
        return 0

    data = {"name": name, "fields": fields}
    result = _api("POST", f"/api/database/tables/database/{DATABASE_ID}/", data)
    table_id = result.get("id", 0)
    if table_id:
        logger.info(f"Created Baserow table '{name}' with ID {table_id}")
    return table_id


def setup_tables() -> dict:
    """Create all 3 tables if they don't exist. Returns dict of table IDs."""
    global TABLE_IDS

    if not API_TOKEN or not DATABASE_ID:
        logger.warning("Baserow not configured (missing BASEROW_API_TOKEN or BASEROW_DATABASE_ID)")
        return TABLE_IDS

    # List existing tables
    existing = _api("GET", f"/api/database/tables/database/{DATABASE_ID}/")
    existing_names = {}
    if isinstance(existing, list):
        existing_names = {t["name"]: t["id"] for t in existing}
    elif isinstance(existing, dict) and "results" in existing:
        existing_names = {t["name"]: t["id"] for t in existing["results"]}

    table_map = {
        "client_settings": ("Client_Settings", CLIENT_SETTINGS_FIELDS),
        "content_approvals": ("Content_Approvals", CONTENT_APPROVALS_FIELDS),
        "image_style_preferences": ("Image_Style_Preferences", IMAGE_STYLE_PREFS_FIELDS),
    }

    for key, (name, fields) in table_map.items():
        if name in existing_names:
            TABLE_IDS[key] = existing_names[name]
            logger.info(f"Found existing table '{name}' with ID {existing_names[name]}")
        elif TABLE_IDS[key] == 0:
            TABLE_IDS[key] = _create_table(name, fields)

    return TABLE_IDS


# ── Client Settings ──────────────────────────────────────────────────────────

def _find_row(table_key: str, field: str, value: str) -> dict:
    """Find a row by field value. Returns first match or empty dict."""
    table_id = TABLE_IDS.get(table_key, 0)
    if not table_id or not is_configured():
        return {}

    result = _api("GET", f"/api/database/rows/table/{table_id}/?user_field_names=true&search={value}&size=10")
    rows = result.get("results", [])
    for row in rows:
        if str(row.get(field, "")).strip() == value:
            return row
    return {}


def _list_rows(table_key: str, search: str = "", size: int = 100) -> list:
    """List rows from a table with optional search."""
    table_id = TABLE_IDS.get(table_key, 0)
    if not table_id or not is_configured():
        return []

    result = _api("GET", f"/api/database/rows/table/{table_id}/?user_field_names=true&size={size}" +
                  (f"&search={search}" if search else ""))
    return result.get("results", [])


def _create_row(table_key: str, data: dict) -> dict:
    """Create a row in a table. Returns the created row or empty dict."""
    table_id = TABLE_IDS.get(table_key, 0)
    if not table_id or not is_configured():
        return {}
    return _api("POST", f"/api/database/rows/table/{table_id}/?user_field_names=true", data)


def _update_row(table_key: str, row_id: int, data: dict) -> dict:
    """Update a row by ID. Returns the updated row or empty dict."""
    table_id = TABLE_IDS.get(table_key, 0)
    if not table_id or not is_configured():
        return {}
    return _api("PATCH", f"/api/database/rows/table/{table_id}/{row_id}/?user_field_names=true", data)


def get_client_settings(client_id: str) -> dict:
    """Read Client_Settings row by client_id. Returns field values or empty dict."""
    row = _find_row("client_settings", "client_id", client_id)
    if not row:
        return {}
    return {k: v for k, v in row.items() if not k.startswith("order_") and k != "id"}


def save_client_settings(client_id: str, settings: dict) -> int:
    """Upsert Client_Settings row. Returns row_id."""
    existing = _find_row("client_settings", "client_id", client_id)
    settings["client_id"] = client_id
    settings["updated_at"] = datetime.now().strftime("%Y-%m-%d")

    if existing and existing.get("id"):
        result = _update_row("client_settings", existing["id"], settings)
        return result.get("id", existing["id"])
    else:
        settings["created_at"] = datetime.now().strftime("%Y-%m-%d")
        result = _create_row("client_settings", settings)
        return result.get("id", 0)


def get_api_key_from_baserow(client_id: str, service: str) -> str:
    """Fetch a specific API key for a client from Baserow.

    Service mapping:
      gemini -> google_ai_api_key
      wavespeed_en -> wavespeed_api_key
      wavespeed_ru -> wavespeed_ru_api_key
      airtable -> airtable_api_key
      apify -> apify_api_token
    """
    service_field_map = {
        "gemini": "gemini_key",
        "wavespeed_en": "wavespeed_key",
        "wavespeed_ru": "wavespeed_key",
        "airtable": "airtable_key",
        "apify": "apify_key",
        "x_api_key": "x_api_key",
        "x_api_secret": "x_api_secret",
        "x_access_token": "x_access_token",
        "x_access_token_secret": "x_access_secret",
    }
    field = service_field_map.get(service, service)
    settings = get_client_settings(client_id)
    return str(settings.get(field, "") or "")


def is_setup_complete(client_id: str) -> bool:
    """Check if the client has completed the first-login setup wizard."""
    settings = get_client_settings(client_id)
    return bool(settings.get("setup_complete"))


def mark_setup_complete(client_id: str):
    """Mark the client's setup wizard as complete."""
    save_client_settings(client_id, {"setup_complete": True})


# ── Content Approvals ────────────────────────────────────────────────────────

def _find_approval(client_id: str, week_of: str, topic_index: int, platform: str) -> dict:
    """Find an approval row by composite key."""
    rows = _list_rows("content_approvals", search=f"{client_id} {week_of}")
    for row in rows:
        if (str(row.get("client_id", "")) == client_id and
            str(row.get("week_of", "")) == week_of and
            row.get("topic_index") == topic_index and
            str(row.get("platform", "")).lower() == platform.lower()):
            return row
    return {}


def get_content_approval(client_id: str, week_of: str, topic_index: int, platform: str) -> dict:
    """Get approval state for a specific content item."""
    row = _find_approval(client_id, week_of, topic_index, platform)
    if not row:
        return {
            "content_status": "pending",
            "image_status": "waiting",
            "translation_status": "pending",
        }
    return {
        "content_status": row.get("content_status", {}).get("value", "pending") if isinstance(row.get("content_status"), dict) else str(row.get("content_status", "pending")),
        "image_status": row.get("image_status", {}).get("value", "waiting") if isinstance(row.get("image_status"), dict) else str(row.get("image_status", "waiting")),
        "translation_status": row.get("translation_status", {}).get("value", "pending") if isinstance(row.get("translation_status"), dict) else str(row.get("translation_status", "pending")),
        "notes": row.get("notes", ""),
        "row_id": row.get("id"),
    }


def set_content_approval(client_id: str, week_of: str, topic_index: int,
                          platform: str, status: str, notes: str = "") -> int:
    """Set content approval status. Creates row if it doesn't exist."""
    existing = _find_approval(client_id, week_of, topic_index, platform)
    data = {"content_status": status}
    if notes:
        data["notes"] = notes
    if status == "approved":
        data["content_approved_at"] = datetime.now().strftime("%Y-%m-%d")
        data["image_status"] = "pending"  # Unlock image generation

    if existing and existing.get("id"):
        result = _update_row("content_approvals", existing["id"], data)
        return result.get("id", existing["id"])
    else:
        data.update({
            "client_id": client_id,
            "week_of": week_of,
            "topic_index": topic_index,
            "platform": platform,
            "image_status": "waiting" if status != "approved" else "pending",
            "translation_status": "pending",
        })
        result = _create_row("content_approvals", data)
        return result.get("id", 0)


def set_image_approval(client_id: str, week_of: str, topic_index: int,
                        platform: str, status: str) -> int:
    """Set image approval status."""
    existing = _find_approval(client_id, week_of, topic_index, platform)
    data = {"image_status": status}
    if status == "approved":
        data["image_approved_at"] = datetime.now().strftime("%Y-%m-%d")

    if existing and existing.get("id"):
        result = _update_row("content_approvals", existing["id"], data)
        return result.get("id", existing["id"])
    return 0


def set_translation_status(client_id: str, week_of: str, topic_index: int,
                            platform: str, status: str) -> int:
    """Set translation status."""
    existing = _find_approval(client_id, week_of, topic_index, platform)
    data = {"translation_status": status}

    if existing and existing.get("id"):
        result = _update_row("content_approvals", existing["id"], data)
        return result.get("id", existing["id"])
    return 0


def get_week_approvals(client_id: str, week_of: str) -> list:
    """Get all approval states for a given week."""
    rows = _list_rows("content_approvals", search=f"{client_id} {week_of}")
    approvals = []
    for row in rows:
        if str(row.get("client_id", "")) == client_id and str(row.get("week_of", "")) == week_of:
            approvals.append({
                "topic_index": row.get("topic_index"),
                "platform": row.get("platform", ""),
                "content_status": row.get("content_status", {}).get("value", "pending") if isinstance(row.get("content_status"), dict) else str(row.get("content_status", "pending")),
                "image_status": row.get("image_status", {}).get("value", "waiting") if isinstance(row.get("image_status"), dict) else str(row.get("image_status", "waiting")),
                "translation_status": row.get("translation_status", {}).get("value", "pending") if isinstance(row.get("translation_status"), dict) else str(row.get("translation_status", "pending")),
                "row_id": row.get("id"),
            })
    return approvals


def init_week_approvals(client_id: str, week_of: str, topic_count: int = 21):
    """Initialize approval rows for a new week (all content_status=pending)."""
    for i in range(topic_count):
        for platform in ["Twitter", "Telegram"]:
            existing = _find_approval(client_id, week_of, i, platform)
            if not existing:
                _create_row("content_approvals", {
                    "client_id": client_id,
                    "week_of": week_of,
                    "topic_index": i,
                    "platform": platform,
                    "content_status": "pending",
                    "image_status": "waiting",
                    "translation_status": "pending",
                })


# ── Image Style Preferences ─────────────────────────────────────────────────

def get_style_preferences(client_id: str) -> list:
    """Get all style sample records for a client."""
    rows = _list_rows("image_style_preferences", search=client_id)
    return [
        {
            "id": row.get("id"),
            "style_preset": row.get("style_preset", ""),
            "sample_image_url": row.get("sample_image_url", ""),
            "sample_prompt": row.get("sample_prompt", ""),
            "selected": bool(row.get("selected")),
        }
        for row in rows
        if str(row.get("client_id", "")) == client_id
    ]


def save_style_preference(client_id: str, style_preset: str,
                           image_url: str, prompt: str) -> int:
    """Save a generated style sample. Returns row_id."""
    result = _create_row("image_style_preferences", {
        "client_id": client_id,
        "style_preset": style_preset,
        "sample_image_url": image_url,
        "sample_prompt": prompt,
        "selected": False,
        "created_at": datetime.now().strftime("%Y-%m-%d"),
    })
    return result.get("id", 0)


def select_style(client_id: str, style_row_id: int):
    """Mark one style as selected, unmark all others for this client."""
    prefs = get_style_preferences(client_id)
    for pref in prefs:
        if pref["id"] == style_row_id:
            _update_row("image_style_preferences", pref["id"], {"selected": True})
        elif pref.get("selected"):
            _update_row("image_style_preferences", pref["id"], {"selected": False})


def get_selected_style(client_id: str) -> dict:
    """Get the client's chosen style preference. Returns {} if none selected."""
    prefs = get_style_preferences(client_id)
    for pref in prefs:
        if pref.get("selected"):
            return pref
    return {}


# ── CLI Setup ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Baserow client state manager")
    parser.add_argument("--setup", action="store_true", help="Create Baserow tables")
    parser.add_argument("--test", action="store_true", help="Test connectivity")
    parser.add_argument("--client", default="bobe", help="Client ID for test operations")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.setup:
        ids = setup_tables()
        print(f"\nTable IDs (add to .env):")
        for key, tid in ids.items():
            env_key = f"BASEROW_TABLE_{key.upper()}"
            print(f"  {env_key}={tid}")

    if args.test:
        print(f"\nTesting with client: {args.client}")
        settings = get_client_settings(args.client)
        if settings:
            print(f"  Settings found: {list(settings.keys())}")
        else:
            print(f"  No settings found (Baserow may not be configured)")
        print(f"  Setup complete: {is_setup_complete(args.client)}")

        prefs = get_style_preferences(args.client)
        print(f"  Style preferences: {len(prefs)} samples")

        selected = get_selected_style(args.client)
        print(f"  Selected style: {selected.get('style_preset', 'none')}")
