# Airtable Interface Setup Guide

After running the migration (`python scripts/airtable_migrate.py --client bobe`), your Airtable base has inline images, colored Status dropdowns, and colored Bucket tags. This guide walks you through setting up 4 Interface layouts for a visual content review experience.

**Time required:** ~15 minutes (one-time setup per base)

**Prerequisites:**
- Migration script has been run (Image fields are Attachment type, Status/Bucket are singleSelect)
- At least one Week-* table with data

---

## Quick Wins: Views (No Interface Required)

Before building Interfaces, you can immediately improve your Grid view:

### Gallery View
1. Open any Week-* table
2. Click the view switcher (top-left, next to "Grid view")
3. Click **+ Create a view** -> **Gallery**
4. Name it "Content Cards"
5. Click **Cover field** -> select **Image_URL_EN**
6. Click **Fields** -> show: Topic, Bucket, Platform, Status, Day
7. Click **Group** -> group by **Bucket** for organized sections

### Kanban View
1. Click **+ Create a view** -> **Kanban**
2. Name it "Status Board"
3. Kanban will auto-detect the **Status** singleSelect field
4. You now have columns: Draft | Approved | Published | Rejected
5. Drag cards between columns to change status
6. Click **Fields** -> show Image_URL_EN for thumbnails on cards

---

## Interface Layout 1: Content Gallery

A visual card wall for browsing all content with image thumbnails.

### Setup Steps

1. From your Airtable base, click **Interfaces** in the top nav bar
2. Click **+ New interface**
3. Select **Gallery** layout
4. Name it "Content Gallery"

### Configure the Data Source

5. Click **Data source** -> select your most recent Week-* table
6. To show all weeks: click **Data source** -> **+ Add another source** for each Week table
   - Alternatively, if you have many weeks, use one table at a time and switch as needed

### Configure the Card Layout

7. **Cover image**: Click the cover area -> select **Image_URL_EN**
8. **Title field**: Set to **Topic**
9. **Visible fields** (click to add):
   - **Bucket** (shows as colored tag)
   - **Platform**
   - **Day**
   - **Status** (shows as colored tag)
   - **Format**

### Add Filter Controls

10. Click **+ Add element** -> **Filter** control
11. Add filters for:
    - **Bucket** (filter by Trending / Education / Announcements)
    - **Status** (filter by Draft / Approved / Published)
    - **Platform** (filter by Twitter / Telegram)

### Recommended Sort

12. Click the sort option -> sort by **Date** ascending, then **Day**

---

## Interface Layout 2: Content Review

Step through Draft items one-by-one for approval. See full content with both EN and RU images side by side.

### Setup Steps

1. In your Interface, click **+ Add page**
2. Select **Record review** layout
3. Name it "Content Review"

### Configure the Data Source

4. Click **Data source** -> select your Week-* table
5. Click **Filter** -> add filter: **Status** is **Draft**
   - This shows only items waiting for approval

### Configure the Record View

6. The record view shows one item at a time with left/right navigation
7. **Fields to display** (recommended order):
   - **Topic** (title)
   - **Image_URL_EN** (English image, renders full-size)
   - **Image_URL_RU** (Russian image, renders full-size)
   - **Content** (English copy)
   - **Content_RU** (Russian copy)
   - **Bucket**
   - **Platform**
   - **Format**
   - **Hashtags**
   - **Hashtags_RU**
   - **Day**
   - **Date**

### Add Approval Action

8. Click **+ Add element** -> **Button**
9. Configure the button:
   - Label: "Approve"
   - Action: **Update record**
   - Field to update: **Status**
   - New value: **Approved**
10. Optionally add a "Reject" button the same way with value **Rejected**

### Usage

- Click through items using the left/right arrows
- Review the images and content
- Click "Approve" or "Reject" for each item
- Approved items disappear from the queue (filtered out by Status = Draft)

---

## Interface Layout 3: Weekly Dashboard

A high-level overview with stats, charts, and recent items.

### Setup Steps

1. Click **+ Add page**
2. Select **Dashboard** layout
3. Name it "Weekly Dashboard"

### Add a Filter Control

4. Click **+ Add element** -> **Filter** control
5. Add filter for **Week** field (so you can switch between weeks)

### Add Summary Numbers

6. Click **+ Add element** -> **Number**
7. Configure:
   - Data source: your Week-* table
   - Summarize: **Count**
   - Filter: **Status** is **Draft**
   - Label: "Pending Review"
8. Repeat for:
   - Count where Status = Approved, label "Approved"
   - Count where Status = Published, label "Published"

### Add a Bucket Chart

9. Click **+ Add element** -> **Chart**
10. Configure:
    - Type: **Bar chart**
    - X-axis: **Bucket**
    - Y-axis: Count of records
    - Group by: **Status** (for stacked bars showing progress per bucket)

### Add a Recent Items Gallery

11. Click **+ Add element** -> **Gallery**
12. Configure:
    - Data source: your Week-* table
    - Filter: **Status** is **Approved**
    - Cover image: **Image_URL_EN**
    - Fields: Topic, Bucket, Platform
    - Sort: Date descending (most recent first)
    - Limit: 6 items

---

## Interface Layout 4: Publishing Board

A Kanban board for drag-and-drop status management.

### Setup Steps

1. Click **+ Add page**
2. Select **Kanban** layout
3. Name it "Publishing Board"

### Configure the Board

4. **Grouping field**: Select **Status**
   - This creates columns: Draft | Approved | Published | Rejected
5. **Card cover**: Select **Image_URL_EN** for thumbnail on each card
6. **Card fields** (click to add):
   - **Topic**
   - **Bucket** (colored tag)
   - **Platform**
   - **Day**

### Configure Data Source

7. Click **Data source** -> select your Week-* table
8. Optionally add a filter control for **Bucket** to focus on one content type

### Usage

- Drag cards from **Draft** to **Approved** after review
- Drag cards from **Approved** to **Published** after posting
- The colored Bucket tags help you identify content type at a glance
- Click any card to see full details (content, images, hashtags)

---

## Tips

- **Free plan limit**: Airtable's free plan allows 1 Interface per base. If you need all 4 layouts, upgrade to Team ($20/user/month) or consolidate into fewer pages.
- **Multi-week**: If you frequently switch between weeks, add a "Week" filter control to each layout page rather than switching tables.
- **Sharing**: Click **Share** on any Interface to create a link. Set permissions to "Can view" for stakeholders who just need to review content, or "Can edit" for team members who approve content.
- **Mobile**: Airtable Interfaces work on mobile browsers. The Gallery and Kanban layouts are particularly useful for quick reviews on the go.
- **Notification**: Set up Airtable automations (Automations tab) to send email/Slack when Status changes to "Approved" or when new records are created.

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Images show as text links, not thumbnails | Field type is still `url` not `multipleAttachments` | Run `python scripts/airtable_migrate.py --client bobe` |
| Status doesn't show colored dropdown | Field type is still `singleLineText` | Run migration script |
| Gallery shows no cover images | Cover field not set | Click cover area -> select Image_URL_EN |
| Images are blank/broken | R2 URL expired or bucket not public | Check `r2.public_url` in config.json, verify the URL works in a browser |
| "No matching records" in Record Review | All items already approved | Change filter from Status=Draft to Status=any, or generate new content |
