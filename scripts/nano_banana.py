#!/usr/bin/env python3
"""
BoBe Content Pipeline - Image Generator (WaveSpeed GPT-Image-1.5)
Generates branded images using WaveSpeed.ai's GPT-Image-1.5 Edit API.
Sends BoBe logo + mascot reference images for accurate character/logo fidelity.

Environment variables (loaded from .env):
  WAVESPEED_API_KEY: Your WaveSpeed.ai API key

Usage:
  python scripts/nano_banana.py --topic "DCA bots beat emotion" --headline "Steady is good." --output image.png
  python scripts/nano_banana.py --prompt "Full custom prompt" --output image.png
  python scripts/nano_banana.py --mock --output test.png
  python scripts/nano_banana.py --no-reference --prompt "..." --output image.png  # skip reference images
"""

import os
import sys
import time
import base64
import argparse
import requests
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

WAVESPEED_API_KEY = os.environ.get("WAVESPEED_API_KEY")
OUTPUT_DIR = Path(__file__).parent.parent / "outputs" / "content"
BRAND_DIR = Path(__file__).parent.parent / "reference" / "bobe-brand"

API_BASE = "https://api.wavespeed.ai/api/v3"
EDIT_ENDPOINT = f"{API_BASE}/openai/gpt-image-1.5/edit"
TEXT_ENDPOINT = f"{API_BASE}/openai/gpt-image-1.5/text-to-image"
POLL_ENDPOINT = f"{API_BASE}/predictions"

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
    """Load reference images as base64 data URIs for the WaveSpeed API."""
    images = []
    for path in paths:
        p = Path(path)
        if not p.exists():
            print(f"  Warning: reference image not found, skipping: {p}")
            continue
        mime = "image/jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else "image/png"
        b64 = base64.b64encode(p.read_bytes()).decode()
        images.append(f"data:{mime};base64,{b64}")
        print(f"  Reference loaded: {p.name}")
    return images


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


def _poll_result(request_id, headers, timeout=180):
    """Poll WaveSpeed API for job completion and return the image URL."""
    start = time.time()
    while time.time() - start < timeout:
        poll = requests.get(f"{POLL_ENDPOINT}/{request_id}/result", headers=headers)
        poll.raise_for_status()
        result = poll.json()
        status = result["data"]["status"]
        if status == "completed":
            return result["data"]["outputs"][0]
        elif status == "failed":
            raise RuntimeError(f"Image generation failed: {result['data'].get('error')}")
        time.sleep(3)
    raise TimeoutError(f"Image generation timed out after {timeout}s")


def generate_image(prompt: str, output_path: str, reference_paths: list = None) -> str:
    """Generate an image using WaveSpeed GPT-Image-1.5 with reference images for brand fidelity.

    If reference_paths are provided, uses the Edit endpoint (supports up to 10 reference images).
    If no references, falls back to the Text-to-Image endpoint.
    """
    if not WAVESPEED_API_KEY:
        raise ValueError("WAVESPEED_API_KEY not set. Check your .env file.")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {WAVESPEED_API_KEY}",
    }

    if reference_paths is None:
        reference_paths = DEFAULT_REFERENCES

    # Load reference images
    print(f"  Loading {len(reference_paths)} reference images...")
    ref_images = load_reference_images(reference_paths)

    if ref_images:
        # Use Edit endpoint with reference images + input_fidelity
        print(f"  Generating image with {len(ref_images)} reference(s) via GPT-Image-1.5 Edit...")
        print(f"  Prompt: {prompt[:120].strip()}...")

        payload = {
            "prompt": prompt,
            "images": ref_images,
            "size": "1536*1024",
            "quality": "medium",
            "input_fidelity": "high",
            "output_format": "png",
        }
        resp = requests.post(EDIT_ENDPOINT, json=payload, headers=headers)
        resp.raise_for_status()
    else:
        # Fallback to Text-to-Image (no references)
        print("  No reference images, using GPT-Image-1.5 Text-to-Image...")
        print(f"  Prompt: {prompt[:120].strip()}...")

        payload = {
            "prompt": prompt,
            "size": "1536*1024",
            "quality": "medium",
            "output_format": "png",
        }
        resp = requests.post(TEXT_ENDPOINT, json=payload, headers=headers)
        resp.raise_for_status()

    data = resp.json()
    request_id = data["data"]["id"]
    print(f"  Submitted: {request_id}")

    # Poll for completion
    image_url = _poll_result(request_id, headers)

    # Download and save
    img_resp = requests.get(image_url)
    img_resp.raise_for_status()
    return save_image(img_resp.content, output_path)


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

    print(f"  [MOCK] Placeholder created: {placeholder_path}")
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
    parser = argparse.ArgumentParser(description="Generate BoBe branded images with WaveSpeed GPT-Image-1.5 + reference images")
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

    print(f"\nGenerating BoBe image via WaveSpeed GPT-Image-1.5...")
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
