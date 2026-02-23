# Onboard Client

> Create a new client configuration from the template. Conducts a full structured Q&A, then auto-drafts all config and content files in one pass. The client should be ready to run `/weekly-pipeline` with no further manual editing.

## Variables

client_name: $ARGUMENTS (optional — the new client's ID/slug)

---

## Instructions

### Phase 1 — Identify the Client

1. If `client_name` is provided as an argument, use it as the client ID (lowercase, no spaces).
2. If not provided, ask:
   - **Client ID** (slug, lowercase, no spaces — e.g., `acmecrypto`, `fitpro`, `saasly`)
   - **Display name** (e.g., "Acme Crypto", "FitPro", "Saasly")

---

### Phase 2 — Structured Q&A

Ask all of the following questions before writing any files. Gather all answers first, then proceed to Phase 3.

Present the questions conversationally, in order. You may group related questions to avoid feeling like a form.

**Identity & Product**

1. What is the client's **website URL**? (e.g., `bobe.app`, `acmecrypto.com`)
2. **One-line tagline**: How would you describe the product in one sentence?
3. **What does the product/service do?** (2-3 sentences, plain language — what problem does it solve, how does it work, what does the user get?)

**Audience**

4. **Who is the target audience?** Include: age range, their current situation, top 2-3 pain points, and what they want instead.
5. **Why do customers choose this product over alternatives?** Top 2-3 differentiators.

**Voice & Messaging**

6. **Brand tone and voice**: Describe it in 3-4 adjectives (e.g., "calm, educational, transparent, no-hype"). What does it feel like to read? What does it NOT sound like?
7. **What should content always avoid?** Specific phrases, claims, or topics that are off-brand or legally risky (e.g., "guaranteed returns", competitor bashing, overpromising).
8. **Messaging pillars**: What are the 2-4 core things you want your audience to believe about this product? (Probe: "What do you want people to think of when they think of this brand?")

**Distribution**

9. **Which platforms** should content be generated for? (Twitter/X, Telegram, LinkedIn, Instagram — or other?)
10. **Languages**: English only, or additional languages? (Note: Russian translation is built into the pipeline. Other languages require manual setup.)

**Scraping & Discovery**

11. **Primary scraping keywords**: 8-12 terms your audience uses when talking about this topic online. These filter scraped posts for relevance.
12. **Negative keywords**: Terms that indicate spam, off-topic content, or brand-damaging posts to exclude.
13. **Subreddits**: Which Reddit communities does your audience frequent? (List 2-5)

**Content & CTAs**

14. **CTA examples**: 2-3 calls-to-action you want used in content (e.g., "Try BoBe free: bobe.app", "Join 10,000 users: app.com/signup")
15. **Brand hashtags**: 2-4 hashtags owned by the brand (e.g., `#BoBe`, `#BoBeApp`)

**Brand & Visuals**

16. **Brand colors**: Primary color, accent color, text color (hex codes or descriptions — e.g., "#1a1a2e navy", "electric blue accent")
17. **Mascot or character**: Describe the brand character for image generation in detail (appearance, style, features). If none, say "none" and we'll use a generic clean style.

**Airtable Delivery (Optional)**

18. **Airtable for content delivery?** Do you want generated content to automatically sync to an Airtable base so the client can review, approve, and track it online?
    - If **yes**: Ask them to follow `reference/airtable-client-setup.md` to create a Base and get credentials. Ask them to provide the **Base ID** (starts with `app...`) and confirm the `AIRTABLE_API_KEY` is set in `.env`.
    - If **no**: Airtable will be disabled; content will be saved to Excel only.

---

### Phase 3 — Copy Template and Write All Files

**3a. Copy template directory:**
```bash
cp -r clients/_template clients/{client_id}
```

**3b. Write `clients/{client_id}/config.json`** — complete, all fields filled using Q&A answers:

```json
{
  "client_id": "{client_id}",
  "display_name": "{display_name}",
  "tagline": "{tagline}",
  "website": "{website}",
  "brand": {
    "primary_color": "{primary_color}",
    "accent_color": "{accent_color}",
    "text_color": "{text_color}",
    "secondary_accent": "{secondary_accent or derive from brand colors}",
    "surface_color": "{darker shade of primary}",
    "background_gradient": "{primary} to {darker shade}",
    "logo_path": "brand/logo.png",
    "reference_images": ["brand/logo.png"],
    "mascot_description": "{mascot description from Q18, or 'No mascot — use clean brand banner style'}",
    "logo_description": "{client display_name} logo in {accent_color}, placed in the top-left corner",
    "background_style": "{derived from brand colors}"
  },
  "content": {
    "tone": "{tone from Q7}",
    "voice": "{voice from Q7 expanded}",
    "brand_terms_keep": ["{display_name}", "{any other always-capitalized terms}"],
    "cta_url": "{website}",
    "cta_examples": ["{CTA1 from Q15}", "{CTA2}", "{CTA3}"],
    "hashtags": ["{hashtags from Q16}"],
    "messaging_pillars": ["{pillar 1 from Q9}", "{pillar 2}", "{pillar 3}", "{pillar 4 if applicable}"],
    "platforms": ["{platforms from Q10 — e.g., ['twitter', 'telegram']}"],
    "platform_formats": {
      "twitter": {
        "thread_tweets": 5,
        "single_max_chars": 280,
        "thread_topics_per_day": 2,
        "single_topics_per_day": 1
      },
      "telegram": {
        "min_chars": 400,
        "max_chars": 1200,
        "end_with_question": true
      }
    }
  },
  "scraping": {
    "keywords": ["{keywords from Q12}"],
    "negative_keywords": ["{negative keywords from Q13}"],
    "subreddits": ["{subreddits from Q14}"]
  },
  "image": {
    "style_presets": {
      "minimal": "clean minimalist banner, single focal point, dark background with {primary_color}",
      "tech": "futuristic {industry-relevant} data visualization, glowing UI elements on dark background",
      "notification": "realistic smartphone mockup showing {display_name} app notification"
    },
    "angle_style_map": {
      "Pain Point": "minimal",
      "Education": "tech",
      "Transparency": "notification",
      "Product": "notification"
    }
  },
  "languages": ["{languages from Q11 — always include 'en'}"],
  "airtable": {
    "enabled": {true if Airtable requested, false otherwise},
    "base_id": "{base_id if provided, else ''}",
    "api_key_env": "AIRTABLE_API_KEY"
  }
}
```

**3c. Write `clients/{client_id}/content-guidelines.md`** — fully drafted, no placeholders:

Using the Q&A answers, write a complete content-guidelines.md for this client. Follow the scaffold structure in `clients/_template/content-guidelines.md` but replace ALL placeholder text with real, specific content. Key sections:

- Brand voice: 3-4 adjectives + expansion (from Q7)
- Messaging pillars: 3-4 pillars derived from Q9, each with name, description, and example quote
- Platform sections: one section per platform in the platforms list (from Q10), with format and tone rules specific to this client
- What to always avoid: specific phrases, claim types, or topics from Q8 + negative keywords from Q13
- CTAs by platform: from Q15, adapted per platform
- Hashtag library: from Q16 + keyword-derived suggestions from Q12

**3d. Write `clients/{client_id}/context.md`** — fully drafted, no placeholders:

Using the Q&A answers, write a complete context.md for this client:

- Organization Overview: 2-3 sentences from Q3
- Products/Services: bullet list from Q3 + Q5 (differentiators)
- Target Audience (ICP): who they are, pain points, goals from Q4
- Positioning: differentiators from Q5, market context, what this brand is NOT

**3e. Write `clients/{client_id}/keywords.md`** — fully drafted, no placeholders:

Using the Q&A answers and config:

- Primary keywords: top 8-10 from Q12 (most product-relevant)
- Secondary keywords: remaining keywords from Q12 (broader terms)
- Negative keywords: from Q13
- Subreddits: from Q14 (formatted as `r/subreddit`)
- Twitter search queries: 3-5 ready-to-use Apify queries constructed from primary keywords

---

### Phase 4 — Airtable Setup (if enabled)

If the client requested Airtable:

1. Confirm `AIRTABLE_API_KEY` is set in `.env`. If not, print:
   ```
   ACTION REQUIRED: Add your Airtable Personal Access Token to .env:
   AIRTABLE_API_KEY=pat...your_token...
   See reference/airtable-client-setup.md for setup instructions.
   ```
2. Confirm `airtable.base_id` is set in the new client's `config.json`.
3. Print: "Airtable is enabled. After running /weekly-pipeline, all content will automatically sync to your Airtable base."

---

### Phase 5 — Verify and Activate

**5a. Run config validation:**
```bash
python -c "
import sys; sys.path.insert(0, 'scripts')
from client_config import load_config, is_airtable_enabled
c = load_config('{client_id}')
print(f'Config loaded: {c[\"display_name\"]}')
print(f'Platforms: {c[\"content\"][\"platforms\"]}')
print(f'Languages: {c[\"languages\"]}')
print(f'Airtable enabled: {is_airtable_enabled(\"{client_id}\")}')
"
```

Expected: prints display name, platforms list, languages list, and Airtable status.

**5b. Ask:** "Do you want to set {display_name} as the active client now?"
- If yes: write `{client_id}\n` to `.active-client`

**5c. Show the new client directory structure:**
```bash
find clients/{client_id} -type f | sort
```

**5d. Print the completion summary:**
```
Client onboarded: {display_name} ({client_id})
Files created:
  clients/{client_id}/config.json
  clients/{client_id}/content-guidelines.md
  clients/{client_id}/context.md
  clients/{client_id}/keywords.md
  clients/{client_id}/brand/README.md  (from template)

Next steps:
  1. Add brand assets: clients/{client_id}/brand/logo.png (required for image generation)
  2. Run a mock pipeline test:
     python scripts/weekly_pipeline.py --action create-workbook --week-of YYYY-MM-DD --client {client_id}
  3. Run the full pipeline: /weekly-pipeline
```

---

## Notes

- Brand asset instructions are in `clients/{client_id}/brand/README.md` (copied from template)
- Airtable setup guide: `reference/airtable-client-setup.md`
- To switch active client later: `/switch-client {client_id}`
- To test without API calls: add `--mock` to any pipeline command
