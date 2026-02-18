# Plan: BoBe Content Automation Pipeline

**Created:** 2026-02-18
**Status:** Implemented — 2026-02-18
**Request:** Build an automated content pipeline that scrapes Twitter/Reddit via Apify, curates top topics, generates copy using a content skill, outputs to Excel, and creates images with Nano Banana Pro.

---

## Overview

### What This Plan Accomplishes

This plan creates a comprehensive content automation system for BoBe that: (1) scrapes Twitter and Reddit for crypto/DeFi/yield content using Apify API, (2) filters and ranks topics relevant to BoBe's positioning, (3) exports curated topics to an Excel spreadsheet, (4) generates Telegram/Twitter-ready copy for the top 2-3 daily topics, and (5) creates accompanying images using Google's Nano Banana Pro API. The system will be invocable via a `/content-pipeline` command.

### Why This Matters

BoBe's growth strategy relies on content-driven marketing, ambassador expansion, and belief-building content. Manual content creation is time-consuming and inconsistent. This automation ensures BoBe maintains a steady stream of relevant, timely content that responds to what's actually trending in the crypto/DeFi space—without requiring constant manual monitoring. It directly supports Rut's responsibilities for funnel infrastructure and organic acquisition strategy.

---

## Current State

### Relevant Existing Structure

| File/Folder | Relevance |
|-------------|-----------|
| `context/BoBe Context.md` | Defines BoBe's products, ICP, and positioning—used to filter relevant topics |
| `context/RT BoBe Info.md` | Defines Rut's role and marketing priorities |
| `.claude/commands/` | Where the `/content-pipeline` command will live |
| `.claude/skills/` | Where the content creation skill and image generation skill will live |
| `outputs/` | Where daily content Excel files and generated images will be stored |
| `scripts/` | Where automation scripts will live |

### Gaps or Problems Being Addressed

1. **No content sourcing automation** — Currently no way to automatically discover trending crypto/DeFi topics
2. **No structured content workflow** — Content creation is ad-hoc, not systematized
3. **No image generation integration** — No tooling for creating branded visual content
4. **Manual research burden** — Rut must manually scan Twitter/Reddit for content ideas
5. **No content tracking** — No Excel-based system to track what topics were covered and what content was generated

---

## Proposed Changes

### Summary of Changes

- Create a `/content-pipeline` command that orchestrates the full workflow
- Create a `content-generator` skill for producing Telegram/Twitter copy
- Create an `image-generator` skill for Nano Banana Pro integration
- Create Python scripts for Apify scraping and Excel management
- Create configuration files for API keys and scraping parameters
- Add reference materials for BoBe-relevant keywords and content guidelines
- Establish an `outputs/content/` directory structure for daily content outputs

### New Files to Create

| File Path | Purpose |
|-----------|---------|
| `.claude/commands/content-pipeline.md` | Main command to run the full content automation pipeline |
| `.claude/skills/content-generator/SKILL.md` | Skill for generating Telegram/Twitter copy from topics |
| `.claude/skills/image-generator/SKILL.md` | Skill for creating images via Nano Banana Pro API |
| `scripts/apify_scraper.py` | Python script to call Apify API for Twitter/Reddit scraping |
| `scripts/excel_manager.py` | Python script to create/update Excel spreadsheets with topics and content |
| `scripts/nano_banana.py` | Python script to call Nano Banana Pro API for image generation |
| `reference/bobe-keywords.md` | List of keywords and topics relevant to BoBe for filtering |
| `reference/content-guidelines.md` | BoBe tone, style, and messaging guidelines for content generation |
| `reference/api-setup.md` | Documentation for setting up Apify and Nano Banana Pro API keys |
| `reference/bobe-brand/` | Directory for BoBe brand reference images (logo, colors, style examples) |
| `reference/bobe-brand/README.md` | Documentation of brand assets and how to use them |
| `outputs/content/.gitkeep` | Establish directory for content outputs |

### Files to Modify

| File Path | Changes |
|-----------|---------|
| `CLAUDE.md` | Add documentation for `/content-pipeline` command and new skills |

### Files to Delete (if any)

None.

---

## Design Decisions

### Key Decisions Made

1. **Apify over direct scraping**: Apify handles rate limiting, IP rotation, and API complexity. Their Twitter and Reddit scrapers are well-maintained and compliant with legal requirements for public data.

