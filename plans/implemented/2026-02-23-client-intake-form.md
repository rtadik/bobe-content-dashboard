# Plan: Client Intake Form + Automated Credential Email + /onboard-from-intake Command

**Created:** 2026-02-23
**Status:** Draft
**Request:** Build a shareable client onboarding intake form that clients fill out themselves. On submit: auto-generate dashboard login credentials, email them to the client (with login link), and output a structured intake JSON. Each form field shows a contextual tip on focus. Rut runs `/onboard-from-intake {path}` to generate all config files and write the client's credentials.

---

## Overview

### What This Plan Accomplishes

A polished static HTML intake form collects all onboarding answers from a client plus their email address. When submitted: the browser generates a random password, sends the client a welcome email via EmailJS (login URL + credentials), and downloads a structured intake JSON. Rut saves the JSON and runs `/onboard-from-intake {path}` — Claude generates all four config files and writes the client's credentials to `credentials.json` so they can log in immediately after the first deploy. Every field shows a small contextual tip box on focus, fading in next to the field with guidance.

### Why This Matters

The current `/onboard-client` workflow requires Rut to be the human relay. This plan eliminates that entirely: clients self-serve, receive their credentials automatically, and Rut triggers config generation from a JSON file. No back-and-forth, no delays, no manual credential management.

---

## Current State

### Relevant Existing Structure

```
.claude/commands/onboard-client.md    — 18-question Q&A → writes 4 config files
clients/_template/                    — Template dir (config.json, content-guidelines.md, context.md, keywords.md)
clients/_template/config.json         — Full config schema
admin/admin.css                       — CSS variables: --bg, --surface, --blue, --green, --text, etc.
scripts/build_static.py               — Copies static assets to dist/ during deploy
dist/                                 — Static site output (deployed to GitHub Pages)
credentials.json                      — Client login credentials (gitignored, SHA-256 hashed passwords)
reference/github-actions-setup.md     — Documents DASHBOARD_CREDENTIALS secret format
```

### Gaps or Problems Being Addressed

- `/onboard-client` requires live Q&A that Rut must personally conduct
- No way to send clients a self-service form link
- No automated credential delivery — Rut has to manually set up logins and communicate them
- No contextual guidance in the form — clients don't know how to answer technical questions

---

## Proposed Changes

### Summary of Changes

- Add `email` field to the intake form (required, for credential delivery)
- Create `intake/index.html` — full multi-section intake form with contextual tip boxes on field focus
- Create `intake/intake.css` — dark theme, tooltip styles, progress bar
- Create `intake/intake.js` — form logic, tip system, password generation, EmailJS send, JSON download
- Create `intake/intake-config.js` — EmailJS credentials config (gitignored, Rut fills once)
- Create `intake/intake-config.example.js` — template for the config (committed)
- Create `clients/intake/` directory — received intake JSONs (gitignored)
- Create `.claude/commands/onboard-from-intake.md` — reads intake JSON, generates config files, writes credentials
- Update `scripts/build_static.py` — copy `intake/` into `dist/intake/` during deploy
- Update `CLAUDE.md` — document new command, workflow, and files
- Update `.gitignore` — ignore `clients/intake/*.json` and `intake/intake-config.js`

### New Files to Create

| File Path | Purpose |
|---|---|
| `intake/index.html` | Multi-section intake form, all questions, tip system, EmailJS integration |
| `intake/intake.css` | Dark theme styles, tooltip/tip box, progress bar, mobile responsive |
| `intake/intake.js` | Form logic: tips, validation, password gen, email send, JSON download |
| `intake/intake-config.js` | EmailJS keys + dashboard base URL (gitignored, filled by Rut once) |
| `intake/intake-config.example.js` | Template/example of intake-config.js (committed, safe to share) |
| `clients/intake/.gitkeep` | Tracks directory without committing JSON files |
| `.claude/commands/onboard-from-intake.md` | New Claude command: reads intake JSON, generates all config + credentials |

