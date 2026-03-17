#!/usr/bin/env python3
"""
Airtable Migration — Convert existing Week tables to visual schema.

Migrates existing Airtable Week-* tables from the old schema (url fields,
singleLineText for Status/Bucket) to the new visual schema:
  - Image_URL_EN / Image_URL_RU: url -> multipleAttachments (inline images)
  - Status: singleLineText -> singleSelect (colored dropdown)
  - Bucket: singleLineText -> singleSelect (colored tags)

Strategy (Airtable API does not support field type conversion):
  1. Rename old field (e.g., Image_URL_EN -> Image_URL_EN_old)
  2. Create new field with correct type and original name
  3. Copy data from old field to new field (per record)
  4. Old fields left as *_old for safety (can be hidden or deleted in UI)

Usage:
  python scripts/airtable_migrate.py --client bobe --dry-run
  python scripts/airtable_migrate.py --client bobe
  python scripts/airtable_migrate.py --client bobe --cleanup  # delete _old fields
"""

import os
import sys
import time
import argparse
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent))
import client_config
import airtable_writer

AIRTABLE_API_URL = "https://api.airtable.com/v0"
AIRTABLE_META_URL = "https://api.airtable.com/v0/meta/bases"

RATE_LIMIT_DELAY = 0.25  # 4 req/sec (under 5/sec limit)
BATCH_SIZE = 10  # Airtable batch limit

# Fields to migrate: name -> (target_type, creation_body)
FIELD_MIGRATIONS = {
    "Image_URL_EN": {
        "target_type": "multipleAttachments",
        "from_types": ["url", "singleLineText"],
        "create_body": {"name": "Image_URL_EN", "type": "multipleAttachments"},
    },
    "Image_URL_RU": {
        "target_type": "multipleAttachments",
        "from_types": ["url", "singleLineText"],
        "create_body": {"name": "Image_URL_RU", "type": "multipleAttachments"},
    },
    "Status": {
        "target_type": "singleSelect",
        "from_types": ["singleLineText"],
        "create_body": {
            "name": "Status",
            "type": "singleSelect",
            "options": {"choices": airtable_writer.STATUS_CHOICES},
        },
    },
    "Bucket": {
        "target_type": "singleSelect",
        "from_types": ["singleLineText"],
        "create_body": {
            "name": "Bucket",
            "type": "singleSelect",
            "options": {"choices": airtable_writer.BUCKET_CHOICES},
        },
    },
    "Platform": {
        "target_type": "singleSelect",
        "from_types": ["singleLineText"],
        "create_body": {
            "name": "Platform",
            "type": "singleSelect",
            "options": {"choices": airtable_writer.PLATFORM_CHOICES},
        },
    },
    "Format": {
        "target_type": "singleSelect",
        "from_types": ["singleLineText"],
        "create_body": {
            "name": "Format",
            "type": "singleSelect",
            "options": {"choices": airtable_writer.FORMAT_CHOICES},
        },
    },
}


