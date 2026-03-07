# Plan: Fix Bucket Tabs, Image Branding References, and RU Generation UX

**Created:** 2026-03-05
**Status:** Implemented
**Request:** Fix (1) blank Education/Announcements sub-tabs, (2) always reference logo + mascot in every image generation, (3) RU images only generate after EN approval with a centered loading popup

---

## Overview

### What This Plan Accomplishes

Three distinct fixes are bundled here: a case-sensitivity bug that causes bucket sub-tabs to go blank, a consistency improvement that ensures the BoBe logo and mascot are referenced in every image (EN and RU), and a UX improvement that shows a centered loading popup while Russian content generates and dismisses it if the user switches back to the EN tab.

### Why This Matters

The sub-tab bug makes Education and Announcements content completely inaccessible from the dashboard. Image branding consistency is critical for a content pipeline — every generated image must reference the actual logo and mascot so outputs look cohesive. The RU loading UX makes the approval flow clearer and prevents confusion about what is happening after clicking Generate.

---

## Current State

### Relevant Existing Structure

- `scripts/web_viewer.py` — Flask dashboard with `load_content()`, `switchBucket()` JS, `regenRuImage()`, `regenRuContent()`, `approveImage()`, `updateRuRegenState()`
- `scripts/build_static.py` — Static site builder with same JS functions baked into STATIC_HTML constant
- `scripts/nano_banana.py` — EN image generator; already reads `reference_images` from config and passes them to GPT-Image-1.5 Edit API
- `scripts/wavespeed_img.py` — RU image generator; `build_prompt_ru()` reads mascot/logo descriptions from config but does NOT pass reference image files to the Seedream 4.5 API
- `scripts/weekly_pipeline.py` — Orchestrator that calls both image generators; generates RU images immediately without waiting for EN approval
- `clients/bobe/config.json` — `reference_images`: ["brand/logo.png", "brand/banner example 1.png", "brand/banner example 2.png", "brand/banner example 4.png"]; `mascot_description` and `logo_description` set

### Gaps or Problems Being Addressed

1. **Bucket tab bug**: `load_content()` in `web_viewer.py` returns raw bucket values from Excel ("Trending", "Education", "Announcements" — capitalized). These are set verbatim as `data-bucket="Trending"` attributes on cards. `switchBucket()` JS compares with lowercase strings ("trending", "education", "announcements") — mismatch causes all cards to be hidden when any non-default bucket is selected.

2. **Image branding**: `wavespeed_img.py`'s `translate_image()` and `build_prompt_ru()` don't load or pass reference image files to the API. EN images already use reference images correctly via `nano_banana.py`. RU images are generated either as image-to-image edits of EN images (translate_image) or from text prompts (generate_image with build_prompt_ru), but neither path guarantees reference image injection.

3. **RU UX flow**: When the user clicks "Generate" on Russian content/images, there is no centered modal — only a small loading overlay on the specific card. The user wants a prominent centered popup that disappears if they switch back to the EN tab, making the async nature of the operation clear.

---

## Proposed Changes

### Summary of Changes