### Files to Modify

| File Path | Changes |
|---|---|
| `scripts/build_static.py` | Copy `intake/` → `dist/intake/` during static build |
| `CLAUDE.md` | Add `/onboard-from-intake`, `intake/`, workflow, EmailJS setup note |
| `.gitignore` | Add `clients/intake/*.json` and `intake/intake-config.js` |

### Files to Delete (if any)

None.

---

## Design Decisions

### Key Decisions Made

1. **EmailJS for automated email — no backend required**: EmailJS sends emails directly from the browser via their API. Free tier: 200 emails/month. Requires a one-time account setup (Service + Template + Public Key). Rut sets these values in `intake/intake-config.js` (gitignored). No server, no API gateway, no cost.

2. **Password follows a fixed deterministic pattern — `{client_id}123`**: No random generation needed. Client credentials are always: username = `{client_id}`, password = `{client_id}123` (e.g., `rejiglabs` / `rejiglabs123`). Admin credentials are fixed: username = `admin`, password = `admin123`. The password is derived at submit time from the `client_id` field value — no storage in the intake JSON needed. The email sends these exact credentials.

3. **Credentials written by `/onboard-from-intake`**: The command derives the password (`{client_id}123`), SHA-256 hashes it, and writes `credentials.json["clients"][client_id]`. Admin credentials (`admin` / `admin123`) are written once during initial setup and not touched during client onboarding. Rut runs `/deploy` after onboarding to publish updated credentials.

4. **Contextual tip boxes via `data-tip` attributes**: Every `<input>` and `<textarea>` gets a `data-tip="..."` attribute containing a short, friendly tip for that specific field. JS adds a focus event listener to all fields — on focus, a small `<div class="tip-box">` fades in adjacent to the field showing the tip. On blur, it fades out. The tip box is absolutely positioned to the right on desktop, below on mobile.

5. **`intake-config.js` is gitignored; `intake-config.example.js` is committed**: The config file contains EmailJS keys and the dashboard base URL. It must never be committed. The example file shows the structure so it's easy to set up.

6. **Form has 9 sections** (was 8 — added Contact section for email): Contact, About Your Business, Audience, Voice & Messaging, Platforms & Languages, Keywords & Community, Content & CTAs, Brand & Visuals, Content Delivery.

8. **Static form also works as a local file**: Clients can open `intake/index.html` directly in their browser without a server. EmailJS works from `file://` as long as the keys are set. The hosted URL (`/intake/`) is the primary share method but not required.

### Alternatives Considered

