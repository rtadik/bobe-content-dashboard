#!/usr/bin/env python3
"""
Standalone Pipeline Runner

End-to-end pipeline: scrape topics → generate content via Gemini API →
images via WaveSpeed → Excel workbook → Airtable sync → build static site.

Runs without Claude Code. Used by GitHub Actions for remote pipeline execution.
The Claude-driven /weekly-pipeline command remains the gold standard for
quality-critical runs (better brand voice consistency).

Usage:
  python scripts/pipeline_runner.py --client bobe
  python scripts/pipeline_runner.py --client bobe --week-of 2026-02-23
  python scripts/pipeline_runner.py --mock
  python scripts/pipeline_runner.py --skip-images --skip-airtable --skip-deploy

Flags:
  --client         Client ID (default: reads .active-client or bobe)
  --week-of        Week start date YYYY-MM-DD (default: Monday of current week)
  --mock           Dry run, no API calls
  --skip-images    Skip image generation
  --skip-airtable  Skip Airtable sync
  --skip-deploy    Skip static site build (GH Actions handles deploy separately)
"""

import os
import sys
import json
import re
import subprocess
import argparse
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))
import client_config

# Use the same Python interpreter that launched this script (works on macOS + Linux + GH Actions)
# Quoted to handle paths with spaces (e.g. "Claude Code" directory on macOS)
PY = f'"{sys.executable}"'

GOOGLE_AI_API_KEY = os.environ.get("GOOGLE_AI_API_KEY")
PROJECT_ROOT = Path(__file__).parent.parent
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# ── Utilities ─────────────────────────────────────────────────────────────────

def get_monday(date_str=None):
    """Return Monday of current (or specified) week as YYYY-MM-DD."""
    if date_str:
        d = datetime.strptime(date_str, "%Y-%m-%d")
    else:
        d = datetime.now()
    monday = d - timedelta(days=d.weekday())
    return monday.strftime("%Y-%m-%d")


def topic_slug(topic, max_chars=30):
    """Convert topic text to a safe filename slug."""
    s = topic.lower()[:max_chars]
    s = re.sub(r"[^a-z0-9\s]", "", s)
    s = re.sub(r"\s+", "_", s.strip())
    return s or "topic"


def make_image_path(client_id, week_of, day, slug, platform, ru=False):
    """Build the expected image output path."""
    suffix = "_ru" if ru else ""
    return (
        f"outputs/content/{client_id}/images/{week_of}-weekly/"
        f"{week_of}_{day.lower()}_{slug}_{platform.lower()}{suffix}.png"
    )


def run_cmd(cmd, check=True):
    """Run a shell command, raise on non-zero exit if check=True."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        print(f"    {result.stdout.strip()}")
    if result.returncode != 0:
        if result.stderr.strip():
            print(f"    stderr: {result.stderr.strip()[:300]}")
        if check:
            raise RuntimeError(
                f"Command failed (exit {result.returncode}): {cmd[:120]}"
            )
    return result


# ── Gemini API ─────────────────────────────────────────────────────────────────

def call_gemini(prompt, model="gemini-2.0-flash"):
    """Call Gemini API and return the text response."""
    if not GOOGLE_AI_API_KEY:
        raise ValueError("GOOGLE_AI_API_KEY not set. Check your .env file.")
    try:
        from google import genai
        client = genai.Client(api_key=GOOGLE_AI_API_KEY)
        response = client.models.generate_content(model=model, contents=prompt)
        return response.text
    except ImportError:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GOOGLE_AI_API_KEY)
            m = genai.GenerativeModel(model)
            response = m.generate_content(prompt)
            return response.text
        except ImportError:
            raise ImportError(
                "No Gemini SDK found. Install: pip install google-genai"
            )


def extract_json(text):
    """Extract the first JSON array or object from a text response."""
    # Try fenced code block first
    match = re.search(r"```(?:json)?\s*([\[\{][\s\S]*?[\]\}])\s*```", text)
    if match:
        return json.loads(match.group(1))
    # Try raw JSON
    match = re.search(r"([\[\{][\s\S]*[\]\}])", text)
    if match:
        return json.loads(match.group(1))
    raise ValueError(f"No valid JSON found in response:\n{text[:400]}")


# ── Prompts ────────────────────────────────────────────────────────────────────

TOPIC_POOL_PROMPT = """\
You are a content strategist for {display_name}.

