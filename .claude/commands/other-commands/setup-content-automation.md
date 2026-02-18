# Setup Content Automation

> Execute the BoBe Content Automation Pipeline plan to set up all scripts, skills, and infrastructure.

## Instructions

This command implements the full content automation setup from `plans/2026-02-18-bobe-content-automation.md`.

**Before running, ensure you have:**
1. BoBe brand reference images ready to provide (logo, style examples)
2. Your Apify API token (or will set up account)
3. Your Google AI Studio API key for Nano Banana Pro (or will set up account)

---

## Execute

Read and implement the plan at `plans/2026-02-18-bobe-content-automation.md`.

Follow the Step-by-Step Tasks in exact order:

1. **Step 1**: Create `outputs/content/` directory structure
2. **Step 2**: Create reference materials (keywords, content guidelines, API setup docs)
3. **Step 3**: Set up `reference/bobe-brand/` directory and prompt user for brand images
4. **Step 4**: Create `scripts/apify_scraper.py` with full implementation
5. **Step 5**: Create `scripts/excel_manager.py` with full implementation
6. **Step 6**: Create `scripts/nano_banana.py` with full implementation
7. **Step 7**: Create `.claude/skills/content-generator/SKILL.md`
8. **Step 8**: Create `.claude/skills/image-generator/SKILL.md`
9. **Step 9**: Create `.claude/commands/content-pipeline.md`
10. **Step 10**: Update `CLAUDE.md` with new capabilities

**Important:**
- Create complete, working implementations — not stubs
- Ask the user for brand images during Step 3
- Make Python scripts executable with `chmod +x`
- Validate each step before proceeding to the next

---

## After Implementation

1. Run the validation checklist from the plan
2. Update the plan status to "Implemented"
3. Provide a summary of what was created
4. Remind user to:
   - Add their brand images to `reference/bobe-brand/`
   - Set environment variables (`APIFY_API_TOKEN`, `GOOGLE_AI_API_KEY`)
   - Install Python dependencies (`pip install requests openpyxl google-genai`)
   - Run `/content-pipeline` to test the setup
