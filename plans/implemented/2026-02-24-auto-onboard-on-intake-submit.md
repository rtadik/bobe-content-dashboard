# Auto-Onboard on Intake Submit

**Date:** 2026-02-24
**Status:** Implemented
**Priority:** High

## Overview

When a client submits the intake form at content.rejiglabs.com/intake/, automate the full
onboarding pipeline so Rut takes zero manual steps. Currently the flow requires two manual
commands (/onboard-from-intake and /deploy). This plan eliminates both.

### Current Flow (Manual)

1. Client submits form at /intake/
2. EmailJS sends credential email to client
3. JSON is downloaded by browser
4. Rut manually runs: /onboard-from-intake clients/intake/{client}.json
5. Rut manually runs: /deploy

### Target Flow (Fully Automated)

1. Client submits form at /intake/
2. EmailJS sends credential email to client (unchanged)
3. Browser also POSTs intake JSON to Cloudflare Worker (new, parallel to step 2)
4. Cloudflare Worker validates JSON, triggers auto-onboard.yml via GitHub API
5. auto-onboard.yml creates client directory, populates all four config files, commits to main
6. auto-onboard.yml builds static site with --include-admin and deploys to gh-pages
7. Client dashboard is live at content.rejiglabs.com/dashboard/{client_id}/

Total automation: zero manual steps for Rut after initial one-time Cloudflare Worker setup.

---

## Architecture Decision: Why Cloudflare Worker

The intake form is public-facing static HTML/JS hosted on GitHub Pages. A GitHub PAT with
Actions write scope cannot be embedded in browser JS — it would be publicly visible in the
source and could be extracted to trigger arbitrary workflows.

The Cloudflare Worker acts as a thin, secure server-side proxy:
- Receives intake JSON from the browser over HTTPS
- Holds the GitHub PAT exclusively in Cloudflare environment variables (never exposed)
- Validates the payload before touching GitHub
- Triggers workflow_dispatch on auto-onboard.yml
- Returns a JSON status response to the browser

Cloudflare Workers free tier: 100,000 requests/day, $0/month. No account credit card
required beyond initial signup (free plan exists).

---

## Files to Create or Modify

### New Files

1. `worker/onboard-worker.js` — Cloudflare Worker source code
2. `worker/wrangler.toml` — Wrangler config for deployment
3. `.github/workflows/auto-onboard.yml` — New GitHub Actions workflow

### Modified Files

4. `intake/intake.js` — Add Cloudflare Worker POST after EmailJS send
5. `intake/intake-config.example.js` — Add workerUrl field documentation
6. `intake/intake-config.js` — Add workerUrl field (gitignored, user fills in)
7. `reference/github-actions-setup.md` — Add Cloudflare Worker setup section

---

## Step 1: Create the Cloudflare Worker

### File: `worker/onboard-worker.js`

This is the complete Worker source. It must:
- Accept CORS preflight (OPTIONS) from content.rejiglabs.com
- Accept POST with raw intake JSON body
- Validate required fields before touching GitHub
- Call GitHub API to trigger workflow_dispatch on auto-onboard.yml
- Return JSON success or error

```javascript
/**
 * onboard-worker.js — Cloudflare Worker
 *
 * Secure proxy between the intake form (public browser JS) and GitHub Actions.
 * Holds the GitHub PAT in Cloudflare env vars. Never exposed to the browser.
 *
 * Environment variables required (set in Cloudflare dashboard or wrangler secret):
 *   GITHUB_PAT   — Fine-grained PAT with Actions: write on rtadik/bobe-content-dashboard
 *   GITHUB_REPO  — e.g. "rtadik/bobe-content-dashboard"
 *   ALLOWED_ORIGIN — e.g. "https://content.rejiglabs.com"
 */

const WORKFLOW_FILE = "auto-onboard.yml";
const GITHUB_API    = "https://api.github.com";

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const allowedOrigin = env.ALLOWED_ORIGIN || "https://content.rejiglabs.com";

    // ── CORS preflight ──────────────────────────────────────────────────────
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: corsHeaders(allowedOrigin),
      });
    }

    // ── Only accept POST ────────────────────────────────────────────────────
    if (request.method !== "POST") {
      return jsonResponse({ error: "Method not allowed" }, 405, allowedOrigin);
    }

    // ── Parse body ──────────────────────────────────────────────────────────
    let intake;
    try {
      intake = await request.json();
    } catch {
      return jsonResponse({ error: "Invalid JSON body" }, 400, allowedOrigin);
    }

    // ── Validate required fields ────────────────────────────────────────────
    const validationError = validateIntake(intake);
    if (validationError) {
      return jsonResponse({ error: validationError }, 400, allowedOrigin);
    }

    // ── Trigger GitHub Actions workflow_dispatch ─────────────────────────────
    const intakeJson = JSON.stringify(intake);
    const ghResponse = await fetch(
      `${GITHUB_API}/repos/${env.GITHUB_REPO}/actions/workflows/${WORKFLOW_FILE}/dispatches`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${env.GITHUB_PAT}`,
          Accept: "application/vnd.github+json",
          "X-GitHub-Api-Version": "2022-11-28",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ref: "main",
          inputs: {
            intake_json: intakeJson,
          },
        }),
      }
    );

    if (!ghResponse.ok) {
      let ghError = "GitHub API error";
      try {
        const body = await ghResponse.json();
        ghError = body.message || ghError;
      } catch {}
      console.error(`GitHub API returned ${ghResponse.status}: ${ghError}`);
      return jsonResponse(
        { error: "Failed to trigger onboarding workflow", detail: ghError },
        502,
        allowedOrigin
      );
    }

    // GitHub returns 204 No Content on success
    return jsonResponse(
      {
        ok: true,
        message: `Onboarding workflow triggered for client "${intake.client_id}". Your dashboard will be live in 3-5 minutes.`,
        client_id: intake.client_id,
      },
      200,
      allowedOrigin
    );
  },
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function validateIntake(intake) {
  if (!intake || typeof intake !== "object") {
    return "Intake must be a JSON object";
  }
  if (!intake.client_id || typeof intake.client_id !== "string") {
    return "Missing required field: client_id";
  }
  if (!/^[a-z0-9_-]+$/.test(intake.client_id)) {
    return "client_id must be lowercase letters, numbers, hyphens, or underscores only";
  }
  if (!intake.display_name || typeof intake.display_name !== "string") {
    return "Missing required field: display_name";
  }
  if (!intake.contact || !intake.contact.email) {
    return "Missing required field: contact.email";
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(intake.contact.email)) {
    return "contact.email is not a valid email address";
  }
  return null; // valid
}

