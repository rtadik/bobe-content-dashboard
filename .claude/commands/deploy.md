# Deploy

> Build and deploy the content dashboard to Cloudflare Pages

## Variables

date: $ARGUMENTS (optional — build only a specific date, defaults to all available dates)

---

## Instructions

### Step 1 — Build the static site (with admin panel)

```bash
cd "/Users/rt/Claude Code/RT Content Generator" && ./venv/bin/python scripts/build_static.py --output dist --include-admin --client bobe
```

If a specific date was provided:
```bash
cd "/Users/rt/Claude Code/RT Content Generator" && ./venv/bin/python scripts/build_static.py --output dist --include-admin --client bobe --date {date}
```

### Step 2 — Verify the build

Check the build output:
- Confirm `dist/index.html` exists
- Confirm at least one `dist/dashboard/bobe/week-*.html` exists
- Confirm `dist/dashboard/bobe/images/` contains the expected images
- Report total file count and size

### Step 3 — Deploy to Cloudflare Pages

```bash
cd "/Users/rt/Claude Code/RT Content Generator" && \
CLOUDFLARE_ACCOUNT_ID=ab553c828367aff2894c0552f182b46a \
CLOUDFLARE_API_TOKEN=VzuElDltrNGutS8IXh0dUwlHBJYlCDsWl09H1-oU \
npx wrangler pages deploy dist --project-name bobe-content-dashboard --branch main --commit-dirty=true 2>&1
```

### Step 4 — Report

Tell the user:
- Build successful: X pages, Y images, Z total size
- Deployed to: https://content.rejiglabs.com (Cloudflare Pages)
- Fallback URL: https://bobe-content-dashboard.pages.dev

---

## Hosting Details

- **Provider**: Cloudflare Pages (free tier — unlimited requests, 500 builds/month)
- **Project**: `bobe-content-dashboard`
- **Account**: `ab553c828367aff2894c0552f182b46a` (Ruttherick@gmail.com)
- **Custom domain**: `content.rejiglabs.com` — CNAME must point to `bobe-content-dashboard.pages.dev`
- **Fallback URL**: https://bobe-content-dashboard.pages.dev (always works, no DNS needed)
- **Migration note**: Moved from GitHub Pages (gh-pages branch) on 2026-03-12 due to GitHub Actions being disabled on the rtadik account.