2. **Excel for data storage**: Excel provides a portable, human-readable format that Rut can review and share. It also integrates well with other tools and doesn't require database setup.

3. **Separate skills for content and image generation**: Modular skills allow reuse across different workflows and maintain separation of concerns. The content generator can be used independently of image generation.

4. **Python scripts for API calls**: Python provides robust libraries for API interaction (requests, openpyxl) and is easier to maintain than embedding complex API logic directly in skill instructions.

5. **Two-sheet Excel structure**: Sheet 1 for scraped/curated topics, Sheet 2 for generated content. This provides clear separation and audit trail.

6. **Nano Banana Pro (gemini-3-pro-image-preview)**: Google's latest image generation model offers superior text rendering for captions/CTAs and professional-grade output quality.

7. **Keyword-based relevance filtering**: Topics are filtered against BoBe-relevant keywords (DeFi, yield, trading bots, automation, etc.) to ensure only relevant content is surfaced.

### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|-----------------|
| ScrapeCreators API | Apify has more mature Twitter/Reddit scrapers and MCP support |
| Google Sheets | Excel is more portable and doesn't require Google account setup |
| Single monolithic script | Modular scripts are easier to debug, test, and maintain |
| Direct API calls in skill | Python scripts provide better error handling and reusability |
| Manual topic selection | Automated relevance scoring reduces manual burden while still allowing human override |

### Open Questions (if any)

1. **Apify API key**: User needs to provide their Apify API token. Plan assumes this will be stored as environment variable `APIFY_API_TOKEN`.

2. **Nano Banana Pro API key**: User needs a Google AI Studio API key. Plan assumes this will be stored as environment variable `GOOGLE_AI_API_KEY`.

3. **Content tone preference**: Should generated content be more professional/educational or casual/engaging? Plan includes guidelines but may need user input.

4. **Image style preference**: What visual style should generated images follow? (Modern/minimalist, bold/crypto-themed, infographic-style?) Plan will include configurable prompts.

5. **Posting workflow**: Does user want the pipeline to just generate content, or also queue/post it? Plan focuses on generation only; posting can be added later.

---

## Step-by-Step Tasks

Execute these tasks in order during implementation.

### Step 1: Create Output Directory Structure

Establish the directory structure for content outputs.

**Actions:**

- Create `outputs/content/` directory
- Add `.gitkeep` file to preserve directory in git

**Files affected:**

- `outputs/content/.gitkeep` (create)

---

### Step 2: Create Reference Materials

Create the reference documents that guide topic filtering and content generation.

**Actions:**

- Create `reference/bobe-keywords.md` with:
  - Primary keywords (yield, DeFi, trading bot, automation, AI trading, on-chain, smart contract)
  - Secondary keywords (crypto, passive income, portfolio, risk management, APY)
  - Competitor terms to monitor (trading automation platforms)
  - Negative keywords to filter out (scam, rug pull, pump and dump)

- Create `reference/content-guidelines.md` with:
  - BoBe voice and tone (transparent, educational, not hype-driven)
  - Messaging pillars (automation, risk management, transparency)
  - Content formats (threads, single tweets, Telegram posts)
  - CTAs and engagement patterns
  - What to avoid (unrealistic APY claims, speculation language)

- Create `reference/api-setup.md` with:
  - Apify account setup instructions
  - How to get Apify API token
  - Google AI Studio setup for Nano Banana Pro
  - Environment variable configuration
  - Rate limits and usage guidelines

**Files affected:**

- `reference/bobe-keywords.md` (create)
- `reference/content-guidelines.md` (create)
- `reference/api-setup.md` (create)

---

### Step 3: Set Up BoBe Brand Reference Images

Create the brand assets directory and document how reference images should be used for consistent image generation.

**Actions:**

- Create `reference/bobe-brand/` directory
- Create `reference/bobe-brand/README.md` documenting:
  - What reference images are included
  - How they should be used in image prompts
  - Brand color palette (hex codes)
  - Logo usage guidelines
  - Visual style principles

**User action required:**

The user must provide BoBe reference images to be placed in `reference/bobe-brand/`:
- `logo.png` - Primary BoBe logo
- `logo-dark.png` - Logo for dark backgrounds (if available)
- `style-example-1.png` - Example of approved visual style
- `style-example-2.png` - Additional style example
- `color-palette.png` - Brand color palette (optional)

