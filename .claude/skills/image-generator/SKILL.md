---
name: image-generator
description: Generate branded images for BoBe content using Google's Gemini image generation API via scripts/nano_banana.py. Use when creating visuals for social media posts, banners, or marketing materials. Handles prompt optimization for BoBe's mascot-driven brand style. Always reference brand assets in reference/bobe-brand/ for style consistency.
---

# Image Generator for BoBe

Generate branded images using the Gemini image generation API (scripts/nano_banana.py).

## Prerequisites

- `GOOGLE_AI_API_KEY` in `.env` file
- Python packages installed: `pip install google-genai python-dotenv`
- Brand reference images in `reference/bobe-brand/`

## Quick Usage

```bash
# Standard generation — automatically attaches logo + mascot reference images
python scripts/nano_banana.py --topic "automated trading beats emotion" --headline "Steady is good." --style tech --output outputs/content/image.png

# Generate from full custom text instruction (reference images still attached by default)
python scripts/nano_banana.py --prompt "your full instruction here" --output outputs/content/image.png

# Preview prompt + reference list without generating
python scripts/nano_banana.py --topic "DCA strategy" --headline "Just let it run." --show-prompt

# Add extra reference images (e.g. a specific banner example)
python scripts/nano_banana.py --topic "..." --reference reference/bobe-brand/banner\ example\ 5.png --output image.png

# Skip reference images (text-only fallback)
python scripts/nano_banana.py --no-reference --prompt "..." --output image.png

# Test without API call
python scripts/nano_banana.py --mock --output outputs/content/test.png
```

## How Reference Images Work

Every generation automatically sends **4 reference images** to Gemini alongside the text prompt:
1. `reference/bobe-brand/logo.png` — so Gemini reproduces the exact BoBe APP logo
2. `reference/bobe-brand/banner example 1.png` — mascot reference (clean/minimal style)
3. `reference/bobe-brand/banner example 2.png` — mascot reference (with trading setup)
4. `reference/bobe-brand/banner example 4.png` — mascot reference (action/outdoor)

Gemini is instructed to **replicate the mascot exactly** — same face, same glasses, same proportions, same BoBe t-shirt — and to **reproduce the logo faithfully** in the top-left corner.

## Style Presets

| Preset | Description | When to Use |
|--------|-------------|-------------|
| `tech` | Floating holographic UI panels, charts, tech aesthetic | Trading/automation topics |
| `minimal` | Clean, single focal point, dark navy | Simple message posts |
| `neon` | Cyberpunk city, neon blue/pink lights | High energy / launch posts |
| `outdoor` | Photorealistic urban setting | Relatable/lifestyle content |
| `notification` | Smartphone showing BoBe app | Social proof / result posts |

## The BoBe Mascot (Always Include)

All prompts must feature the BoBe mascot. Use this exact description:

> **3D clay chibi figurine, young Asian man, round thick-framed dark glasses, short dark styled hair, wearing white BoBe t-shirt, cute round chubby face, chibi proportions**

See `reference/bobe-brand/README.md` for the full prompt template and example images.

## Brand Colors

| Color | Hex | Use In Prompts |
|-------|-----|----------------|
| Dark BG | #111B32 → #070A1B | Default background gradient |
| Blue | #1589DC → #49ACF2 | Accent, charts, highlights |
| Green | #5BD69F | Positive results, yield numbers |
| Pink | #FF4FDA → #EE01BC | Energy accents, cyberpunk |
| White | #FFFFFF | All headline text |

## Prompt Template

```
BoBe mascot (3D clay chibi figurine, young Asian man with round dark glasses, white BoBe t-shirt)
[SCENARIO], [STYLE DESCRIPTION],
deep dark navy background (#111B32 to #070A1B),
bold white headline text "[HEADLINE]" in upper area,
BoBe APP logo top-left corner,
professional social media banner composition,
high resolution, 16:9 aspect ratio,
cinematic 3D render quality
```

## Working with Content Generator Output

When using output from the `content-generator` skill, extract the `image_prompt` field and pass directly:

```bash
# If content generator returned image_prompt, use it directly:
python scripts/nano_banana.py --prompt "PASTE_IMAGE_PROMPT_HERE" --output outputs/content/DATE_TOPIC_PLATFORM.png
```

## Output Naming Convention

Files saved to `outputs/content/` should follow:
```
{YYYY-MM-DD}_{topic-slug}_{platform}.png
```

Example: `2026-02-18_dca-beats-emotion_twitter.png`

## Quality Tips

1. **Be specific about the scenario** — "sitting at trading desk" > "working with crypto"
2. **Include chart colors** — "green upward trading charts" signals positive sentiment
3. **Specify headline placement** — "bold white text top-left" or "centered at top"
4. **Match the brand examples** — study `reference/bobe-brand/banner example *.png` for reference
5. **Keep headline short** — 4–6 words max for legibility in generated images
