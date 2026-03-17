# Plan: Airtable Visual Frontend with Inline Images + Interface Guide

**Created:** 2026-03-17
**Status:** Implemented
**Request:** Optimize Airtable to have a visual front-end for content review, not just grid view

---

## Overview

### What This Plan Accomplishes

Transforms the Airtable content base from a plain text grid into a visual content review platform where you can see images inline, browse content as cards, filter by bucket/status/day, and review items one-by-one for approval. This involves two changes: (1) a schema migration from URL fields to Attachment fields so images render natively in Airtable, and (2) a step-by-step guide for setting up Airtable Interfaces (Gallery, Record Review, Dashboard) manually in the UI.

### Why This Matters

Right now, the Airtable base stores images as plain URL text strings. This means you see `https://pub-afa75...r2.dev/bobe/...png` instead of the actual image. Gallery views, Interface Designer layouts, and card previews all depend on Attachment-type fields to render images visually. Converting to Attachment fields unlocks the full visual experience within Airtable itself, giving you a native content review tool without needing to visit the deployed dashboard.

---

## Current State

### Relevant Existing Structure

| File | Role |
|------|------|
| `scripts/airtable_writer.py` | Creates tables with `url`-type image fields, writes records inline during pipeline |
| `scripts/airtable_sync.py` | Legacy batch sync from Excel, also uses `url`-type image fields |
| `scripts/pipeline_runner.py` | Orchestrates pipeline, calls `airtable_writer.write_record()` and `update_image_urls()` |
| `scripts/web_viewer.py` / `build_static.py` | Read from Airtable via `records_to_topics()`, expect URL strings |
| `reference/airtable-client-setup.md` | Client-facing setup guide |
| `clients/bobe/config.json` | BoBe Airtable config (`base_id`, `images_base_url`) |

### Gaps or Problems Being Addressed

1. **Images are invisible in Airtable** — `Image_URL_EN` and `Image_URL_RU` are `url`-type fields that display as clickable text links, not rendered images
2. **No visual views** — Only the default Grid view exists. No Gallery, Kanban, or Interface layouts are set up
3. **No approval workflow in Airtable** — Status changes require manually typing in a cell. No dropdown, no Record Review layout
4. **No documentation** on how to set up Airtable's visual features for content review

---

## Proposed Changes

### Summary of Changes

- **Schema migration**: Change `Image_URL_EN` and `Image_URL_RU` from `url` type to `multipleAttachments` type in table creation
- **Write format change**: When writing image URLs to Airtable, wrap them in attachment format (`[{"url": "https://..."}]`) instead of plain strings
- **Read format change**: When reading records, extract URL strings from attachment objects
- **Status field upgrade**: Change `Status` from `singleLineText` to `singleSelect` with predefined options (Draft, Approved, Published, Rejected)
- **Bucket field upgrade**: Change `Bucket` from `singleLineText` to `singleSelect` with options (Trending, Education, Announcements)
- **Add reference guide**: Step-by-step instructions for creating Airtable Interface layouts manually
- **Migration script**: One-time script to convert existing tables to the new schema

### New Files to Create

| File Path | Purpose |
|-----------|---------|
| `scripts/airtable_migrate.py` | One-time migration script: converts existing week tables to new schema (attachment fields, singleSelect fields) |
| `reference/airtable-interface-setup.md` | Step-by-step visual guide for creating Airtable Interface layouts (Gallery, Record Review, Dashboard, Kanban) |

### Files to Modify

| File Path | Changes |
|-----------|---------|
| `scripts/airtable_writer.py` | Change `Image_URL_EN`/`Image_URL_RU` to `multipleAttachments` type; change `Status` and `Bucket` to `singleSelect`; update `write_record()` to use attachment format; update `update_image_urls()` for attachment format; update `records_to_topics()` to extract URL from attachment objects |
| `scripts/airtable_sync.py` | Update `build_table_fields()` to use `multipleAttachments`; update record writing to use attachment format |
| `scripts/pipeline_runner.py` | No changes needed (delegates to `airtable_writer`) |
| `scripts/web_viewer.py` | No changes needed (`records_to_topics()` in `airtable_writer.py` handles extraction) |
| `scripts/build_static.py` | No changes needed (uses `records_to_topics()`) |
| `reference/airtable-client-setup.md` | Add section on setting up views and interfaces; reference the new guide |
| `CLAUDE.md` | Update Airtable schema description, add reference to new guide |

### Files to Delete

None.

---

## Design Decisions

### Key Decisions Made

1. **Use `multipleAttachments` instead of keeping `url` type**: Airtable only renders images inline for Attachment fields. URL fields always display as clickable text. This is the single most impactful change — it unlocks Gallery view, Interface Gallery elements, and Record Review image previews. The attachment format accepts `[{"url": "https://..."}]` so we don't need to upload files, just provide the R2 public URLs.