**README.md content:**

```markdown
# BoBe Brand Assets

Reference images for maintaining brand consistency in generated visuals.

## Contents

| File | Description |
|------|-------------|
| `logo.png` | Primary BoBe logo (transparent background) |
| `logo-dark.png` | Logo variant for dark backgrounds |
| `style-example-*.png` | Approved visual style examples |

## Brand Colors

| Color | Hex | Usage |
|-------|-----|-------|
| Primary Blue | #[TBD] | Main accent color |
| Secondary Purple | #[TBD] | Gradient accent |
| Background Light | #[TBD] | Light mode backgrounds |
| Background Dark | #[TBD] | Dark mode backgrounds |

## Visual Style Principles

- Modern, clean, minimalist
- Professional fintech aesthetic
- Blue/purple gradient accents
- Avoid: rockets, moons, excessive crypto memes
- Focus: automation, technology, trust

## Using Reference Images with Nano Banana Pro

When generating images, reference these assets:
1. Use color palette for consistent branding
2. Match style of example images
3. Maintain professional, non-hype aesthetic
4. Include space for text overlays when needed

## Image Prompt Template

Include in prompts:
"BoBe brand style, modern fintech aesthetic, [primary blue] and [secondary purple] gradient accents, clean professional design, [specific subject]"
```

**Files affected:**

- `reference/bobe-brand/README.md` (create)
- `reference/bobe-brand/` (create directory)

---

### Step 4: Create Apify Scraper Script

Create the Python script that calls Apify API to scrape Twitter and Reddit.

**Actions:**

- Create `scripts/apify_scraper.py` with functions:
  - `scrape_twitter(keywords, count=50)` - Calls Apify Twitter scraper actor
  - `scrape_reddit(subreddits, keywords, count=50)` - Calls Apify Reddit scraper actor
  - `filter_by_relevance(posts, keywords)` - Filters posts by BoBe keywords
  - `rank_by_engagement(posts)` - Ranks posts by likes/comments/shares
  - `get_top_topics(posts, n=3)` - Returns top N topics for content creation

- Include error handling for API failures
- Include rate limiting awareness
- Return structured data suitable for Excel export

**Files affected:**

- `scripts/apify_scraper.py` (create)

**Script specification:**

```python
#!/usr/bin/env python3
"""
BoBe Content Pipeline - Apify Scraper
Scrapes Twitter and Reddit for crypto/DeFi content relevant to BoBe.

Environment variables:
- APIFY_API_TOKEN: Your Apify API token

Usage:
    python scripts/apify_scraper.py --platform twitter --keywords "defi,yield,trading bot"
    python scripts/apify_scraper.py --platform reddit --subreddits "defi,cryptocurrency" --keywords "yield,automation"
"""

import os
import json
import argparse
from datetime import datetime
from typing import List, Dict
import requests

APIFY_API_TOKEN = os.environ.get("APIFY_API_TOKEN")
APIFY_BASE_URL = "https://api.apify.com/v2"

# Apify actor IDs for scraping
TWITTER_ACTOR_ID = "apidojo~tweet-scraper"  # Tweet Scraper V2
REDDIT_ACTOR_ID = "trudax~reddit-scraper"   # Reddit Scraper

def scrape_twitter(keywords: List[str], count: int = 50) -> List[Dict]:
    """Scrape Twitter for posts matching keywords."""
    # Implementation details...
    pass

def scrape_reddit(subreddits: List[str], keywords: List[str], count: int = 50) -> List[Dict]:
    """Scrape Reddit for posts from specified subreddits matching keywords."""
    # Implementation details...
    pass

def filter_by_relevance(posts: List[Dict], keywords: List[str], negative_keywords: List[str]) -> List[Dict]:
    """Filter posts by relevance to BoBe keywords, excluding negative keywords."""
    # Implementation details...
    pass

def rank_by_engagement(posts: List[Dict]) -> List[Dict]:
    """Rank posts by engagement metrics (likes, comments, retweets/upvotes)."""
    # Implementation details...
    pass

def get_top_topics(posts: List[Dict], n: int = 3) -> List[Dict]:
    """Extract top N topics from ranked posts."""
    # Implementation details...
    pass

def main():
    parser = argparse.ArgumentParser(description="Scrape Twitter/Reddit for BoBe content")
    # Argument parsing...
    pass

if __name__ == "__main__":
    main()
```