- **Formspree / Netlify Forms**: Handles form submission but email customization is limited and it adds a third-party dependency. Rejected.
- **Generate credentials server-side**: Would require a backend or serverless function. Overkill for this scale. Rejected.
- **Show tips as static hint text below every field**: Clutters the form. Contextual on-focus tips keep it clean. Accepted approach.
- **Store password hash in intake JSON instead of plaintext**: Would prevent `/onboard-from-intake` from doing anything useful with it (can't reverse a hash). Plaintext in gitignored file is acceptable given the threat model.

### Open Questions (if any)

None — design is fully specified.

---

## Step-by-Step Tasks

### Step 1: Create `clients/intake/` directory and update `.gitignore`

**Actions:**

- Create `clients/intake/.gitkeep`
- Add to `.gitignore`:
  ```
  clients/intake/*.json
  intake/intake-config.js
  ```

**Files affected:** `clients/intake/.gitkeep`, `.gitignore`

---

### Step 2: Create `intake/intake-config.example.js`

A committed template showing the config structure that Rut fills in once.

**Content:**

```js
// intake-config.js — EmailJS credentials and dashboard URL
// Copy this file to intake-config.js and fill in your values.
// intake-config.js is gitignored and must never be committed.

window.INTAKE_CONFIG = {
  emailjs: {
    publicKey:   "YOUR_EMAILJS_PUBLIC_KEY",   // from emailjs.com → Account → API Keys
    serviceId:   "YOUR_EMAILJS_SERVICE_ID",   // from emailjs.com → Email Services
    templateId:  "YOUR_EMAILJS_TEMPLATE_ID"   // from emailjs.com → Email Templates
  },
  dashboardBaseUrl: "https://rtadik.github.io/bobe-content-dashboard"
  // Login URL sent to client will be: {dashboardBaseUrl}/login.html
};
```

**Files affected:** `intake/intake-config.example.js`

---

### Step 3: Create `intake/intake.css`

Dark theme stylesheet matching the admin panel. Key additions beyond the original plan: tooltip/tip box styles.

**Key CSS additions:**

```css
/* Tip box — fades in on field focus */
.field-wrapper { position: relative; }

.tip-box {
  position: absolute;
  left: calc(100% + 12px);
  top: 0;
  width: 220px;
  background: var(--surface3);
  border: 1px solid var(--border2);
  border-radius: var(--radius-sm);
  padding: 0.75rem 1rem;
  font-size: 0.78rem;
  color: var(--muted2);
  line-height: 1.5;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s ease;
  z-index: 10;
}

.tip-box::before {
  content: "💡";
  display: block;
  margin-bottom: 0.3rem;
  font-size: 0.9rem;
}

.tip-box.visible { opacity: 1; }

/* Mobile: tip box goes below the field */
@media (max-width: 900px) {
  .tip-box {
    position: static;
    width: 100%;
    margin-top: 0.5rem;
    left: auto;
  }
}

/* Progress bar */
.progress-bar { display: flex; gap: 4px; margin-bottom: 2rem; }
.progress-step { flex: 1; height: 4px; background: var(--surface2); border-radius: 2px; transition: background 0.3s; }
.progress-step.active { background: var(--blue); }
.progress-step.done { background: var(--green); }
```

**Full styles also include:** section cards, labels, hint text, inputs, textareas, color pickers, checkboxes, submit button, success panel, email status indicator.

**Files affected:** `intake/intake.css`

---

### Step 4: Create `intake/index.html`

Full intake form. 9 sections. Each field wrapped in `.field-wrapper` with a `.tip-box` sibling. EmailJS loaded from CDN. Progress bar at top.

**HTML structure:**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Client Intake Form</title>
  <link rel="stylesheet" href="intake.css">
</head>
<body>
  <div class="container">
    <header>
      <h1>Client Intake Form</h1>
      <p class="subtitle">Tell us about your brand. This takes about 10-15 minutes. We'll email you your login credentials when you're done.</p>
      <div class="progress-bar" id="progressBar"><!-- 9 steps --></div>
    </header>

    <form id="intakeForm">

      <!-- Section 1: Contact -->
      <!-- Section 2: About Your Business -->
      <!-- Section 3: Your Audience -->
      <!-- Section 4: Voice & Messaging -->
      <!-- Section 5: Platforms & Languages -->
      <!-- Section 6: Keywords & Community -->
      <!-- Section 7: Content & CTAs -->
      <!-- Section 8: Brand & Visuals -->
      <!-- Section 9: Content Delivery (Optional) -->

      <button type="submit" class="btn-submit">Submit — Send My Credentials</button>
    </form>

    <!-- Success panel (hidden until submit) -->
    <div class="success-panel" id="successPanel">
      <h2>You're all set!</h2>
      <p id="successMsg">Your login credentials have been sent to <strong id="clientEmail"></strong>.</p>
      <p class="hint">Also save your intake file below — your agency partner needs it to complete setup.</p>
      <div class="success-actions">
        <button onclick="downloadJSON()" class="btn-download">Download Intake File</button>
        <button onclick="copyJSON()" class="btn-copy">Copy to Clipboard</button>
      </div>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/@emailjs/browser@4/dist/email.min.js"></script>
  <script src="intake-config.js"></script>
  <script src="intake.js"></script>
</body>
</html>
```

**Full question-to-field mapping (with tip text):**

```
Section 1: Contact
  email            email input     "Your email address"
                   tip: "We'll send your dashboard login credentials here. Use a work email you check regularly."

Section 2: About Your Business
  client_id        text input      "Your unique ID (lowercase, no spaces — e.g. acmecrypto)"
                   tip: "This becomes your username and your dashboard URL path. Use your brand name, all lowercase, no spaces. Example: if your brand is Acme Crypto, use 'acmecrypto'."
  display_name     text input      "Brand display name"
                   tip: "How your brand name appears in content and on your dashboard. Capitalization matters — e.g. 'Acme Crypto', not 'acmecrypto'."
  website          url input       "Website URL"
                   tip: "Your main website. Include https://. This is used in CTAs and content links."
  tagline          text input      "One-line tagline"
                   tip: "One sentence that captures what you do. Think of it as your Twitter bio or elevator pitch. Example: 'Automated crypto yield for busy investors.'"
  description      textarea        "What does your product/service do? (2-3 sentences)"
                   tip: "Explain it like you're talking to a smart friend who doesn't know your industry. What problem does it solve? How does it work? What does the user get?"

Section 3: Your Audience
  audience_age     text input      "Age range of your target audience"
                   tip: "E.g. '25-40' or '18-35'. Be honest — this shapes the tone and vocabulary of all content."
  audience_situation textarea      "What's their current situation? What are they struggling with?"
                   tip: "Describe where they are right now, before they found you. E.g. 'They're spending hours manually trading crypto and still losing money.' The more specific, the better."
  pain_points      textarea        "Top 2-3 pain points (one per line)"
                   tip: "What frustrates them most? What keeps them up at night? Each line = one pain point. E.g. 'Emotional trading decisions / No time to manage positions / Don't trust black-box yield products'"
  desired_outcome  textarea        "What do they want instead?"
                   tip: "Describe their ideal situation after using your product. What does success look like for them?"
  differentiators  textarea        "Why do customers choose you over alternatives? (top 2-3, one per line)"
                   tip: "What makes you different from other options? Think: what do your best customers say when they recommend you? Each line = one differentiator."

Section 4: Voice & Messaging
  tone_adjectives  text input      "Brand tone in 3-4 adjectives"
                   tip: "E.g. 'direct, educational, no-hype, approachable'. These guide every piece of content generated. Think about what it feels like to read your brand."
  tone_description textarea        "Expand on the tone. What does it NOT sound like?"
                   tip: "E.g. 'We explain things clearly without jargon. We never hype or promise guaranteed results. We don't sound like a startup trying too hard to be cool.' Contrasts are as useful as positives."
  content_avoid    textarea        "What should content always avoid? (one per line)"
                   tip: "Specific phrases, claim types, or topics that are off-brand or legally risky. E.g. 'guaranteed returns / competitor comparisons / overly technical jargon / FOMO language'"
  messaging_pillars textarea       "2-4 core beliefs you want your audience to hold (one per line)"
                   tip: "What do you want people to think of when they think of your brand? E.g. 'This platform is transparent and auditable / Automation beats emotional trading / You don't need to be an expert to earn yield'"

Section 5: Platforms & Languages
  platforms        checkboxes      Twitter/X, Telegram, LinkedIn, Instagram
                   tip: "Select all platforms you want content generated for. Twitter/X and Telegram are fully supported. LinkedIn and Instagram use the same copy format with minor adjustments."
  languages        checkboxes      English, Russian
                   tip: "English is always included. Russian is built into the pipeline — all content gets auto-translated and Russian-specific images are generated. Other languages require custom setup."

Section 6: Keywords & Community
  keywords         textarea        "8-12 terms your audience uses online (one per line)"
                   tip: "These filter scraped social media posts to find relevant trending topics for your content. Think: what would your ideal customer type into Twitter search? E.g. 'crypto yield / automated trading / DCA strategy / passive income crypto'"
  negative_keywords textarea       "Terms that indicate spam or off-topic content (one per line)"
                   tip: "Posts containing these words will be filtered out during scraping. E.g. 'giveaway / airdrop / get rich quick / NFT mint / pump'. When in doubt, include it."
  subreddits       textarea        "Reddit communities your audience uses (no r/ prefix, one per line)"
                   tip: "Where does your audience hang out on Reddit? E.g. 'CryptoCurrency / algotrading / personalfinance / investing'. We scrape these for trending discussion topics."

Section 7: Content & CTAs
  cta_examples     textarea        "2-3 calls-to-action for content (one per line)"
                   tip: "What action do you want readers to take? Include the full CTA text and URL. E.g. 'Start earning yield today: bobe.app / Join 10,000 users: bobe.app/signup / See how it works: bobe.app/demo'"
  hashtags         textarea        "2-4 brand hashtags (include #, one per line)"
                   tip: "Hashtags that belong to your brand and will appear consistently in content. E.g. '#BoBe / #BoBeApp / #AutomatedYield'. Keep it to 2-4 — quality over quantity."

Section 8: Brand & Visuals
  primary_color    color input     "Primary brand color"
                   tip: "Your main brand color — used as the dominant background tone in generated images. Click the color swatch to pick, or type a hex code like #1a1a2e."
  accent_color     color input     "Accent color"
                   tip: "Your highlight or call-to-action color. Used for glowing elements, buttons, and key visual accents in generated images."
  text_color       color input     "Text color"
                   tip: "Usually white (#ffffff) or near-white. This is the primary text color used in generated image banners."
  mascot           textarea        "Describe your mascot or brand character"
                   tip: "Describe in detail: species/type, appearance, colors, style, distinguishing features. E.g. 'A small friendly robot with a glowing blue chest panel, rounded edges, and a calm expression. Pixel art style, dark metallic body.' If you have no mascot, write 'none' and we'll use a clean banner style."

Section 9: Content Delivery (Optional)
  airtable_enabled radio           Yes / No
                   tip: "If Yes, all generated content (copy, hashtags, image links) will automatically sync to an Airtable base where you can review, approve, and track status. Free Airtable account required. If No, content is delivered as an Excel file."
  airtable_base_id text input      "Airtable Base ID (shown only if Yes selected)"
                   tip: "Found in your Airtable base URL: airtable.com/{BASE_ID}/... — starts with 'app'. See the setup guide your partner will send for instructions."
```

**Files affected:** `intake/index.html`

---

### Step 5: Create `intake/intake.js`

Full form logic. Four main responsibilities: tip system, form validation, credential generation + email send, JSON assembly + download.

**Actions — Tip System:**

```js
// On page load, attach focus/blur listeners to all fields with data-tip
document.querySelectorAll('[data-tip]').forEach(field => {
  const wrapper = field.closest('.field-wrapper');
  const tipBox = wrapper?.querySelector('.tip-box');
  if (!tipBox) return;
  field.addEventListener('focus', () => tipBox.classList.add('visible'));
  field.addEventListener('blur',  () => tipBox.classList.remove('visible'));
});
```

**Actions — Password Derivation:**

```js
function derivePassword(clientId) {
  return `${clientId}123`;
}
```

Password is always `{client_id}123`. No randomness — deterministic, easy for clients to remember, and Rut always knows what it is. Admin credentials are fixed separately (`admin` / `admin123`) and not touched during this flow.

**Actions — Email Send via EmailJS:**

```js
async function sendCredentialEmail({ email, displayName, clientId, password, loginUrl }) {
  emailjs.init(window.INTAKE_CONFIG.emailjs.publicKey);
  return emailjs.send(
    window.INTAKE_CONFIG.emailjs.serviceId,
    window.INTAKE_CONFIG.emailjs.templateId,
    {
      to_email:     email,
      to_name:      displayName,
      client_id:    clientId,
      password:     password,
      login_url:    loginUrl,
      dashboard_url: `${window.INTAKE_CONFIG.dashboardBaseUrl}/dashboard/${clientId}/`
    }
  );
}
```

**EmailJS Template variables** (Rut configures in EmailJS dashboard):
- `{{to_name}}` — client display name
- `{{to_email}}` — recipient
- `{{client_id}}` — their username
- `{{password}}` — their temporary password
- `{{login_url}}` — full login URL
- `{{dashboard_url}}` — direct link to their dashboard (post-login)

**Actions — Form Submit Handler:**

```js
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!validateForm()) return;

  const password = generatePassword();
  const loginUrl = `${window.INTAKE_CONFIG.dashboardBaseUrl}/login.html`;

  // Show sending state
  submitBtn.textContent = 'Sending credentials...';
  submitBtn.disabled = true;

  const clientId = getValue('client_id');
  const password = derivePassword(clientId);

  try {
    await sendCredentialEmail({
      email: getValue('email'),
      displayName: getValue('display_name'),
      clientId,
      password,
      loginUrl
    });
    intakeData = buildIntakeJSON();
    showSuccessPanel();
  } catch (err) {
    // EmailJS failed — show credentials in panel so client can note them down
    intakeData = buildIntakeJSON();
    showSuccessPanel({ emailFailed: true, clientId, password });
  }
});
```

**Actions — JSON Assembly (`buildIntakeJSON`):**

Output schema (same as before, with two additions):

```json
{
  "intake_version": "1.0",
  "submitted_at": "2026-02-23T12:00:00Z",
  "contact": {
    "email": "..."
  },
  "client_id": "...",
  "display_name": "...",
  "website": "...",
  "tagline": "...",
  "description": "...",
  "audience": { ... },
  "differentiators": [...],
  "voice": { ... },
  "platforms": [...],
  "languages": [...],
  "scraping": { ... },
  "content": { ... },
  "brand": { ... },
  "airtable": { ... }
}
```

**Actions — Success Panel:**

- Show `#successPanel`, hide `#intakeForm`
- Set `#clientEmail` to the email value
- If EmailJS failed: show a warning with the generated password visible so they can note it down, and a message "Email delivery failed — please save your credentials from the downloaded file"
- "Download Intake File" button: triggers `{client_id}-intake.json` download
- "Copy to Clipboard" button: copies JSON string