Brand: {display_name} — {tagline}
Tone: {tone}
Target audience: retail crypto users age 20-35, $500-$20k in crypto, exhausted from emotional trading
Messaging pillars: {pillars}
Keywords: {keywords}

Scraped live topics from Twitter this week ({n_scraped} found):
{scraped_summary}

Generate a weekly schedule of exactly 21 content topics (3 per day, 7 days).
Use scraped live topics where directly relevant to the brand; fill the rest with evergreen topics.
Live/trending topics go to Mon-Wed priority; evergreen fills Thu-Sun and remaining slots.
Each day: mix of Pain Point, Education, and Transparency/Product angles.
Vary angles so consecutive days do not repeat the same angle.

CRITICAL RULES:
- NEVER use em-dashes, en-dashes, or double-hyphens (-- or — or –) in topic text
- Replace with commas, colons, or rephrase
- Topics must be concise (max 80 chars) and specific
- No hype, no guaranteed return claims

Return ONLY a JSON array of exactly 21 objects, no other text:
[
  {{
    "topic_num": 1,
    "day": "Mon",
    "date": "{date_mon}",
    "topic": "topic text here",
    "angle": "Pain Point",
    "source": "Live"
  }},
  ...
]

Day/date schedule: Mon {date_mon}, Tue {date_tue}, Wed {date_wed}, Thu {date_thu}, Fri {date_fri}, Sat {date_sat}, Sun {date_sun}
3 topics per day, numbered 1-21. Angles rotate: Pain Point, Education, Transparency/Product."""


CONTENT_GEN_PROMPT = """\
You are a content writer for {display_name}.

Brand voice: {tone}
Voice: {voice}
Product: {tagline}
Messaging pillars: {pillars}
CTAs: {ctas}
Hashtags: {hashtags}

CRITICAL RULES:
- NEVER use — (em-dash), – (en-dash), or -- (double-hyphen) as punctuation
- Replace with commas, colons, or rephrase entirely
- The --- tweet separator is the ONLY exception (structural separator between tweets)
- No guaranteed return claims, no hype, no moon/rocket emojis

Topic #{topic_num}: "{topic}"
Angle: {angle}
Day: {day}, Date: {date}
Platform: {platform}
Format: {format_desc}

{platform_rules}

Generate content in BOTH English and Russian.

