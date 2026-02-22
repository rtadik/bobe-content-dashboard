---
name: image-generator
description: Generate branded images for the active client's content using WaveSpeed GPT-Image-1.5 via scripts/nano_banana.py (EN) and WaveSpeed Seedream 4.5 via scripts/wavespeed_img.py (RU). Use when creating visuals for social media posts, banners, or marketing materials. Loads mascot, colors, and style from client config.
---

# Image Generator

Generate branded images using WaveSpeed GPT-Image-1.5 (EN, `scripts/nano_banana.py`) and WaveSpeed Seedream 4.5 (RU, `scripts/wavespeed_img.py`).

## Prerequisites

- `WAVESPEED_API_KEY` in `.env` file
- Python packages installed: `pip install requests python-dotenv`
- Brand reference images in `clients/{active_client}/brand/`
- Client config at `clients/{active_client}/config.json`

## Quick Usage

```bash
# EN image: automatically loads reference images from client config
python scripts/nano_banana.py --topic "automated trading beats emotion" --headline "Steady is good." --style tech --output outputs/content/bobe/image.png

# Generate from full custom prompt
python scripts/nano_banana.py --prompt "your full instruction here" --output outputs/content/bobe/image.png

# Preview prompt + reference list without generating
python scripts/nano_banana.py --topic "DCA strategy" --headline "Just let it run." --show-prompt

# Add extra reference images
python scripts/nano_banana.py --topic "..." --reference clients/bobe/brand/banner\ example\ 5.png --output image.png

# Skip reference images (text-only fallback)
python scripts/nano_banana.py --no-reference --prompt "..." --output image.png

# RU image: via WaveSpeed Seedream 4.5
python scripts/wavespeed_img.py --prompt "Russian image prompt..." --output outputs/content/bobe/image_ru.png

# Override active client
python scripts/nano_banana.py --client otherclient --topic "..." --output image.png

# Test without API call
python scripts/nano_banana.py --mock --output outputs/content/test.png
```

## How Reference Images Work

Reference images are configured per client in `clients/{active_client}/config.json` under `brand.reference_images`. The GPT-Image-1.5 Edit endpoint automatically loads these images alongside the text prompt. Typical references include a logo and banner examples showing the client's mascot/character style.

The model is instructed to replicate the client's mascot and logo faithfully based on the config's `mascot_description` and `logo_description` fields.

## Style Presets

Style presets are configured per client in `config.json` under `content.style_presets`. Common presets:

| Preset | Description | When to Use |
|--------|-------------|-------------|
| `tech` | Floating holographic UI panels, charts, tech aesthetic | Trading/automation topics |
| `minimal` | Clean, single focal point | Simple message posts |
| `neon` | Cyberpunk city, neon lights | High energy / launch posts |
| `outdoor` | Photorealistic urban setting | Relatable/lifestyle content |
| `notification` | Smartphone showing app | Social proof / result posts |

## Mascot / Character

Each client's mascot or character description is loaded from `config.json` → `brand.mascot_description`. Do not hardcode any mascot descriptions. Read the config at runtime.

See `clients/{active_client}/brand/README.md` for reference images and style guidance.

## Brand Colors

Brand colors are loaded from `config.json` → `brand.colors`. Do not hardcode color values.

## Prompt Template

The prompt is built dynamically from client config values. The general structure:

```
{mascot_description}
[SCENARIO], [STYLE DESCRIPTION],
{background_style},
bold white headline text "[HEADLINE]" in upper area,
{logo_description} top-left corner,
professional social media banner composition,
high resolution, 16:9 aspect ratio,
cinematic 3D render quality
```

## Working with Content Generator Output

When using output from the `content-generator` skill, extract the `image_prompt` field and pass directly:

```bash
# EN image from content generator prompt:
python scripts/nano_banana.py --prompt "PASTE_IMAGE_PROMPT_HERE" --output outputs/content/{active_client}/images/DATE_TOPIC_PLATFORM.png

# RU image from content generator prompt:
python scripts/wavespeed_img.py --prompt "PASTE_IMAGE_PROMPT_RU_HERE" --output outputs/content/{active_client}/images/DATE_TOPIC_PLATFORM_ru.png
```

## Output Naming Convention

Files saved to `outputs/content/{active_client}/images/` should follow:
```
{YYYY-MM-DD}_{topic-slug}_{platform}.png      # EN
{YYYY-MM-DD}_{topic-slug}_{platform}_ru.png    # RU
```

Example: `2026-02-18_dca-beats-emotion_twitter.png`

## Quality Tips

1. **Be specific about the scenario** — "sitting at trading desk" > "working with crypto"
2. **Include chart colors** — "green upward trading charts" signals positive sentiment
3. **Specify headline placement** — "bold white text top-left" or "centered at top"
4. **Match the brand examples** — study `clients/{active_client}/brand/` for reference
5. **Keep headline short** — 4–6 words max for legibility in generated images
