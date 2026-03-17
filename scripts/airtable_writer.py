#!/usr/bin/env python3
"""
Airtable Writer — Write content items directly to Airtable (no Excel intermediate).

Writes one content row at a time to the Week-{week_of} table in the client's
Airtable base. Creates the table if it doesn't exist (via meta API).

Schema written:
  Date, Bucket, Day, Topic, Platform, Format, Content, Image_Prompt,
  Image_URL_EN, Hashtags, Content_RU, Image_Prompt_RU, Image_URL_RU,
  Hashtags_RU, Status, Tweet_URL, Week, Client

Usage:
  import airtable_writer
  api_key = airtable_writer.get_api_key("bobe")
  table_id = airtable_writer.get_or_create_table(base_id, week_of, api_key)
  record_id = airtable_writer.write_record(base_id, table_id, item, week_of, "bobe", api_key)
  airtable_writer.update_image_urls(base_id, table_id, record_id, image_url_en=url, api_key=api_key)
  records = airtable_writer.load_records(base_id, table_id, api_key)
"""

import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import sys
sys.path.insert(0, str(Path(__file__).parent))
import client_config

AIRTABLE_BASE_URL = "https://api.airtable.com/v0"
AIRTABLE_META_URL = "https://api.airtable.com/v0/meta/bases"

# singleSelect choices for structured fields
STATUS_CHOICES = [
    {"name": "Draft",         "color": "yellowLight2"},
    {"name": "Approved",      "color": "greenLight2"},
    {"name": "Published",     "color": "blueLight2"},
    {"name": "Rejected",      "color": "redLight2"},
    {"name": "Pending Input", "color": "grayLight2"},
]
BUCKET_CHOICES = [
    {"name": "Trending",      "color": "cyanLight2"},
    {"name": "Education",     "color": "purpleLight2"},
    {"name": "Announcements", "color": "orangeLight2"},
]
PLATFORM_CHOICES = [
    {"name": "Twitter",  "color": "blueLight2"},
    {"name": "Telegram", "color": "tealLight2"},
]
FORMAT_CHOICES = [
    {"name": "thread",  "color": "purpleLight2"},
    {"name": "single",  "color": "greenLight2"},
    {"name": "post",    "color": "orangeLight2"},
]


def _wrap_attachment(url: str):
    """Wrap a URL string in Airtable multipleAttachments format."""
    if not url:
        return None
    return [{"url": url}]


def _extract_attachment_url(value) -> str:
    """Extract URL from an Airtable attachment field value (list of dicts) or plain string."""
    if not value:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list) and len(value) > 0:
        first = value[0]
        if isinstance(first, dict):
            return first.get("url", "") or first.get("thumbnails", {}).get("large", {}).get("url", "")
    return ""


def get_api_key(client_id: str = None) -> str:
    """Return the Airtable API key for the given client."""
    key_env = "AIRTABLE_API_KEY"
    if client_id:
        try:
            cfg = client_config.load_config(client_id)
            key_env = cfg.get("airtable", {}).get("api_key_env", "AIRTABLE_API_KEY")
        except Exception:
            pass
    return os.environ.get(key_env, "")


def get_or_create_table(base_id: str, week_of: str, api_key: str) -> str:
    """
    Return the table ID for Week-{week_of}. Creates the table if not found.
    Returns table ID string.
    """
    table_name = f"Week-{week_of}"
    headers = {"Authorization": f"Bearer {api_key}"}

    # List existing tables
    resp = requests.get(f"{AIRTABLE_META_URL}/{base_id}/tables", headers=headers, timeout=15)
    resp.raise_for_status()
    tables = resp.json().get("tables", [])

    for t in tables:
        if t["name"] == table_name:
            return t["id"]

    # Create table with the full 18-field schema
    # Image fields use multipleAttachments so images render inline in Airtable
    # Status and Bucket use singleSelect for dropdowns and colored labels
    fields = [
        {"name": "Date",           "type": "singleLineText"},
        {"name": "Bucket",         "type": "singleSelect", "options": {"choices": BUCKET_CHOICES}},
        {"name": "Day",            "type": "singleLineText"},
        {"name": "Topic",          "type": "singleLineText"},
        {"name": "Platform",       "type": "singleSelect", "options": {"choices": PLATFORM_CHOICES}},
        {"name": "Format",         "type": "singleSelect", "options": {"choices": FORMAT_CHOICES}},
        {"name": "Content",        "type": "multilineText"},
        {"name": "Image_Prompt",   "type": "multilineText"},
        {"name": "Image_URL_EN",   "type": "multipleAttachments"},
        {"name": "Hashtags",       "type": "singleLineText"},
        {"name": "Content_RU",     "type": "multilineText"},
        {"name": "Image_Prompt_RU","type": "multilineText"},
        {"name": "Image_URL_RU",   "type": "multipleAttachments"},
        {"name": "Hashtags_RU",    "type": "singleLineText"},
        {"name": "Status",         "type": "singleSelect", "options": {"choices": STATUS_CHOICES}},
        {"name": "Tweet_URL",      "type": "url"},
        {"name": "Week",           "type": "singleLineText"},
        {"name": "Client",         "type": "singleLineText"},
    ]
    body = {"name": table_name, "fields": fields}
    resp = requests.post(
        f"{AIRTABLE_META_URL}/{base_id}/tables",
        headers={**headers, "Content-Type": "application/json"},
        json=body,
        timeout=15,
    )
    resp.raise_for_status()
    print(f"  Created Airtable table: {table_name}")
    return resp.json()["id"]


