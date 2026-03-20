# Cloudflare Access Setup

Authentication for content.rejiglabs.com via Cloudflare Zero Trust (Access). Configured 2026-03-18.

---

## Overview

Cloudflare Access gates the entire content dashboard at the network edge before any request reaches the origin. Authentication uses **email OTP (one-time passcode)** — no passwords to manage or leak. Free tier supports 50 users and unlimited applications.

After a user authenticates, Cloudflare issues a signed JWT and attaches it to the request. A Cloudflare Pages Function (`functions/auth-route.js`) reads that JWT, extracts the email, maps it to a `client_id` via the `EMAIL_MAP` environment variable, and redirects to `/dashboard/{client_id}/`. Admin email routes to `/admin/`. The intake form is exempt — it has a bypass policy that keeps it public.

---

## Architecture

```
User visits content.rejiglabs.com
        │
        ▼
Cloudflare Access intercepts
        │
        ├── Path matches /intake/* → Bypass policy → request passes through (no auth)
        │
        └── All other paths → "Allowed Clients" policy
                │
                ▼
        Email OTP challenge
        (Cloudflare sends 6-digit code to entered email)
                │
                ▼
        JWT issued (CF_Authorization cookie, 8-hour session)
                │
                ▼
        Pages Function: functions/auth-route.js
                │
                ├── Decodes CF Access JWT → reads email claim
                ├── Looks up email in EMAIL_MAP env var
                ├── admin email → redirect to /admin/
                └── client email → redirect to /dashboard/{client_id}/
```

---

## One-Time Setup (already done)

Configured on 2026-03-18. Recorded here for reference if settings are ever reset or rebuilt.

### 1. Zero Trust Application

1. Go to **https://dash.cloudflare.com** → select your account → **Zero Trust** (left sidebar)
2. Navigate to **Access → Applications → Add Application → Self-hosted**
3. Configure:
   - **Application name**: Content Dashboard
   - **Session duration**: 8 hours
   - **Application domain**: `content.rejiglabs.com`
4. Click **Next**

### 2. Access Policies

Create two policies in this order (order matters — bypass must be evaluated first):

**Policy 1 — Public Intake (Bypass)**
| Field | Value |
|-------|-------|
| Policy name | Public Intake |
| Action | Bypass |
| Include | Everyone |
| Path | `intake/*` |

**Policy 2 — Allowed Clients (Allow)**
| Field | Value |
|-------|-------|
| Policy name | Allowed Clients |
| Action | Allow |
| Include | Emails: `adikari.rut@gmail.com`, `ruttherick@gmail.com` |

Click **Save application**.

### 3. Cloudflare Pages Environment Variables

Go to **https://dash.cloudflare.com → Pages → bobe-content-dashboard → Settings → Environment variables**.

Add the following (Production environment):

| Variable | Value |
|----------|-------|
| `EMAIL_MAP` | `{"adikari.rut@gmail.com": "bobe"}` |
| `ADMIN_EMAIL` | `ruttherick@gmail.com` |

`EMAIL_MAP` is a JSON object mapping authenticated client emails to their `client_id`. The admin email is checked separately — it routes to `/admin/` instead of a client dashboard.

---

## Adding a New Client

When a new client is onboarded and needs dashboard access:

1. **Get their login email** from the intake form or direct communication.

2. **Add to CF Access policy:**
   - Zero Trust → Access → Applications → Content Dashboard → Edit
   - Policies → Allowed Clients → Edit
   - Under Include → Emails → add the new email
   - Save

3. **Update EMAIL_MAP:**
   - Pages → bobe-content-dashboard → Settings → Environment variables
   - Edit `EMAIL_MAP` — add the new `"email": "client_id"` pair
   - Example: `{"adikari.rut@gmail.com": "bobe", "client@example.com": "acmecorp"}`
   - Save

4. **Update client config:**
   Add to `clients/{client_id}/config.json`:
   ```json
   "auth": {
     "email": "client@example.com"
   }
   ```

5. **No redeploy needed.** CF Access policy updates take effect immediately. The updated `EMAIL_MAP` takes effect on the next request after saving (no rebuild required).

---

## Updating BoBe Client Email

The BoBe client email (`adikari.rut@gmail.com`) may change. To update:

1. **CF Access policy:** Remove the old email, add the new one under Allowed Clients → Include → Emails
2. **EMAIL_MAP:** Edit the env var — update the key from old email to new email
3. **Client config:** Update `clients/bobe/config.json` → `auth.email`

No code redeploy required.

---

## Revoking Access

1. Remove the email from the CF Access policy (Allowed Clients → Include → Emails → delete)
2. Optionally remove the entry from `EMAIL_MAP` (prevents the "email not in map" error on any cached session)

Effect is immediate — the user will hit the CF Access challenge on their next request and be denied.

To invalidate an existing session before it expires: Zero Trust → Access → Active Sessions → revoke by user.

---

## Testing

Open a fresh **incognito window** and follow this sequence:

**Auth flow:**
1. Visit `https://content.rejiglabs.com`
2. You should see the Cloudflare Access email input screen (not the old username/password form)
3. Enter an authorized email
4. Check that email's inbox for the OTP code (arrives within ~30 seconds)
5. Enter the code
6. You should be auto-redirected to `/dashboard/{client_id}/` (or `/admin/` for the admin email)

**Intake bypass:**
1. In the same incognito window (logged out or before logging in), visit `https://content.rejiglabs.com/intake/`
2. The intake form should load without any CF Access challenge

---

## Troubleshooting

**"Your email is not authorized" error after OTP:**
The email passed CF Access (it's in the Allow policy) but is not in `EMAIL_MAP`. Add it to the Pages env var under the correct `client_id`.

**Intake form shows login screen:**
The Bypass policy is missing or ordered incorrectly. It must be listed above the Allow policy in the CF Access application's policy list. Edit the application and drag/reorder if needed.

**Dashboard redirects to /login after CF Access:**
The Pages Function is not setting the `dash_routed` cookie or is not running at all. Check:
- `functions/auth-route.js` exists at the repo root (not inside `dist/`)
- Deploying with `npx wrangler pages deploy dist` from the repo root, not from inside `dist/`
- The Pages project has the function deployed — check Pages → bobe-content-dashboard → Functions tab

**Pages Function not running at all:**
Wrangler must be run from the repo root so it detects the `functions/` directory. Running from inside `dist/` will deploy only static files with no functions.

**JWT decode error in function logs:**
The CF Access JWT format may have changed, or the function is reading the wrong cookie/header. Check the raw value of the `CF_Authorization` cookie in browser DevTools. CF Access JWTs are standard RS256-signed JWTs — decode at jwt.io to inspect claims.

---

## Local Development

Cloudflare Access only applies to the deployed site at content.rejiglabs.com. It does not intercept local traffic.

- **Local Flask** (`web_viewer.py` at `localhost:5001`) uses its own session system — unaffected by CF Access
- **Pages Function** (`functions/auth-route.js`) does not run locally with `wrangler pages dev` unless explicitly configured
- The legacy `sessionStorage` auth check in dashboard pages remains as defense-in-depth for local development scenarios

No local changes are needed to develop or test content features locally.
