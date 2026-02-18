#!/usr/bin/env python3
"""
BoBe Content Pipeline - Image Generator (Gemini)
Generates branded images using Google's Gemini image generation API.
Sends actual BoBe logo + mascot reference images for accurate character/logo fidelity.

Environment variables (loaded from .env):
  GOOGLE_AI_API_KEY: Your Google AI Studio API key

Usage:
  python scripts/nano_banana.py --topic "DCA bots beat emotion" --headline "Steady is good." --output image.png
  python scripts/nano_banana.py --prompt "Full custom prompt" --output image.png
  python scripts/nano_banana.py --mock --output test.png
  python scripts/nano_banana.py --no-reference --prompt "..." --output image.png  # skip reference images
"""

import os
import sys
import argparse
import base64
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

GOOGLE_AI_API_KEY = os.environ.get("GOOGLE_AI_API_KEY")
OUTPUT_DIR = Path(__file__).parent.parent / "outputs" / "content"
BRAND_DIR = Path(__file__).parent.parent / "reference" / "bobe-brand"

# Default reference images sent with every generation
DEFAULT_REFERENCES = [
    BRAND_DIR / "logo.png",                     # Exact logo to reproduce
    BRAND_DIR / "banner example 1.png",         # Mascot reference: minimal/clean
    BRAND_DIR / "banner example 2.png",         # Mascot reference: with trading setup
    BRAND_DIR / "banner example 4.png",         # Mascot reference: outdoor/action
]

STYLE_PRESETS = {
    "minimal": "minimalist clean design, single focal point, plenty of negative space on dark navy",
    "tech": "floating holographic trading UI panels and candlestick charts in background, tech fintech aesthetic",
    "neon": "cyberpunk neon city background with blue and pink neon light trails, atmospheric night scene",
    "outdoor": "photorealistic urban outdoor setting, city street, natural lighting",
    "notification": "realistic smartphone mockup showing BoBe app notification on screen",
}


def load_reference_images(paths: list) -> list:
    """Load reference images, skipping any that don't exist."""
    from google.genai import types

    parts = []
    for path in paths:
        p = Path(path)
        if not p.exists():
            print(f"  Warning: reference image not found, skipping: {p}")
            continue
        mime = "image/jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else "image/png"
        with open(p, "rb") as f:
            data = f.read()
        parts.append(types.Part.from_bytes(data=data, mime_type=mime))
        print(f"  Reference loaded: {p.name}")
    return parts


def build_prompt(
    topic: str,
    headline: str = "",
    style: str = "tech",
    extra: str = ""
) -> str:
    """Build the text instruction prompt. Reference images are passed separately."""
    style_desc = STYLE_PRESETS.get(style, STYLE_PRESETS["tech"])
    headline_part = f'\n- Include the bold white headline text: "{headline}"' if headline else ""

    prompt = f"""You are given reference images:
- Image 1: The exact BoBe APP logo — reproduce it exactly in the top-left corner
- Images 2-4: The BoBe mascot character — a 3D chibi figurine with round thick-framed glasses, short styled hair, white BoBe t-shirt, chubby round face. Replicate this character exactly with the same proportions, features, and style.

Generate a new high-quality 16:9 social media banner image with these requirements:
- MASCOT: Use the exact same mascot character shown in the reference images (same glasses, same face, same proportions, same BoBe t-shirt)
- LOGO: Place the exact BoBe APP logo in the top-left corner, reproduced faithfully from the reference
- SCENE: {topic}
- STYLE: {style_desc}
- BACKGROUND: Deep dark navy gradient (dark blue-black)
- COMPOSITION: Professional social media banner, mascot prominent on the right side{headline_part}
- QUALITY: Cinematic 3D render quality, high resolution"""

    if extra:
        prompt += f"\n- ADDITIONAL: {extra}"

    return prompt


