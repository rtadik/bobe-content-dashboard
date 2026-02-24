# Scalability Plan: Multi-Client SaaS Architecture
**Date**: 2026-02-24
**Status**: Pending implementation
**Scope**: Scale platform from 1 client to 5-10 active clients reliably

---

## Current State Assessment

The platform is **workable for 2-3 clients** but has 5 critical blockers that prevent scaling to 5-10 clients. Everything architecturally sound (config discovery, output isolation, per-client routing, GitHub Actions parameterization) is already in place. What's missing is resource isolation and deployment safety.

### What already scales ✅
- Client discovery via `clients/{client_id}/` directories (O(N) scan)
- Output isolation under `outputs/content/{client_id}/`
- Dashboard routing at `/dashboard/{client_id}/`
- GitHub Actions workflows accept `client_id` as input — concurrent pipelines fully supported
- Auth: SHA-256 hashed credentials auto-generated per client at build time
- Airtable sync is per-client opt-in

### Critical blockers ❌

| # | Blocker | Impact | Files Affected |
|---|---------|--------|----------------|
| 1 | Shared Gemini API key | Rate limit (60 RPM) exceeded at 2-3 concurrent pipelines | `pipeline_runner.py`, `weekly_pipeline.py` |
| 2 | Shared WaveSpeed API key | Unknown rate limit; likely fails at 3-5 concurrent clients | `nano_banana.py`, `wavespeed_img.py` |
| 3 | Concurrent deployment race condition | Last `gh-pages` push wins; earlier clients' data overwritten | `weekly-pipeline.yml`, `regenerate-item.yml` |
| 4 | GitHub Pages bandwidth | Estimated 168 GB/month at 5 clients vs 100 GB/month limit | Static image serving |
| 5 | Admin panel hardcoded to one repo | `REPO = "rtadik/bobe-content-dashboard"` — breaks with separate repos | `admin/admin.js` |

### Moderate issues ⚠️
- No image retention policy (unbounded storage growth)
- Credentials from all clients baked into a single `login.html`
- Clients must enter a GitHub PAT to use regen buttons on the live dashboard
- Airtable sync has no retry/backoff logic

---

## SaaS Best Practices Applied to This Platform

Based on multi-tenant SaaS architecture principles:

1. **Tenant isolation** — Each tenant (client) needs isolated API credentials, not shared pools
2. **Deployment serialization** — Concurrent writes to a shared branch must be gated with concurrency controls
3. **CDN for static assets** — Images should be served from a CDN, not a source repo
4. **Self-service client actions** — Clients should be able to trigger regeneration without knowing internal infrastructure (no GitHub PAT exposure)
5. **Observability per tenant** — Pipeline runs should be tagged/scoped per client

---

## Implementation Plan

### Phase 1: Per-Client API Key Isolation (Priority: CRITICAL, ~4 hours)

**Goal**: Each client provides their own Gemini and WaveSpeed API keys. This removes the shared rate limit bottleneck and enables true parallel pipelines.

#### 1a. Add API key fields to `clients/_template/config.json` and `clients/bobe/config.json`

```json
"api_keys": {
  "gemini": "",
  "wavespeed_en": "",
  "wavespeed_ru": ""
}
```

- If a client's key is empty, fall back to the global env var (backwards-compatible)
- BoBe uses global keys by default (Rut manages them)
- New clients can optionally supply their own keys during onboarding

#### 1b. Update `scripts/client_config.py`

Add `get_api_key(client_id, service)`:
```python
def get_api_key(client_id: str, service: str) -> str:
    """Return client-specific API key, falling back to global env var."""
    config = load_config(client_id)
    client_key = config.get("api_keys", {}).get(service, "")
    if client_key:
        return client_key
    # Fallback to global env vars
    env_map = {
        "gemini": "GOOGLE_AI_API_KEY",
        "wavespeed_en": "WAVESPEED_API_KEY",
        "wavespeed_ru": "WAVESPEED_API_KEY",
    }
    return os.environ.get(env_map.get(service, ""), "")
```

#### 1c. Update consuming scripts

