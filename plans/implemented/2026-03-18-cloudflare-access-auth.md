# Plan: Cloudflare Access Authentication

**Created:** 2026-03-18
**Status:** Implemented
**Request:** Replace client-side SHA-256 authentication with Cloudflare Access for the deployed dashboard at content.rejiglabs.com

---

## Overview

### What This Plan Accomplishes

Replaces the current client-side SHA-256 auth (hashes baked into static HTML) with Cloudflare Access — Cloudflare's Zero Trust gateway — which intercepts requests at the network edge before any HTML is served. Phase 1 is pure configuration (no code). Phase 2 adds a Cloudflare Pages Function that reads the Access identity JWT and auto-routes clients directly to their dashboard without a second login.

### Why This Matters

The current SHA-256 hashed passwords (e.g., `bobe123`) are embedded in the page source and trivially brute-forceable. Any visitor with the URL can see the hash and crack a dictionary password in seconds. Cloudflare Access moves authentication to the network level, supports email one-time passcodes (no passwords to crack or forget), and is free for up to 50 users — a perfect fit for this small-client platform.

---

## Current State

### Relevant Existing Structure

- **`scripts/build_static.py`**: Generates credentials via `generate_credentials()` (line 64) — derives username `admin`, password `{client_id}123`, SHA-256 hashes it, and injects as `const CREDENTIALS = {{ credentials_json }}` into every generated `login.html`
- **`dist/login.html`**: Client-side `handleLogin()` function compares SHA-256 hash of entered password against baked-in credentials; stores session in `sessionStorage`
- **`dist/dashboard/bobe/index.html`** and all dashboard pages: Check `sessionStorage.getItem('dash_auth')` on load — redirect to `login.html` if absent
- **`dist/admin/index.html`**: Separate auth path — uses GitHub PAT stored in `sessionStorage` (not the SHA-256 system)
- **`intake/index.html`**: Public-facing onboarding form — **must remain unauthenticated**
- **Cloudflare Pages**: Site is already hosted at `content.rejiglabs.com` via `npx wrangler pages deploy dist --project-name bobe-content-dashboard`
- **`worker/wrangler.toml`**: Existing Cloudflare Worker for intake onboarding — confirms Cloudflare account is already active
- **`clients/bobe/config.json`**: Per-client config — will need an `auth.email` field added for email→client_id routing

### Gaps or Problems Being Addressed

1. **SHA-256 hash visible in page source**: Anyone with the URL can view-source and see the hash; `bobe123` is crackable instantly
2. **Passwords baked at build time**: Adding or changing client auth requires a full redeploy
3. **Client has to log in twice** (once via Access, once via the site form) in Phase 2 — eliminated by auto-routing Pages Function
4. **No audit trail**: No record of who accessed what and when
5. **sessionStorage sessions**: Lost on tab close; not shared across browser tabs

---

## Proposed Changes

### Summary of Changes

- **Phase 1 (no code — config only)**: Enable Cloudflare Access on the domain; create email OTP policy; exclude `/intake/*` from protection
- **Phase 2 (code)**: Add `functions/auth-route.js` Pages Function that reads CF Access JWT, maps email → client_id, and redirects; update client configs with `auth.email`; update `build_static.py` to generate a minimal auto-redirect login page; remove SHA-256 credential injection
- **Phase 3 (cleanup)**: Remove sessionStorage auth checks from dashboard pages (or keep as defense-in-depth); update reference docs and CLAUDE.md

### New Files to Create

| File Path | Purpose |
|-----------|---------|
| `functions/auth-route.js` | Cloudflare Pages Function: reads CF Access JWT, maps email → client_id, issues session cookie, redirects to correct dashboard |
| `reference/cloudflare-access-setup.md` | Step-by-step guide: Zero Trust dashboard config, Access Application, email OTP policy, bypass rules for `/intake/` |

### Files to Modify

| File Path | Changes |
|-----------|---------|
| `scripts/build_static.py` | Remove `generate_credentials()` and `{{ credentials_json }}` injection; replace `login.html` template with minimal auto-redirect page; add `auth_email` field read from client config |
| `clients/bobe/config.json` | Add `"auth": { "email": "adikari.rut@gmail.com" }` field |
| `clients/_template/config.json` | Add `"auth": { "email": "" }` field to template |
| `reference/github-actions-setup.md` | Add note: credentials section is now managed via Cloudflare Access (no longer baked at build time) |
| `CLAUDE.md` | Update auth description, add CF Access to deployment section, update credentials note |

