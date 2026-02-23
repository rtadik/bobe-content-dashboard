# Deploy

> Build and deploy the content dashboard to GitHub Pages

## Variables

date: $ARGUMENTS (optional — build only a specific date, defaults to all available dates)

---

## Instructions

### Step 1 — Build the static site (with admin panel)

```bash
cd "/Users/rt/Claude Code/bobe-image-content-gen" && ./venv/bin/python scripts/build_static.py --output dist --include-admin
```

If a specific date was provided:
```bash
cd "/Users/rt/Claude Code/bobe-image-content-gen" && ./venv/bin/python scripts/build_static.py --output dist --include-admin --date {date}
```

### Step 2 — Verify the build

Check the build output:
- Confirm `dist/index.html` exists
- Confirm at least one `dist/{date}.html` exists
- Confirm `dist/images/` contains the expected images
- Report total file count and size

### Step 3 — Deploy to GitHub Pages

Push the `dist/` folder contents to the `gh-pages` branch of the content dashboard repo:

```bash
cd "/Users/rt/Claude Code/bobe-image-content-gen" && git subtree push --prefix dist origin gh-pages
```

If that fails (e.g. due to history conflicts), use the force push method:
```bash
cd "/Users/rt/Claude Code/bobe-image-content-gen/dist" && git init && git add -A && git commit -m "Deploy content dashboard $(date +%Y-%m-%d)" && git push -f https://github.com/rtadik/bobe-content-dashboard.git HEAD:gh-pages && cd .. && rm -rf dist/.git
```

### Step 4 — Report

Tell the user:
- Build successful: X pages, Y images, Z total size
- Deployed to: https://rtadik.github.io/bobe-content-dashboard
- Share this URL with your client

---

## First-Time Setup

### GitHub Pages

The repo `rtadik/bobe-content-dashboard` must have GitHub Pages enabled:

1. Go to https://github.com/rtadik/bobe-content-dashboard/settings/pages
2. Under **Source**, select **Deploy from a branch**
3. Branch: `gh-pages` / folder: `/ (root)`
4. Click **Save**

The site will be live at: **https://rtadik.github.io/bobe-content-dashboard**

GitHub Pages is free, no credit card required, 100 GB/month bandwidth.

---

## After First Deploy

Once the site is live, set the URL in the client config so Airtable sync can attach images:

```json
// clients/bobe/config.json
"airtable": {
  "images_base_url": "https://rtadik.github.io/bobe-content-dashboard"
}
```

This is already set for BoBe. No action needed.