2. **Upgrade Status and Bucket to `singleSelect`**: This enables native Kanban boards (group by Status), colored labels, dropdown selection (no more manual typing), and proper filter/group controls in Interface Designer. The predefined options ensure data consistency.

3. **Manual Interface setup (not automated)**: Airtable does not offer an API for creating Interfaces. The Interface Designer is UI-only. Rather than fighting this, we provide a clear reference guide with screenshots/descriptions for setting up the 4 most useful layouts. This is a one-time setup per client base (~15 minutes).

4. **Backward-compatible reading**: `records_to_topics()` will handle both old format (plain URL strings) and new format (attachment objects), so existing tables still work alongside new ones.

5. **Migration script for existing tables**: Rather than leaving old Week tables with the broken schema, provide a one-time migration script that converts field types and reformats existing records.

### Alternatives Considered

- **Build a custom Airtable Extension (React app)**: Too heavy. Requires Blocks SDK, React development, manual installation per base, and Team plan ($20/mo). The native Interface Designer provides 90% of the value for free.
- **Use a third-party portal (Softr, Noloco)**: Adds cost, complexity, and another platform to manage. Airtable's built-in Interface Designer is sufficient.
- **Keep URL fields and use a Formula workaround**: Airtable formulas cannot render images. There is no workaround that displays images from URL fields.

### Open Questions

1. **Existing tables**: Should the migration script convert all existing Week tables, or only future tables? (Recommendation: migrate all existing tables so the experience is consistent.)
2. **Thumbnail size in Airtable**: Attachment thumbnails in Gallery view are auto-generated by Airtable. The R2 images (1024x1024) will work but Airtable generates its own thumbnail. Just FYI — no action needed.

---

## Step-by-Step Tasks

### Step 1: Update `airtable_writer.py` Schema and Write Logic

Update the table creation schema and record write/read functions to use Attachment fields and singleSelect fields.

**Actions:**

- Change `Image_URL_EN` field type from `"url"` to `"multipleAttachments"` in `get_or_create_table()`
- Change `Image_URL_RU` field type from `"url"` to `"multipleAttachments"`
- Change `Status` field type from `"singleLineText"` to `{"type": "singleSelect", "options": {"choices": [{"name": "Draft", "color": "yellowLight2"}, {"name": "Approved", "color": "greenLight2"}, {"name": "Published", "color": "blueLight2"}, {"name": "Rejected", "color": "redLight2"}]}}`
- Change `Bucket` field type from `"singleLineText"` to `{"type": "singleSelect", "options": {"choices": [{"name": "Trending", "color": "cyanLight2"}, {"name": "Education", "color": "purpleLight2"}, {"name": "Announcements", "color": "orangeLight2"}]}}`
- In `write_record()`: wrap `image_url_en` and `image_url_ru` values in attachment format: `[{"url": value}]` (only when value is truthy)
- In `update_image_urls()`: wrap URLs in attachment format: `[{"url": value}]`
- In `records_to_topics()`: extract URL from attachment objects. Handle both formats:
  - Old format (string): use as-is
  - New format (list of dicts): extract `[0]["url"]`

**Files affected:**

- `scripts/airtable_writer.py`

---

### Step 2: Update `airtable_sync.py` Schema (Legacy Sync)

Keep the legacy batch sync consistent with the new schema.

**Actions:**

- In `build_table_fields()`: change `Image_URL_EN`/`Image_URL_RU` from `"url"` to `"multipleAttachments"` (when `use_attachments=True`)
- Update `Status` and `Bucket` field definitions to `singleSelect` with same choices
- Update record-building logic to wrap image URLs in attachment format `[{"url": value}]`

**Files affected:**

- `scripts/airtable_sync.py`

---

### Step 3: Create Migration Script

Build a one-time script that converts existing Airtable Week tables to the new schema.

**Actions:**

- Create `scripts/airtable_migrate.py` that:
  1. Lists all Week-* tables in the base
  2. For each table, checks current field types
  3. If `Image_URL_EN` is `url` type, uses the Airtable Meta API to convert it to `multipleAttachments`
  4. If `Image_URL_RU` is `url` type, converts to `multipleAttachments`
  5. If `Status` is `singleLineText`, converts to `singleSelect` with choices
  6. If `Bucket` is `singleLineText`, converts to `singleSelect` with choices
  7. For each record in each table: reads the current URL strings from Image fields, rewrites them as attachment objects `[{"url": "..."}]`
  8. Includes `--dry-run` flag to preview changes without applying
  9. Includes `--client` flag for multi-client support
  10. Handles rate limiting (5 requests/sec Airtable limit)