def write_record(
    base_id: str,
    table_id: str,
    item: dict,
    week_of: str,
    client_id: str,
    api_key: str,
) -> str:
    """
    Write a single content item to Airtable. Returns the created record ID.

    item keys: date, bucket, day, topic, platform, format, content, image_prompt,
               image_url_en (optional), hashtags, content_ru, image_prompt_ru,
               image_url_ru (optional), hashtags_ru, status, tweet_url (optional)
    """
    hashtags = item.get("hashtags", [])
    hashtags_ru = item.get("hashtags_ru", [])
    if isinstance(hashtags, list):
        hashtags = ", ".join(hashtags)
    if isinstance(hashtags_ru, list):
        hashtags_ru = ", ".join(hashtags_ru)

    # Capitalize bucket name to match singleSelect choices
    bucket_raw = item.get("bucket", "")
    bucket_val = bucket_raw.strip().capitalize() if bucket_raw else ""
    if bucket_val.lower() == "announcements":
        bucket_val = "Announcements"

    fields = {
        "Date":            str(item.get("date", "")),
        "Bucket":          bucket_val or None,
        "Day":             item.get("day", ""),
        "Topic":           item.get("topic", ""),
        "Platform":        item.get("platform", ""),
        "Format":          item.get("format", ""),
        "Content":         item.get("content", ""),
        "Image_Prompt":    item.get("image_prompt", ""),
        "Image_URL_EN":    _wrap_attachment(item.get("image_url_en")),
        "Hashtags":        hashtags,
        "Content_RU":      item.get("content_ru", ""),
        "Image_Prompt_RU": item.get("image_prompt_ru", ""),
        "Image_URL_RU":    _wrap_attachment(item.get("image_url_ru")),
        "Hashtags_RU":     hashtags_ru,
        "Status":          item.get("status", "Draft"),
        "Tweet_URL":       item.get("tweet_url") or None,
        "Week":            week_of,
        "Client":          client_id,
    }
    # Remove None values — Airtable rejects null for attachment/url-type fields
    fields = {k: v for k, v in fields.items() if v is not None}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = f"{AIRTABLE_BASE_URL}/{base_id}/{table_id}"
    resp = requests.post(url, headers=headers, json={"fields": fields}, timeout=15)
    resp.raise_for_status()
    return resp.json()["id"]


def update_image_urls(
    base_id: str,
    table_id: str,
    record_id: str,
    image_url_en: str = None,
    image_url_ru: str = None,
    api_key: str = "",
):
    """Patch Image_URL_EN and/or Image_URL_RU on an existing record (attachment format)."""
    fields = {}
    if image_url_en:
        fields["Image_URL_EN"] = _wrap_attachment(image_url_en)
    if image_url_ru:
        fields["Image_URL_RU"] = _wrap_attachment(image_url_ru)
    if not fields:
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = f"{AIRTABLE_BASE_URL}/{base_id}/{table_id}/{record_id}"
    resp = requests.patch(url, headers=headers, json={"fields": fields}, timeout=15)
    resp.raise_for_status()


def update_publish_status(
    base_id: str,
    table_id: str,
    record_id: str,
    status: str = "Published",
    tweet_url: str = "",
    api_key: str = "",
):
    """Update Status and Tweet_URL on a record after publishing to X."""
    fields = {"Status": status}
    if tweet_url:
        fields["Tweet_URL"] = tweet_url

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = f"{AIRTABLE_BASE_URL}/{base_id}/{table_id}/{record_id}"
    resp = requests.patch(url, headers=headers, json={"fields": fields}, timeout=15)
    resp.raise_for_status()


def load_records(base_id: str, table_id: str, api_key: str) -> list:
    """
    Fetch all records from a table. Returns list of {id, fields} dicts.
    Handles pagination automatically.
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    records = []
    offset = None

    while True:
        params = {"pageSize": 100}
        if offset:
            params["offset"] = offset
        resp = requests.get(
            f"{AIRTABLE_BASE_URL}/{base_id}/{table_id}",
            headers=headers,
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break
        time.sleep(0.25)

    return records


def list_week_tables(base_id: str, api_key: str) -> list:
    """
    Return sorted list of week_of strings for all Week-* tables in the base.
    E.g. ["2026-03-09", "2026-03-02", "2026-02-16"]
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.get(f"{AIRTABLE_META_URL}/{base_id}/tables", headers=headers, timeout=15)
    resp.raise_for_status()
    tables = resp.json().get("tables", [])
    weeks = []
    for t in tables:
        name = t.get("name", "")
        if name.startswith("Week-") and len(name) == 15:  # "Week-YYYY-MM-DD"
            weeks.append(name[5:])  # strip "Week-"
    return sorted(weeks, reverse=True)