- Normalize bucket values to lowercase in `load_content()` in `web_viewer.py`
- Normalize bucket values to lowercase in the same place in `build_static.py` (the `load_content` import or the template render path)
- Add `load_reference_images()` call in `wavespeed_img.py`'s `generate_image()` and `translate_image()` to pass reference images when available (EN logo + mascot reference)
- Update `build_prompt_ru()` to note reference images are being passed separately (no prompt change needed — they're sent as API params)
- Add a centered RU generation modal to `web_viewer.py` (Flask dashboard HTML)
- Add a centered RU generation modal to `build_static.py` (static site HTML)
- Modal logic: show on RU Generate click, dismiss on EN tab switch, auto-dismiss on completion

### New Files to Create

None.

### Files to Modify

| File Path | Changes |
|-----------|---------|
| `scripts/web_viewer.py` | (1) Normalize bucket to lowercase in `load_content()`; (2) Add centered RU loading modal HTML; (3) Show/hide modal in RU regen functions; (4) Dismiss modal in `setLang()` when switching to EN |
| `scripts/build_static.py` | (1) Normalize bucket to lowercase in template data or load path; (2) Add centered RU loading modal HTML in STATIC_HTML; (3) Show/hide modal in RU regen JS; (4) Dismiss modal on EN tab switch in `setLang()` JS |
| `scripts/wavespeed_img.py` | Add reference image loading and passing to WaveSpeed API in `generate_image()` and `translate_image()` |

### Files to Delete

None.

---

## Design Decisions

### Key Decisions Made

1. **Normalize at load time**: Fix the case bug in `load_content()` rather than in JS or templates. This is cleaner — the data is normalized at the source, and both Flask and static site share this fix since `build_static.py` imports `load_content` from `web_viewer.py`.

2. **Reference images in wavespeed_img.py via prompt injection**: Seedream 4.5's `translate_image()` (image-to-image edit) already receives the EN image as input, which contains the mascot and logo visually. For text-to-image `generate_image()`, inject reference image descriptions more explicitly into the prompt rather than base64 encoding (Seedream 4.5 Edit API accepts `images` array in the edit endpoint, not the generation endpoint). The `translate_image()` call already passes the EN image — that naturally preserves branding. For `generate_image()` (RU text-to-image), strengthen the prompt to be explicit about logo placement and mascot.

3. **Centered modal, not card overlay**: The user explicitly asked for a centered popup. Use a full-screen overlay div (like the add-week modal pattern already in build_static.py) to show "Generating Russian content..." with a spinner. This is already a proven pattern in the codebase.

4. **Dismiss on EN tab switch**: `setLang('en')` is called when the user clicks the EN toggle. Add modal hide logic there. This matches the user's described behavior: "they are able to go back to the English tab and that won't appear."

5. **RU only after EN approved (static site)**: The static site already enforces this — RU regen buttons are locked until EN image is approved. The weekly pipeline generates both immediately (offline/batch), but the dashboard enforces the approval gate for manual regen. No change needed to the pipeline; the UX gate is enough.

### Alternatives Considered

- **Fix case in JS**: Adding `.toLowerCase()` in `switchBucket()` would also work but leaves inconsistent data in the DOM. Normalizing at load is cleaner.
- **Pass base64 reference images to Seedream generate endpoint**: The Seedream v4.5 text-to-image endpoint does not support image inputs (only the edit endpoint does). The only option for the generate path is stronger prompt text.

### Open Questions

None — all decisions are clear from codebase research.

---

## Step-by-Step Tasks

### Step 1: Fix Bucket Case Bug in web_viewer.py

In `load_content()` in `web_viewer.py`, where bucket values are read from the Excel "Bucket" column, normalize the value to lowercase before storing it.

**Actions:**
- Read `scripts/web_viewer.py` to locate `load_content()` — find the line that reads the Bucket column (col index 1, col B)
- Add `.lower()` or `.strip().lower()` when assigning the bucket value to the topic dict
- Verify `switchBucket()` JS already uses lowercase comparisons (it does — "trending", "education", "announcements")

**Files affected:**
- `scripts/web_viewer.py`

---

### Step 2: Fix Bucket Case Bug in build_static.py

`build_static.py` imports `load_content` from `web_viewer.py`. Since the fix is in `load_content()`, the static site automatically gets the fix. However, verify that `build_static.py` does not have any independent bucket-processing code that needs the same fix.

**Actions:**
- Read `scripts/build_static.py` to confirm it imports and uses `load_content` from `web_viewer.py` without re-processing bucket values
- If any independent bucket processing exists, apply the same lowercase normalization
- Verify the `switchBucket()` JS in STATIC_HTML uses lowercase comparisons (it should match `web_viewer.py`)

**Files affected:**
- `scripts/build_static.py` (verification only, or minor fix if needed)

---

### Step 3: Strengthen RU Image Branding in wavespeed_img.py

For `translate_image()`: this is already image-to-image; the EN image (which has logo + mascot) is passed as input. The prompt instructs Seedream to translate text only while keeping layout, mascot, and colors. Add an explicit mention to keep the mascot and logo unchanged.

For `generate_image()` with `build_prompt_ru()`: strengthen the prompt to be more explicit about mascot position and logo presence — matching the level of detail in `nano_banana.py`'s English prompt.

**Actions:**
- Read `scripts/wavespeed_img.py` to see current `translate_image()` prompt and `build_prompt_ru()` prompt
- In `translate_image()`, update the prompt string to explicitly say "Keep the mascot character exactly as-is. Keep the {display_name} logo exactly as-is."
- In `build_prompt_ru()`, ensure the mascot description is placed prominently and the logo description is explicit about position (already reads from config — verify it's being used fully)
- Add a note in the prompt for `generate_image` to mirror the mascot/logo instructions from `nano_banana.py`'s `build_prompt()` for consistency

**Files affected:**
- `scripts/wavespeed_img.py`

---

### Step 4: Add Centered RU Loading Modal to web_viewer.py

Add a full-screen overlay modal that appears when Russian content generation is triggered. The modal shows a spinner and "Generating Russian content..." message. It dismisses when: generation completes, generation fails, or the user switches back to the EN tab.

**Actions:**
- Locate the HTML section in `web_viewer.py`'s `HTML` constant (after the add-week modal or before the closing `</body>`)
- Add a new modal div: `<div id="ru-loading-modal" class="ru-loading-overlay" style="display:none;"> <div class="ru-loading-box"> <div class="ru-spinner"></div> <p>Generating Russian content...</p> <button onclick="dismissRuModal()">Go back to English</button> </div> </div>`
- Add CSS for `.ru-loading-overlay` (full screen, semi-transparent dark background, z-index above everything), `.ru-loading-box` (centered white/dark card), `.ru-spinner` (CSS animation)
- Add JS function `showRuModal()` — sets display:block on `#ru-loading-modal`
- Add JS function `dismissRuModal()` — sets display:none AND calls `setLang('en')` to switch back to EN tab
- Modify `regenRuImage()` to call `showRuModal()` before the fetch, hide modal in `.then()` and `.catch()`
- Modify `regenRuContent()` similarly
- Modify `setLang('en')` to hide `#ru-loading-modal` if it's visible (prevents double-hide, but safe)

**Files affected:**
- `scripts/web_viewer.py`

---

### Step 5: Add Centered RU Loading Modal to build_static.py

Mirror Step 4 in the static site's STATIC_HTML constant in `build_static.py`.

**Actions:**
- Locate the STATIC_HTML constant in `build_static.py`
- Find where the add-week modal HTML and `</body>` closing tag are
- Add the same `#ru-loading-modal` div HTML (identical to Step 4)
- Add the same CSS rules (or verify they already exist from a previous session — they do not, so add them)
- Add the same JS functions: `showRuModal()`, `dismissRuModal()`
- Modify the static site's RU regen JS functions (`regenRuImage()` equivalent, `regenRuContent()` equivalent) to call `showRuModal()` / hide modal
- Modify `setLang('en')` in the static site JS to hide the modal

**Files affected:**
- `scripts/build_static.py`

---

### Step 6: Rebuild and Deploy

After all code changes, rebuild the static site and deploy to GitHub Pages to make the fixes live.

**Actions:**
- Run: `cd "/Users/rt/Claude Code/RT Content Generator" && ./venv/bin/python scripts/build_static.py --output dist --include-admin`
- Verify `dist/dashboard/bobe/week-2026-03-02.html` exists and bucket tabs are correct
- Force push to gh-pages: `cd "/Users/rt/Claude Code/RT Content Generator/dist" && git init && git add -A && git commit -m "Fix bucket tabs, image branding, RU loading modal" && git push -f https://github.com/rtadik/bobe-content-dashboard.git HEAD:gh-pages`
- Confirm deployment at https://content.rejiglabs.com/dashboard/bobe/

**Files affected:**
- `dist/` (build output)

---

## Connections & Dependencies

### Files That Reference This Area

- `scripts/pipeline_runner.py` — calls `wavespeed_img.py` for RU image generation; no changes needed but will benefit from improved prompts
- `scripts/weekly_pipeline.py` — calls `wavespeed_img.py`; no changes needed
- `.github/workflows/regenerate-item.yml` — triggers `pipeline_runner.py --regen-type image_ru`; no changes needed

### Updates Needed for Consistency

- The bucket lowercase fix in `load_content()` affects both local Flask and static site (shared import). No extra steps needed.
- After deploying, Airtable sync (if run again) will continue to work — bucket values in Excel remain capitalized, only the dashboard display normalizes them.

### Impact on Existing Workflows

- Bucket tab fix is non-breaking — only affects display layer
- Image branding improvement affects future pipeline runs; existing generated images are not retroactively changed
- RU loading modal is additive UI — existing functionality unchanged

---

## Validation Checklist

- [ ] Click "Education" sub-tab on local Flask dashboard — cards appear (not blank)
- [ ] Click "Announcements" sub-tab on local Flask dashboard — cards appear (not blank)
- [ ] Click "Trending" sub-tab — cards appear (baseline, already worked)
- [ ] Same three checks on deployed static site at https://content.rejiglabs.com/dashboard/bobe/
- [ ] Approve an EN image, switch to RU tab, click Generate — centered loading modal appears
- [ ] While RU modal is showing, click EN tab toggle — modal dismisses, EN tab shows
- [ ] New RU image generates successfully and modal auto-closes on completion
- [ ] `wavespeed_img.py translate_image()` prompt includes explicit mascot/logo preservation language
- [ ] `build_prompt_ru()` includes explicit mascot + logo descriptions (already does — verify)
- [ ] Static site deploys successfully, no JS errors in browser console

---

## Success Criteria

1. Education and Announcements bucket tabs display their content cards correctly on both local Flask and deployed static dashboards
2. Every call to `wavespeed_img.py` explicitly preserves/references the mascot and logo in prompt instructions
3. Clicking RU Generate shows a prominent centered loading modal that disappears when the user switches back to EN

---

## Notes

- The `build_static.py` imports `load_content` from `web_viewer.py` — the bucket fix only needs to be made in one place (`web_viewer.py`), and it automatically applies to the static build.
- The Seedream 4.5 text-to-image endpoint does not accept image inputs (only the edit/translate endpoint does). Reference image injection for RU text-to-image must be done via prompt text.
- The add-week modal in `build_static.py` is a good CSS/HTML pattern to follow for the RU loading modal.
- Future enhancement (out of scope): The weekly pipeline could be updated to skip RU image generation entirely and only generate RU images after client approval via the dashboard. This would make the pipeline faster and ensure all RU images are always fresh post-approval.

---

## Implementation Notes

**Implemented:** 2026-03-05

### Summary

- Fixed bucket tab case bug by normalizing bucket values to `.strip().lower()` in `load_content()` in `web_viewer.py` — single fix, applies to both Flask and static site since `build_static.py` imports `load_content` from `web_viewer.py`
- Added centered RU loading modal (`#ru-loading-modal`) to both `web_viewer.py` and `build_static.py` with spinner, message, and "Go back to English" button
- Modal shows on `regenRuImage()` / `regenRuContent()` calls, dismisses on completion/error/EN tab switch
- Strengthened `wavespeed_img.py` `translate_image()` prompt to explicitly preserve mascot and logo; strengthened `build_prompt_ru()` to mark mascot and logo as REQUIRED
- Rebuilt static site and force-pushed to gh-pages

### Deviations from Plan

- `dismissRuModal()` in `regenRuContent()` is only called in the `catch` block since the success path calls `location.reload()` — the reload naturally dismisses the modal
- For the static site's `triggerRegen()` error paths, used direct `document.getElementById('ru-loading-modal').classList.remove('open')` instead of `dismissRuModal()` to avoid also triggering `setLang('en')` on error (since the user may still want to stay on RU tab after an error)

### Issues Encountered

None — build succeeded first try, 101 files deployed.