**Note on field type conversion**: Airtable's Meta API (`PATCH /meta/bases/{baseId}/tables/{tableId}/fields/{fieldId}`) supports changing field types. When converting `url` → `multipleAttachments`, existing URL values are automatically converted to attachment objects by Airtable. However, when converting `singleLineText` → `singleSelect`, existing text values must match the choice names exactly or they'll be cleared. Our Status values ("Draft", "Approved", "Published") and Bucket values ("Trending", "Education", "Announcements") are consistent, so this is safe.

**Files affected:**

- `scripts/airtable_migrate.py` (new)

---

### Step 4: Create Airtable Interface Setup Guide

Write a detailed reference guide for manually creating Airtable Interface layouts.

**Actions:**

- Create `reference/airtable-interface-setup.md` covering these 4 recommended layouts:

**Layout 1: Content Gallery (Gallery layout)**
- Purpose: Visual browsing of all content with image thumbnails
- Cover image field: `Image_URL_EN` (attachment renders as card image)
- Card fields: Topic, Bucket (colored tag), Day, Platform, Status (colored tag)
- Filter controls: Bucket, Status, Platform
- Sort: by Date ascending

**Layout 2: Content Review (Record Review layout)**
- Purpose: Step through items one-by-one for approval
- Filter: Status = "Draft"
- Display fields: Image_URL_EN, Image_URL_RU (side by side), Topic, Content, Content_RU, Hashtags, Hashtags_RU, Platform, Format, Bucket
- Action button: Change Status to "Approved"

**Layout 3: Weekly Dashboard (Dashboard layout)**
- Purpose: High-level stats and progress tracking
- Elements:
  - Number element: Count of records by Status (Draft / Approved / Published)
  - Chart element: Bar chart of items by Bucket
  - Gallery element: Recently approved items
  - Filter control: Week field

**Layout 4: Publishing Board (Kanban layout)**
- Purpose: Drag-and-drop status management
- Group by: Status field
- Card fields: Topic, Bucket, Platform, Image_URL_EN (thumbnail)
- Columns: Draft → Approved → Published

Each layout section includes:
- What to click in the Airtable UI (step by step)
- Which fields to add/configure
- Recommended filter and sort settings
- Tips for the best visual experience

**Files affected:**

- `reference/airtable-interface-setup.md` (new)

---

### Step 5: Update Reference Documentation

Update existing docs to reference the new schema and interface guide.

**Actions:**

- In `reference/airtable-client-setup.md`:
  - Update the "What the Airtable Table Looks Like" section to note that Image fields are now Attachment type (images render inline)
  - Update Status field description to note it's a dropdown (singleSelect)
  - Add a new section "Setting Up Visual Views" that links to `reference/airtable-interface-setup.md`
  - Update the "Tips for Using Airtable" section to recommend the Interface layouts

- In `CLAUDE.md`:
  - Update the `airtable_writer.py` schema description to reflect Attachment fields
  - Add `airtable_migrate.py` to the scripts table
  - Add `reference/airtable-interface-setup.md` to the reference section
  - Add this plan to the Implemented plans table (after implementation)

**Files affected:**

- `reference/airtable-client-setup.md`
- `CLAUDE.md`

---

### Step 6: Test the Migration

Validate that everything works end-to-end.

**Actions:**

1. Run `python scripts/airtable_migrate.py --client bobe --dry-run` to preview changes
2. Run `python scripts/airtable_migrate.py --client bobe` to execute migration on existing tables
3. Verify in Airtable UI that:
   - Image thumbnails appear in Grid view cells
   - Status field shows colored dropdown
   - Bucket field shows colored dropdown
4. Run a mock pipeline to verify new tables create correctly:
   `python scripts/pipeline_runner.py --client bobe --mock`
5. Run a real single-topic regen to verify image URLs write as attachments:
   Check that the image appears inline in the Airtable record
6. Set up at least the Gallery Interface layout following the guide

**Files affected:**

- No code changes, validation only

---

## Connections & Dependencies

### Files That Reference This Area

- `scripts/pipeline_runner.py` — calls `airtable_writer.write_record()` and `update_image_urls()`
- `scripts/web_viewer.py` — calls `airtable_writer.records_to_topics()` and `load_records()`
- `scripts/build_static.py` — calls `airtable_writer.records_to_topics()`
- `scripts/x_publisher.py` — calls `airtable_writer.update_publish_status()`
- `.github/workflows/weekly-pipeline.yml` — runs `pipeline_runner.py`
- `.github/workflows/generate-announcement.yml` — runs `pipeline_runner.py`
- `.github/workflows/regenerate-item.yml` — runs `pipeline_runner.py`

### Updates Needed for Consistency