- `pipeline_runner.py`: Replace `GOOGLE_AI_API_KEY = os.environ.get(...)` with `get_api_key(client_id, "gemini")`
- `nano_banana.py`: Replace `WAVESPEED_API_KEY` lookup with `get_api_key(client_id, "wavespeed_en")`
- `wavespeed_img.py`: Replace `WAVESPEED_API_KEY` lookup with `get_api_key(client_id, "wavespeed_ru")`

#### 1d. Update `/onboard-client` command

Add question: "Do you want to provide your own Gemini and WaveSpeed API keys? (Optional — leave blank to use shared keys)"

---

### Phase 2: Deployment Serialization (Priority: CRITICAL, ~2 hours)

**Goal**: Prevent concurrent `gh-pages` pushes from overwriting each other.

#### 2a. Add GitHub Actions concurrency group to both workflow files

In `.github/workflows/weekly-pipeline.yml` and `.github/workflows/regenerate-item.yml`, add at the top level:

```yaml
concurrency:
  group: gh-pages-deploy
  cancel-in-progress: false
```

This queues deployments — if 3 clients trigger pipelines simultaneously, they process in order without clobbering each other. `cancel-in-progress: false` ensures no pipeline is dropped.

#### 2b. Separate content generation from deployment

Split both workflows into two jobs:
1. `generate` — runs the pipeline (parallelizable, no concurrency gate)
2. `deploy` — builds static site and pushes to `gh-pages` (serialized via concurrency group)

This means 5 clients can generate content simultaneously, but deployments are queued and orderly.

---

### Phase 3: Image CDN — Move Off GitHub Pages (Priority: HIGH, ~4 hours)

**Goal**: Images should not count against GitHub Pages bandwidth. Serve them from Cloudflare Pages or R2.

**Recommended approach: Cloudflare Pages (free tier)**

- GitHub Pages stays for HTML/JS (negligible bandwidth)
- Images moved to a separate Cloudflare Pages project (or R2 bucket)
- `config.json` `images_base_url` updated to Cloudflare URL per client

**Alternative (simpler)**: Keep GitHub Pages but add lazy loading + browser cache headers. At 5 clients, actual user traffic is low — the 100 GB limit is a soft limit and rarely enforced for small sites. Monitor actual usage before migrating.

**Recommended for now**: Monitor, don't migrate yet. Revisit at 5+ active clients.

---

### Phase 4: Client Self-Service Regen (Priority: HIGH, ~3 hours)

**Goal**: Clients can regenerate images and content directly from their dashboard without needing to know about GitHub PATs or internal infrastructure.

**Current state**: The regen buttons exist on the live dashboard but require the client to enter a GitHub PAT with `Actions: write` scope — this is a developer credential, not a user-friendly experience.

**Solution**: Proxy regen requests through a lightweight serverless function.

