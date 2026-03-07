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
from client_config import get_api_key

try:
    import r2_uploader
    HAS_R2 = True
except ImportError:
    HAS_R2 = False

API_BASE = "https://api.wavespeed.ai/api/v3"
MODEL_ENDPOINT = f"{API_BASE}/bytedance/seedream-v4.5"
EDIT_ENDPOINT = f"{API_BASE}/bytedance/seedream-v4.5/edit"
POLL_ENDPOINT = f"{API_BASE}/predictions"


def generate_image(prompt, output_path, size="2560*1440", timeout=120, client_id=None, upload_r2=True):
    """Submit image generation, poll for completion, download result.
    Returns (local_path, r2_url) tuple. r2_url is None if R2 not configured or upload_r2=False.
    """
    api_key = get_api_key(client_id or "bobe", "wavespeed_ru")
    if not api_key:
        raise RuntimeError("WAVESPEED_API_KEY not set in .env")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
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

            r2_url = None
            if upload_r2 and HAS_R2:
                try:
                    if r2_uploader.is_configured():
                        filename = Path(output_path).name
                        week_of = filename.split("_")[0] if "_" in filename else "unknown"
                        key = r2_uploader.make_key(client_id or "bobe", week_of, filename)
                        r2_url = r2_uploader.upload_bytes(img_resp.content, key)
                        print(f"  Uploaded to R2: {r2_url}")
                except Exception as e:
                    print(f"  R2 upload failed (image saved locally): {e}")

            return str(output_path), r2_url
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

Character (REQUIRED): {mascot_desc}. Place the mascot prominently on the right side of the image. The mascot must be clearly visible and match this exact description.

Text: Include bold white Cyrillic headline text: "{headline_ru}"
Place the headline on the left side, large and readable.

Logo (REQUIRED): Top-left corner — {logo_desc}. The logo must be clearly visible and placed exactly in the top-left corner.

Style: Cinematic 3D render, professional aesthetic.
Topic context: {topic}"""


def translate_image(source_path, output_path, size="2560*1440", timeout=120, client_id=None, upload_r2=True):
    """Translate an existing English image to Russian using Seedream 4.5 Edit.
    Returns (local_path, r2_url) tuple. r2_url is None if R2 not configured or upload_r2=False.
    """
    api_key = get_api_key(client_id or "bobe", "wavespeed_ru")
    if not api_key:
        raise RuntimeError("WAVESPEED_API_KEY not set in .env")

    config = client_config.load_config(client_id)
    display_name = config.get("display_name", "Brand")

    b64 = base64.b64encode(Path(source_path).read_bytes()).decode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "prompt": (
            "Translate all English text in this image to Russian (Cyrillic). "
            "Keep the same layout, colors, and overall design unchanged. "
            "Keep the mascot character exactly as-is — same pose, outfit, expression, and style. "
            f"Keep the '{display_name}' logo exactly as-is in the top-left corner. "
            "Only translate the text; do not alter any visual elements."
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

            r2_url = None
            if upload_r2 and HAS_R2:
                try:
                    if r2_uploader.is_configured():
                        filename = Path(output_path).name
                        week_of = filename.split("_")[0] if "_" in filename else "unknown"
                        key = r2_uploader.make_key(client_id or "bobe", week_of, filename)
                        r2_url = r2_uploader.upload_bytes(img_resp.content, key)
                        print(f"  Uploaded to R2: {r2_url}")
                except Exception as e:
                    print(f"  R2 upload failed (image saved locally): {e}")

            return str(output_path), r2_url
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
    return str(output_path), None


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
    parser.add_argument("--no-r2", action="store_true",
                        help="Skip R2 upload even if configured")
    client_config.add_client_arg(parser)
    args = parser.parse_args()

    active_client = client_config.resolve_client(args)

    if args.mock:
        mock_generate(args.output)
        return

    upload_r2 = not args.no_r2
    if args.edit_image:
        path, r2_url = translate_image(args.edit_image, args.output, size=args.size,
                                       upload_r2=upload_r2, client_id=active_client)
        if r2_url:
            print(f"  R2: {r2_url}")
    elif args.prompt:
        path, r2_url = generate_image(args.prompt, args.output, size=args.size,
                                      upload_r2=upload_r2, client_id=active_client)
        if r2_url:
            print(f"  R2: {r2_url}")
    elif args.topic and args.headline:
        prompt = build_prompt_ru(args.topic, args.headline, args.style, client_id=active_client)
        path, r2_url = generate_image(prompt, args.output, size=args.size,
                                      upload_r2=upload_r2, client_id=active_client)
        if r2_url:
            print(f"  R2: {r2_url}")
    else:
        parser.error("Provide --edit-image, --prompt, or both --topic and --headline")


if __name__ == "__main__":
    main()