function corsHeaders(origin) {
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
  };
}

function jsonResponse(body, status, origin) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json",
      ...corsHeaders(origin),
    },
  });
}


### File: `worker/wrangler.toml`

```toml
name = "intake-onboard-worker"
main = "onboard-worker.js"
compatibility_date = "2024-01-01"

# Environment variables (non-secret, safe to commit)
[vars]
ALLOWED_ORIGIN = "https://content.rejiglabs.com"
GITHUB_REPO    = "rtadik/bobe-content-dashboard"

# Secrets (GITHUB_PAT) are set via: wrangler secret put GITHUB_PAT
# Never put the PAT value in wrangler.toml


---

## Step 2: Create the GitHub Actions Workflow

### File: `.github/workflows/auto-onboard.yml`

This workflow receives the full intake JSON as a string input, parses it with Python,
creates the client directory from `clients/_template/`, writes all four config files with
real content derived from intake data, commits to main, then builds and deploys the static
site to gh-pages.

Important constraints observed from existing workflows:
- Use `actions/checkout@v4` with `ref: main` and `token: ${{ secrets.GITHUB_TOKEN }}`
- Set `permissions: contents: write` at the job level
- The deploy step uses `git push -f` to gh-pages (matching weekly-pipeline.yml pattern)
- pip dependencies: `requests openpyxl google-genai python-dotenv jinja2 flask pillow`
- Python inline scripts use `PYEOF` heredoc delimiter (matching onboard-client.yml pattern)
- The concurrency group `gh-pages-deploy` is shared with weekly-pipeline.yml and
  regenerate-item.yml so deploys don't race each other

```yaml
name: Auto-Onboard Client from Intake

on:
  workflow_dispatch:
    inputs:
      intake_json:
        description: 'Full intake JSON string (sent by Cloudflare Worker)'
        required: true

concurrency:
  group: gh-pages-deploy
  cancel-in-progress: false