#### Option A: Cloudflare Worker (recommended, free tier)
- Client clicks Regen → hits `https://regen.content.rejiglabs.com/{client_id}/{topic_index}/{regen_type}`
- Cloudflare Worker validates the request (checks the client's session token)
- Worker calls the GitHub Actions API with the stored PAT (secret stored in Worker env)
- Client never sees the PAT

**Implementation**:
1. Create a Cloudflare Worker with the GitHub PAT stored as a secret
2. Add a simple auth check: verify the client session token matches the expected client_id
3. Update the dashboard's regen button JS to call the Worker URL instead of GitHub API directly
4. Remove the "Enter your GitHub PAT" prompt from the dashboard

#### Option B: Keep current PAT flow but generate scoped tokens per client
- Generate a read-only PAT per client with minimal scope
- Store in `clients/{client_id}/config.json` as `github_regen_token`
- Auto-inject into the built dashboard so the client never has to enter it
- Less infrastructure, less ideal security model

**Recommended**: Option A for production; Option B as an interim fix while implementing Option A.

---

### Phase 5: Credential Isolation (Priority: MEDIUM, ~2 hours)

**Goal**: Each client's login page only contains their own credentials, not all clients'.

**Current state**: `login.html` bakes in all clients' hashed credentials. If the repo is public or leaked, all clients' password hashes are exposed.

**Solution**: Per-client login pages at `/dashboard/{client_id}/login.html` that only include that client's credentials. The root `/login.html` can redirect based on URL or show a client selector.

---

### Phase 6: Image Retention Policy (Priority: LOW, ~1 hour)

**Goal**: Prevent unbounded storage growth.

- Add `--purge-older-than 90` flag to `build_static.py` that deletes image directories older than N days from `dist/`
- Add similar cleanup to `pipeline_runner.py` for `outputs/content/{client_id}/images/`
- Default retention: 90 days (12 weeks of content)

---

## Recommended Implementation Order

| Phase | What | Effort | Priority | Unlocks |
|-------|------|--------|----------|---------|
| 1 | Per-client API keys | 4 hrs | CRITICAL | Concurrent pipelines for 5-10 clients |
| 2 | Deployment serialization | 2 hrs | CRITICAL | No deployment race conditions |
| 4b | Auto-inject regen token | 2 hrs | HIGH | Client-friendly regen experience |
| 5 | Credential isolation | 2 hrs | MEDIUM | Client privacy |
| 3 | CDN for images | 4 hrs | LOW (monitor first) | Bandwidth at scale |
| 4a | Cloudflare Worker proxy | 3 hrs | LOW (if 4b sufficient) | Zero-friction regen |
| 6 | Retention policy | 1 hr | LOW | Storage hygiene |

**MVP for 5 clients**: Phase 1 + Phase 2 = ~6 hours. Everything else is optimization.

---

## Agent-Team Implementation Strategy

Implementation uses a team of 5 parallel Claude agents to compress wall-clock time. Agents are spawned via the Task tool in two waves due to the Phase 1a/1b → 1c dependency.

### Wave 1 — Agent 1 alone (foundational)

| Agent | Phase | Files |
|-------|-------|-------|
| 1 | Phase 1a+1b: Add `api_keys` schema to configs + add `get_api_key()` to `client_config.py` | `clients/_template/config.json`, `clients/bobe/config.json`, `scripts/client_config.py` |

Agent 1 must complete first because all consuming scripts (Wave 2, Agent 2) import `get_api_key()` from `client_config.py`.

### Wave 2 — Agents 2-5 in parallel (after Agent 1 completes)

| Agent | Phase | Files |
|-------|-------|-------|
| 2 | Phase 1c: Swap hardcoded env var lookups for `get_api_key()` calls | `scripts/pipeline_runner.py`, `scripts/nano_banana.py`, `scripts/wavespeed_img.py` |
| 3 | Phase 2: Add concurrency groups + split generate/deploy jobs | `.github/workflows/weekly-pipeline.yml`, `.github/workflows/regenerate-item.yml` |
| 4 | Phase 4b: Auto-inject per-client regen token into built dashboard | `scripts/build_static.py`, `clients/bobe/config.json` (add `github_regen_token` field) |
| 5 | Phase 5: Per-client credential isolation in login pages | `scripts/build_static.py` (generate per-client login), root `login.html` (client selector) |

### Dependency graph

```
Agent 1 (Phase 1a+1b)
    └── Agent 2 (Phase 1c)   ─┐
    Agent 3 (Phase 2)         ├── all independent of each other in Wave 2
    Agent 4 (Phase 4b)        ├──
    Agent 5 (Phase 5)        ─┘
```

---

## What Does NOT Need to Change

- Client discovery (already dynamic, O(N))
- Output directory structure (already isolated)
- Dashboard routing (already per-client)
- Excel workbook format (already 14-column bilingual)
- Airtable sync (already per-client opt-in)
- Onboarding flow (already template-driven)
- GitHub Actions parameterization (already accepts client_id)

---

## Summary

The platform's multi-client foundation is solid. The gaps are all operational — shared API keys, shared deployment target, and client UX friction. Fixing Phase 1 + 2 makes the platform reliable for 5-10 clients. The rest is polish and scale-prep for 10+ clients.