Russian rules:
- Conversational tone, like a knowledgeable friend. Not formal, not slang.
- Twitter: ~280 char target (allow up to 340 since Russian runs ~30% longer)
- Telegram: maintain structure and engagement question at end
- Keep English hashtags (#DeFi, #USDT, #BoBe etc.) AND add 1-2 Cyrillic ones (#Крипто, #АвтоТрейдинг, #Доходность)
- The --- tweet separator stays unchanged in Russian threads
- No em-dashes, en-dashes, or double-hyphens in Russian either

Image prompt guidelines:
- Include brand mascot: {mascot}
- Background style: {bg_style}
- Image style preset: {style_preset}
- Include a bold prominent headline in the image text

Return ONLY a JSON object, no other text:
{{
  "content": "English content here",
  "image_prompt": "Detailed image prompt with mascot, background, style, and bold English headline",
  "hashtags": ["#Tag1", "#Tag2", "#Tag3"],
  "content_ru": "Russian content here",
  "image_prompt_ru": "Same as image_prompt but with bold RUSSIAN/CYRILLIC headline instead of English",
  "hashtags_ru": ["#Tag1", "#Tag2", "#Крипто"]
}}"""


def get_platform_rules(config, platform, fmt):
    """Return platform-specific content rules string."""
    pf = config.get("content", {}).get("platform_formats", {})
    if platform.lower() == "twitter":
        if fmt == "thread":
            n = pf.get("twitter", {}).get("thread_tweets", 5)
            return (
                f"Write a {n}-tweet thread. Separate tweets with exactly ---. "
                f"Tweet 1: hook or bold claim. Tweets 2-3: education or insight. "
                f"Tweet 4: how {config.get('display_name', 'the brand')} connects. "
                f"Tweet 5: soft CTA. Each tweet must be 280 chars or fewer."
            )
        else:
            return "Write a single tweet, 280 chars or fewer. Hook + insight + 2-3 hashtags."
    elif platform.lower() == "telegram":
        min_c = pf.get("telegram", {}).get("min_chars", 400)
        max_c = pf.get("telegram", {}).get("max_chars", 1200)
        return (
            f"Write a Telegram post between {min_c} and {max_c} characters. "
            f"Educational tone, explain the 'why'. Use line breaks generously. "
            f"End with an engagement question to the reader."
        )
    return "Write content appropriate for this platform in the brand voice."


def get_style_preset(config, angle):
    """Get image style key and description for a given topic angle."""
    style_map = config.get("image", {}).get("angle_style_map", {})
    style_key = style_map.get(angle, "minimal")
    presets = config.get("image", {}).get("style_presets", {})
    style_desc = presets.get(style_key, "clean minimal design on dark background")
    return style_key, style_desc


# ── Mock data ──────────────────────────────────────────────────────────────────

def make_mock_topics(day_dates):
    """Generate mock 21-topic schedule for dry runs."""
    topics = []
    angles = ["Pain Point", "Education", "Product"]
    for i in range(21):
        day = DAYS[i // 3]
        topics.append({
            "topic_num": i + 1,
            "day": day,
            "date": day_dates[day],
            "topic": f"Mock topic {i+1}: crypto automation insight for testing",
            "angle": angles[i % 3],
            "source": "Evergreen",
        })
    return topics


MOCK_CONTENT = {
    "content": "Mock EN content. No real API calls made in --mock mode.",
    "image_prompt": "Mock image prompt: BoBe mascot, dark navy background, bold headline.",
    "hashtags": ["#DeFi", "#TradingBot", "#BoBe"],
    "content_ru": "Мок контент. API вызовы не выполнялись в режиме --mock.",
    "image_prompt_ru": "Мок промпт: маскот BoBe, тёмно-синий фон, жирный заголовок на кириллице.",
    "hashtags_ru": ["#DeFi", "#TradingBot", "#BoBe", "#Крипто"],
}


# ── Main pipeline ──────────────────────────────────────────────────────────────

def run_pipeline(client_id, week_of, mock=False, skip_images=False,
                 skip_airtable=False, skip_deploy=False):
    """Run the full autonomous content pipeline."""

    config = client_config.load_config(client_id)
    display_name = config.get("display_name", client_id)
    output_dir = client_config.get_output_dir(client_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  {display_name} Pipeline Runner")
    print(f"  Client: {client_id} | Week: {week_of}")
    print(f"  Mock: {mock} | Skip images: {skip_images}")
    print(f"{'='*60}\n")

    # Day dates for the full week
    week_start = datetime.strptime(week_of, "%Y-%m-%d")
    day_dates = {
        DAYS[i]: (week_start + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(7)
    }

    # Content config shortcuts
    tone = config.get("content", {}).get("tone", "transparent, educational")
    voice = config.get("content", {}).get("voice", "")
    pillars = "; ".join(config.get("content", {}).get("messaging_pillars", []))
    ctas = "; ".join(config.get("content", {}).get("cta_examples", []))
    hashtags = ", ".join(config.get("content", {}).get("hashtags", []))
    keywords = ", ".join(client_config.get_keywords(client_id)[:15])
    mascot = config.get("brand", {}).get("mascot_description", "brand mascot")
    bg_style = config.get("brand", {}).get("background_style", "dark navy background")

    errors = []

    # ── Phase 1: Scrape Topics ────────────────────────────────────────────────
    print("Phase 1: Scraping trending topics...")
    scraped_topics = []

    if not mock:
        scrape_output = "/tmp/pipeline_runner_scraped.json"
        try:
            run_cmd(
                f"{PY} scripts/apify_scraper.py "
                f"--platform twitter --count 50 --days 7 --top 20 "
                f"--output {scrape_output} --client {client_id}",
                check=False,
            )
            if Path(scrape_output).exists():
                with open(scrape_output) as f:
                    scraped_topics = json.load(f)
                print(f"  Scraped {len(scraped_topics)} topics")
            else:
                print("  Warning: scraper produced no output, using evergreen fallback")
        except Exception as e:
            print(f"  Warning: scraping failed ({e}), using evergreen fallback")
    else:
        print("  [mock] Skipping scrape")

    # ── Phase 2: Assemble 21-Topic Pool ──────────────────────────────────────
    print("\nPhase 2: Assembling 21-topic pool via Gemini...")

    if mock:
        topics = make_mock_topics(day_dates)
        print("  [mock] Using mock topics")
    else:
        scraped_summary = (
            "\n".join(
                f"  - {t.get('text', t.get('topic', ''))[:100]}"
                for t in scraped_topics[:20]
            )
            or "  (none available — use 100% evergreen)"
        )

        prompt = TOPIC_POOL_PROMPT.format(
            display_name=display_name,
            tagline=config.get("tagline", ""),
            tone=tone,
            pillars=pillars,
            keywords=keywords,
            n_scraped=len(scraped_topics),
            scraped_summary=scraped_summary,
            date_mon=day_dates["Mon"],
            date_tue=day_dates["Tue"],
            date_wed=day_dates["Wed"],
            date_thu=day_dates["Thu"],
            date_fri=day_dates["Fri"],
            date_sat=day_dates["Sat"],
            date_sun=day_dates["Sun"],
        )

        try:
            response = call_gemini(prompt)
            topics = extract_json(response)
            # Fill in dates if Gemini omitted them
            for t in topics:
                if not t.get("date"):
                    t["date"] = day_dates.get(t.get("day", "Mon"), week_of)
            print(f"  Generated {len(topics)} topics via Gemini")
        except Exception as e:
            print(f"  Warning: Gemini topic generation failed ({e}), using mock fallback")
            errors.append(f"Phase 2 topic generation: {e}")
            topics = make_mock_topics(day_dates)

    # Print topic schedule
    print(f"\n  {'#':<4} {'Day':<5} {'Date':<12} {'Angle':<16} Topic")
    print(f"  {'-'*72}")
    for t in topics:
        print(
            f"  {t['topic_num']:<4} {t['day']:<5} {t.get('date', ''):<12} "
            f"{t.get('angle', ''):<16} {t['topic'][:48]}"
        )
    print()

    # ── Phase 3: Create Workbook ──────────────────────────────────────────────
    print("Phase 3: Creating workbook...")
    try:
        run_cmd(
            f"{PY} scripts/weekly_pipeline.py "
            f"--action create-workbook --week-of {week_of} --client {client_id}"
        )
        print(f"  Workbook: outputs/content/{client_id}/{week_of}-weekly-content.xlsx")
    except Exception as e:
        print(f"  Error creating workbook: {e}")
        raise

    # ── Phase 4: Content Generation Loop ─────────────────────────────────────
    print(f"\nPhase 4: Generating 42 content items (21 topics x 2 platforms)...")
    content_items = []

    for topic_data in topics:
        topic_num = topic_data["topic_num"]
        day = topic_data["day"]
        date = topic_data.get("date", day_dates.get(day, week_of))
        topic = topic_data["topic"]
        angle = topic_data.get("angle", "Education")

        # Position within the day (1, 2, or 3) — topics 1-2/day get thread format
        day_position = ((topic_num - 1) % 3) + 1
        twitter_fmt = "thread" if day_position <= 2 else "single"

        slug = topic_slug(topic)
        style_key, style_desc = get_style_preset(config, angle)

        for platform in ["Twitter", "Telegram"]:
            item_num = (topic_num - 1) * 2 + (1 if platform == "Twitter" else 2)
            fmt = twitter_fmt if platform == "Twitter" else "long-form"

            print(f"  Generating {item_num}/42: {day} #{topic_num} {platform} ({fmt})...")

            en_path = make_image_path(client_id, week_of, day, slug, platform)
            ru_path = make_image_path(client_id, week_of, day, slug, platform, ru=True)

            if mock:
                c = dict(MOCK_CONTENT)
                c["content"] = f"[Mock {platform} EN] {topic[:60]}"
                c["content_ru"] = f"[Мок {platform} RU] {topic[:60]}"
            else:
                format_desc = fmt + (" (5 tweets separated by ---)" if fmt == "thread" else "")
                platform_rules = get_platform_rules(config, platform, fmt)

                prompt = CONTENT_GEN_PROMPT.format(
                    display_name=display_name,
                    tone=tone,
                    voice=voice,
                    tagline=config.get("tagline", ""),
                    pillars=pillars,
                    ctas=ctas,
                    hashtags=hashtags,
                    topic_num=topic_num,
                    topic=topic,
                    angle=angle,
                    day=day,
                    date=date,
                    platform=platform,
                    format_desc=format_desc,
                    platform_rules=platform_rules,
                    mascot=mascot,
                    bg_style=bg_style,
                    style_preset=style_desc,
                )

                try:
                    response = call_gemini(prompt)
                    c = extract_json(response)
                except Exception as e:
                    print(f"    Warning: content generation failed for item {item_num}: {e}")
                    errors.append(f"Item {item_num} content: {e}")
                    c = dict(MOCK_CONTENT)
                    c["content"] = f"[Fallback EN] {topic}"
                    c["content_ru"] = f"[Запасной RU] {topic}"

            content_json = {
                "date": date,
                "day": day,
                "topic": topic,
                "platform": platform,
                "format": fmt,
                "content": c.get("content", ""),
                "image_prompt": c.get("image_prompt", f"{display_name} branded image: {topic}"),
                "image_path": en_path,
                "hashtags": c.get("hashtags", []),
                "content_ru": c.get("content_ru", ""),
                "image_prompt_ru": c.get("image_prompt_ru", f"{display_name} изображение: {topic}"),
                "image_path_ru": ru_path,
                "hashtags_ru": c.get("hashtags_ru", []),
                "status": "Draft",
            }

            tmp_file = f"/tmp/pipeline_content_{item_num}.json"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(content_json, f, ensure_ascii=False, indent=2)

            try:
                run_cmd(
                    f"{PY} scripts/weekly_pipeline.py --action save-content "
                    f"--week-of {week_of} --content-file {tmp_file} --client {client_id}"
                )
            except Exception as e:
                print(f"    Warning: failed to save item {item_num}: {e}")
                errors.append(f"Save item {item_num}: {e}")

            content_items.append(content_json)

    print(f"\n  Content: {len(content_items)} items generated, {len(errors)} errors so far")

    # ── Phase 5: Image Generation Loop ───────────────────────────────────────
    if not skip_images:
        print(f"\nPhase 5: Generating 42 images (21 EN + 21 RU)...")

        for topic_data in topics:
            topic_num = topic_data["topic_num"]
            day = topic_data["day"]
            topic = topic_data["topic"]
            angle = topic_data.get("angle", "Education")

            # Use the Twitter content item for image prompts
            twitter_item = next(
                (c for c in content_items
                 if c["topic"] == topic and c["platform"] == "Twitter"),
                None,
            )

            if not twitter_item:
                print(f"  Warning: no Twitter item found for topic {topic_num}, skipping")
                continue

            slug = topic_slug(topic)
            style_key, _ = get_style_preset(config, angle)

            en_img = twitter_item["image_path"]
            ru_img = twitter_item["image_path_ru"]

            # Ensure image output directory exists
            img_dir = (PROJECT_ROOT / en_img).parent
            img_dir.mkdir(parents=True, exist_ok=True)

            print(f"  Images {topic_num}/21 [{day}]: {topic[:42]}...")

            if not mock:
                # Sanitize prompts for shell usage
                en_prompt = twitter_item["image_prompt"].replace('"', "'")
                ru_prompt = twitter_item["image_prompt_ru"].replace('"', "'")

                # EN image via nano_banana.py (GPT-Image-1.5)
                try:
                    run_cmd(
                        f'{PY} scripts/nano_banana.py '
                        f'--prompt "{en_prompt}" '
                        f'--output "{en_img}" '
                        f'--style {style_key} '
                        f'--client {client_id}'
                    )
                    print(f"    EN: {Path(en_img).name}")
                except Exception as e:
                    print(f"    Warning: EN image failed for topic {topic_num}: {e}")
                    errors.append(f"EN image topic {topic_num}: {e}")

                # RU image via wavespeed_img.py (Seedream 4.5)
                try:
                    run_cmd(
                        f'{PY} scripts/wavespeed_img.py '
                        f'--prompt "{ru_prompt}" '
                        f'--output "{ru_img}" '
                        f'--client {client_id}'
                    )
                    print(f"    RU: {Path(ru_img).name}")
                except Exception as e:
                    print(f"    Warning: RU image failed for topic {topic_num}: {e}")
                    errors.append(f"RU image topic {topic_num}: {e}")
            else:
                print(f"    [mock] Skipping image API calls")
    else:
        print("\nPhase 5: Skipping image generation (--skip-images)")

    # ── Phase 6: Finalize Workbook ────────────────────────────────────────────
    print("\nPhase 6: Finalizing workbook...")
    try:
        run_cmd(
            f"{PY} scripts/weekly_pipeline.py "
            f"--action finalize --week-of {week_of} --client {client_id}"
        )
        print("  Workbook finalized")
    except Exception as e:
        print(f"  Warning: finalize failed: {e}")
        errors.append(f"Finalize: {e}")

    # ── Phase 6.5: Airtable Sync ──────────────────────────────────────────────
    airtable_enabled = client_config.is_airtable_enabled(client_id)
    if not skip_airtable and airtable_enabled:
        print("\nPhase 6.5: Syncing to Airtable...")
        if mock:
            print("  [mock] Skipping Airtable sync")
        else:
            try:
                run_cmd(
                    f"{PY} scripts/airtable_sync.py "
                    f"--week-of {week_of} --client {client_id}"
                )
                print("  Airtable sync complete")
            except Exception as e:
                print(f"  Warning: Airtable sync failed: {e}")
                errors.append(f"Airtable sync: {e}")
    elif skip_airtable:
        print("\nPhase 6.5: Skipping Airtable sync (--skip-airtable)")
    else:
        print("\nPhase 6.5: Airtable not enabled for this client, skipping")

    # ── Phase 7: Build Static Site ────────────────────────────────────────────
    if not skip_deploy:
        print("\nPhase 7: Building static site...")
        if mock:
            print("  [mock] Skipping static site build")
        else:
            try:
                run_cmd(
                    f"{PY} scripts/build_static.py "
                    f"--output dist --include-admin --client {client_id}"
                )
                print("  Static site built: dist/")
            except Exception as e:
                print(f"  Warning: static site build failed: {e}")
                errors.append(f"Static build: {e}")
    else:
        print("\nPhase 7: Skipping static site build (--skip-deploy)")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  {display_name} Pipeline Complete")
    print(f"  Week: {week_of}")
    print(f"  Content: {len(content_items)}/42 items generated")
    print(f"  Errors: {len(errors)}")
    if errors:
        print(f"\n  Error log (first 10):")
        for err in errors[:10]:
            print(f"    - {err}")
    print(f"\n  Excel:  outputs/content/{client_id}/{week_of}-weekly-content.xlsx")
    print(f"  Images: outputs/content/{client_id}/images/{week_of}-weekly/")
    print(f"{'='*60}\n")

    return len(errors) == 0


def main():
    parser = argparse.ArgumentParser(
        description="Standalone end-to-end pipeline runner (Gemini-powered)"
    )
    parser.add_argument(
        "--client", default=None,
        help="Client ID (default: reads .active-client or bobe)",
    )
    parser.add_argument(
        "--week-of", default=None,
        help="Week start date YYYY-MM-DD (default: Monday of current week)",
    )
    parser.add_argument(
        "--mock", action="store_true",
        help="Dry run: skip all API calls, use mock content",
    )
    parser.add_argument(
        "--skip-images", action="store_true",
        help="Skip image generation phases",
    )
    parser.add_argument(
        "--skip-airtable", action="store_true",
        help="Skip Airtable sync",
    )
    parser.add_argument(
        "--skip-deploy", action="store_true",
        help="Skip static site build (GH Actions handles deploy as a separate step)",
    )
    args = parser.parse_args()

    client_id = args.client or client_config.get_active_client()
    week_of = get_monday(getattr(args, "week_of", None))

    success = run_pipeline(
        client_id=client_id,
        week_of=week_of,
        mock=args.mock,
        skip_images=args.skip_images,
        skip_airtable=args.skip_airtable,
        skip_deploy=args.skip_deploy,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
