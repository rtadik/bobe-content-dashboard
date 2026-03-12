#!/usr/bin/env python3
"""
Content Pipeline - Image Generator (WaveSpeed GPT-Image-1.5)
Generates branded images using WaveSpeed.ai's GPT-Image-1.5 Edit API.
Sends client brand reference images for accurate character/logo fidelity.

Multi-client: reads brand assets and mascot description from client config.

Environment variables (loaded from .env):
  WAVESPEED_API_KEY: Your WaveSpeed.ai API key

Usage:
  python scripts/nano_banana.py --topic "DCA bots beat emotion" --headline "Steady is good." --output image.png
  python scripts/nano_banana.py --prompt "Full custom prompt" --output image.png
  python scripts/nano_banana.py --mock --output test.png
  python scripts/nano_banana.py --no-reference --prompt "..." --output image.png  # skip reference images
  python scripts/nano_banana.py --client newclient --topic "..." --output image.png
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
EDIT_ENDPOINT = f"{API_BASE}/openai/gpt-image-1.5/edit"
TEXT_ENDPOINT = f"{API_BASE}/openai/gpt-image-1.5/text-to-image"
POLL_ENDPOINT = f"{API_BASE}/predictions"


def get_default_references(client_id=None):
    """Get default reference image paths from client config."""
    return client_config.get_reference_images(client_id)


def get_style_presets(client_id=None):
    """Get style presets from client config, with sensible defaults."""
    config = client_config.load_config(client_id)
    return config.get("image", {}).get("style_presets", {
        "minimal": "minimalist clean design, single focal point, plenty of negative space on dark navy",
        "tech": "floating holographic trading UI panels and candlestick charts in background, tech fintech aesthetic",
        "notification": "realistic smartphone mockup showing app notification on screen",
    })


def load_reference_images(paths: list, client_id: str = None) -> list:
    """Load reference images as base64 data URIs for the WaveSpeed API.
    For the first image (logo), falls back to logo_url in config if local file is missing.
    """
    images = []
    for i, path in enumerate(paths):
        p = Path(path)
        if p.exists():
            mime = "image/jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else "image/png"
            b64 = base64.b64encode(p.read_bytes()).decode()
            images.append(f"data:{mime};base64,{b64}")
            print(f"  Reference loaded: {p.name}")
        elif i == 0 and client_id:
            # First image is always the logo — try logo_url from config as fallback
            config = client_config.load_config(client_id)
            logo_url = config.get("brand", {}).get("logo_url", "").strip()
            if logo_url:
                print(f"  Local logo not found, fetching from logo_url: {logo_url}")
                try:
                    resp = requests.get(logo_url, timeout=20)
                    resp.raise_for_status()
                    ext = logo_url.split("?")[0].split(".")[-1].lower()
                    mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
                    b64 = base64.b64encode(resp.content).decode()
                    images.append(f"data:{mime};base64,{b64}")
                    print(f"  Logo fetched from URL ({len(resp.content)} bytes)")
                except Exception as e:
                    print(f"  Warning: could not fetch logo from URL: {e}")
            else:
                print(f"  Warning: reference image not found, skipping: {p}")
        else:
            print(f"  Warning: reference image not found, skipping: {p}")
    return images


def build_prompt(
    topic: str,
    headline: str = "",
    style: str = "tech",
    extra: str = "",
    client_id: str = None
) -> str:
    """Build the text instruction prompt. Reference images are passed separately."""
    config = client_config.load_config(client_id)
    brand = config.get("brand", {})
    display_name = config.get("display_name", "Brand")

    style_presets = get_style_presets(client_id)
    style_desc = style_presets.get(style, style_presets.get("tech", "tech fintech aesthetic"))

    mascot_desc = brand.get("mascot_description", "brand mascot character")
    logo_desc = brand.get("logo_description", f"{display_name} logo in the top-left corner")
    bg_style = brand.get("background_style", "Deep dark navy gradient")

    headline_part = f'\n- Include the bold white headline text: "{headline}"' if headline else ""

    # Build reference image instructions dynamically
    ref_images = brand.get("reference_images", [])

    if ref_images:
        mascot_ref_note = (
            f"\n- Reference Images 2-{len(ref_images)}: The {display_name} mascot character. "
            f"Replicate this character exactly: same face, proportions, clothing, style. DO NOT create a different character."
            if len(ref_images) > 1 else ""
        )
        ref_block = f"""=== REFERENCE IMAGE INSTRUCTIONS (MANDATORY) ===
You have been given {len(ref_images)} reference image(s). Follow these exactly:
- Reference Image 1: This is the real {display_name} logo. You MUST copy it with 100% fidelity. DO NOT redesign it, recreate it from text, or invent a new logo. Place it in the top-left corner exactly as it appears in the reference.{mascot_ref_note}

Ignoring these reference images is not acceptable. The logo and mascot must match the references precisely.
=================================================

"""
    else:
        ref_block = ""

    prompt = f"""{ref_block}Generate a new high-quality 16:9 social media banner image with these requirements:
- LOGO: Copy the exact {display_name} logo from Reference Image 1 — place it top-left. DO NOT invent or redesign the logo.
- MASCOT: Replicate the exact character from the reference images ({mascot_desc}). Same face, same proportions, same style.
- SCENE: {topic}
- STYLE: {style_desc}
- BACKGROUND: {bg_style}
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