### Files to Delete (if any)

None — changes are additive; existing credential system removed from `build_static.py` but no standalone file deleted.

---

## Design Decisions

### Key Decisions Made

1. **Email OTP (not OAuth/SSO)**: The simplest policy that requires zero client setup — clients just enter their email and receive a code. No Google/Microsoft account required.

2. **Exclude `/intake/*` from Access**: The intake form is public-facing — new clients fill it out before they have credentials. It must remain unauthenticated.

3. **Keep `/admin/*` inside Access**: The admin panel is already gated by GitHub PAT. Adding CF Access as an outer layer costs nothing and adds a layer.

4. **Pages Function for auto-routing (not a Worker)**: A Pages Function at `functions/auth-route.js` runs in the same Cloudflare Pages project — no separate Worker deployment needed. It intercepts requests to `/login` and reads the `CF_Authorization` cookie that Access injects.

5. **Email → client_id mapping in Pages Function env vars**: Store as `EMAIL_MAP` JSON string in Cloudflare Pages project environment variables (e.g., `{"adikari.rut@gmail.com": "bobe"}`). This avoids adding a KV namespace and keeps it manageable for small client counts.

6. **Keep sessionStorage checks as defense-in-depth**: Remove the SHA-256 password check but keep the `sessionStorage` presence check on dashboard pages. The Pages Function sets a session cookie on successful routing; dashboard pages verify it. This means a misconfigured CF Access policy doesn't expose raw content.

7. **Session cookie set by Pages Function**: On first visit post-CF-Access, the Pages Function reads the JWT, sets a `dash_session` cookie (httpOnly, SameSite=Lax, 8hr expiry), and redirects. Dashboard pages verify this cookie presence client-side (not the actual JWT — just the cookie as a session indicator).

### Alternatives Considered

- **Cloudflare Access + keep existing password login**: Two login steps, bad UX. Rejected.
- **One CF Access Application per client path** (`/dashboard/bobe/*` with bobe email allow-list): Clean isolation but requires managing N applications as clients grow. Rejected in favor of centralized email→client_id mapping.
- **Cloudflare Pages basic auth (`.htpasswd` style)**: Cloudflare Pages doesn't support native HTTP basic auth without a Worker. Rejected.
- **Keep SHA-256 auth, just strengthen passwords**: Doesn't fix the hash-in-source problem. Rejected.

### Open Questions

_All resolved._

| Question | Answer |
|----------|--------|
| BoBe client email | `adikari.rut@gmail.com` |
| Admin email (routes to `/admin/`) | `ruttherick@gmail.com` |
| Transition / grace period | Yes — keep old `sessionStorage` check alongside new `dash_routed` cookie for 2 weeks post-deploy |

---

## Parallel Execution Strategy

When running `/implement`, several steps are independent and can be executed concurrently using subagents. This reduces total wall-clock time.

### Parallelization Map

```
Step 1 (manual CF config) ─────────────────────── YOU do this in browser (no code)
Step 3 (CF Pages env vars) ────────────────────── YOU do this in browser (no code)

Step 2 (client configs)     ┐
Step 4 (functions/auth-route.js) ┤ ← PARALLEL — all independent, spawn 4 agents at once
Step 7 (reference doc)      ┤
Step 8 (CLAUDE.md update)   ┘

Step 5 + 6 (build_static.py) ─── SEQUENTIAL after above (same file, two related edits)

Step 9 (testing) ────────────────── LAST, after deploy
```

### Agent Split for `/implement`

| Agent | Tasks | Notes |
|-------|-------|-------|
| Agent A | Step 2 — update `clients/bobe/config.json` + `clients/_template/config.json` | Simple JSON edits |
| Agent B | Step 4 — create `functions/auth-route.js` | New file, self-contained |
| Agent C | Step 7 — create `reference/cloudflare-access-setup.md` | New file, self-contained |
| Agent D | Step 8 — update `CLAUDE.md` | Independent of code changes |
| Main thread | Steps 5+6 — update `build_static.py` (large file, two related edits in one pass) | Must be sequential; main thread handles to avoid merge conflicts |

