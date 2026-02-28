# Plan: Multi-Client Content Platform Architecture

**Created:** 2026-02-19
**Status:** Implemented
**Request:** Architect this workspace so it can serve multiple clients beyond BoBe, each with their own brand, keywords, tone, and reference images.

---

## Overview

### What This Plan Accomplishes

Transform this single-client BoBe content pipeline into a multi-client platform where each client has isolated brand assets, keywords, content guidelines, and output directories. The same pipeline commands run for any client by switching a single config value.

### Why This Matters

You're sitting on a productizable content engine. Right now everything from keywords to mascot descriptions to output paths is hardcoded to BoBe. Making this multi-client lets you onboard new clients with minimal setup: drop in their brand assets, fill out a config file, and the entire pipeline (scraping, content generation, image generation, dashboard, deployment) works for them out of the box.

---

## The Big Decision: Fork vs. Multi-Tenant

### Option A: Fork into separate workspaces per client

**Pros:** Simple, no refactoring needed, full isolation
**Cons:** Duplicate maintenance (bug fixes, feature upgrades must be applied to every fork), workspace sprawl, no shared tooling improvements

### Option B: Multi-tenant in a single workspace (Recommended)

**Pros:** Single codebase to maintain, new client = new config folder, shared improvements benefit all clients, one set of commands
**Cons:** Requires refactoring to extract hardcoded values, slightly more complex directory structure

### Recommendation: Option B

Forking works for 2 clients but becomes unmanageable at 5+. Every pipeline improvement, bug fix, or new feature would need to be manually replicated. A config-driven approach means adding a client is a 15-minute setup task, not a workspace clone.

---

## Current State

### Where BoBe Is Hardcoded (Audit Summary)

The brand name "BoBe" appears in **40+ locations** across the codebase. Key categories:

| Category | Files Affected | Examples |
|----------|---------------|----------|
| Brand identity | `nano_banana.py`, `wavespeed_img.py`, `web_viewer.py`, `build_static.py` | Mascot description, logo path, color palette, page titles |
| Keywords & topics | `weekly_pipeline.py`, `apify_scraper.py`, `bobe-keywords.md` | `WEEKLY_KEYWORDS`, negative keywords, subreddits |
| Voice & tone | `content-guidelines.md`, `weekly_pipeline.py`, content-generator SKILL | "transparent, educational, no hype" |
| Output paths | All scripts | `outputs/content/` (no client namespace) |
| Dashboard UI | `web_viewer.py`, `build_static.py` | `<title>BoBe Content Dashboard</title>`, header brand name |
| Claude commands | `weekly-pipeline.md`, SKILL.md files | Evergreen topics, brand-specific prompts |

### Gaps Being Addressed

- No way to run the pipeline for a different client without manually editing 10+ files
- Brand assets, keywords, and content rules are scattered across the codebase rather than centralized
- Outputs from different clients would collide in the same directory
- Dashboard shows a single brand with no client switching

---

## Proposed Architecture

### Client Config Structure

Each client gets a directory under `clients/`:

```
clients/
├── bobe/                          # Existing client (migrated)
│   ├── config.json                # Master config: name, colors, tone, keywords, etc.
│   ├── brand/                     # Brand assets (logo, banners, references)
│   │   ├── logo.png
│   │   ├── banner-1.png
│   │   └── ...
│   ├── content-guidelines.md      # Voice, tone, messaging pillars
│   ├── keywords.md                # Keyword lists for scraping
│   └── context.md                 # Business context for content generation
├── client-template/               # Template for onboarding new clients
│   ├── config.json
│   ├── brand/
│   ├── content-guidelines.md
│   ├── keywords.md
│   └── context.md
```

### config.json Schema