def _inject_reference_header(prompt: str, ref_count: int, client_id: str = None) -> str:
    """Prepend mandatory reference image instructions to any prompt when references are present.
    This ensures logo/mascot fidelity even when the prompt was generated externally (e.g. by Gemini).
    """
    if ref_count == 0:
        return prompt
    config = client_config.load_config(client_id)
    display_name = config.get("display_name", "Brand")
    mascot_desc = config.get("brand", {}).get("mascot_description", "brand mascot character")
    mascot_note = (
        f"\n- Reference Images 2-{ref_count}: Mascot character ({mascot_desc}). Copy exactly — same face, proportions, clothing. DO NOT create a different character."
        if ref_count > 1 else ""
    )
    header = f"""=== MANDATORY REFERENCE INSTRUCTIONS ===
You have {ref_count} reference image(s). You MUST follow these:
- Reference Image 1: The REAL {display_name} logo. Copy it with 100% fidelity into the top-left corner. DO NOT redesign, reinvent, or create a new logo from text. Use ONLY what is shown in the reference.{mascot_note}
=========================================

"""
    return header + prompt


def generate_image(prompt: str, output_path: str, reference_paths: list = None, client_id: str = None, upload_r2: bool = True) -> tuple:
    """Generate an image using WaveSpeed GPT-Image-1.5 with reference images for brand fidelity.

    If reference_paths are provided, uses the Edit endpoint (supports up to 10 reference images).
    If no references, falls back to the Text-to-Image endpoint.
    Returns (local_path, r2_url) tuple. r2_url is None if R2 not configured or upload_r2=False.
    """
    api_key = get_api_key(client_id or "bobe", "wavespeed_en")
    if not api_key:
        raise ValueError("WAVESPEED_API_KEY not set. Check your .env file.")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    if reference_paths is None:
        reference_paths = get_default_references()

    # Load reference images
    print(f"  Loading {len(reference_paths)} reference images...")
    ref_images = load_reference_images(reference_paths, client_id=client_id)

    # Always inject reference header when references are present (even for externally-built prompts)
    prompt = _inject_reference_header(prompt, len(ref_images), client_id)

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
    local_path = save_image(img_resp.content, output_path)

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

    return local_path, r2_url


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
    return placeholder_path, None


def generate_for_content(topic: str, content_text: str, date: str, platform: str, style: str = "tech", client_id: str = None) -> dict:
    """High-level helper: build prompt metadata for a piece of content."""
    first_sentence = content_text.split(".")[0].split("\n")[0]
    words = first_sentence.split()
    headline = " ".join(words[:6]) + ("..." if len(words) > 6 else "")

    prompt = build_prompt(topic=topic, headline=headline, style=style, client_id=client_id)
    output_dir = client_config.get_output_dir(client_id)
    topic_slug = topic.lower().replace(" ", "_")[:30]
    filename = f"{date}_{topic_slug}_{platform}.png"
    output_path = output_dir / filename

    return {
        "prompt": prompt,
        "output_path": str(output_path),
        "headline": headline,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate branded images with WaveSpeed GPT-Image-1.5 + reference images")
    parser.add_argument("--prompt", default=None,
                        help="Full custom text instruction (overrides topic/headline builder)")
    parser.add_argument("--topic", default="automated crypto trading",
                        help="Scene/topic for the image")
    parser.add_argument("--headline", default="",
                        help="Short headline text to include on the image")
    parser.add_argument("--style", default="tech",
                        help="Visual style preset")
    parser.add_argument("--output", default=None,
                        help="Output file path")
    parser.add_argument("--reference", action="append", default=None,
                        help="Additional reference image path (can be used multiple times)")
    parser.add_argument("--no-reference", action="store_true",
                        help="Disable reference images, text-only prompt")
    parser.add_argument("--mock", action="store_true",
                        help="Mock mode, no API call")
    parser.add_argument("--no-r2", action="store_true",
                        help="Skip R2 upload even if configured")
    parser.add_argument("--show-prompt", action="store_true",
                        help="Print full text prompt and exit without generating")
    client_config.add_client_arg(parser)

    args = parser.parse_args()
    active_client = client_config.resolve_client(args)
    config = client_config.load_config(active_client)
    output_dir = client_config.get_output_dir(active_client)

    # Determine reference images to use
    if args.no_reference:
        reference_paths = []
    elif args.reference:
        reference_paths = [Path(r) for r in args.reference]
    else:
        reference_paths = get_default_references(active_client)

    # Build text prompt
    if args.prompt:
        prompt = args.prompt
    else:
        prompt = build_prompt(topic=args.topic, headline=args.headline, style=args.style, client_id=active_client)

    if args.show_prompt:
        loaded = load_reference_images(reference_paths, client_id=active_client)
        final_prompt = _inject_reference_header(prompt, len(loaded), active_client)
        print("\n--- REFERENCE IMAGES ---")
        for r in reference_paths:
            exists = "\u2713" if Path(r).exists() else "\u2717 missing"
            print(f"  {exists}  {r}")
        print("\n--- FINAL PROMPT (as sent to API) ---")
        print(final_prompt)
        return

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
        topic_slug = args.topic.lower().replace(" ", "_")[:30]
        output_path = str(output_dir / f"{date_str}_{topic_slug}.png")

    output_dir.mkdir(parents=True, exist_ok=True)

    display_name = config.get("display_name", "Brand")
    print(f"\nGenerating {display_name} image via WaveSpeed GPT-Image-1.5...")
    print(f"Client: {active_client}")
    print(f"Style: {args.style}")
    print(f"Output: {output_path}")
    print(f"References: {len(reference_paths)} image(s)")

    if args.mock:
        print("Running in MOCK mode, no API call made.")
        result_path, _ = mock_generate(output_path)
    else:
        result_path, r2_url = generate_image(
            prompt, output_path, reference_paths,
            upload_r2=not args.no_r2, client_id=active_client
        )
        if r2_url:
            print(f"  R2: {r2_url}")

    print(f"\nDone: {result_path}")
    return result_path


if __name__ == "__main__":
    main()