**Files affected:** `intake/intake.js`

---

### Step 6: Create `.claude/commands/onboard-from-intake.md`

New Claude command that reads intake JSON and generates all config files + writes credentials.

**Key additions vs original plan:**

- After writing config files (Phase 3), add a **Phase 3f — Write Credentials**:
  ```
  Read credentials.json (or create it if missing).
  SHA-256 hash the plaintext password from intake.credentials.generated_password.
  Add entry: credentials.json[client_id] = { password_hash, display_name, email }
  Save credentials.json.
  Print: "Credentials written for {display_name}. Run /deploy to publish the updated credentials."
  ```

- After credentials are written, remind Rut to delete the intake JSON:
  ```
  Print: "SECURITY NOTE: Delete clients/intake/{client_id}-intake.json — it contains a plaintext password."
  ```

**Full command structure:**

```markdown
# Onboard Client from Intake

> Read a completed client intake JSON file and generate all client config files + credentials in one pass.

## Variables

intake_path: $ARGUMENTS (required — path to the intake JSON, e.g. clients/intake/rejiglabs-intake.json)

## Instructions

### Phase 1 — Read Intake File
Read JSON at {intake_path}. Validate required fields. Extract client_id, display_name, email, generated_password.

### Phase 2 — Derive Missing Fields
Same derivation rules as /onboard-client Phase 3 (surface_color, background_gradient, style_presets, etc.)

### Phase 3 — Copy Template and Write All Files
3a. cp -r clients/_template clients/{client_id}
3b. Write config.json
3c. Write content-guidelines.md
3d. Write context.md
3e. Write keywords.md
3f. Write credentials:
    - Derive password: `{client_id}123`
    - Read credentials.json (create if missing: {"clients": {}, "admin": {"password_hash": sha256("admin123")}})
    - SHA-256 hash: credentials.clients[client_id] = { password_hash: sha256("{client_id}123"), display_name, email }
    - Save credentials.json
    - Print: "Credentials written for {display_name} — username: {client_id}, password: {client_id}123"
    - Print: "Admin credentials unchanged — username: admin, password: admin123"

### Phase 4 — Airtable (if enabled)
Same as /onboard-client Phase 4.

### Phase 5 — Verify and Activate
5a. Config validation
5b. Ask about active client
5c. Show directory
5d. Print completion summary including credentials summary (username/password in plaintext for Rut's reference)
```

