# Onboard Client

> Create a new client configuration from the template. Walks through setup interactively.

## Variables

client_name: $ARGUMENTS (optional — the new client's ID/slug)

---

## Instructions

1. **If no client_name provided**, ask the user for:
   - Client ID (slug, lowercase, no spaces — e.g., "acmecrypto")
   - Display name (e.g., "Acme Crypto")

2. **Copy template**:
   ```bash
   cp -r clients/_template clients/{client_id}
   ```

3. **Gather information** from the user:
   - Display name and website URL
   - Tagline (one-line description)
   - Brand tone and voice description
   - 5-10 scraping keywords relevant to their product
   - Negative keywords to exclude
   - Relevant subreddits
   - Brand colors (primary, accent, text)
   - Mascot/character description (if any)
   - Languages to support (en, ru, etc.)

4. **Update config.json** with the gathered information:
   - Fill in all fields in `clients/{client_id}/config.json`
   - Replace all placeholder values

5. **Remind the user** to:
   - Add brand assets (logo.png, banner examples) to `clients/{client_id}/brand/`
   - Update `clients/{client_id}/content-guidelines.md` with their voice and messaging pillars
   - Update `clients/{client_id}/keywords.md` with detailed keyword lists
   - Update `clients/{client_id}/context.md` with business context

6. **Set as active** (optional):
   - Ask if they want to switch to this client now
   - If yes, write the client ID to `.active-client`

7. **Verify**:
   ```bash
   python -c "import sys; sys.path.insert(0, 'scripts'); from client_config import load_config; c = load_config('{client_id}'); print(f'Config loaded: {c[\"display_name\"]}')"
   ```

8. **Report**:
   - Show the new client directory structure
   - Remind that `/weekly-pipeline` will now work for this client
   - Suggest running `/weekly-pipeline --mock` to test