```json
{
  "client_id": "bobe",
  "display_name": "BoBe",
  "tagline": "AI-driven crypto yield automation",
  "website": "bobe.app",
  "brand": {
    "primary_color": "#1a1a2e",
    "accent_color": "#00d4ff",
    "text_color": "#ffffff",
    "logo_path": "brand/logo.png",
    "reference_images": [
      "brand/logo.png",
      "brand/banner-1.png",
      "brand/banner-2.png"
    ],
    "mascot_description": "A 3D chibi clay figurine, young Asian man with round thick-framed glasses...",
    "background_style": "Deep dark navy gradient (dark blue-black)"
  },
  "content": {
    "tone": "transparent, educational, no hype, no guaranteed return claims",
    "brand_terms_keep": ["BoBe", "USDT", "DCA"],
    "cta_url": "bobe.app",
    "cta_examples": [
      "See how BoBe works →",
      "Try BoBe free: bobe.app"
    ],
    "hashtags": ["#BoBe", "#BoBeApp", "#DeFi", "#CryptoYield"]
  },
  "scraping": {
    "keywords": [
      "trading bot", "yield", "DCA strategy", "automated trading",
      "on-chain yield", "crypto automation", "AI trading"
    ],
    "negative_keywords": [
      "rug pull", "scam", "pump and dump", "meme coin",
      "guaranteed returns", "get rich quick"
    ],
    "subreddits": ["defi", "CryptoCurrency", "ethfinance", "algotrading"]
  },
  "image": {
    "style_presets": {
      "minimal": "clean minimalist banner, solid dark background",
      "tech": "futuristic data visualization banner with glowing elements",
      "notification": "realistic smartphone mockup showing app notification"
    }
  },
  "languages": ["en", "ru"]
}
```

### Output Path Namespacing

```
outputs/
└── content/
    ├── bobe/                      # Client-scoped
    │   ├── 2026-02-16-weekly-content.xlsx
    │   ├── images/
    │   │   └── 2026-02-16-weekly/
    │   └── 2026-02-16-approvals.json
    └── newclient/
        ├── 2026-02-16-weekly-content.xlsx
        └── ...
```

### Active Client Selection

A simple `.active-client` file in the workspace root (gitignored) holds the current client ID:

```
bobe
```

Scripts read this to determine which config to load. Can be overridden with `--client` flag on any script. The `/weekly-pipeline` command reads it automatically.

---

## Proposed Changes

### Summary of Changes

- Create `clients/` directory structure with BoBe migrated and a blank template
- Add `scripts/client_config.py` module that loads client config and provides it to all scripts
- Refactor all 6 scripts to read brand/keywords/tone from client config instead of hardcoded values
- Namespace output paths by client ID
- Update dashboard to show client brand name and colors dynamically
- Update Claude commands and skills to be client-aware
- Add `/switch-client` command and `/onboard-client` command

### New Files to Create

| File Path | Purpose |
|-----------|---------|
| `clients/bobe/config.json` | BoBe's master configuration (migrated from hardcoded values) |
| `clients/bobe/brand/` | Move existing `reference/bobe-brand/` assets here |
| `clients/bobe/content-guidelines.md` | Move existing `reference/content-guidelines.md` |
| `clients/bobe/keywords.md` | Move existing `reference/bobe-keywords.md` |
| `clients/bobe/context.md` | Move/merge existing `context/BoBe Context.md` |
| `clients/_template/config.json` | Blank config template for new clients |
| `clients/_template/content-guidelines.md` | Template content guidelines |
| `clients/_template/keywords.md` | Template keyword file |
| `clients/_template/context.md` | Template business context |
| `scripts/client_config.py` | Central config loader module used by all scripts |
| `.active-client` | Current client ID (gitignored) |
| `.claude/commands/switch-client.md` | `/switch-client` command |
| `.claude/commands/onboard-client.md` | `/onboard-client` command |

### Files to Modify

| File Path | Changes |
|-----------|---------|
| `scripts/weekly_pipeline.py` | Import client_config; replace hardcoded keywords, brand refs, output paths |
| `scripts/nano_banana.py` | Load brand assets and mascot description from client config |
| `scripts/wavespeed_img.py` | Load brand assets and mascot description from client config |
| `scripts/apify_scraper.py` | Load keywords and negative keywords from client config |
| `scripts/web_viewer.py` | Dynamic brand name, colors, output path from client config |
| `scripts/build_static.py` | Dynamic brand name, colors, output path from client config |
| `.claude/commands/weekly-pipeline.md` | Read client config for keywords, evergreen topics, brand terms |
| `.claude/skills/content-generator/SKILL.md` | Reference client config paths instead of hardcoded BoBe files |
| `.claude/skills/image-generator/SKILL.md` | Reference client config paths instead of hardcoded BoBe paths |
| `CLAUDE.md` | Document multi-client architecture, new commands |
| `.gitignore` | Add `.active-client` |

### Files to Move/Reorganize

| From | To | Notes |
|------|----|-------|
| `reference/bobe-brand/*` | `clients/bobe/brand/*` | Keep `reference/` for generic docs only |
| `reference/content-guidelines.md` | `clients/bobe/content-guidelines.md` | Client-specific |
| `reference/bobe-keywords.md` | `clients/bobe/keywords.md` | Client-specific |