**Files affected:** `.claude/commands/onboard-from-intake.md`

---

### Step 7: EmailJS Setup — One-Time Configuration

This is a setup task for Rut, documented in the plan and referenced in the command.

**Steps Rut must complete once:**

1. Go to [emailjs.com](https://emailjs.com) → sign up (free, 200 emails/month)
2. Add an **Email Service**: connect Gmail, Outlook, or any SMTP. Note the **Service ID**.
3. Create an **Email Template** with this content:
   ```
   Subject: Your {display_name} Dashboard Access

   Hi {{to_name}},

   Your content dashboard is ready. Here are your login credentials:

   Username: {{client_id}}
   Password: {{password}}

   Login here: {{login_url}}

   After logging in, you'll be taken directly to your dashboard:
   {{dashboard_url}}

   This is a temporary password. You can request a change at any time.

   — The team
   ```
   Note the **Template ID**.
4. Go to Account → API Keys → note the **Public Key**.
5. Copy `intake/intake-config.example.js` to `intake/intake-config.js`
6. Fill in the three keys + dashboard base URL
7. Run `/deploy` — the intake form at `/intake/` will now send emails

**Add to `reference/` a new file:** `reference/emailjs-setup.md` documenting these steps.

**Files affected:** `intake/intake-config.js` (created by Rut, gitignored), `reference/emailjs-setup.md`

---

### Step 8: Create `reference/emailjs-setup.md`

Permanent setup guide for EmailJS, analogous to `reference/airtable-client-setup.md`. Written during implementation.

**Files affected:** `reference/emailjs-setup.md`

---

### Step 9: Update `scripts/build_static.py`

**Actions:**

- After existing asset copy steps, add:
  ```python
  # Copy intake form
  intake_src = Path('intake')
  if intake_src.exists():
      shutil.copytree(intake_src, dist / 'intake', dirs_exist_ok=True)
      # Never copy intake-config.js — it contains EmailJS keys
      config_in_dist = dist / 'intake' / 'intake-config.js'
      if config_in_dist.exists():
          config_in_dist.unlink()
  ```
- The `intake-config.example.js` is committed and will deploy (it contains no real keys, just the template)

**Files affected:** `scripts/build_static.py`

---

### Step 10: Update `CLAUDE.md`

**Actions:**

- Add `/onboard-from-intake` to Commands section
- Add `intake/` and `clients/intake/` to Workspace Structure
- Add `onboard-from-intake.md` to the `.claude/commands/` listing
- Add `reference/emailjs-setup.md` to the reference listing
- Add note about EmailJS one-time setup in API Requirements table

**Files affected:** `CLAUDE.md`

---

### Step 11: Update `.gitignore`

**Actions:**

```
# Intake JSONs (may contain client PII + plaintext passwords)
clients/intake/*.json

# EmailJS config (contains API keys)
intake/intake-config.js
```

**Files affected:** `.gitignore`

---

### Step 12: Test the full workflow end-to-end

**Actions:**

1. Set up EmailJS (Step 7) and create `intake/intake-config.js`
2. Open `intake/index.html` locally in browser
3. Focus several fields — verify tip boxes fade in and out
4. Submit with empty required fields — verify validation errors
5. Fill the form fully with Rejig Labs test data, submit
6. Verify email is received at the test address with correct credentials and login URL
7. Verify JSON downloads as `rejiglabs-intake.json` with all fields + `credentials.generated_password`
8. Save to `clients/intake/rejiglabs-intake.json`
9. Run `/onboard-from-intake clients/intake/rejiglabs-intake.json`
10. Verify all 4 config files created with no placeholders
11. Verify `credentials.json` has `rejiglabs` entry with hashed password
12. Run config validation: `python -c "import sys; sys.path.insert(0,'scripts'); from client_config import load_config; c=load_config('rejiglabs'); print(c['display_name'])"`
13. Run `/deploy` — verify `dist/intake/index.html` exists, `dist/intake/intake-config.js` does NOT exist
14. Verify login works with generated credentials at the deployed URL

---

## Connections & Dependencies

### Files That Reference This Area

- `.claude/commands/onboard-client.md` — parallel command, same output files
- `scripts/client_config.py` — reads config files generated by both commands
- `scripts/build_static.py` — deploys the form
- `credentials.json` — written by `/onboard-from-intake`
- `CLAUDE.md` — documents all commands

### Updates Needed for Consistency

- `CLAUDE.md` must reflect new command, files, and EmailJS dependency
- `reference/` must include `emailjs-setup.md`

### Impact on Existing Workflows

- `/onboard-client` unchanged
- The form is additive — new route `/intake/` on the deployed dashboard
- `credentials.json` is now also written by `/onboard-from-intake` (was only written manually or by `/deploy` setup)

---

## Validation Checklist

- [ ] `intake/index.html` opens locally, all 9 sections render
- [ ] Tip boxes fade in on field focus, fade out on blur, work on mobile (appear below)
- [ ] Validation errors show on empty required-field submit
- [ ] EmailJS sends credential email when form submits (real credentials, correct login URL)
- [ ] Email subject, body, and variables render correctly from template
- [ ] Success panel shows after email send; shows email address
- [ ] If EmailJS fails, fallback panel shows generated password + download prompt
- [ ] JSON downloads as `{client_id}-intake.json` with all fields including `credentials.generated_password`
- [ ] `/onboard-from-intake clients/intake/test-intake.json` generates all 4 config files
- [ ] `credentials.json` updated with SHA-256 hashed password for the client
- [ ] No placeholder text in any generated config file
- [ ] `build_static.py` copies `intake/` but strips `intake-config.js` from `dist/`
- [ ] `clients/intake/*.json` and `intake/intake-config.js` are gitignored
- [ ] `CLAUDE.md` updated with new command and file structure
- [ ] `reference/emailjs-setup.md` exists with complete setup instructions

---

## Success Criteria

The implementation is complete when:

1. Rut can send `https://rtadik.github.io/bobe-content-dashboard/intake/` to a new client, they fill it out in 10-15 minutes, and receive an email with their dashboard login credentials automatically
2. `/onboard-from-intake clients/intake/{client_id}-intake.json` generates all four config files with zero placeholders AND writes the client's hashed credentials to `credentials.json`
3. The client can log in at `/login.html` with the emailed credentials and reach their dashboard immediately after Rut runs `/deploy`

---

## Notes

- **EmailJS free tier**: 200 emails/month. Upgrade to paid ($15/month) if volume grows.
- **Credential pattern**: Client username = `{client_id}`, password = `{client_id}123`. Admin username = `admin`, password = `admin123`. Only SHA-256 hashes are stored in `credentials.json` — never plaintext.
- **Future enhancement**: Save form draft to `localStorage` so clients can return. Not in scope.
- **Future enhancement**: Auto-trigger `/onboard-from-intake` via GitHub Actions webhook on form submit. Would require exposing a PAT. Out of scope.