---

### Step 5: Create Excel Manager Script

Create the Python script that manages Excel spreadsheet creation and updates.

**Actions:**

- Create `scripts/excel_manager.py` with functions:
  - `create_daily_workbook(date)` - Creates new workbook with two sheets
  - `add_topics_to_sheet1(workbook, topics)` - Adds scraped topics with metadata
  - `add_content_to_sheet2(workbook, content)` - Adds generated content
  - `save_workbook(workbook, path)` - Saves to outputs/content/

- Sheet 1 columns: Date, Platform, Topic, Original Post, Engagement Score, URL, Relevance Score, Selected
- Sheet 2 columns: Date, Topic, Platform Target, Content, Image Prompt, Image Path, Status

**Files affected:**

- `scripts/excel_manager.py` (create)

**Script specification:**

```python
#!/usr/bin/env python3
"""
BoBe Content Pipeline - Excel Manager
Creates and manages Excel spreadsheets for content pipeline tracking.

Usage:
    python scripts/excel_manager.py --action create --date 2026-02-18
    python scripts/excel_manager.py --action add-topics --file path/to/workbook.xlsx --topics topics.json
    python scripts/excel_manager.py --action add-content --file path/to/workbook.xlsx --content content.json
"""

import os
import json
import argparse
from datetime import datetime
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, PatternFill

def create_daily_workbook(date: str) -> Workbook:
    """Create a new workbook with Topics and Content sheets."""
    # Implementation details...
    pass

def add_topics_to_sheet1(workbook: Workbook, topics: list) -> None:
    """Add scraped topics to the Topics sheet."""
    # Implementation details...
    pass

def add_content_to_sheet2(workbook: Workbook, content: list) -> None:
    """Add generated content to the Content sheet."""
    # Implementation details...
    pass

def save_workbook(workbook: Workbook, output_dir: str, date: str) -> str:
    """Save workbook to outputs/content/ directory."""
    # Implementation details...
    pass

def main():
    parser = argparse.ArgumentParser(description="Manage BoBe content pipeline Excel files")
    # Argument parsing...
    pass

if __name__ == "__main__":
    main()
```

---

### Step 6: Create Nano Banana Pro Script

Create the Python script that calls Google's Nano Banana Pro API for image generation.

**Actions:**

- Create `scripts/nano_banana.py` with functions:
  - `generate_image(prompt, style, output_path)` - Generates image from prompt
  - `build_prompt(topic, content, style_template)` - Builds optimized image prompt
  - `save_image(image_data, path)` - Saves generated image to file

- Include error handling for API failures
- Support multiple output resolutions (1024x1024 default, 4K optional)

**Files affected:**

- `scripts/nano_banana.py` (create)

**Script specification:**

```python
#!/usr/bin/env python3
"""
BoBe Content Pipeline - Nano Banana Pro Image Generator
Generates images using Google's Nano Banana Pro (Gemini 3 Pro Image) API.

Environment variables:
- GOOGLE_AI_API_KEY: Your Google AI Studio API key

Usage:
    python scripts/nano_banana.py --prompt "Modern crypto trading dashboard" --output image.png
    python scripts/nano_banana.py --topic "DeFi yields" --content "Automate your trading" --style modern
"""

import os
import json
import argparse
import base64
from pathlib import Path
from google import genai

GOOGLE_AI_API_KEY = os.environ.get("GOOGLE_AI_API_KEY")
MODEL_ID = "gemini-3-pro-image-preview"

def generate_image(prompt: str, output_path: str, resolution: str = "1024x1024") -> str:
    """Generate an image using Nano Banana Pro."""
    # Implementation details...
    pass

def build_prompt(topic: str, content: str, style: str = "modern") -> str:
    """Build an optimized image generation prompt for BoBe content."""
    # Include BoBe brand elements, style guidelines
    # Implementation details...
    pass

def save_image(image_data: bytes, path: str) -> str:
    """Save generated image to file."""
    # Implementation details...
    pass

def main():
    parser = argparse.ArgumentParser(description="Generate BoBe content images with Nano Banana Pro")
    # Argument parsing...
    pass

if __name__ == "__main__":
    main()
```

---

### Step 7: Create Content Generator Skill

Create the skill for generating Telegram/Twitter copy from curated topics.

**Actions:**