def generate_image(prompt: str, output_path: str, reference_paths: list = None) -> str:
    """Generate an image using Google Gemini with reference images for mascot/logo fidelity."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("Error: google-genai package not installed.")
        print("Run: pip install google-genai")
        sys.exit(1)

    if not GOOGLE_AI_API_KEY:
        raise ValueError("GOOGLE_AI_API_KEY not set. Check your .env file.")

    client = genai.Client(api_key=GOOGLE_AI_API_KEY)

    # Build multimodal contents: reference images first, then text prompt
    if reference_paths is None:
        reference_paths = DEFAULT_REFERENCES

    print(f"  Loading {len(reference_paths)} reference images...")
    image_parts = load_reference_images(reference_paths)

    if not image_parts:
        print("  Warning: no reference images loaded — falling back to text-only prompt")

    # Combine: images + text instruction
    contents = image_parts + [types.Part.from_text(text=prompt)]

    print(f"  Generating image with {len(image_parts)} reference(s)...")
    print(f"  Prompt: {prompt[:120].strip()}...")

    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
        ),
    )

    # Extract image data from response
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            image_data = part.inline_data.data
            return save_image(image_data, output_path)

    raise RuntimeError("No image data returned from Gemini API")


def save_image(image_data: bytes, path: str) -> str:
    """Save generated image bytes to file."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "wb") as f:
        f.write(image_data)

    print(f"  Image saved: {output_path}")
    return str(output_path)


def mock_generate(output_path: str) -> str:
    """Create a placeholder image for testing without API calls."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    minimal_png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )

    placeholder_path = str(output_path).replace(".png", "_MOCK_PLACEHOLDER.png")
    with open(placeholder_path, "wb") as f:
        f.write(minimal_png)

    print(f"  Mock placeholder: {placeholder_path}")
    return placeholder_path


def generate_for_content(topic: str, content_text: str, date: str, platform: str, style: str = "tech") -> dict:
    """High-level helper: build prompt metadata for a piece of content."""
    first_sentence = content_text.split(".")[0].split("\n")[0]
    words = first_sentence.split()
    headline = " ".join(words[:6]) + ("..." if len(words) > 6 else "")

    prompt = build_prompt(topic=topic, headline=headline, style=style)
    topic_slug = topic.lower().replace(" ", "_")[:30]
    filename = f"{date}_{topic_slug}_{platform}.png"
    output_path = OUTPUT_DIR / filename

    return {
        "prompt": prompt,
        "output_path": str(output_path),
        "headline": headline,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate BoBe branded images with Gemini + reference images")
    parser.add_argument("--prompt", default=None,
                        help="Full custom text instruction (overrides topic/headline builder)")
    parser.add_argument("--topic", default="automated crypto trading",
                        help="Scene/topic for the image")
    parser.add_argument("--headline", default="",
                        help="Short headline text to include on the image")
    parser.add_argument("--style", choices=list(STYLE_PRESETS.keys()), default="tech",
                        help="Visual style preset")
    parser.add_argument("--output", default=None,
                        help="Output file path")
    parser.add_argument("--reference", action="append", default=None,
                        help="Additional reference image path (can be used multiple times)")
    parser.add_argument("--no-reference", action="store_true",
                        help="Disable reference images — text-only prompt")
    parser.add_argument("--mock", action="store_true",
                        help="Mock mode — no API call")
    parser.add_argument("--show-prompt", action="store_true",
                        help="Print full text prompt and exit without generating")

    args = parser.parse_args()

    # Determine reference images to use
    if args.no_reference:
        reference_paths = []
    elif args.reference:
        reference_paths = [Path(r) for r in args.reference]
    else:
        reference_paths = DEFAULT_REFERENCES

    # Build text prompt
    if args.prompt:
        prompt = args.prompt
    else:
        prompt = build_prompt(topic=args.topic, headline=args.headline, style=args.style)

    if args.show_prompt:
        print("\n--- REFERENCE IMAGES ---")
        for r in reference_paths:
            exists = "✓" if Path(r).exists() else "✗ missing"
            print(f"  {exists}  {r}")
        print("\n--- TEXT PROMPT ---")
        print(prompt)
        return

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
        topic_slug = args.topic.lower().replace(" ", "_")[:30]
        output_path = str(OUTPUT_DIR / f"{date_str}_{topic_slug}.png")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\nGenerating BoBe image...")
    print(f"Style: {args.style}")
    print(f"Output: {output_path}")
    print(f"References: {len(reference_paths)} image(s)")

    if args.mock:
        print("Running in MOCK mode — no API call made.")
        result_path = mock_generate(output_path)
    else:
        result_path = generate_image(prompt, output_path, reference_paths)

    print(f"\nDone: {result_path}")
    return result_path


if __name__ == "__main__":
    main()