jobs:
  onboard:
    runs-on: ubuntu-latest
    timeout-minutes: 15

    permissions:
      contents: write

    steps:
      - name: Checkout main
        uses: actions/checkout@v4
        with:
          ref: main
          token: ${{ secrets.GITHUB_TOKEN }}
          fetch-depth: 0

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: pip install requests openpyxl google-genai python-dotenv jinja2 flask pillow

      - name: Validate and parse intake JSON
        id: parse
        env:
          INTAKE_JSON: ${{ github.event.inputs.intake_json }}
        run: |
          python3 - <<'PYEOF'
          import json, os, sys, re

          raw = os.environ["INTAKE_JSON"]
          try:
              intake = json.loads(raw)
          except json.JSONDecodeError as e:
              print(f"ERROR: Could not parse intake_json: {e}")
              sys.exit(1)

          # Validate required fields
          client_id = intake.get("client_id", "").strip()
          if not client_id or not re.match(r'^[a-z0-9_-]+$', client_id):
              print(f"ERROR: Invalid or missing client_id: '{client_id}'")
              sys.exit(1)

          display_name = intake.get("display_name", "").strip()
          if not display_name:
              print("ERROR: Missing display_name")
              sys.exit(1)

          email = intake.get("contact", {}).get("email", "").strip()
          if not email:
              print("ERROR: Missing contact.email")
              sys.exit(1)

          # Write parsed values to GITHUB_OUTPUT for use in later steps
          output_file = os.environ.get("GITHUB_OUTPUT", "/dev/null")
          with open(output_file, "a") as f:
              f.write(f"client_id={client_id}\n")
              f.write(f"display_name={display_name}\n")
              f.write(f"email={email}\n")

          print(f"Intake validated: client_id={client_id}, display_name={display_name}")
          PYEOF

      - name: Check client does not already exist
        run: |
          CLIENT_ID="${{ steps.parse.outputs.client_id }}"
          if [ -d "clients/${CLIENT_ID}" ]; then
            echo "WARNING: Client '${CLIENT_ID}' already exists. Skipping directory creation."
            echo "CLIENT_EXISTS=true" >> $GITHUB_ENV
          else
            echo "CLIENT_EXISTS=false" >> $GITHUB_ENV
          fi

      - name: Create client directory from template
        if: env.CLIENT_EXISTS == 'false'
        run: |
          CLIENT_ID="${{ steps.parse.outputs.client_id }}"
          cp -r clients/_template "clients/${CLIENT_ID}"
          echo "Copied template to clients/${CLIENT_ID}"

      - name: Write config.json from intake data
        env:
          INTAKE_JSON: ${{ github.event.inputs.intake_json }}
          CLIENT_ID: ${{ steps.parse.outputs.client_id }}
        run: |
          python3 - <<'PYEOF'
          import json, os

          raw = os.environ["INTAKE_JSON"]
          intake = json.loads(raw)
          client_id = os.environ["CLIENT_ID"]

          config_path = f"clients/{client_id}/config.json"
          with open(config_path) as f:
              config = json.load(f)

          # Core identity
          config["client_id"]    = client_id
          config["display_name"] = intake.get("display_name", "")
          config["tagline"]      = intake.get("tagline", "")
          config["website"]      = intake.get("website", "")

          # Brand colors
          brand = intake.get("brand", {})
          config["brand"]["primary_color"] = brand.get("primary_color", "#1a1a2e")
          config["brand"]["accent_color"]  = brand.get("accent_color",  "#00d4ff")
          config["brand"]["text_color"]    = brand.get("text_color",    "#ffffff")
          if brand.get("mascot"):
              config["brand"]["mascot_description"] = brand["mascot"]

          # Content settings
          voice = intake.get("voice", {})
          tone_adjectives = voice.get("tone_adjectives", [])
          config["content"]["tone"]  = ", ".join(tone_adjectives) if tone_adjectives else "professional, clear, educational"
          config["content"]["voice"] = voice.get("tone_description", "")
          config["content"]["cta_examples"] = intake.get("content", {}).get("cta_examples", [])
          config["content"]["hashtags"]     = intake.get("content", {}).get("hashtags", [])
          config["content"]["messaging_pillars"] = voice.get("messaging_pillars", [])

          # Platforms
          platforms = intake.get("platforms", ["twitter", "telegram"])
          config["content"]["platforms"] = platforms

          # Languages
          languages_raw = intake.get("languages", ["english"])
          lang_map = {"english": "en", "russian": "ru"}
          config["languages"] = [lang_map.get(l.lower(), l) for l in languages_raw]

          # Scraping keywords
          scraping = intake.get("scraping", {})
          config["scraping"]["keywords"]          = scraping.get("keywords", [])
          config["scraping"]["negative_keywords"] = scraping.get("negative_keywords", ["scam", "spam"])
          config["scraping"]["subreddits"]        = scraping.get("subreddits", [])

          # Airtable
          airtable = intake.get("airtable", {})
          if airtable.get("enabled") and airtable.get("base_id"):
              config["airtable"]["enabled"] = True
              config["airtable"]["base_id"] = airtable["base_id"]

          with open(config_path, "w") as f:
              json.dump(config, f, indent=2)

          print(f"config.json written for client: {client_id}")
          print(f"  Platforms: {platforms}")
          print(f"  Languages: {config['languages']}")
          print(f"  Keywords: {len(scraping.get('keywords', []))} entries")
          PYEOF

      - name: Write content-guidelines.md from intake data
        env:
          INTAKE_JSON: ${{ github.event.inputs.intake_json }}
          CLIENT_ID: ${{ steps.parse.outputs.client_id }}
        run: |
          python3 - <<'PYEOF'
          import json, os

          raw = os.environ["INTAKE_JSON"]
          intake = json.loads(raw)
          client_id = os.environ["CLIENT_ID"]
          display_name = intake.get("display_name", client_id)

          voice = intake.get("voice", {})
          tone_adjectives = voice.get("tone_adjectives", [])
          tone_description = voice.get("tone_description", "")
          content_avoid = voice.get("content_avoid", [])
          messaging_pillars = voice.get("messaging_pillars", [])

          audience = intake.get("audience", {})
          content = intake.get("content", {})
          cta_examples = content.get("cta_examples", [])
          hashtags = content.get("hashtags", [])

          tone_summary = ", ".join(tone_adjectives) if tone_adjectives else "professional, clear, educational"

          # Build content-guidelines.md content
          # Note: no em-dashes, no double-hyphens per CLAUDE.md rules
          lines = []
          lines.append(f"# {display_name} Content Guidelines")
          lines.append("")
          lines.append("Reference for content generation. All generated content must align with these principles.")
          lines.append("")
          lines.append("---")
          lines.append("")
          lines.append("## Brand Voice")
          lines.append("")
          lines.append(f"**{tone_summary}.**")
          lines.append("")
          if tone_description:
              lines.append(tone_description)
          else:
              lines.append(f"{display_name} communicates with clarity and substance. Every post teaches something, builds trust, or addresses a real audience need.")
          lines.append("")
          lines.append("---")
          lines.append("")
          lines.append("## Messaging Pillars")
          lines.append("")
          lines.append("Every piece of content should connect to one or more of these:")
          lines.append("")
          for i, pillar in enumerate(messaging_pillars, 1):
              lines.append(f"### {i}. {pillar}")
              lines.append("")
          if not messaging_pillars:
              lines.append("### 1. Education")
              lines.append("### 2. Trust Building")
              lines.append("### 3. Product Value")
              lines.append("")
          lines.append("---")
          lines.append("")
          lines.append("## Twitter / X Guidelines")
          lines.append("")
          lines.append("### Single Post (up to 280 chars)")
          lines.append("- Open with a hook or relatable pain point")
          lines.append("- One clear insight or value proposition")
          lines.append("- Optional: 1 soft CTA")
          lines.append("- Max 2-3 hashtags from the hashtag library")
          lines.append("")
          lines.append("### Thread (5 tweets)")
          lines.append("- Tweet 1: Hook or bold claim")
          lines.append("- Tweets 2-3: Education or insight breakdown")
          lines.append("- Tweet 4: How the product connects to the topic")
          lines.append("- Tweet 5: Soft CTA or follow prompt")
          lines.append("")
          lines.append("---")
          lines.append("")
          lines.append("## Telegram Guidelines")
          lines.append("")
          lines.append("- Length: 400 to 1200 characters")
          lines.append("- More educational tone than Twitter, explain the why")
          lines.append("- Use bullet points for clarity where appropriate")
          lines.append("- Use line breaks generously, avoid walls of text")
          lines.append("- End with an engagement question relevant to the audience")
          lines.append("")
          lines.append("---")
          lines.append("")
          lines.append("## What to Always Avoid")
          lines.append("")
          lines.append("| Avoid | Why |")
          lines.append("|-------|-----|")
          for item in content_avoid:
              lines.append(f"| {item} | Off-brand or damages audience trust |")
          if not content_avoid:
              lines.append("| Hype and unverifiable claims | Damages credibility |")
              lines.append("| Spam language | Off-brand |")
          lines.append("")
          lines.append("---")
          lines.append("")
          lines.append("## CTAs by Platform")
          lines.append("")
          lines.append("**Twitter:**")
          for cta in cta_examples[:2]:
              lines.append(f"- {cta}")
          if not cta_examples:
              lines.append(f"- Learn more at {intake.get('website', 'our website')}")
          lines.append("")
          lines.append("**Telegram:**")
          for cta in cta_examples[2:4] or cta_examples[:2]:
              lines.append(f"- {cta}")
          lines.append("")
          lines.append("---")
          lines.append("")
          lines.append("## Content Category Types")
          lines.append("")
          lines.append("| Type | Use Case |")
          lines.append("|------|----------|")
          lines.append("| Education | Explain a concept relevant to the product or industry |")
          lines.append("| Pain Point | Speak to a frustration the target audience experiences |")
          lines.append("| Proof | Share results, mechanics, or social proof transparently |")
          lines.append("| Trend Reaction | Comment on an industry trend through the brand lens |")
          lines.append("| Product | Direct feature or benefit highlight |")
          lines.append("")
          lines.append("---")
          lines.append("")
          lines.append("## Hashtag Library")
          lines.append("")
          lines.append(f"**Always relevant:** {' '.join(hashtags[:4])}")
          lines.append(f"**Contextual:** {' '.join(hashtags[4:8])}")
          if not hashtags:
              lines.append("**Always relevant:** #YourBrand")
          lines.append("")

          output = "\n".join(lines)
          path = f"clients/{client_id}/content-guidelines.md"
          with open(path, "w") as f:
              f.write(output)
          print(f"content-guidelines.md written ({len(output)} chars)")
          PYEOF

      - name: Write context.md from intake data
        env:
          INTAKE_JSON: ${{ github.event.inputs.intake_json }}
          CLIENT_ID: ${{ steps.parse.outputs.client_id }}
        run: |
          python3 - <<'PYEOF'
          import json, os

          raw = os.environ["INTAKE_JSON"]
          intake = json.loads(raw)
          client_id = os.environ["CLIENT_ID"]
          display_name = intake.get("display_name", client_id)

          audience = intake.get("audience", {})
          differentiators = intake.get("differentiators", [])
          description = intake.get("description", "")
          website = intake.get("website", "")
          tagline = intake.get("tagline", "")

          pain_points = audience.get("pain_points", [])
          situation = audience.get("situation", "")
          desired_outcome = audience.get("desired_outcome", "")
          age_range = audience.get("age_range", "")

          lines = []
          lines.append(f"# {display_name} — Client Context")
          lines.append("")
          lines.append("---")
          lines.append("")
          lines.append("## Organization Overview")
          lines.append("")
          if description:
              lines.append(description)
          else:
              lines.append(f"{display_name} is a company focused on serving its target audience.")
          if tagline:
              lines.append("")
              lines.append(f"**Tagline:** {tagline}")
          if website:
              lines.append(f"**Website:** {website}")
          lines.append("")
          lines.append("---")
          lines.append("")
          lines.append("## Target Audience (ICP)")
          lines.append("")
          lines.append("**Who they are:**")
          if age_range:
              lines.append(f"* Age range: {age_range}")
          if situation:
              lines.append(f"* {situation}")
          lines.append("")
          lines.append("**Pain points:**")
          for pp in pain_points:
              lines.append(f"* {pp}")
          if not pain_points:
              lines.append("* (To be filled during onboarding)")
          lines.append("")
          if desired_outcome:
              lines.append("**What they want:**")
              lines.append(f"* {desired_outcome}")
              lines.append("")
          lines.append("---")
          lines.append("")
          lines.append("## Positioning")
          lines.append("")
          lines.append(f"**How {display_name} is different:**")
          for diff in differentiators:
              lines.append(f"* {diff}")
          if not differentiators:
              lines.append("* (To be filled during onboarding)")
          lines.append("")

          output = "\n".join(lines)
          path = f"clients/{client_id}/context.md"
          with open(path, "w") as f:
              f.write(output)
          print(f"context.md written ({len(output)} chars)")
          PYEOF

      - name: Write keywords.md from intake data
        env:
          INTAKE_JSON: ${{ github.event.inputs.intake_json }}
          CLIENT_ID: ${{ steps.parse.outputs.client_id }}
        run: |
          python3 - <<'PYEOF'
          import json, os

          raw = os.environ["INTAKE_JSON"]
          intake = json.loads(raw)
          client_id = os.environ["CLIENT_ID"]
          display_name = intake.get("display_name", client_id)

          scraping = intake.get("scraping", {})
          keywords = scraping.get("keywords", [])
          negative_keywords = scraping.get("negative_keywords", ["scam", "spam"])
          subreddits = scraping.get("subreddits", [])

          # Split keywords into primary (first half) and secondary (second half)
          mid = max(1, len(keywords) // 2)
          primary_kw = keywords[:mid]
          secondary_kw = keywords[mid:]

          lines = []
          lines.append(f"# {display_name} — Keyword Reference")
          lines.append("")
          lines.append("Used by the content pipeline to filter and rank scraped posts for relevance.")
          lines.append("")
          lines.append("---")
          lines.append("")
          lines.append("## Primary Keywords (High Relevance)")
          lines.append("")
          lines.append("These directly relate to the core offering:")
          lines.append("")
          for kw in primary_kw:
              lines.append(f"- {kw}")
          if not primary_kw:
              lines.append("- (add primary keywords here)")
          lines.append("")
          lines.append("---")
          lines.append("")
          lines.append("## Secondary Keywords (Medium Relevance)")
          lines.append("")
          lines.append("These relate to the broader audience, pain points, and adjacent topics:")
          lines.append("")
          for kw in secondary_kw:
              lines.append(f"- {kw}")
          if not secondary_kw:
              lines.append("- (add secondary keywords here)")
          lines.append("")
          lines.append("---")
          lines.append("")
          lines.append("## Negative Keywords (Filter Out)")
          lines.append("")
          lines.append("Exclude posts containing these:")
          lines.append("")
          for kw in negative_keywords:
              lines.append(f"- {kw}")
          lines.append("")
          lines.append("---")
          lines.append("")
          lines.append("## Subreddits to Monitor")
          lines.append("")
          for sub in subreddits:
              clean = sub.lstrip("r/")
              lines.append(f"- r/{clean}")
          if not subreddits:
              lines.append("- (add relevant subreddits here)")
          lines.append("")
          lines.append("---")
          lines.append("")
          lines.append("## Twitter Search Queries")
          lines.append("")
          lines.append("Ready-to-use queries for the Apify scraper:")
          lines.append("")
          for i, kw in enumerate(primary_kw[:5], 1):
              lines.append(f'{i}. "{kw}" -scam -spam')
          if not primary_kw:
              lines.append('1. "your keyword" -scam -spam')
          lines.append("")

          output = "\n".join(lines)
          path = f"clients/{client_id}/keywords.md"
          with open(path, "w") as f:
              f.write(output)
          print(f"keywords.md written ({len(output)} chars)")
          PYEOF

      - name: Commit new client directory to main
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add "clients/${{ steps.parse.outputs.client_id }}/"
          git diff --cached --quiet && echo "Nothing to commit" || \
            git commit -m "Auto-onboard client: ${{ steps.parse.outputs.client_id }} (${{ steps.parse.outputs.display_name }})"
          git push origin main

      - name: Log onboard summary
        run: |
          echo ""
          echo "Client '${{ steps.parse.outputs.client_id }}' onboarded successfully."
          echo "Contact email: ${{ steps.parse.outputs.email }}"
          echo ""

  deploy:
    needs: onboard
    runs-on: ubuntu-latest
    timeout-minutes: 15

    concurrency:
      group: gh-pages-deploy
      cancel-in-progress: false

    permissions:
      contents: write

    steps:
      - name: Checkout main
        uses: actions/checkout@v4
        with:
          ref: main
          token: ${{ secrets.GITHUB_TOKEN }}
          fetch-depth: 0

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: pip install requests openpyxl google-genai python-dotenv jinja2 flask pillow

      - name: Create .env from secrets
        run: |
          echo "APIFY_API_TOKEN=${{ secrets.APIFY_API_TOKEN }}" >> .env
          echo "GOOGLE_AI_API_KEY=${{ secrets.GOOGLE_AI_API_KEY }}" >> .env
          echo "WAVESPEED_API_KEY=${{ secrets.WAVESPEED_API_KEY }}" >> .env
          echo "AIRTABLE_API_KEY=${{ secrets.AIRTABLE_API_KEY }}" >> .env
          echo "GH_REGEN_TOKEN=${{ secrets.GH_REGEN_TOKEN }}" >> .env

      - name: Build static site (all clients)
        run: |
          python scripts/build_static.py \
            --output dist \
            --include-admin

      - name: Copy admin panel to dist
        run: |
          mkdir -p dist/admin
          cp admin/index.html dist/admin/index.html
          cp admin/admin.css dist/admin/admin.css
          cp admin/admin.js dist/admin/admin.js

      - name: Copy intake form to dist
        run: |
          mkdir -p dist/intake
          cp intake/index.html dist/intake/index.html
          cp intake/intake.css dist/intake/intake.css
          cp intake/intake.js dist/intake/intake.js
          cp intake/intake-config.example.js dist/intake/intake-config.example.js
          if [ -f intake/intake-config.js ]; then
            cp intake/intake-config.js dist/intake/intake-config.js
          fi

      - name: Deploy to GitHub Pages (gh-pages branch)
        run: |
          cd dist
          git init
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add -A
          git commit -m "Deploy after auto-onboard: ${{ steps.parse.outputs.client_id || 'unknown' }} $(date +%Y-%m-%d)"
          git push -f https://x-access-token:${{ secrets.GITHUB_TOKEN }}@github.com/rtadik/bobe-content-dashboard.git HEAD:gh-pages
          cd ..


Key design decisions in this workflow:
- `steps.parse.outputs.client_id` propagates client_id from validation step to all later
  steps using GITHUB_OUTPUT (the modern replacement for set-output)
- The `CLIENT_EXISTS` env var guards against re-creating an existing client (idempotent on
  retries)
- The deploy job builds all clients (no `--client` flag) so the landing/login pages and all
  existing client dashboards are also rebuilt correctly
- The `git diff --cached --quiet` check prevents an empty commit error if the client already
  existed and no files changed
- `intake-config.js` is copied to dist conditionally since it is gitignored and may not be
  present in the CI checkout (it only exists when deployed via local /deploy)

---

## Step 3: Update `intake/intake.js`

Modify `handleSubmit` to POST intake JSON to the Cloudflare Worker after EmailJS completes.
The Worker call is fire-and-forget from the user's perspective: email delivery is the
primary signal of success, Worker failure shows a soft warning but does not block the
success panel.

Changes to `handleSubmit` function (lines 347-374 in current file):

```javascript
async function handleSubmit(e) {
  e.preventDefault();
  if (!validateForm()) return;

  const submitBtn = document.getElementById('submitBtn');
  submitBtn.textContent = 'Sending credentials...';
  submitBtn.disabled = true;

  const clientId   = getValue('client_id');
  const password   = derivePassword(clientId);
  const email      = getValue('email');
  const displayName = getValue('display_name');

  const baseUrl     = window.INTAKE_CONFIG ? window.INTAKE_CONFIG.dashboardBaseUrl : '';
  const loginUrl    = baseUrl ? baseUrl + '/login.html' : '';
  const dashboardUrl = baseUrl ? baseUrl + '/dashboard/' + clientId + '/' : '';

  // Build JSON first (needed for fallback download even if email fails)
  intakeData = buildIntakeJSON();

  // ── Step 1: EmailJS credential email ──────────────────────────────────────
  let emailFailed = false;
  try {
    await sendCredentialEmail({ email, displayName, clientId, password, loginUrl, dashboardUrl });
  } catch (err) {
    console.warn('EmailJS error:', err);
    emailFailed = true;
  }

  // ── Step 2: Cloudflare Worker — trigger auto-onboard (non-blocking) ───────
  let workerStatus = 'pending'; // 'ok' | 'error' | 'pending'
  const workerUrl = window.INTAKE_CONFIG ? window.INTAKE_CONFIG.workerUrl : null;

  if (workerUrl) {
    try {
      submitBtn.textContent = 'Setting up your dashboard...';
      const resp = await fetch(workerUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(intakeData),
      });
      if (resp.ok) {
        workerStatus = 'ok';
      } else {
        const errBody = await resp.json().catch(() => ({}));
        console.warn('Worker error response:', resp.status, errBody);
        workerStatus = 'error';
      }
    } catch (err) {
      console.warn('Worker fetch error:', err);
      workerStatus = 'error';
    }
  } else {
    console.warn('INTAKE_CONFIG.workerUrl not set — skipping auto-onboard trigger');
    workerStatus = 'error';
  }

  // ── Step 3: Show success panel ────────────────────────────────────────────
  showSuccessPanel({ emailFailed, clientId, password, workerStatus });
}


Update `showSuccessPanel` to accept and display `workerStatus`:

```javascript
function showSuccessPanel({ emailFailed = false, clientId = '', password = '', workerStatus = 'pending' } = {}) {
  document.getElementById('intakeForm').style.display = 'none';
  const panel = document.getElementById('successPanel');
  panel.classList.add('show');

  const email = getValue('email');
  document.getElementById('clientEmail').textContent = email;

  // Credentials display
  const creds = document.getElementById('successCredentials');
  creds.innerHTML =
    '<strong>Your credentials:</strong><br>' +
    'Username: <strong>admin</strong><br>' +
    'Password: <strong>' + (password || derivePassword(getValue('client_id'))) + '</strong>';

  // Worker / onboarding status message
  const statusEl = document.getElementById('onboardStatus');
  if (statusEl) {
    if (workerStatus === 'ok') {
      statusEl.style.display = 'block';
      statusEl.className = 'onboard-status onboard-ok';
      statusEl.textContent =
        'Your dashboard is being set up automatically. It will be live at content.rejiglabs.com/dashboard/' +
        (clientId || getValue('client_id')) + '/ within 3-5 minutes.';
    } else if (workerStatus === 'error') {
      statusEl.style.display = 'block';
      statusEl.className = 'onboard-status onboard-warn';
      statusEl.textContent =
        'Automatic setup encountered an issue. Your intake file has been downloaded. ' +
        'Forward it to your partner to complete setup manually.';
    }
    // If 'pending' (workerUrl not configured), show nothing extra
  }

  if (emailFailed) {
    const warn = document.getElementById('emailWarning');
    warn.style.display = 'block';
    warn.textContent =
      'Email delivery failed. Your credentials are shown above — save them now. ' +
      'Download your intake file and send it to your partner to complete setup.';
    document.getElementById('successMsg').innerHTML =
      'There was a problem sending the credential email to <strong>' + email + '</strong>.';
  }

  panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}


Add a div with id `onboardStatus` inside `#successPanel` in `intake/index.html`. Place it
between the credentials display and the download buttons:

```html
<div id="onboardStatus" class="onboard-status" style="display:none"></div>


Add CSS for the status element in `intake/intake.css`:

```css
.onboard-status {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-size: 0.9rem;
  line-height: 1.5;
}
.onboard-ok {
  background: rgba(91, 214, 159, 0.12);
  border: 1px solid rgba(91, 214, 159, 0.3);
  color: #5bd69f;
}
.onboard-warn {
  background: rgba(255, 193, 7, 0.1);
  border: 1px solid rgba(255, 193, 7, 0.3);
  color: #ffc107;
}


---

## Step 4: Update `intake/intake-config.example.js`

Add `workerUrl` to the example config so Rut knows to fill it in after deploying the Worker:

```javascript
// intake-config.js — EmailJS credentials, dashboard URL, and Cloudflare Worker URL
// Copy this file to intake-config.js and fill in your values.
// intake-config.js is gitignored and must never be committed.

window.INTAKE_CONFIG = {
  emailjs: {
    publicKey:  "YOUR_EMAILJS_PUBLIC_KEY",
    serviceId:  "YOUR_EMAILJS_SERVICE_ID",
    templateId: "YOUR_EMAILJS_TEMPLATE_ID"
  },
  dashboardBaseUrl: "https://content.rejiglabs.com",
  // Login URL sent to client: {dashboardBaseUrl}/login.html
  // Dashboard URL: {dashboardBaseUrl}/dashboard/{client_id}/

  workerUrl: "https://intake-onboard-worker.YOUR_SUBDOMAIN.workers.dev"
  // Cloudflare Worker URL. After deploying with wrangler, replace with your actual URL.
  // If you set a custom domain, use that instead (e.g. "https://onboard.rejiglabs.com").
  // Leave as empty string "" to disable auto-onboarding (manual /onboard-from-intake only).
};


---

## Step 5: Deploy the Cloudflare Worker (Wrangler CLI)

### One-Time Setup (run locally, not in CI)

```bash
# Install Wrangler globally (or via npx)
npm install -g wrangler

# Authenticate with Cloudflare
wrangler login
# Opens browser to Cloudflare OAuth — log in with your Cloudflare account

# Navigate to the worker directory
cd /Users/rt/Claude\ Code/RT\ Content\ Generator/worker

# Deploy the worker (creates it on Cloudflare if it doesn't exist)
wrangler deploy

# Note the workers.dev URL printed after deploy, e.g.:
# https://intake-onboard-worker.YOUR_SUBDOMAIN.workers.dev
# Copy this into intake/intake-config.js as workerUrl

# Set the GitHub PAT as a secret (never stored in wrangler.toml)
wrangler secret put GITHUB_PAT
# Paste the fine-grained PAT when prompted (see GitHub PAT requirements below)

# Verify the GITHUB_REPO var is correct in wrangler.toml, then redeploy
wrangler deploy


### GitHub PAT Requirements for the Cloudflare Worker

The PAT stored in the Worker needs:
- Fine-grained token (not classic)
- Repository access: Only `rtadik/bobe-content-dashboard`
- Permissions: Actions = Read and write (to trigger workflow_dispatch)
- No other permissions required

This is a separate PAT from the admin panel PAT. It lives only in Cloudflare's secret store.
Create it at: GitHub Settings → Developer Settings → Personal access tokens → Fine-grained tokens

### Verify the Worker is Working

```bash
# Test with a minimal valid intake JSON (replace YOUR_WORKER_URL)
curl -X POST https://intake-onboard-worker.YOUR_SUBDOMAIN.workers.dev \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "testclient",
    "display_name": "Test Client",
    "contact": { "email": "test@example.com" }
  }'

# Expected response:
# {"ok":true,"message":"Onboarding workflow triggered for client \"testclient\"...","client_id":"testclient"}


After confirming the Worker responds correctly, check GitHub Actions at:
https://github.com/rtadik/bobe-content-dashboard/actions
to confirm the `auto-onboard.yml` workflow was triggered.

---

## Step 6: GitHub Secrets Needed

No new GitHub Secrets are required. The `auto-onboard.yml` workflow uses:

| Secret | Already exists | Source |
|--------|---------------|--------|
| `GITHUB_TOKEN` | Auto-provided by GitHub Actions | Not a secret, auto-injected |
| `APIFY_API_TOKEN` | Yes (from weekly-pipeline setup) | Existing |
| `GOOGLE_AI_API_KEY` | Yes | Existing |
| `WAVESPEED_API_KEY` | Yes | Existing |
| `AIRTABLE_API_KEY` | Yes | Existing |
| `GH_REGEN_TOKEN` | Yes | Existing |

The `GITHUB_PAT` for triggering the workflow lives in Cloudflare Worker secrets only. It is
never passed to or stored in GitHub Secrets.

The `auto-onboard.yml` workflow itself uses `secrets.GITHUB_TOKEN` for git operations
(committing the new client dir and pushing to gh-pages). `GITHUB_TOKEN` is automatically
available to all workflows with no setup required.

---

## Step 7: Security Considerations

### CORS Restriction

The Worker's `ALLOWED_ORIGIN` env var is set to `https://content.rejiglabs.com` in
`wrangler.toml`. The Worker returns this origin in `Access-Control-Allow-Origin` headers.
Browsers enforce this: the intake form (served from content.rejiglabs.com) can reach the
Worker, but a random third-party site cannot trigger POSTs to it from a browser context.

Note: CORS is a browser enforcement mechanism only. A server-side attacker can POST to the
Worker directly without a browser. The next two mitigations address this.

### Intake JSON Validation

The Worker validates:
- `client_id` exists and matches `^[a-z0-9_-]+$`
- `display_name` exists and is a non-empty string
- `contact.email` exists and passes basic email regex

The GitHub Actions workflow validates again server-side (defense in depth). If validation
fails in the workflow, the run fails cleanly with a clear error message in the logs.

### Duplicate Client Protection

The `auto-onboard.yml` workflow checks `if [ -d "clients/${CLIENT_ID}" ]` before creating
the directory. If the client already exists, directory creation is skipped but the deploy
still runs (idempotent behavior, useful for retries or re-submissions).

### Rate Limiting

Cloudflare Workers free tier enforces rate limits automatically (100k requests/day, no
per-IP configuration needed on the free tier). For additional protection against abuse,
you can enable Cloudflare's built-in rate limiting rules in the Cloudflare dashboard under
Security → WAF → Rate Limiting Rules (available on free tier with basic config).

### Workflow Concurrency

`auto-onboard.yml` shares the `gh-pages-deploy` concurrency group with `weekly-pipeline.yml`
and `regenerate-item.yml`. This prevents simultaneous deploys from corrupting the gh-pages
branch. With `cancel-in-progress: false`, queued jobs wait their turn rather than being
cancelled.

---

## Step 8: Testing Steps

### Test 1: Worker Validation Rejects Bad Input

```bash
# Missing client_id — should return 400
curl -X POST https://YOUR_WORKER_URL \
  -H "Content-Type: application/json" \
  -d '{"display_name": "Test", "contact": {"email": "test@example.com"}}'
# Expected: {"error":"Missing required field: client_id"}

# Invalid client_id format — should return 400
curl -X POST https://YOUR_WORKER_URL \
  -H "Content-Type: application/json" \
  -d '{"client_id": "Test Client!", "display_name": "Test", "contact": {"email": "t@e.com"}}'
# Expected: {"error":"client_id must be lowercase letters, numbers..."}


### Test 2: Worker Triggers Workflow on Valid Input

```bash
curl -X POST https://YOUR_WORKER_URL \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "testclient99",
    "display_name": "Test Client 99",
    "contact": {"email": "test@example.com"},
    "tagline": "Test tagline",
    "website": "test.com",
    "description": "A test client for pipeline validation.",
    "audience": {"pain_points": ["pain1"], "situation": "test situation"},
    "differentiators": ["diff1"],
    "voice": {"tone_adjectives": ["clear"], "messaging_pillars": ["Trust"], "content_avoid": ["spam"]},
    "platforms": ["twitter"],
    "scraping": {"keywords": ["keyword1", "keyword2", "keyword3"]},
    "content": {"cta_examples": ["Try it"], "hashtags": ["#Test"]},
    "brand": {"primary_color": "#1a1a2e", "accent_color": "#00aaff", "text_color": "#ffffff"},
    "airtable": {"enabled": false, "base_id": ""},
    "languages": ["english"]
  }'
