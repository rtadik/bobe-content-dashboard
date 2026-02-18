# Deploy

> Build and deploy the BoBe content dashboard to the web

## Variables

date: $ARGUMENTS (optional — build only a specific date, defaults to all available dates)

---

## Instructions

### Step 1 — Build the static site

```bash
cd "/Users/rt/Claude Code/bobe-image-content-gen" && ./venv/bin/python scripts/build_static.py --output dist
```

If a specific date was provided:
```bash
cd "/Users/rt/Claude Code/bobe-image-content-gen" && ./venv/bin/python scripts/build_static.py --output dist --date {date}
```

### Step 2 — Verify the build

Check the build output:
- Confirm `dist/index.html` exists
- Confirm at least one `dist/{date}.html` exists
- Confirm `dist/images/` contains the expected images
- Report total file count and size

### Step 3 — Deploy

**Option A: Cloudflare Pages (recommended)**
```bash
npx wrangler pages deploy dist --project-name bobe-content
```

**Option B: GitHub Pages**
Ensure the repo has GitHub Pages enabled on the `gh-pages` branch, then:
```bash
cd "/Users/rt/Claude Code/bobe-image-content-gen/dist" && git init && git add -A && git commit -m "Deploy content dashboard" && git push -f git@github.com:USER/REPO.git main:gh-pages
```

**Option C: Manual upload**
Tell the user to:
1. Go to https://dash.cloudflare.com → Pages → Create a project → Upload assets
2. Drag the `dist/` folder
3. Deploy

### Step 4 — Report

Tell the user:
- Build successful: X pages, Y images, Z total size
- Deployed to: [URL]
- Share this URL with your client

---

## First-Time Setup

### Cloudflare Pages (recommended, $0/month, unlimited bandwidth)

1. Create a free Cloudflare account at https://dash.cloudflare.com
2. Go to Workers & Pages → Create → Pages → Upload assets
3. Upload the `dist/` folder
4. Choose a project name (e.g., `bobe-content`)
5. Get the URL: `https://bobe-content.pages.dev`
6. For subsequent deploys, either re-upload or use Wrangler CLI:
   ```bash
   npm install -g wrangler
   wrangler login
   npx wrangler pages deploy dist --project-name bobe-content
   ```

### GitHub Pages (alternative, $0/month, 100 GB/month bandwidth)

1. Create a public repo (or use the existing one)
2. Go to Settings → Pages → Source: Deploy from branch `gh-pages`
3. Push the `dist/` contents to `gh-pages` branch
4. Get the URL: `https://username.github.io/repo-name`
