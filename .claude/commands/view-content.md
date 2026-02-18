# View Content

> Launch the BoBe content dashboard at http://localhost:5000

## Variables

date: $ARGUMENTS (optional — e.g. `2026-02-18`. Defaults to most recent date available.)

---

## Instructions

### Step 1 — Ensure Flask is installed

```bash
/Users/rt/Claude\ Code/bobe-image-content-gen/venv/bin/pip install flask --quiet
```

### Step 2 — Launch the dashboard

```bash
cd "/Users/rt/Claude Code/bobe-image-content-gen" && ./venv/bin/python scripts/web_viewer.py
```

### Step 3 — Confirm to the user

Tell the user:
- Dashboard is running at **http://localhost:5000**
- Auto-loads the most recent pipeline output
- Use the date picker (top-right) to switch between pipeline runs
- Click any image to enlarge it (lightbox)
- Click **Copy** next to any content to copy it to clipboard
- Click **Twitter** / **Telegram** tabs to switch between formats
- Click any hashtag chip to copy it
- Press **Ctrl+C** in the terminal to stop the server
