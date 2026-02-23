# Onboard Client from Intake

> Read a completed client intake JSON file and generate all client config files + credentials in one pass. No Q&A required.

## Variables

intake_path: $ARGUMENTS (required — path to the intake JSON, e.g. clients/intake/rejiglabs-intake.json)

---

## Instructions

### Phase 1 — Read and Validate Intake File

1. Read JSON at `{intake_path}`.
2. Validate required fields exist: `client_id`, `display_name`, `contact.email`, `description`, `voice`, `scraping.keywords`.
3. If any required field is missing, print a clear error naming the missing field(s) and stop.
4. Extract: `client_id`, `display_name`, `email` (from `contact.email`).
5. Derive password: `{client_id}123`
6. Print: `Reading intake for: {display_name} ({client_id})`

---

### Phase 2 — Derive Missing Fields

From the intake data, derive the following fields not directly provided in the form:

- **`surface_color`**: lighten primary_color by 10% (or use a hardcoded dark surface like `#111B32` if no primary provided)
- **`background_gradient`**: `"linear-gradient(135deg, {primary_color} 0%, {darker_variant} 100%)"`
- **`style_presets`**: map from keywords/description — default to `["minimal", "tech", "notification"]`
- **`platforms`** (config format): map intake `platforms` array to config schema. Twitter → `{"id": "twitter", "enabled": true}`, etc.
- **`languages`**: map intake `languages` array to config format

---

### Phase 3 — Copy Template and Write All Config Files

**3a. Copy template directory:**
```bash
cp -r clients/_template clients/{client_id}
```

**3b. Write `clients/{client_id}/config.json`:**

Use the full config schema from `clients/_template/config.json`. Fill in all values from the intake JSON. Use derived values for fields not in the intake. Do not leave any placeholder values.

Key mappings:
- `client_id` → intake `client_id`
- `display_name` → intake `display_name`
- `website` → intake `website`
- `tagline` → intake `tagline`
- `description` → intake `description`
- `brand.primary_color` → intake `brand.primary_color`
- `brand.accent_color` → intake `brand.accent_color`
- `brand.text_color` → intake `brand.text_color`
- `brand.mascot_description` → intake `brand.mascot`
- `scraping.keywords` → intake `scraping.keywords`
- `scraping.negative_keywords` → intake `scraping.negative_keywords`
- `scraping.subreddits` → intake `scraping.subreddits`
- `content.cta_examples` → intake `content.cta_examples`
- `content.hashtags` → intake `content.hashtags`
- `airtable.enabled` → intake `airtable.enabled`
- `airtable.base_id` → intake `airtable.base_id`

**3c. Write `clients/{client_id}/content-guidelines.md`:**

Generate a full content guidelines file using:
- `voice.tone_adjectives` → tone section
- `voice.tone_description` → expand into guidelines
- `voice.content_avoid` → avoid section
- `voice.messaging_pillars` → messaging pillars section
- `audience` → ICP section
- `differentiators` → positioning section

Follow the structure of `clients/bobe/content-guidelines.md` as reference. Do not copy BoBe's content — generate content specific to this client.

**3d. Write `clients/{client_id}/context.md`:**

Generate a business context file using:
- `display_name`, `tagline`, `description`
- `audience` (age_range, situation, desired_outcome)
- `differentiators`
- `website`

Follow the structure of `clients/bobe/context.md` as reference.

**3e. Write `clients/{client_id}/keywords.md`:**

Generate a keywords file using:
- `scraping.keywords` → primary keywords
- `scraping.negative_keywords` → negative keywords
- `scraping.subreddits` → subreddit list

Follow the structure of `clients/bobe/keywords.md` as reference.

**3f. Write credentials:**

1. Read `credentials.json` at the project root. If it does not exist, create it with this structure:
   ```json
   {
     "clients": {},
     "admin": {
       "username": "admin",
       "password_hash": "<sha256 of 'admin123'>"
     }
   }
   ```
   SHA-256 of `admin123` = `240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9`

2. Compute SHA-256 of `{client_id}123` using Python:
   ```python
   import hashlib
   hashlib.sha256(f"{client_id}123".encode()).hexdigest()
   ```

3. Add entry:
   ```json
   "clients": {
     "{client_id}": {
       "username": "{client_id}",
       "password_hash": "<computed hash>",
       "display_name": "{display_name}",
       "email": "{email}"
     }
   }
   ```

4. Save `credentials.json`.

5. Print:
   ```
   Credentials written for {display_name}
     Username: {client_id}
     Password: {client_id}123
   Admin credentials unchanged (admin / admin123)
   ```

6. Print security note:
   ```
   SECURITY NOTE: Delete clients/intake/{client_id}-intake.json — it may contain sensitive data.
   ```

---

### Phase 4 — Airtable Setup (if enabled)

If `intake.airtable.enabled` is true:

1. Verify `AIRTABLE_API_KEY` is set in `.env`.
2. Remind Rut to create the Airtable base schema. Reference: `reference/airtable-client-setup.md`.
3. Print: `Airtable enabled for {client_id}. Base ID: {base_id}. See reference/airtable-client-setup.md for schema setup.`

---

### Phase 5 — Verify and Activate

**5a. Config validation:**
```bash
python -c "import sys; sys.path.insert(0,'scripts'); from client_config import load_config; c=load_config('{client_id}'); print('Config OK:', c['display_name'])"
```

If validation fails, print the error and ask Rut to check the generated config.

**5b. Ask about activating this client:**
> Would you like to switch the active client to {client_id}? (yes/no)

If yes: write `{client_id}` to `.active-client`.

**5c. Show client directory:**
```bash
ls clients/{client_id}/
```

**5d. Print completion summary:**

```
Onboarding complete for {display_name} ({client_id})

Files created:
  clients/{client_id}/config.json
  clients/{client_id}/content-guidelines.md
  clients/{client_id}/context.md
  clients/{client_id}/keywords.md
  credentials.json (updated)

Credentials:
  Username: {client_id}
  Password: {client_id}123

Next steps:
  1. Run /deploy to publish the updated credentials to the live dashboard
  2. The client can log in at: https://rtadik.github.io/bobe-content-dashboard/login.html
  3. Delete the intake JSON: clients/intake/{client_id}-intake.json
```