def api_headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def get_tables(base_id: str, api_key: str) -> list:
    """Fetch all tables with their field schemas."""
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.get(f"{AIRTABLE_META_URL}/{base_id}/tables", headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json().get("tables", [])


def find_week_tables(tables: list) -> list:
    """Filter to Week tables (Week-YYYY-MM-DD or Week N), sorted by name descending."""
    week_tables = []
    for t in tables:
        name = t.get("name", "")
        if name.startswith("Week"):
            week_tables.append(t)
    week_tables.sort(key=lambda t: t["name"], reverse=True)
    return week_tables


def get_fields_to_migrate(table: dict) -> list:
    """
    Check which fields in a table need migration.
    Returns list of (field_id, field_name, current_type, migration_config) tuples.
    """
    to_migrate = []
    fields = table.get("fields", [])
    field_names = {f["name"] for f in fields}

    for field in fields:
        fname = field.get("name", "")
        ftype = field.get("type", "")
        fid = field.get("id", "")

        if fname in FIELD_MIGRATIONS:
            migration = FIELD_MIGRATIONS[fname]
            if ftype in migration["from_types"]:
                to_migrate.append((fid, fname, ftype, migration))
            elif ftype == migration["target_type"]:
                pass  # Already migrated
        # Check for partially migrated state (old field renamed but new not created)
        elif fname.endswith("_old") and fname[:-4] in FIELD_MIGRATIONS:
            original = fname[:-4]
            if original not in field_names:
                print(f"    Warning: {fname} exists but {original} missing. Partially migrated?")

    return to_migrate


def get_old_fields_to_cleanup(table: dict) -> list:
    """Find _old fields that can be deleted during cleanup."""
    old_fields = []
    for field in table.get("fields", []):
        fname = field.get("name", "")
        if fname.endswith("_old") and fname[:-4] in FIELD_MIGRATIONS:
            old_fields.append((field["id"], fname))
    return old_fields


def rename_field(base_id: str, table_id: str, field_id: str,
                 new_name: str, api_key: str) -> bool:
    """Rename a field via Meta API PATCH."""
    headers = api_headers(api_key)
    url = f"{AIRTABLE_META_URL}/{base_id}/tables/{table_id}/fields/{field_id}"
    resp = requests.patch(url, headers=headers, json={"name": new_name}, timeout=30)
    return resp.status_code == 200


def create_field(base_id: str, table_id: str, body: dict, api_key: str) -> str | None:
    """Create a new field. Returns field ID or None on failure."""
    headers = api_headers(api_key)
    url = f"{AIRTABLE_META_URL}/{base_id}/tables/{table_id}/fields"
    resp = requests.post(url, headers=headers, json=body, timeout=30)
    if resp.status_code == 200:
        return resp.json().get("id")
    print(f"    Error creating field: HTTP {resp.status_code} - {resp.text[:200]}")
    return None


def delete_field(base_id: str, table_id: str, field_id: str, api_key: str) -> bool:
    """Delete a field via Meta API DELETE. May fail on free plan."""
    headers = api_headers(api_key)
    url = f"{AIRTABLE_META_URL}/{base_id}/tables/{table_id}/fields/{field_id}"
    resp = requests.delete(url, headers=headers, timeout=30)
    return resp.status_code == 200


def load_all_records(base_id: str, table_id: str, api_key: str) -> list:
    """Fetch all records from a table with pagination."""
    headers = {"Authorization": f"Bearer {api_key}"}
    records = []
    offset = None
    while True:
        params = {"pageSize": 100}
        if offset:
            params["offset"] = offset
        resp = requests.get(
            f"{AIRTABLE_API_URL}/{base_id}/{table_id}",
            headers=headers, params=params, timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break
        time.sleep(RATE_LIMIT_DELAY)
    return records


def copy_field_data(base_id: str, table_id: str, records: list,
                    old_field: str, new_field: str, field_type: str,
                    api_key: str) -> int:
    """
    Copy data from old_field to new_field for all records.
    Transforms data format based on field_type.
    Records may have been loaded before or after field rename, so we
    check both the original name and the _old name.
    Returns count of records updated.
    """
    headers = api_headers(api_key)
    old_field_renamed = f"{old_field}_old"
    updated = 0

    # Build update batches
    updates = []
    for rec in records:
        rec_id = rec["id"]
        fields = rec.get("fields", {})
        # Check both original name (if loaded before rename) and _old name (if loaded after)
        old_val = fields.get(old_field_renamed, "") or fields.get(old_field, "")
        if not old_val:
            continue

        if field_type == "multipleAttachments":
            # Convert URL string to attachment format
            if isinstance(old_val, str) and old_val.startswith("http"):
                new_val = [{"url": old_val}]
            else:
                continue
        elif field_type == "singleSelect":
            # singleSelect accepts plain strings for record writes
            text = old_val.strip() if isinstance(old_val, str) else str(old_val).strip()
            if not text:
                continue
            # Normalize to match choice names
            if old_field == "Bucket":
                if text.lower() == "announcements":
                    text = "Announcements"
                elif text.lower() == "trending":
                    text = "Trending"
                elif text.lower() == "education":
                    text = "Education"
                else:
                    text = text.capitalize()
            elif old_field == "Status":
                # Map non-standard statuses to closest standard choice
                STATUS_MAP = {"Pending Input": "Draft"}
                text = STATUS_MAP.get(text, text)
            elif old_field == "Platform":
                text = text.capitalize()
            elif old_field == "Format":
                text = text.lower()
                FORMAT_MAP = {"long": "post", "long-form": "post"}
                text = FORMAT_MAP.get(text, text)
            new_val = text
        else:
            new_val = old_val

        updates.append({"id": rec_id, "fields": {new_field: new_val}})

    # Send in batches of 10
    for i in range(0, len(updates), BATCH_SIZE):
        batch = updates[i:i + BATCH_SIZE]
        url = f"{AIRTABLE_API_URL}/{base_id}/{table_id}"
        resp = requests.patch(url, headers=headers, json={"records": batch}, timeout=30)
        if resp.status_code == 200:
            updated += len(batch)
        else:
            print(f"    Batch error: HTTP {resp.status_code} - {resp.text[:200]}")
        time.sleep(RATE_LIMIT_DELAY)

    return updated


def migrate_table(base_id: str, table: dict, api_key: str, dry_run: bool) -> dict:
    """
    Migrate all applicable fields in a single table.
    Strategy: rename old -> create new -> copy data.
    """
    table_name = table["name"]
    table_id = table["id"]
    to_migrate = get_fields_to_migrate(table)

    if not to_migrate:
        print(f"  {table_name}: already up to date")
        return {"migrated": 0, "failed": 0}

    print(f"  {table_name}: {len(to_migrate)} field(s) to migrate")
    stats = {"migrated": 0, "failed": 0}

    if dry_run:
        for _, field_name, current_type, migration in to_migrate:
            target = migration["target_type"]
            print(f"    [DRY RUN] {field_name}: {current_type} -> {target}")
            print(f"      1. Rename {field_name} -> {field_name}_old")
            print(f"      2. Create new {field_name} ({target})")
            print(f"      3. Copy data from {field_name}_old -> {field_name}")
        stats["migrated"] = len(to_migrate)
        return stats

    # Load records once (for data copy phase)
    print(f"    Loading records...")
    records = load_all_records(base_id, table_id, api_key)
    print(f"    Found {len(records)} records")

    for field_id, field_name, current_type, migration in to_migrate:
        target = migration["target_type"]
        old_name = f"{field_name}_old"
        print(f"    {field_name}: {current_type} -> {target}")

        # Step 1: Rename old field
        print(f"      Renaming {field_name} -> {old_name}")
        if not rename_field(base_id, table_id, field_id, old_name, api_key):
            print(f"      Failed to rename {field_name}")
            stats["failed"] += 1
            continue
        time.sleep(RATE_LIMIT_DELAY)

        # Step 2: Create new field with original name and target type
        print(f"      Creating new {field_name} ({target})")
        new_field_id = create_field(base_id, table_id, migration["create_body"], api_key)
        if not new_field_id:
            # Revert rename on failure
            rename_field(base_id, table_id, field_id, field_name, api_key)
            stats["failed"] += 1
            continue
        time.sleep(RATE_LIMIT_DELAY)

        # Step 3: Copy data from old field to new field
        if records:
            print(f"      Copying data ({len(records)} records)...")
            copied = copy_field_data(
                base_id, table_id, records,
                field_name, field_name, target, api_key,
            )
            print(f"      Copied {copied} records")

        stats["migrated"] += 1
        time.sleep(RATE_LIMIT_DELAY)

    return stats


def cleanup_table(base_id: str, table: dict, api_key: str, dry_run: bool) -> int:
    """Delete _old fields from a migrated table."""
    table_name = table["name"]
    table_id = table["id"]
    old_fields = get_old_fields_to_cleanup(table)

    if not old_fields:
        return 0

    deleted = 0
    for field_id, field_name in old_fields:
        if dry_run:
            print(f"    [DRY RUN] Would delete {field_name} from {table_name}")
            deleted += 1
        else:
            if delete_field(base_id, table_id, field_id, api_key):
                print(f"    Deleted {field_name} from {table_name}")
                deleted += 1
            else:
                print(f"    Could not delete {field_name} (may need manual removal in Airtable UI)")
            time.sleep(RATE_LIMIT_DELAY)

    return deleted


def main():
    parser = argparse.ArgumentParser(
        description="Migrate existing Airtable Week tables to visual schema "
                    "(attachment images, singleSelect dropdowns)."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without applying them")
    parser.add_argument("--cleanup", action="store_true",
                        help="Delete _old backup fields after verifying migration")
    client_config.add_client_arg(parser)
    args = parser.parse_args()

    active_client = client_config.resolve_client(args)
    config = client_config.load_config(active_client)
    display_name = config.get("display_name", active_client)
    at_config = config.get("airtable", {})

    if not at_config.get("enabled") or not at_config.get("base_id"):
        print(f"Airtable not enabled for {active_client}. Nothing to migrate.")
        sys.exit(0)

    base_id = at_config["base_id"]
    api_key = airtable_writer.get_api_key(active_client)
    if not api_key:
        print("Error: No Airtable API key found. Check .env or client config.")
        sys.exit(1)

    mode = "[DRY RUN] " if args.dry_run else ""
    print(f"\n{mode}Airtable Migration - {display_name} ({active_client})")
    print(f"Base: {base_id}")

    # Fetch all tables
    print("Fetching tables...")
    all_tables = get_tables(base_id, api_key)
    week_tables = find_week_tables(all_tables)

    if not week_tables:
        print("No Week-* tables found. Nothing to migrate.")
        sys.exit(0)

    print(f"Found {len(week_tables)} Week table(s)\n")

    if args.cleanup:
        print("Cleanup mode: deleting _old backup fields\n")
        total_deleted = 0
        for table in week_tables:
            deleted = cleanup_table(base_id, table, api_key, args.dry_run)
            total_deleted += deleted
        print(f"\nDeleted {total_deleted} _old field(s)")
        return

    # Migration mode
    print("Migration: rename old fields -> create new typed fields -> copy data\n")
    total = {"migrated": 0, "failed": 0}
    for table in week_tables:
        stats = migrate_table(base_id, table, api_key, args.dry_run)
        for k in total:
            total[k] += stats[k]
        time.sleep(RATE_LIMIT_DELAY)

    # Summary
    print(f"\n{'='*60}")
    print(f"  {mode}Migration Complete - {display_name}")
    print(f"  Tables processed: {len(week_tables)}")
    print(f"  Fields migrated:  {total['migrated']}")
    if total["failed"]:
        print(f"  Fields failed:    {total['failed']}")
    print(f"{'='*60}")

    if args.dry_run:
        print("\nRun without --dry-run to apply changes.")
    else:
        print("\nOld fields renamed with _old suffix (backup). To remove them:")
        print(f"  python scripts/airtable_migrate.py --client {active_client} --cleanup")
        print("  Or hide/delete them manually in the Airtable UI.")


if __name__ == "__main__":
    main()