---

## Design Decisions

### Key Decisions Made

1. **Config file over database**: A JSON config file per client is simpler than a database, version-controllable, and human-editable. For a content pipeline serving 5-20 clients, this is the right level of complexity.

2. **`.active-client` file over environment variable**: A file persists across terminal sessions and is visible/editable. An env var would be forgotten between sessions. The file is gitignored so each machine can have its own active client.

3. **`clients/` directory over `reference/` subdirs**: Grouping everything per-client (config, brand, guidelines, keywords) in one directory makes onboarding intuitive: "copy the template folder, fill it in."

4. **Namespace outputs by client**: `outputs/content/bobe/` instead of `outputs/content/`. Prevents file collisions and makes it clear which client's content you're looking at.

5. **No authentication/accounts needed**: This is a local CLI tool, not a SaaS. "Switching clients" is changing a config value, not logging into a different account. The dashboard can optionally show a client picker in the header.

6. **Keep the existing pipeline structure**: The 21-topic, 42-item, bilingual pipeline structure stays the same. Only the brand-specific inputs change per client.

### Alternatives Considered

- **Separate workspaces per client (forking)**: Rejected because maintenance burden grows linearly with clients. A bug fix in `web_viewer.py` would need to be applied to every fork.
- **Git branches per client**: Rejected because branches diverge and merging becomes painful. Config-based switching is cleaner.
- **Environment variables for everything**: Rejected because there are too many client-specific values (mascot description alone is a paragraph). A config file is more appropriate.
- **YAML config instead of JSON**: Either works. JSON chosen because Python's `json` module is built-in (no extra dependency) and the config is structured data, not prose.

### Open Questions for Discussion

1. **Should each client's brand assets (logos, banners) be git-tracked?** They could be large. Options: (a) track them in git (simple, works for <20 clients), (b) gitignore brand assets and document setup separately, (c) store in a shared cloud folder.

2. **Dashboard client switching**: Should the web dashboard have a dropdown to switch between clients, or should it always show the active client? A dropdown would let you compare content across clients.

3. **Per-client API keys**: Should each client potentially have their own API keys (e.g., separate Apify token for billing), or share the same keys? Currently all keys are in `.env`.

4. **Deployment isolation**: When deploying via `/deploy`, should each client get their own Cloudflare Pages project (separate URLs), or should there be a single site with client routing?

---

## Step-by-Step Tasks

### Step 1: Create the client_config.py module

Build the central config loader that all scripts will import.

**Actions:**
- Create `scripts/client_config.py` with functions:
  - `get_active_client()` — reads `.active-client` file, returns client ID string
  - `load_config(client_id=None)` — loads and returns the full config dict for the active (or specified) client
  - `get_brand_dir(client_id=None)` — returns Path to client's brand directory
  - `get_output_dir(client_id=None)` — returns Path to client's output directory
  - `get_reference_images(client_id=None)` — returns list of Paths to reference images
  - `get_keywords(client_id=None)` — returns keyword list
  - `get_negative_keywords(client_id=None)` — returns negative keyword list
- Add `--client` flag support (passed through to override `.active-client`)

**Files affected:**
- `scripts/client_config.py` (new)
- `.active-client` (new)
- `.gitignore` (add `.active-client`)

---

### Step 2: Create the clients/ directory structure and migrate BoBe

Move BoBe's brand-specific files into `clients/bobe/` and create the config.json.