# Expected: {"ok":true,"message":"Onboarding workflow triggered...","client_id":"testclient99"}


Then verify in GitHub Actions that `auto-onboard.yml` run appears and passes.
Verify `clients/testclient99/` is committed to main branch.
Verify site rebuilds and `content.rejiglabs.com/dashboard/testclient99/` is accessible.

Clean up after test:

```bash
# Delete test client from repo (run locally in the repo)
git rm -r clients/testclient99/
git commit -m "Remove test client testclient99"
git push origin main
# Then run /deploy to rebuild without testclient99


### Test 3: Full End-to-End via Intake Form

1. Open https://content.rejiglabs.com/intake/
2. Fill out the form with test data (use `testclient99` as client_id)
3. Submit
4. Verify:
   - EmailJS sends the credential email
   - Success panel shows with credentials
   - `onboardStatus` div shows "Your dashboard is being set up automatically..."
   - GitHub Actions shows `auto-onboard.yml` triggered
   - After 3-5 minutes, https://content.rejiglabs.com/dashboard/testclient99/ is accessible
   - Login with username `admin`, password `testclient99123` works

### Test 4: Worker Failure Graceful Degradation

Temporarily set an invalid `GITHUB_PAT` in the Worker's env vars via Cloudflare dashboard,
then submit the intake form. Verify:
- EmailJS email still sends (email delivery is not blocked by Worker failure)
- Success panel shows warning message about automatic setup encountering an issue
- JSON download is available as fallback
- No uncaught JavaScript errors in the browser console

---

## File Change Summary

| File | Action | Notes |
|------|--------|-------|
| `worker/onboard-worker.js` | Create | Cloudflare Worker source |
| `worker/wrangler.toml` | Create | Wrangler deployment config |
| `.github/workflows/auto-onboard.yml` | Create | New GitHub Actions workflow |
| `intake/intake.js` | Modify | Add Worker POST in handleSubmit, update showSuccessPanel |
| `intake/index.html` | Modify | Add onboardStatus div inside successPanel |
| `intake/intake.css` | Modify | Add .onboard-status, .onboard-ok, .onboard-warn styles |
| `intake/intake-config.example.js` | Modify | Add workerUrl field with documentation |
| `intake/intake-config.js` | Modify | Add workerUrl field (gitignored, user fills in) |
| `reference/github-actions-setup.md` | Modify | Add Cloudflare Worker setup section |
| `CLAUDE.md` | Modify | Add auto-onboard workflow to Pending Plans table, update Scripts table |

---

## Implementation Order

Execute in this order to avoid breaking the live site during implementation:

1. Create `worker/` directory and files (no impact until deployed)
2. Create `.github/workflows/auto-onboard.yml` (no impact until triggered)
3. Update `intake/intake-config.example.js` (documentation only, no behavior change)
4. Deploy Cloudflare Worker via wrangler CLI (creates the Worker, not yet connected to form)
5. Update `intake/intake-config.js` with `workerUrl` (connects form to Worker)
6. Modify `intake/intake.js` (adds Worker POST, backward compatible — no-ops if workerUrl missing)
7. Modify `intake/index.html` (add onboardStatus div)
8. Modify `intake/intake.css` (add status styles)
9. Run `/deploy` to push all changes to gh-pages
10. Run Test 2 (curl Worker directly) to confirm workflow triggers
11. Run Test 3 (end-to-end via intake form) to confirm full flow
12. Update `CLAUDE.md` and `reference/github-actions-setup.md`

---

## Notes on `build_static.py` and Multi-Client Deploy

The `build_static.py` script when called without `--client` builds all clients found in
`outputs/content/`. The `auto-onboard.yml` deploy job calls it without `--client` so the
entire site rebuilds, including the landing page, login page, all existing client dashboards,
and the new client's (empty) dashboard stub.

A newly onboarded client's dashboard at `/dashboard/{client_id}/` will show an empty state
(no content yet) until their first `/weekly-pipeline` run. This is expected behavior. The
login credentials are baked into the auth layer by `build_static.py` automatically based on
the existence of `clients/{client_id}/config.json`. No separate credential registration step
is needed.


---

### Critical Files for Implementation

- `/Users/rt/Claude Code/RT Content Generator/intake/intake.js` - Core file to modify: add Worker POST in `handleSubmit`, update `showSuccessPanel` signature and behavior
- `/Users/rt/Claude Code/RT Content Generator/.github/workflows/auto-onboard.yml` - New file to create: the GitHub Actions workflow that parses intake JSON and populates all four client config files
- `/Users/rt/Claude Code/RT Content Generator/clients/_template/config.json` - Pattern to follow: every field written by the workflow's Python steps must map to this exact JSON schema
- `/Users/rt/Claude Code/RT Content Generator/.github/workflows/weekly-pipeline.yml` - Pattern to follow for deploy job structure: concurrency group, gh-pages push command, pip install list, artifact handling
- `/Users/rt/Claude Code/RT Content Generator/intake/intake-config.example.js` - Must add `workerUrl` field so the gitignored `intake-config.js` gets the new field when Rut updates it

---

## Implementation Notes

**Implemented:** 2026-02-24

### Summary

- Created `worker/onboard-worker.js` — Cloudflare Worker with CORS, validation, and GitHub API trigger
- Created `worker/wrangler.toml` — Wrangler deployment config
- Created `.github/workflows/auto-onboard.yml` — two-job workflow (onboard + deploy)
- Modified `intake/intake.js` — refactored `handleSubmit` with two-step flow (EmailJS then Worker), updated `showSuccessPanel` to accept and display `workerStatus`
- Modified `intake/index.html` — added `#onboardStatus` div inside success panel
- Modified `intake/intake.css` — added `.onboard-status`, `.onboard-ok`, `.onboard-warn` styles
- Modified `intake/intake-config.example.js` — added `workerUrl` field with documentation
- Updated `CLAUDE.md` — added auto-onboard workflow to Pending Plans and GitHub Actions sections

### Deviations from Plan

- `intake/intake-config.js` (the gitignored live file) was not modified — it requires Rut to add the `workerUrl` manually after deploying the Worker, as it is machine-specific and gitignored
- `reference/github-actions-setup.md` update was deferred; the Cloudflare setup guide is provided directly to the user as part of the implementation report

### Issues Encountered

None.