- Create skill directory `.claude/skills/content-generator/`
- Create `SKILL.md` with:
  - Frontmatter defining name and description
  - Instructions for generating platform-specific content
  - Reference to content guidelines
  - Output format specifications

**Files affected:**

- `.claude/skills/content-generator/SKILL.md` (create)

**Skill content:**

```markdown
---
name: content-generator
description: Generate Telegram and Twitter content for BoBe from curated crypto/DeFi topics. Use when creating social media posts, threads, or announcements based on trending topics or news. Produces copy aligned with BoBe's transparent, educational, non-hype messaging style.
---

# Content Generator for BoBe

Generate platform-specific content (Twitter/Telegram) from crypto/DeFi topics.

## Input Requirements

- Topic summary or headline
- Source platform (where topic was found)
- Key points or quotes
- Target platform (Twitter or Telegram)

## Content Formats

### Twitter Single Post
- Max 280 characters
- Include hook, value prop, CTA
- No unrealistic APY claims
- Use relevant hashtags sparingly (2-3 max)

### Twitter Thread
- 3-5 tweets
- First tweet: Hook/question
- Middle tweets: Value/education
- Final tweet: CTA to learn more about BoBe

### Telegram Post
- Can be longer (up to 4096 chars)
- More educational/detailed
- Include context and explanation
- End with engagement question or CTA

## BoBe Messaging Guidelines

Read `reference/content-guidelines.md` for full guidelines.

Key principles:
- Transparent, not hype-driven
- Educational, not promotional
- Risk-aware, not guaranteeing returns
- Automation-focused, not speculation-focused

## Output Format

Return JSON:
```json
{
  "platform": "twitter|telegram",
  "format": "single|thread",
  "content": "...",
  "image_prompt": "Suggested image prompt for Nano Banana Pro",
  "hashtags": ["#DeFi", "#CryptoTrading"]
}
```
```

---

### Step 8: Create Image Generator Skill

Create the skill for generating images via Nano Banana Pro.

**Actions:**

- Create skill directory `.claude/skills/image-generator/`
- Create `SKILL.md` with:
  - Frontmatter defining name and description
  - Instructions for building effective image prompts
  - BoBe brand guidelines for visuals
  - Reference to nano_banana.py script

**Files affected:**

- `.claude/skills/image-generator/SKILL.md` (create)

**Skill content:**

```markdown
---
name: image-generator
description: Generate images for BoBe content using Nano Banana Pro (Gemini 3 Pro Image). Use when creating visuals for social media posts, infographics, or marketing materials. Handles prompt optimization for BoBe's brand style. Always reference brand assets in reference/bobe-brand/ for style consistency.
---

# Image Generator for BoBe

Generate branded images using Google's Nano Banana Pro API.

## Prerequisites

- `GOOGLE_AI_API_KEY` environment variable set
- Run via `scripts/nano_banana.py`
- Brand reference images in `reference/bobe-brand/`

## Brand Reference Images

Before generating images, review reference images in `reference/bobe-brand/`:
- `logo.png` - BoBe logo for overlay/reference
- `style-example-*.png` - Approved visual styles to match
- See `reference/bobe-brand/README.md` for color palette and guidelines

## Usage

```bash
python scripts/nano_banana.py --prompt "your prompt" --output outputs/content/image.png
python scripts/nano_banana.py --prompt "your prompt" --reference reference/bobe-brand/style-example-1.png --output image.png
```

## BoBe Visual Style Guidelines

### Style Elements (see reference images)
- Modern, clean aesthetic
- Blue/purple gradient accents (crypto-native)
- Minimalist design
- Professional, not "crypto bro" imagery
- Include subtle tech/automation motifs

### What to Include
- Clear focal point
- Text overlay space (if needed)
- High contrast for readability
- Professional quality

### What to Avoid
- Rocket/moon imagery
- Excessive crypto memes
- Cluttered designs
- Low-quality stock imagery feel

## Prompt Building

For best results, prompts should include:
1. Subject matter (what the image shows)
2. Style descriptor (modern, minimalist, professional)
3. Color guidance (use brand colors from reference/bobe-brand/README.md)
4. Mood (trustworthy, innovative, accessible)
5. Technical specs (high resolution, social media optimized)

Example prompt:
"Modern minimalist illustration of automated trading dashboard, blue and purple gradient accents matching BoBe brand style, clean white background, professional fintech aesthetic, high resolution, social media optimized"

## Output

Images saved to `outputs/content/` with naming convention:
`{date}_{topic_slug}_{platform}.png`
```