**Actions:**
- Create `clients/bobe/` directory
- Create `clients/bobe/config.json` with all values extracted from the current hardcoded locations
- Move `reference/bobe-brand/` to `clients/bobe/brand/`
- Move `reference/content-guidelines.md` to `clients/bobe/content-guidelines.md`
- Move `reference/bobe-keywords.md` to `clients/bobe/keywords.md`
- Create `clients/bobe/context.md` from `context/BoBe Context.md` (copy relevant content)
- Create symlinks or update paths so nothing breaks during migration
- Leave `reference/api-setup.md` in place (it's generic, not client-specific)

**Files affected:**
- `clients/bobe/config.json` (new)
- `clients/bobe/brand/` (moved from `reference/bobe-brand/`)
- `clients/bobe/content-guidelines.md` (moved)
- `clients/bobe/keywords.md` (moved)
- `clients/bobe/context.md` (new, derived from existing)

---

### Step 3: Create the client template

Provide a blank template that makes onboarding a new client a fill-in-the-blanks exercise.

**Actions:**
- Create `clients/_template/config.json` with placeholder values and comments
- Create `clients/_template/brand/` with a README explaining what to put here
- Create `clients/_template/content-guidelines.md` with section structure but no BoBe content
- Create `clients/_template/keywords.md` with section structure
- Create `clients/_template/context.md` with section structure

**Files affected:**
- `clients/_template/` (new directory with template files)

---

### Step 4: Refactor scripts to use client_config

Update each script to load client-specific values from config instead of hardcoded constants.

**Actions:**

**nano_banana.py:**
- Import `client_config`
- Replace `BRAND_DIR` with `client_config.get_brand_dir()`
- Replace `DEFAULT_REFERENCES` with `client_config.get_reference_images()`
- Replace hardcoded mascot description in `build_prompt()` with `config["brand"]["mascot_description"]`
- Replace hardcoded background style with `config["brand"]["background_style"]`
- Replace "BoBe" in notification style preset with `config["display_name"]`
- Add `--client` argument

**wavespeed_img.py:**
- Same pattern: load brand name, mascot description, logo text from config
- Replace "BoBe" in `build_prompt_ru()` and `translate_image()`
- Add `--client` argument

**apify_scraper.py:**
- Replace `NEGATIVE_KEYWORDS` with `client_config.get_negative_keywords()`
- Replace default `--keywords` with config-loaded keywords
- Replace default `--subreddits` with config subreddits
- Add `--client` argument

**weekly_pipeline.py:**
- Replace `WEEKLY_KEYWORDS` with config keywords
- Replace hardcoded brand terms in `translate_text_to_russian()` ("BoBe, USDT, DCA" becomes config value)
- Replace output path `OUTPUT_DIR` with `client_config.get_output_dir()`
- Replace notification title with client display name
- Add `--client` argument

**web_viewer.py:**
- Load client config at startup
- Replace hardcoded `<title>`, header brand name, localStorage key with config values
- Update `CONTENT_DIR` to be client-scoped
- Add client name to startup print

**build_static.py:**
- Same as web_viewer: dynamic title, brand name, footer, colors from config

**Files affected:**
- `scripts/nano_banana.py`
- `scripts/wavespeed_img.py`
- `scripts/apify_scraper.py`
- `scripts/weekly_pipeline.py`
- `scripts/web_viewer.py`
- `scripts/build_static.py`

---

### Step 5: Update Claude commands to be client-aware

**Actions:**

**weekly-pipeline.md:**
- Add instruction to read `clients/{active_client}/config.json` at pipeline start
- Replace hardcoded keyword list with "read from client config"
- Replace hardcoded evergreen topics with "generate from client's context and keywords"
- Replace brand-specific prompts with "use client config values"

**Add switch-client.md:**
- Simple command: writes the client ID to `.active-client`
- Lists available clients from `clients/` directory
- Shows current active client

**Add onboard-client.md:**
- Walks through creating a new client directory from template
- Prompts for: client name, website, brand description, keywords, tone
- Creates the config.json and directory structure
- Reminds to add brand assets to the brand/ folder

**Files affected:**
- `.claude/commands/weekly-pipeline.md`
- `.claude/commands/switch-client.md` (new)
- `.claude/commands/onboard-client.md` (new)

---

### Step 6: Update skills to reference client config

**Actions:**
- Update `content-generator/SKILL.md` to read from `clients/{active_client}/content-guidelines.md` and `context.md`
- Update `image-generator/SKILL.md` to read from `clients/{active_client}/brand/` and config
- Remove hardcoded BoBe mascot descriptions, replace with "read from client config"

**Files affected:**
- `.claude/skills/content-generator/SKILL.md`
- `.claude/skills/image-generator/SKILL.md`

---

### Step 7: Update CLAUDE.md and documentation

**Actions:**
- Add "Multi-Client Architecture" section to CLAUDE.md
- Document `clients/` directory structure
- Document `/switch-client` and `/onboard-client` commands
- Update workspace structure tree
- Update the Scripts table with `client_config.py`
- Update existing command descriptions to note client-awareness

**Files affected:**
- `CLAUDE.md`

---

### Step 8: Validate the migration

**Actions:**
- Set active client to `bobe`
- Run `/weekly-pipeline` in mock mode and verify it uses BoBe config
- Launch `/view-content` and verify BoBe branding appears
- Run `nano_banana.py --mock` and verify it loads BoBe reference images
- Verify output files land in `outputs/content/bobe/`

---

## Connections & Dependencies

### Files That Reference Moved Paths

After moving `reference/bobe-brand/` to `clients/bobe/brand/`, these files need path updates:
- `scripts/nano_banana.py` — `BRAND_DIR` constant
- `scripts/wavespeed_img.py` — any brand path references
- `.claude/skills/image-generator/SKILL.md` — references `reference/bobe-brand/`
- `CLAUDE.md` — workspace structure tree

After moving `reference/content-guidelines.md` and `reference/bobe-keywords.md`:
- `.claude/skills/content-generator/SKILL.md` — references these paths
- `.claude/commands/weekly-pipeline.md` — may reference these

### Impact on Existing Workflows

- **No breaking changes if done correctly**: BoBe remains the default active client. All existing commands work the same way, they just read from config instead of hardcoded values.
- **Output path change**: Files move from `outputs/content/` to `outputs/content/bobe/`. Existing workbooks should be moved or the dashboard updated to check both paths for backward compatibility.
- **Dashboard URLs stay the same**: localhost:5001, same routes, just dynamic branding.

---

## Validation Checklist

- [ ] `clients/bobe/config.json` exists and contains all extracted values
- [ ] `scripts/client_config.py` loads config correctly
- [ ] `.active-client` contains `bobe` and is in `.gitignore`
- [ ] All 6 scripts accept `--client` flag and default to active client
- [ ] No remaining hardcoded "BoBe" in scripts (only in `clients/bobe/` files)
- [ ] `nano_banana.py --mock` loads references from `clients/bobe/brand/`
- [ ] `weekly_pipeline.py --action create-workbook --mock` creates workbook in `outputs/content/bobe/`
- [ ] Dashboard shows client name dynamically from config
- [ ] `/switch-client` command works
- [ ] `clients/_template/` exists and is complete
- [ ] `CLAUDE.md` updated with multi-client architecture docs
- [ ] Existing BoBe content in `outputs/content/` migrated or backward-compatible

---

## Success Criteria

1. Running `/weekly-pipeline` produces content using BoBe's config without any hardcoded BoBe references in the script logic
2. A new client can be onboarded by copying `clients/_template/`, filling in their config, adding brand assets, and running the pipeline
3. Switching between clients is a single command (`/switch-client`) or flag (`--client`)
4. All scripts, commands, and skills work identically for any client

---

## Notes

### Implementation Priority

This is a significant refactor touching every script. Recommended approach:
1. Start with `client_config.py` and `clients/bobe/config.json` (the foundation)
2. Refactor one script at a time, testing each before moving on
3. Do the dashboard last (most complex HTML templating)
4. Update commands and skills after scripts are stable

### Future Considerations

- **Client-specific deployment URLs**: Each client could get their own Cloudflare Pages subdomain (e.g., `bobe-content.pages.dev`, `clientx-content.pages.dev`)
- **Multi-client dashboard**: A "hub" dashboard that lists all clients and links to each client's content view
- **Client onboarding wizard**: An interactive `/onboard-client` that asks questions and generates the config
- **Billing per client**: If this becomes a paid service, track API usage (image generations, scrape calls) per client
- **Client-specific API keys**: Allow each client to have their own API keys in their config (useful if they want to pay for their own usage)

### Estimated Scope

This is a multi-session effort. The refactoring touches every script and command file. Breaking it into phases:
- **Phase 1** (Steps 1-3): Config infrastructure + BoBe migration. Can be done in one session.
- **Phase 2** (Step 4): Script refactoring. One session, methodical.
- **Phase 3** (Steps 5-7): Commands, skills, docs. One session.
- **Phase 4** (Step 8): Testing and validation.

---

## Implementation Notes

**Implemented:** 2026-02-22

### Summary

All 8 steps of the plan were executed in a single session. The workspace was transformed from a single-client BoBe-only platform to a config-driven multi-client architecture. BoBe's brand assets, keywords, content guidelines, and context were migrated to `clients/bobe/`. A template directory was created for onboarding new clients. All 6 scripts were refactored to import from `client_config.py`. Commands and skills were updated to be client-aware. CLAUDE.md was updated to reflect the new architecture.

### Deviations from Plan

- Brand assets were moved with `git mv` (preserving history) rather than a simple copy
- The `reference/` directory was kept with just `api-setup.md` (not deleted entirely)
- `context/BoBe Context.md` was kept as a legacy reference alongside the new `clients/bobe/context.md`

### Issues Encountered

None. All file operations and validation tests completed successfully.
