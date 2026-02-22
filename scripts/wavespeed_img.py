#!/usr/bin/env python3
"""
Russian Image Generator via WaveSpeed.ai Seedream 4.5

Generates branded images with Cyrillic text overlays for Russian-language content.
Multi-client: reads brand name and mascot description from client config.
Async workflow: submit, poll, download.

Usage:
  python scripts/wavespeed_img.py --prompt "..." --output path/to/output.png
  python scripts/wavespeed_img.py --topic "Grid trading" --headline "Торговля ботом" --style tech --output path.png
  python scripts/wavespeed_img.py --prompt "..." --output path.png --mock
  python scripts/wavespeed_img.py --client newclient --topic "..." --headline "..." --output path.png

  # Translate an existing EN image to Russian (image-to-image edit):
  python scripts/wavespeed_img.py --edit-image path/to/en_image.png --output path/to/ru_image.png
"""

import os
import sys
import time
import base64
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent))

import client_config

WAVESPEED_API_KEY = os.getenv("WAVESPEED_API_KEY")
API_BASE = "https://api.wavespeed.ai/api/v3"
MODEL_ENDPOINT = f"{API_BASE}/bytedance/seedream-v4.5"
EDIT_ENDPOINT = f"{API_BASE}/bytedance/seedream-v4.5/edit"
POLL_ENDPOINT = f"{API_BASE}/predictions"


def generate_image(prompt, output_path, size="2560*1440", timeout=120):
    """Submit image generation, poll for completion, download result."""
    if not WAVESPEED_API_KEY:
        raise RuntimeError("WAVESPEED_API_KEY not set in .env")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {WAVESPEED_API_KEY}",
    }
    payload = {"prompt": prompt, "size": size}

    # Submit
    resp = requests.post(MODEL_ENDPOINT, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    request_id = data["data"]["id"]
    print(f"  Submitted: {request_id}")

    # Poll
    start = time.time()
    while time.time() - start < timeout:
        poll = requests.get(f"{POLL_ENDPOINT}/{request_id}/result", headers=headers)
        poll.raise_for_status()
        result = poll.json()
        status = result["data"]["status"]
        if status == "completed":
            image_url = result["data"]["outputs"][0]
            img_resp = requests.get(image_url)
            img_resp.raise_for_status()
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(img_resp.content)
            print(f"  Saved: {output_path}")
            return str(output_path)
        elif status == "failed":
            raise RuntimeError(f"Image generation failed: {result['data'].get('error')}")
        time.sleep(2)

    raise TimeoutError(f"Image generation timed out after {timeout}s")


def build_prompt_ru(topic, headline_ru, style="tech", client_id=None):
    """Build a detailed prompt for a branded Russian image with Cyrillic headline."""
    config = client_config.load_config(client_id)
    brand = config.get("brand", {})
    display_name = config.get("display_name", "Brand")

    mascot_desc = brand.get("mascot_description", "brand mascot character")
    logo_desc = brand.get("logo_description", f'Small "{display_name}" logo text in bright blue')
    bg_style = brand.get("background_style", "Dark navy to deep midnight blue gradient")

    style_presets = config.get("image", {}).get("style_presets", {})
    style_desc = style_presets.get(style, style_presets.get("tech", "tech fintech aesthetic"))

    return f"""Create a 16:9 banner image for {display_name}.

Background: {bg_style}, {style_desc}

Character: {mascot_desc}. Place the mascot on the right side of the image.

Text: Include bold white Cyrillic headline text: "{headline_ru}"
Place the headline on the left side, large and readable.

Top-left corner: {logo_desc}.

Style: Cinematic 3D render, professional aesthetic.
Topic context: {topic}"""


def translate_image(source_path, output_path, size="2560*1440", timeout=120, client_id=None):
    """Translate an existing English image to Russian using Seedream 4.5 Edit."""
    if not WAVESPEED_API_KEY:
        raise RuntimeError("WAVESPEED_API_KEY not set in .env")

    config = client_config.load_config(client_id)
    display_name = config.get("display_name", "Brand")

    b64 = base64.b64encode(Path(source_path).read_bytes()).decode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {WAVESPEED_API_KEY}",
    }
    payload = {
        "prompt": (
            "Translate all English text in this image to Russian (Cyrillic). "
            "Keep the same layout, mascot, colors, and design. "
            f"Keep the brand name '{display_name}' unchanged in the logo."
        ),
        "images": [f"data:image/png;base64,{b64}"],
        "size": size,
    }

    resp = requests.post(EDIT_ENDPOINT, json=payload, headers=headers)
    resp.raise_for_status()
    request_id = resp.json()["data"]["id"]
    print(f"  Submitted (edit): {request_id}")

    start = time.time()
    while time.time() - start < timeout:
        poll = requests.get(f"{POLL_ENDPOINT}/{request_id}/result", headers=headers)
        poll.raise_for_status()
        result = poll.json()
        status = result["data"]["status"]
        if status == "completed":
            image_url = result["data"]["outputs"][0]
            img_resp = requests.get(image_url)
            img_resp.raise_for_status()
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(img_resp.content)
            print(f"  Saved: {output_path}")
            return str(output_path)
        elif status == "failed":
            raise RuntimeError(f"Image edit failed: {result['data'].get('error')}")
        time.sleep(2)

    raise TimeoutError(f"Image edit timed out after {timeout}s")


def mock_generate(output_path):
    """Create a placeholder PNG without calling the API."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    # Minimal valid 1x1 PNG
    png_bytes = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
        b'\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18'
        b'\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    Path(output_path).write_bytes(png_bytes)
    print(f"  [MOCK] Placeholder created: {output_path}")
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Generate Russian branded images via WaveSpeed.ai Seedream 4.5"
    )
    parser.add_argument("--prompt", default=None,
                        help="Full prompt text (use instead of --topic/--headline)")
    parser.add_argument("--topic", default=None,
                        help="Topic for context (used with --headline)")
    parser.add_argument("--headline", default=None,
                        help="Russian headline text (Cyrillic)")
    parser.add_argument("--style", default="tech",
                        choices=["minimal", "tech", "notification"],
                        help="Image style preset")
    parser.add_argument("--edit-image", default=None,
                        help="Path to existing EN image to translate to Russian (image-to-image)")
    parser.add_argument("--output", required=True,
                        help="Output file path (.png)")
    parser.add_argument("--size", default="2560*1440",
                        help="Image size in WaveSpeed format (default: 2560*1440)")
    parser.add_argument("--mock", action="store_true",
                        help="Create placeholder without calling API")
    client_config.add_client_arg(parser)
    args = parser.parse_args()

    active_client = client_config.resolve_client(args)

    if args.mock:
        mock_generate(args.output)
        return

    if args.edit_image:
        translate_image(args.edit_image, args.output, size=args.size, client_id=active_client)
    elif args.prompt:
        generate_image(args.prompt, args.output, size=args.size)
    elif args.topic and args.headline:
        prompt = build_prompt_ru(args.topic, args.headline, args.style, client_id=active_client)
        generate_image(prompt, args.output, size=args.size)
    else:
        parser.error("Provide --edit-image, --prompt, or both --topic and --headline")


if __name__ == "__main__":
    main()