---

### Step 9: Create Content Pipeline Command

Create the main command that orchestrates the entire workflow.

**Actions:**

- Create `.claude/commands/content-pipeline.md` with:
  - Step-by-step workflow instructions
  - Integration with scripts and skills
  - User interaction points for topic selection
  - Error handling guidance

**Files affected:**

- `.claude/commands/content-pipeline.md` (create)

**Command content:**

```markdown
# Content Pipeline

> Daily content automation for BoBe: scrape → curate → generate → visualize

## Variables

date: $ARGUMENTS (optional, defaults to today's date in YYYY-MM-DD format)

---

## Prerequisites

Before running, ensure:
- `APIFY_API_TOKEN` environment variable is set
- `GOOGLE_AI_API_KEY` environment variable is set
- Python 3.8+ with required packages (requests, openpyxl, google-genai)

## Workflow

### Phase 1: Scrape & Curate

1. **Run Twitter scraper**
   ```bash
   python scripts/apify_scraper.py --platform twitter --keywords "defi,yield,trading bot,automation,AI trading,on-chain yield"
   ```

2. **Run Reddit scraper**
   ```bash
   python scripts/apify_scraper.py --platform reddit --subreddits "defi,cryptocurrency,ethfinance" --keywords "yield,automation,trading bot"
   ```

3. **Filter and rank results**
   - Apply relevance filtering using `reference/bobe-keywords.md`
   - Rank by engagement score
   - Output top 10-15 topics for review

4. **Create daily Excel workbook**
   ```bash
   python scripts/excel_manager.py --action create --date {date}
   ```

5. **Add topics to Sheet 1**
   ```bash
   python scripts/excel_manager.py --action add-topics --file outputs/content/{date}-content.xlsx --topics scraped_topics.json
   ```

### Phase 2: Topic Selection

Present the user with top 10-15 curated topics. Ask:
- "Here are today's top topics from Twitter and Reddit. Which 2-3 would you like me to create content for?"

Allow user to:
- Select from presented topics
- Provide custom topic
- Skip content generation

### Phase 3: Content Generation

For each selected topic:

1. **Generate content using content-generator skill**
   - Create Twitter thread version
   - Create Telegram post version
   - Generate image prompt suggestion

2. **Add content to Sheet 2**
   ```bash
   python scripts/excel_manager.py --action add-content --file outputs/content/{date}-content.xlsx --content generated_content.json
   ```

### Phase 4: Image Generation

For each piece of content:

1. **Generate image using image-generator skill**
   ```bash
   python scripts/nano_banana.py --prompt "{image_prompt}" --output outputs/content/{date}_{topic_slug}.png
   ```

2. **Update Excel with image paths**

### Phase 5: Review & Output

1. **Save final workbook**
2. **Present summary to user:**
   - Topics covered
   - Content generated (preview)
   - Images created (file paths)
   - Excel file location

3. **Ask if user wants to:**
   - Edit any content
   - Regenerate images
   - Export to clipboard for posting

---

## Output Files

All outputs saved to `outputs/content/`:
- `{date}-content.xlsx` - Full workbook with topics and content
- `{date}_{topic_slug}.png` - Generated images

## Error Handling

- If Apify fails: Report error, offer to retry or use cached data
- If image generation fails: Report error, offer to retry with modified prompt
- If Excel fails: Report error, output content to markdown instead
```

---

### Step 10: Update CLAUDE.md

Update the main workspace documentation to reflect new capabilities.

**Actions:**

- Add `/content-pipeline` to Commands section
- Add content-generator and image-generator to Skills section
- Document new output types in `outputs/content/`
- Add API setup requirements to Notes section

**Files affected:**

- `CLAUDE.md` (modify)

**Changes to make:**

Add to Commands section:
```markdown
### /content-pipeline [date]

**Purpose:** Run the daily content automation pipeline for BoBe.

Scrapes Twitter and Reddit for relevant crypto/DeFi topics, curates and ranks them, generates Telegram/Twitter copy for selected topics, and creates accompanying images. Outputs everything to a dated Excel workbook in `outputs/content/`.

Example: `/content-pipeline 2026-02-18`
```