def records_to_topics(records: list) -> list:
    """
    Convert Airtable records (list of {id, fields} dicts) to the topic dict
    format expected by web_viewer.py and build_static.py.

    Output keys per topic:
      topic, date, day, bucket, img_prompt, image_url_en, img_prompt_ru,
      image_url_ru, twitter, telegram, twitter_ru, telegram_ru,
      hashtags, hashtags_ru, hashtag_list, hashtag_list_ru, status, tweet_url
    """
    topics = {}
    topic_order = []

    for rec in records:
        f = rec.get("fields", {})
        topic_name = f.get("Topic", "")
        if not topic_name:
            continue

        platform = (f.get("Platform") or "").lower()
        content = f.get("Content", "")
        content_ru = f.get("Content_RU", "")
        hashtags = f.get("Hashtags", "")
        hashtags_ru = f.get("Hashtags_RU", "")
        # Extract image URLs from attachment objects or plain strings
        image_en_raw = f.get("Image_URL_EN", "")
        image_ru_raw = f.get("Image_URL_RU", "")
        image_en = _extract_attachment_url(image_en_raw)
        image_ru = _extract_attachment_url(image_ru_raw)
        # Extract singleSelect values (may be dict with "name" key or plain string)
        bucket_raw = f.get("Bucket") or "trending"
        if isinstance(bucket_raw, dict):
            bucket_raw = bucket_raw.get("name", "trending")
        status_raw = f.get("Status", "Draft")
        if isinstance(status_raw, dict):
            status_raw = status_raw.get("name", "Draft")

        if topic_name not in topics:
            topics[topic_name] = {
                "topic":          topic_name,
                "date":           str(f.get("Date", "")),
                "day":            f.get("Day", ""),
                "bucket":         bucket_raw.strip().lower(),
                "img_prompt":     f.get("Image_Prompt", ""),
                "image_url_en":   image_en,
                "img_prompt_ru":  f.get("Image_Prompt_RU", ""),
                "image_url_ru":   image_ru,
                # Legacy fields for backwards compat with web_viewer image resolution
                "image_filename":    None,
                "image_filename_ru": None,
                "raw_image_path":    image_en,
                "raw_image_path_ru": image_ru,
                "twitter":        None,
                "telegram":       None,
                "twitter_ru":     None,
                "telegram_ru":    None,
                "hashtags":       hashtags,
                "hashtags_ru":    hashtags_ru,
                "status":         status_raw,
                "tweet_url":      f.get("Tweet_URL", "") or "",
                "airtable_id":    rec.get("id", ""),
            }
            topic_order.append(topic_name)

        if "twitter" in platform:
            topics[topic_name]["twitter"] = content
            if content_ru:
                topics[topic_name]["twitter_ru"] = content_ru
            topics[topic_name]["status"] = status_raw
            topics[topic_name]["tweet_url"] = f.get("Tweet_URL", "") or ""
            topics[topic_name]["airtable_id"] = rec.get("id", "")
            # Image URLs come from Twitter row (handle attachment objects)
            if image_en:
                topics[topic_name]["image_url_en"] = image_en
                topics[topic_name]["raw_image_path"] = image_en
            if image_ru:
                topics[topic_name]["image_url_ru"] = image_ru
                topics[topic_name]["raw_image_path_ru"] = image_ru
        elif "telegram" in platform:
            topics[topic_name]["telegram"] = content
            if content_ru:
                topics[topic_name]["telegram_ru"] = content_ru
            if hashtags:
                topics[topic_name]["hashtags"] = hashtags
            if hashtags_ru:
                topics[topic_name]["hashtags_ru"] = hashtags_ru

    result = []
    for key in topic_order:
        t = topics[key]
        raw = t["hashtags"]
        t["hashtag_list"] = [h.strip() for h in str(raw).split(",") if h.strip()] if raw else []
        raw_ru = t["hashtags_ru"]
        t["hashtag_list_ru"] = [h.strip() for h in str(raw_ru).split(",") if h.strip()] if raw_ru else []
        # Use image_url_en as image_filename for URL-based display
        t["image_filename"] = t["image_url_en"] or None
        t["image_filename_ru"] = t["image_url_ru"] or None
        result.append(t)

    # Sort by date then day for consistent ordering across loads
    day_order = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
    result.sort(key=lambda t: (
        str(t.get("date", "")),
        day_order.get(str(t.get("day", "")).lower()[:3], 99),
    ))

    return result