Steps 1, 3, and 9 are manual (browser config and testing) — cannot be delegated to agents.

---

## Step-by-Step Tasks

### Step 1: Set Up Cloudflare Zero Trust (manual — no code)

Configure Cloudflare Access via the Zero Trust dashboard. This requires no code changes and can be done in ~15 minutes.

**Actions:**

1. Go to [dash.cloudflare.com](https://dash.cloudflare.com) → select account → **Zero Trust** (left sidebar)
2. If first time: complete Zero Trust onboarding (free plan, no credit card)
3. Navigate to **Access → Applications → Add an Application**
4. Select **Self-hosted**
5. Configure the application:
   - **Application name**: `Content Dashboard`
   - **Session duration**: `8 hours`
   - **Application domain**: `content.rejiglabs.com` (subdomain: `content`, domain: `rejiglabs.com`)
   - **Path**: leave blank (protects entire domain) OR set to `/*`
6. Click **Next** → Configure policies:
   - **Policy name**: `Allowed Clients`
   - **Action**: Allow
   - **Include rule**: `Emails` → add `adikari.rut@gmail.com` (BoBe client) and `ruttherick@gmail.com` (admin)
7. Click **Next** → Leave advanced settings default → **Save**
8. Add a **Bypass** rule for the intake form:
   - Go to the application → **Edit** → **Policies** → **Add a Policy**
   - **Policy name**: `Public Intake`
   - **Action**: Bypass
   - **Include rule**: `Everyone`
   - **Application domain path**: `intake/*`
   - Set policy **order** so Bypass runs before Allow

**Files affected:**
- None (Cloudflare dashboard only)

---

### Step 2: Add `auth.email` to Client Configs

Add an `auth.email` field to each client's config so the system knows which email maps to which client dashboard.

**Actions:**

- Open `clients/bobe/config.json` → add under the top-level object:
  ```json
  "auth": {
    "email": "adikari.rut@gmail.com"
  }
  ```
- Open `clients/_template/config.json` → add the same `"auth": { "email": "" }` field

**Files affected:**
- `clients/bobe/config.json`
- `clients/_template/config.json`

---

### Step 3: Set `EMAIL_MAP` Environment Variable in Cloudflare Pages

Store the email→client_id mapping in the Cloudflare Pages project environment so the Pages Function can read it.

**Actions:**

1. Go to [dash.cloudflare.com](https://dash.cloudflare.com) → **Pages** → `bobe-content-dashboard` → **Settings** → **Environment variables**
2. Add variable:
   - **Name**: `EMAIL_MAP`
   - **Value**: JSON string, e.g.:
     ```json
     {"adikari.rut@gmail.com": "bobe"}
     ```
   - Set for **Production** (and Preview if needed)
3. Add variable:
   - **Name**: `ADMIN_EMAIL`
   - **Value**: `ruttherick@gmail.com`
   - Set for **Production**
4. Click **Save**

**Files affected:**
- None (Cloudflare Pages dashboard only)

---

### Step 4: Create the Pages Function `functions/auth-route.js`

Create a Cloudflare Pages Function that intercepts requests to `/login`, reads the CF Access JWT, maps the email to a client_id, sets a session cookie, and redirects.

**Actions:**

Create `functions/auth-route.js` at the repo root with the following logic:
- Parse the `CF_Authorization` cookie from the request
- Decode the JWT payload (base64url decode the second segment — no signature verification needed since CF Access already validated it before this Function runs)
- Extract the `email` claim
- Look up email in `EMAIL_MAP` env var (parsed as JSON)
- If email matches a client_id: set `dash_session` cookie (httpOnly, SameSite=Lax, 8hr max-age) and redirect to `/dashboard/{client_id}/`
- If email matches admin email: redirect to `/admin/`
- If no match: return 403 with a plain message "Your email is not authorized. Contact support."
- If no JWT (Access not configured or local dev): fall through to serve static `login.html` normally

```javascript
// functions/auth-route.js
export async function onRequest(context) {
  const { request, env } = context;

  // Only intercept GET /login or /login.html
  const url = new URL(request.url);
  if (url.pathname !== '/login' && url.pathname !== '/login.html') {
    return context.next();
  }

  // Read CF Access JWT from cookie
  const cookieHeader = request.headers.get('Cookie') || '';
  const cfJwt = cookieHeader
    .split(';')
    .map(c => c.trim())
    .find(c => c.startsWith('CF_Authorization='))
    ?.split('=')[1];

  if (!cfJwt) {
    // No CF Access token — serve static login.html (local dev or misconfigured)
    return context.next();
  }

  // Decode JWT payload (segment 1, base64url)
  let email;
  try {
    const payload = cfJwt.split('.')[1];
    const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
    email = decoded.email;
  } catch (e) {
    return new Response('Invalid session. Please try again.', { status: 400 });
  }

  if (!email) {
    return new Response('No email in session. Contact support.', { status: 403 });
  }

  // Look up email in EMAIL_MAP
  let emailMap = {};
  try {
    emailMap = JSON.parse(env.EMAIL_MAP || '{}');
  } catch (e) {
    return new Response('Server configuration error.', { status: 500 });
  }

  const adminEmail = env.ADMIN_EMAIL || '';
  const adminEmails = adminEmail.split(',').map(e => e.trim()).filter(Boolean);

  // Admin routing
  if (adminEmails.includes(email)) {
    return redirect('/admin/', context);
  }

  // Client routing
  const clientId = emailMap[email];
  if (clientId) {
    return redirect(`/dashboard/${clientId}/`, context);
  }

  return new Response(
    `Your email (${email}) is not authorized. Contact your account manager.`,
    { status: 403, headers: { 'Content-Type': 'text/plain' } }
  );
}

function redirect(location, context) {
  // Set a lightweight session indicator cookie (httpOnly not available in Pages Functions
  // for client reads, but we use it purely as UX signal — CF Access JWT is the real auth)
  const headers = new Headers({
    Location: location,
    'Set-Cookie': `dash_routed=1; Path=/; Max-Age=28800; SameSite=Lax`,
  });
  return new Response(null, { status: 302, headers });
}
```

**Files affected:**
- `functions/auth-route.js` (new)

---

### Step 5: Update `build_static.py` — Remove SHA-256 Auth, Generate Auto-Redirect Login Page

Replace the credential injection system with a minimal login page that either auto-redirects (after CF Access sets the JWT) or shows a "Log in" button that triggers CF Access.

**Actions:**

- In `scripts/build_static.py`, find the `generate_credentials()` function (line ~64) and the `{{ credentials_json }}` template injection — remove both
- Replace the full `login.html` template section with a minimal redirect page:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Log In — {{ brand_name }}</title>
<!-- Auto-redirect: if CF Access JWT is present, Pages Function handles routing.
     This page is only shown if CF Access is not configured (local dev). -->
<meta http-equiv="refresh" content="0;url=/login">
</head>
<body>
<p>Redirecting...</p>
<script>window.location.replace('/login');</script>
</body>
</html>
```

- Keep the `sessionStorage` auth-check guards on dashboard pages **unchanged** (defense-in-depth — they now check for a `dash_routed` cookie OR the old `dash_auth` key for backward compatibility during transition)
- Remove the `{{ credentials_json }}` Jinja2 variable from the template rendering call

**Files affected:**
- `scripts/build_static.py`

---

### Step 6: Update Dashboard Pages — Accept Cookie-Based Session Signal

The dashboard pages currently check `sessionStorage.getItem('dash_auth')`. During transition, keep this check but also accept the `dash_routed` cookie as a valid session indicator so clients routed by the Pages Function aren't redirected back to login.

**Actions:**

In `build_static.py`, find the inline JS snippet (line ~990):
```javascript
var auth = sessionStorage.getItem('dash_auth');
if (!auth) { window.location.replace('login.html'); return; }
```

Replace with:
```javascript
var auth = sessionStorage.getItem('dash_auth');
var routed = document.cookie.split(';').some(c => c.trim().startsWith('dash_routed='));
if (!auth && !routed) { window.location.replace('/login'); return; }
```

This change appears in two places in `build_static.py` (dashboard page and settings page templates). Update both.

**Files affected:**
- `scripts/build_static.py`

---

### Step 7: Create `reference/cloudflare-access-setup.md`

Write a complete reference guide for setting up and managing Cloudflare Access for this platform.

**Actions:**

Create `reference/cloudflare-access-setup.md` with sections:
1. **Overview** — what CF Access does, why we use it, free tier limits (50 users)
2. **One-time setup** — Zero Trust dashboard walkthrough (mirrors Step 1 above with screenshots callouts)
3. **Adding a new client** — how to add their email to the Access policy + `EMAIL_MAP` env var
4. **Revoking access** — remove email from policy (instant effect, no redeploy needed)
5. **Testing** — how to verify login flow works in incognito
6. **Troubleshooting** — common issues: `intake/` bypass, JWT decode errors, email not in map
7. **Local development** — Pages Function doesn't run locally; existing Flask dashboard uses its own session system

**Files affected:**
- `reference/cloudflare-access-setup.md` (new)

---

### Step 8: Update `CLAUDE.md`

Reflect the new auth architecture in the workspace documentation.

**Actions:**

- **Deployment section** — replace:
  > "Credentials: Auto-generated from client IDs — no manual config or secrets required. Username: `admin`, password: `{client_id}123`..."

  With:
  > "Auth: Cloudflare Access (Zero Trust) gates the entire domain with email OTP. Client emails → client dashboards via Pages Function auto-routing. No passwords to manage or remember. Add/revoke clients via CF Zero Trust dashboard (instant, no redeploy). See `reference/cloudflare-access-setup.md`."

- **API Requirements table** — add row for Cloudflare Access:

  | Service | Env Var | Purpose |
  |---------|---------|---------|
  | Cloudflare Access | `EMAIL_MAP` (Pages env var) | Email → client_id routing for dashboard auth |

- **Scripts table** — remove `generate_credentials()` note, update `build_static.py` description

**Files affected:**
- `CLAUDE.md`

---

### Step 9: Test End-to-End

Validate the full flow before marking complete.

**Actions:**

1. Deploy the updated build: run `/deploy` to push updated `dist/` and `functions/` to Cloudflare Pages
2. Open `content.rejiglabs.com` in an incognito window
3. Confirm CF Access login screen appears (email field, not the old login form)
4. Enter an authorized email → receive OTP → enter code
5. Confirm auto-redirect to `/dashboard/bobe/` (or `/admin/` for admin email)
6. Confirm `intake/` is accessible without login (open `content.rejiglabs.com/intake/` in incognito)
7. Confirm an unauthorized email gets a 403 response (not a dashboard)
8. Confirm logout works: clear cookies → revisit dashboard → CF Access re-challenges

**Files affected:**
- None (validation only)

---

## Connections & Dependencies

### Files That Reference This Area

- `scripts/build_static.py` — generates `login.html` and `{{ credentials_json }}` injection
- `dist/login.html` — current auth implementation (regenerated on each deploy)
- `dist/dashboard/bobe/index.html` — sessionStorage auth guard (regenerated)
- `dist/admin/index.html` — separate GitHub PAT auth (not changed)
- `reference/github-actions-setup.md` — mentions auto-generated credentials
- `CLAUDE.md` — documents auth credentials pattern

### Updates Needed for Consistency

- `reference/github-actions-setup.md`: Remove or update the "Dashboard login credentials are auto-generated" section (line 22) — no longer applicable
- `clients/_template/config.json`: Add `auth.email` so new clients know to fill it in at onboarding
- `/onboard-client` command: Should prompt for client email as part of onboarding Q&A

### Impact on Existing Workflows

- **`/deploy`**: No change to deploy command itself. `functions/` directory at repo root is automatically picked up by Cloudflare Pages on `wrangler pages deploy dist`
- **`/weekly-pipeline`**: No change — pipeline generates content, not auth
- **GitHub Actions** (`weekly-pipeline.yml`, etc.): Build step calls `build_static.py` which no longer generates credential hashes — no secrets needed for auth
- **Local `/view-content`**: Flask dashboard uses its own session system — unaffected by CF Access changes
- **Admin panel**: Now behind CF Access (good) + still requires GitHub PAT for operations (unchanged)

---

## Validation Checklist

- [ ] CF Access Application created at `content.rejiglabs.com` in Zero Trust dashboard
- [ ] Email OTP policy with at least one authorized email (BoBe client email)
- [ ] `/intake/*` bypass policy in place and tested (accessible without login)
- [ ] `EMAIL_MAP` environment variable set in Cloudflare Pages project settings
- [ ] `functions/auth-route.js` created and present in repo root
- [ ] `build_static.py` no longer generates SHA-256 credentials or injects `CREDENTIALS` JSON
- [ ] Dashboard pages accept `dash_routed` cookie as valid session signal
- [ ] End-to-end login flow tested in incognito (email OTP → auto-redirect → correct dashboard)
- [ ] Unauthorized email receives 403 (not dashboard access)
- [ ] `reference/cloudflare-access-setup.md` created
- [ ] `CLAUDE.md` updated to reflect new auth architecture
- [ ] `clients/bobe/config.json` and `clients/_template/config.json` updated with `auth.email` field

---

## Success Criteria

The implementation is complete when:

1. A client visiting `content.rejiglabs.com` is challenged by CF Access (email OTP) — not shown the old username/password form
2. After entering their email OTP, they are automatically routed to their specific dashboard without any further login step
3. The intake form at `/intake/` remains publicly accessible without any login prompt
4. SHA-256 hashed passwords are no longer present in any generated HTML

---

## Notes

- **Transition period**: During the first 1-2 weeks after CF Access is enabled, keep the old `sessionStorage.getItem('dash_auth')` check alongside the new `dash_routed` cookie check. This ensures no disruption if someone has an active session. After the transition, the old check can be removed.
- **Free tier limits**: Cloudflare Access Zero Trust free plan includes 50 users and unlimited applications. More than sufficient for this platform.
- **JWT verification**: The Pages Function decodes the CF Access JWT but does not cryptographically verify it (no public key fetch). This is intentional — CF Access has already verified and issued the JWT at the network layer before the Function runs. Adding signature verification would require fetching the JWKS endpoint on every request, adding latency for no real security gain in this architecture.
- **Future: per-client login pages**: If clients need their own branded login (e.g., `bobe.rejiglabs.com` → auto-routes to BoBe dashboard), CF Access supports multiple hostnames per application and the Pages Function routing logic already handles this.
- **Future: `/onboard-client` update**: The Q&A should include "What email address should your client use to log in?" and write it to `clients/{id}/config.json` → `auth.email`. The onboarder then adds it to CF Access policy + `EMAIL_MAP` env var.

---

## Implementation Notes

**Implemented:** 2026-03-19

### Summary

- Created `functions/auth-route.js` — Cloudflare Pages Function that reads CF Access JWT, maps email → client_id via `EMAIL_MAP` env var, sets `dash_routed` cookie, and redirects to correct dashboard
- Created `reference/cloudflare-access-setup.md` — full reference guide including one-time setup, adding/revoking clients, updating BoBe email, testing, and troubleshooting
- Updated `clients/bobe/config.json` — added `auth.email: adikari.rut@gmail.com`
- Updated `clients/_template/config.json` — added `auth.email: ""` field
- Updated `scripts/build_static.py`:
  - Removed `import hashlib` and `generate_credentials()` function
  - Replaced `LOGIN_HTML` with minimal CF Access passthrough redirect page (no password fields, no SHA-256)
  - Removed `PER_CLIENT_LOGIN_HTML` and per-client login page generation entirely
  - Updated both dashboard and settings page auth guards to accept `dash_routed` cookie alongside `sessionStorage` (transition period grace)
  - Updated all `login.html` redirects to `/login` (Pages Function endpoint)
  - Updated logout to clear `dash_routed` cookie in addition to `sessionStorage`
  - Landing page "Log In" buttons updated from `login.html` to `/login`
  - Removed `credentials` param from `build_site()` signature
- Updated `CLAUDE.md` — auth description, API requirements table (Cloudflare Access row), build_static.py description
- Updated `reference/github-actions-setup.md` — replaced auto-generated credentials note with CF Access reference

### Deviations from Plan

- `PER_CLIENT_LOGIN_HTML` removed entirely (not just simplified) — no need to keep per-client login pages since CF Access routes globally
- Landing page nav links (`/login` references) also updated for consistency (plan didn't explicitly mention these)
- `functions/auth-route.js` uses `redirectWithCookie` helper (named differently from plan's `redirect` to be more descriptive)

### Issues Encountered

- `build_site()` was called with `credentials=credentials` keyword arg in `main()` — updated both the signature and the call site together
- `hashlib` import removed cleanly (only used for SHA-256 credential hashing)