Add new section after Commands:
```markdown
## Skills

This workspace includes specialized skills:

| Skill | Purpose |
|-------|---------|
| `content-generator` | Generate Telegram/Twitter copy from topics |
| `image-generator` | Create images using Nano Banana Pro |
| `skill-creator` | Create new skills |
| `mcp-integration` | Integrate MCP servers |
```

Add to Workspace Structure table:
```markdown
| `outputs/content/` | Daily content outputs (Excel, images) |
```

Add to Notes section:
```markdown
## API Requirements

For `/content-pipeline` to work:
- Set `APIFY_API_TOKEN` environment variable ([Get token](https://console.apify.com/account/integrations))
- Set `GOOGLE_AI_API_KEY` environment variable ([Get key](https://ai.google.dev/))
- Install Python dependencies: `pip install requests openpyxl google-genai`
```

---

## Connections & Dependencies

### Files That Reference This Area

| File | Reference |
|------|-----------|
| `CLAUDE.md` | Will document new command and skills |
| `context/BoBe Context.md` | Referenced by content-generator for messaging alignment |
| `context/RT BoBe Info.md` | Referenced for understanding Rut's priorities |

### Updates Needed for Consistency

- `CLAUDE.md` must be updated with new commands, skills, and output types
- `reference/` directory now contains API and content documentation
- `scripts/` directory now contains Python automation scripts
- `outputs/content/` directory must be created

### Impact on Existing Workflows

| Workflow | Impact |
|----------|--------|
| `/prime` | No change—new content is additive |
| `/create-plan` | No change—can be used to plan content enhancements |
| `/implement` | No change—can be used to implement this plan |
| Daily workflow | New `/content-pipeline` command added to daily options |

---

## Validation Checklist

How to verify the implementation is complete and correct:

- [ ] `outputs/content/` directory exists
- [ ] `reference/bobe-keywords.md` contains relevant keyword lists
- [ ] `reference/content-guidelines.md` contains BoBe messaging guidelines
- [ ] `reference/api-setup.md` contains setup instructions
- [ ] `reference/bobe-brand/` directory exists with README.md
- [ ] `reference/bobe-brand/` contains user-provided brand images (logo, style examples)
- [ ] `scripts/apify_scraper.py` exists and has proper structure
- [ ] `scripts/excel_manager.py` exists and has proper structure
- [ ] `scripts/nano_banana.py` exists and has proper structure
- [ ] `.claude/skills/content-generator/SKILL.md` has valid frontmatter
- [ ] `.claude/skills/image-generator/SKILL.md` has valid frontmatter
- [ ] `.claude/commands/content-pipeline.md` contains full workflow
- [ ] `CLAUDE.md` updated with new command, skills, and API requirements
- [ ] Python scripts are executable (`chmod +x`)

---

## Success Criteria

The implementation is complete when:

1. Running `/content-pipeline` initiates the full scraping → generation → output workflow
2. Excel workbooks are created in `outputs/content/` with proper two-sheet structure
3. Content-generator skill produces BoBe-aligned copy for Twitter and Telegram
4. Image-generator skill successfully calls Nano Banana Pro (when API key is configured)
5. CLAUDE.md accurately documents all new capabilities
6. All reference materials provide actionable guidance for future sessions

---

## Notes

### Future Enhancements

1. **Scheduling**: Add cron-style scheduling for daily automated runs
2. **Posting integration**: Add direct posting to Twitter/Telegram via APIs
3. **Analytics tracking**: Track content performance and feed back into curation
4. **A/B testing**: Generate multiple content variants for testing
5. **Competitor monitoring**: Add competitor content tracking

### Python Dependencies

```
requests>=2.28.0
openpyxl>=3.1.0
google-genai>=1.52.0
```

### Rate Limits

- Apify: Depends on plan; free tier includes $5/month credits
- Nano Banana Pro: ~$0.134 per standard image, $0.24 for 4K

### Testing Without API Keys

Scripts should include mock modes for testing without actual API calls:
```bash
python scripts/apify_scraper.py --mock
python scripts/nano_banana.py --mock
```

### Apify Actor IDs

For reference, these are the recommended Apify actors:
- Twitter: `apidojo/tweet-scraper` (Tweet Scraper V2)
- Reddit: `trudax/reddit-scraper` (Reddit Scraper)

Both support keyword search and return structured JSON data.
