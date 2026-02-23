# EmailJS Setup Guide

> One-time setup for the client intake form credential email system. After setup, clients who submit the intake form at `/intake/` will automatically receive their dashboard login credentials by email.

---

## What This Does

When a client submits the intake form, their browser sends a credential email via EmailJS — no backend required. The email contains their username, password, and login URL. EmailJS free tier: 200 emails/month.

---

## Step 1: Create an EmailJS Account

1. Go to [https://www.emailjs.com](https://www.emailjs.com) and sign up for a free account.

---

## Step 2: Add an Email Service

1. In the EmailJS dashboard, go to **Email Services**.
2. Click **Add New Service**.
3. Choose your email provider (Gmail, Outlook, or custom SMTP).
4. Follow the connection steps (Gmail requires OAuth; Outlook is simpler).
5. Give it a name (e.g. "RT Content Platform").
6. **Note the Service ID** — looks like `service_xxxxxxx`.

---

## Step 3: Create an Email Template

1. Go to **Email Templates** → **Create New Template**.
2. Set the **Subject**: `Your {{display_name}} Dashboard Access`
3. Set the **Body**:

```
Hi {{to_name}},

Your content dashboard is ready. Here are your login credentials:

Username: {{client_id}}
Password: {{password}}

Login here: {{login_url}}

After logging in, you'll be taken directly to your dashboard:
{{dashboard_url}}

This is your permanent password. Contact your partner if you need it changed.

— The team
```

4. Set **To Email**: `{{to_email}}`
5. Set **Reply To**: your email address
6. Save the template.
7. **Note the Template ID** — looks like `template_xxxxxxx`.

---

## Step 4: Get Your Public Key

1. Go to **Account** → **API Keys**.
2. Copy the **Public Key** — looks like `user_xxxxxxxxxxxxxxx` or a random string.

---

## Step 5: Configure the Intake Form

1. In the project, copy the example config:
   ```bash
   cp intake/intake-config.example.js intake/intake-config.js
   ```

2. Open `intake/intake-config.js` and fill in your values:
   ```js
   window.INTAKE_CONFIG = {
     emailjs: {
       publicKey:  "YOUR_PUBLIC_KEY",
       serviceId:  "YOUR_SERVICE_ID",
       templateId: "YOUR_TEMPLATE_ID"
     },
     dashboardBaseUrl: "https://rtadik.github.io/bobe-content-dashboard"
   };
   ```

3. **Never commit `intake-config.js`** — it's already in `.gitignore`.

---

## Step 6: Deploy and Test

1. Run `/deploy` to publish the intake form to `/intake/`.
2. Open `https://rtadik.github.io/bobe-content-dashboard/intake/`
3. Fill in a test submission with your own email.
4. Verify you receive the credential email with correct username, password, and login URL.

---

## Template Variables Reference

| Variable | Value |
|----------|-------|
| `{{to_email}}` | Client's email address |
| `{{to_name}}` | Client's display name |
| `{{client_id}}` | Their username (e.g. `acmecrypto`) |
| `{{password}}` | Their password (e.g. `acmecrypto123`) |
| `{{login_url}}` | Full login URL (e.g. `https://rtadik.github.io/bobe-content-dashboard/login.html`) |
| `{{dashboard_url}}` | Direct dashboard URL (e.g. `.../dashboard/acmecrypto/`) |
| `{{display_name}}` | Brand display name (used in subject) |

---

## Troubleshooting

**Email not received:**
- Check the EmailJS dashboard → **Email Logs** for errors.
- Verify the Service is connected (Gmail may need re-authorization after a few months).
- Check spam folder.

**"INTAKE_CONFIG not loaded" error in console:**
- Make sure `intake/intake-config.js` exists locally. It's gitignored and not deployed — it only needs to exist when testing locally.
- On the deployed site, EmailJS config is loaded from this file. Without it, the form shows credentials in the fallback panel and prompts for a manual download.

**EmailJS free tier limit:**
- Free tier: 200 emails/month.
- Paid plan: $15/month for 1,000 emails/month.
- Upgrade at emailjs.com if volume grows.

---

## Credential Pattern

Credentials follow a fixed pattern — no randomness needed:
- Username: `{client_id}` (same as their client ID)
- Password: `{client_id}123` (e.g. `acmecrypto123`)
- Admin: username `admin`, password `admin123`

Only SHA-256 hashes are stored in `credentials.json`. The plaintext password is never stored anywhere.