- `records_to_topics()` must handle both old (string) and new (attachment list) formats for backward compatibility
- `update_publish_status()` in `airtable_writer.py` writes to Status field — no change needed since it already writes "Published" which matches the singleSelect choice name
- `x_publisher.py` writes to Tweet_URL which stays as `url` type — no change needed

### Impact on Existing Workflows

- **Pipeline runs**: New tables will use the new schema automatically. Content will look the same but images will render inline.
- **Dashboard (static site)**: No impact. `records_to_topics()` extracts URLs from attachment objects the same way.
- **Regen workflow**: No impact. `update_image_urls()` will write in attachment format.
- **Existing week tables**: Migration script converts them. If not migrated, `records_to_topics()` still reads old format.

---

## Validation Checklist

- [ ] `airtable_writer.py` creates tables with `multipleAttachments` for image fields
- [ ] `airtable_writer.py` creates tables with `singleSelect` for Status and Bucket fields
- [ ] `write_record()` sends image URLs in attachment format `[{"url": "..."}]`
- [ ] `update_image_urls()` sends URLs in attachment format
- [ ] `records_to_topics()` handles both string URLs and attachment objects
- [ ] `airtable_sync.py` updated with matching schema changes
- [ ] `airtable_migrate.py` exists and migrates existing tables (field types + record data)
- [ ] Migration script has `--dry-run` and `--client` flags
- [ ] `reference/airtable-interface-setup.md` created with 4 layout guides
- [ ] `reference/airtable-client-setup.md` updated to reference new features
- [ ] CLAUDE.md updated with new script and reference file
- [ ] Images render as thumbnails in Airtable Grid view after migration
- [ ] Status field shows colored dropdown in Airtable after migration
- [ ] Gallery view shows image cards properly

---

## Success Criteria

The implementation is complete when:

1. **New pipeline runs** create Airtable tables where images render inline as thumbnails (not URL text), Status is a colored dropdown, and Bucket is a colored tag
2. **Existing week tables** are migrated to the new schema with images rendering and dropdowns working
3. **A reference guide** exists that walks through creating 4 Airtable Interface layouts (Gallery, Record Review, Dashboard, Kanban) in ~15 minutes
4. **Backward compatibility** is preserved: the static dashboard, Flask viewer, and all workflows continue to work unchanged

---

## Notes

- **Airtable Interfaces cannot be created via API** — this is a known limitation. The Interface Designer is UI-only. The reference guide compensates for this by providing clear step-by-step instructions.
- **Attachment fields from URLs**: Airtable's `multipleAttachments` field accepts `[{"url": "https://..."}]`. Airtable will fetch the image from the URL and generate its own thumbnail. The original R2 URL is preserved in the attachment metadata.
- **Rate limiting**: Airtable allows 5 requests/second. The migration script should include appropriate delays (0.2s between requests).
- **Free plan compatibility**: All features used (Attachment fields, singleSelect, Interface Designer) are available on Airtable's free plan. Interface Designer allows up to 1 interface on free, unlimited on paid.
- **Future consideration**: If we onboard many clients, consider adding Interface setup instructions to the `/onboard-client` flow as a "next steps" section.

---

## Implementation Notes

**Implemented:** 2026-03-18

### Summary

Migrated Airtable schema from plain text/URL fields to visual types (multipleAttachments, singleSelect). Updated `airtable_writer.py` and `airtable_sync.py` for new field types. Created `airtable_migrate.py` for existing table migration. All 3 existing BoBe Week tables migrated successfully. Created comprehensive Interface Designer guide (`reference/airtable-interface-setup.md`).

### Deviations from Plan

1. **Airtable API does not support field type conversion.** The plan assumed `PATCH` could change field types. Instead, the migration script uses a rename-create-copy strategy: rename old field -> create new field with correct type -> copy data.
2. **singleSelect fields accept plain strings for record writes**, not `{"name": "..."}` objects. Fixed in all write functions.
3. **"Pending Input" status** existed in old data but wasn't in the original STATUS_CHOICES. Added it to choices and mapped it to "Draft" during migration.
4. **Free plan API limitation**: Cannot update singleSelect options after field creation. Workaround: ensure all choices are defined at field creation time.
5. **Old fields preserved as backup**: `*_old` fields are left in tables rather than deleted (Airtable free plan API doesn't reliably support field deletion). Can be hidden or deleted in the UI, or via `--cleanup` flag.

### Issues Encountered

- Airtable Meta API `PATCH` to change field type returns 422 "Invalid request". This is an undocumented limitation: the PATCH endpoint only supports name/description changes, not type conversion. Resolved by switching to the rename-create-copy approach.
- Airtable Meta API `PATCH` to update singleSelect options also returns 422 on the free plan. Resolved by including all needed choices at field creation time.
