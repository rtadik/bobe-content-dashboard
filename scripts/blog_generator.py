#!/usr/bin/env python3
"""
Blog Generator

Generates long-form blog posts from approved social media content.
Uses Gemini API for generation, applies programmatic humanizer rules.

Usage:
  python scripts/blog_generator.py --client bobe --topic "DCA bots" \\
    --source-content "Tweet thread text..." --platform twitter --bucket trending

  python scripts/blog_generator.py --client bobe --from-airtable \\
    --week-of 2026-03-16 --topic-index 0
"""

import os
import sys
import json
import re
import argparse
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger("blog")

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import client_config
from utils import call_gemini, extract_json_from_llm, topic_slug

PROJECT_ROOT = Path(__file__).parent.parent


# ── Humanizer Rules (programmatic approximation) ─────────────────────────────

AI_VOCABULARY = [
    "additionally", "delve", "crucial", "pivotal", "landscape", "tapestry",
    "testament", "underscore", "showcase", "foster", "garner", "intricate",
    "intricacies", "interplay", "enduring", "vibrant", "profound", "nestled",
    "groundbreaking", "renowned", "breathtaking", "stunning", "enhancing",
    "highlighting", "underscoring", "emphasizing", "showcasing", "cultivating",
    "encompassing", "exemplifies", "commitment to", "rich history",
    "serves as", "stands as", "in today's", "rapidly evolving",
    "at its core", "it is important to note", "in order to",
    "due to the fact that", "the future looks bright",
]

FILLER_REPLACEMENTS = [
    (r"\bin order to\b", "to"),
    (r"\bdue to the fact that\b", "because"),
    (r"\bat this point in time\b", "now"),
    (r"\bin the event that\b", "if"),
    (r"\bhas the ability to\b", "can"),
    (r"\bit is important to note that\b", ""),
    (r"\bit should be noted that\b", ""),
    (r"\bin today's rapidly evolving\b", "in the current"),
    (r"\bat its core\b", "fundamentally"),
]

COPULA_FIXES = [
    (r"\bserves as\b", "is"),
    (r"\bstands as\b", "is"),
    (r"\bfunctions as\b", "is"),
    (r"\bacts as\b", "is"),
    (r"\bmarks a\b", "is a"),
]

SIGNIFICANCE_PHRASES = [
    r"marking a pivotal",
    r"a testament to",
    r"setting the stage",
    r"indelible mark",
    r"deeply rooted",
    r"the future looks bright",
    r"exciting times lie ahead",
    r"journey toward excellence",
]


def humanize_blog(text: str) -> str:
    """Apply programmatic humanizer rules to blog text.

    This is an approximation of the /humanizer skill for automated pipelines.
    When used via Claude (blog-writer skill), the full /humanizer skill runs instead.
    """
    result = text

    # Remove em-dashes and en-dashes (replace with commas or periods)
    result = result.replace("\u2014", ", ")  # em-dash
    result = result.replace("\u2013", ", ")  # en-dash
    result = re.sub(r"(?<!\w)--(?!\w)", ", ", result)  # double-hyphen

    # Replace curly quotes with straight quotes
    result = result.replace("\u201c", '"').replace("\u201d", '"')
    result = result.replace("\u2018", "'").replace("\u2019", "'")

    # Remove filler phrases
    for pattern, replacement in FILLER_REPLACEMENTS:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    # Fix copula avoidance
    for pattern, replacement in COPULA_FIXES:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    # Remove significance inflation phrases
    for phrase in SIGNIFICANCE_PHRASES:
        result = re.sub(phrase, "", result, flags=re.IGNORECASE)

    # Flag AI vocabulary (log warnings, don't auto-replace since context matters)
    lower = result.lower()
    found_ai_words = [w for w in AI_VOCABULARY if w in lower]
    if found_ai_words:
        logger.warning(f"AI vocabulary detected (consider manual review): {found_ai_words[:5]}")

    # Clean up double spaces and blank lines from removals
    result = re.sub(r"  +", " ", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    result = re.sub(r" ,", ",", result)
    result = re.sub(r"^,\s*", "", result, flags=re.MULTILINE)

    return result.strip()


# ── Blog Generation ──────────────────────────────────────────────────────────

BLOG_PROMPT = """\
You are a blog writer for {display_name}. You write like a knowledgeable person \
talking to peers, not like a brand talking to consumers.

Write a blog post (800-1500 words) based on this social media content:

TOPIC: {topic}
SOURCE PLATFORM: {platform}
SOURCE CONTENT:
{source_content}

BRAND CONTEXT:
- Tone: {tone}
- Voice: {voice}
- Messaging pillars: {pillars}
- CTA examples: {ctas}

BLOG STRUCTURE:
1. Headline (8-12 words, specific, no colons, no "How X is Changing Y")
2. Opening paragraph (2-3 sentences, start with concrete observation, NOT "In today's...")
3. Body (3-4 sections, each 150-300 words, lowercase headings)
4. Brand connection (1 paragraph, educational, no hard sell)
5. Closing (2-3 sentences, soft CTA from brand)

RULES:
- NEVER use em-dashes, en-dashes, or double-hyphens
- NEVER use: delve, crucial, landscape, tapestry, testament, pivotal, showcase, foster
- NEVER use "In conclusion", "The future looks bright", "exciting times"
- NEVER use rule-of-three patterns (don't group things in threes artificially)
- NEVER use "Not only X, but also Y" constructions
- Use lowercase headings (## heading), not Title Case
- Have opinions. React to the topic.
- Vary sentence length. Mix short punchy with longer ones.
- Use specific numbers and examples where possible
- Word count: {target_words} words

IMAGE PROMPTS:
Also suggest 2-3 image prompts for the blog using:
- Mascot: {mascot}
- Background: {bg_style}
- Logo: {logo_desc}
- Style: {style_pref}

Return ONLY valid JSON (no markdown fences, no other text):
{{
  "headline": "...",
  "slug": "url-safe-slug",
  "body": "Full blog in markdown...",
  "meta_description": "150-char SEO description",
  "image_prompts": ["prompt 1", "prompt 2"],
  "word_count": 1050
}}"""


def generate_blog(topic: str, source_content: str, platform: str, bucket: str,
                   client_id: str = None, extra_context: str = None,
                   target_words: int = 1000) -> dict:
    """Generate a blog post from social media content.

    Args:
        topic: Topic title from content card
        source_content: Full text of the Twitter thread or Telegram post
        platform: "twitter" or "telegram"
        bucket: "trending", "education", or "announcements"
        client_id: Client ID (or active client)
        extra_context: Additional context to include
        target_words: Target word count (800-1500)

    Returns:
        Blog dict with headline, slug, body, meta_description, image_prompts, word_count
    """
    if client_id is None:
        client_id = client_config.get_active_client()

    config = client_config.load_config(client_id)
    display_name = config.get("display_name", client_id)
    tone = config.get("content", {}).get("tone", "educational")
    voice = config.get("content", {}).get("voice", "")
    pillars = "; ".join(config.get("content", {}).get("messaging_pillars", []))
    ctas = "; ".join(config.get("content", {}).get("cta_examples", []))
    mascot = config.get("brand", {}).get("mascot_description", "brand mascot")
    bg_style = config.get("brand", {}).get("background_style", "dark background")
    logo_desc = config.get("brand", {}).get("logo_description", "logo in top-left")

    # Get selected style preference
    style_pref = "minimal clean design"
    try:
        pref = client_config.get_style_preference(client_id)
        if pref and pref.get("style_preset"):
            presets = config.get("image", {}).get("style_presets", {})
            style_pref = presets.get(pref["style_preset"], style_pref)
    except Exception:
        pass

    full_content = source_content
    if extra_context:
        full_content += f"\n\nAdditional context: {extra_context}"

    prompt = BLOG_PROMPT.format(
        display_name=display_name,
        topic=topic,
        platform=platform,
        source_content=full_content[:3000],
        tone=tone,
        voice=voice,
        pillars=pillars,
        ctas=ctas,
        mascot=mascot,
        bg_style=bg_style,
        logo_desc=logo_desc,
        style_pref=style_pref,
        target_words=target_words,
    )

    logger.info(f"Generating blog for '{topic}' ({platform}, {bucket})")

    response = call_gemini(prompt, client_id=client_id)
    blog = extract_json_from_llm(response)

    if isinstance(blog, list):
        blog = blog[0] if blog else {}

    # Add metadata
    blog["source_topic"] = topic
    blog["source_platform"] = platform
    blog["source_bucket"] = bucket

    # Apply humanizer
    if blog.get("body"):
        blog["body"] = humanize_blog(blog["body"])
        blog["word_count"] = len(blog["body"].split())

    # Generate slug if missing
    if not blog.get("slug"):
        blog["slug"] = topic_slug(blog.get("headline", topic), max_chars=60)

    return blog


def save_blog(blog: dict, client_id: str, week_of: str = None) -> Path:
    """Save blog as markdown file and return path."""
    out_dir = client_config.get_output_dir(client_id) / "blogs"
    out_dir.mkdir(parents=True, exist_ok=True)

    slug = blog.get("slug", "untitled")
    filename = f"{slug}.md"
    filepath = out_dir / filename

    # Write as markdown with frontmatter
    frontmatter = {
        "title": blog.get("headline", ""),
        "description": blog.get("meta_description", ""),
        "source_topic": blog.get("source_topic", ""),
        "source_platform": blog.get("source_platform", ""),
        "word_count": blog.get("word_count", 0),
        "generated_at": datetime.now().isoformat(),
        "week_of": week_of or "",
        "client_id": client_id,
    }

    content = "---\n"
    for k, v in frontmatter.items():
        content += f"{k}: {json.dumps(v)}\n"
    content += "---\n\n"
    content += f"# {blog.get('headline', 'Untitled')}\n\n"
    content += blog.get("body", "")

    if blog.get("image_prompts"):
        content += "\n\n---\n\n## Image Prompts\n\n"
        for i, prompt in enumerate(blog["image_prompts"], 1):
            content += f"{i}. {prompt}\n"

    filepath.write_text(content, encoding="utf-8")
    logger.info(f"Blog saved: {filepath}")
    return filepath


# ── CLI ──────────────────────────────────────────────────────────────────────

def load_topic_by_index(topic_index: int, week_of: str, client_id: str,
                        platform: str = "twitter", from_airtable: bool = False) -> dict:
    """Load a topic from Airtable or Excel by its 0-based index.

    Returns dict with keys: topic, source_content, bucket, platform.
    """
    from web_viewer import load_content, load_content_from_airtable, find_excel

    topics = []
    date_key = f"week:{week_of}"

    # Try Airtable first if requested
    if from_airtable:
        topics = load_content_from_airtable(date_key, client_id)

    # Fall back to Excel
    if not topics:
        xlsx_path = find_excel(week_of)
        if xlsx_path:
            topics = load_content(xlsx_path)

    if not topics:
        raise ValueError(f"No topics found for week {week_of} (client: {client_id})")

    if topic_index < 0 or topic_index >= len(topics):
        raise ValueError(f"Topic index {topic_index} out of range (0-{len(topics) - 1})")

    t = topics[topic_index]
    # Extract content for the requested platform
    content_key = platform if platform in ("twitter", "telegram") else "twitter"
    source_content = t.get(content_key) or t.get("twitter") or t.get("telegram") or ""

    return {
        "topic": t.get("topic", ""),
        "source_content": source_content,
        "bucket": t.get("bucket", "trending"),
        "platform": platform,
    }


def main():
    parser = argparse.ArgumentParser(description="Blog generator from social content")
    parser.add_argument("--client", default=None, help="Client ID")
    parser.add_argument("--topic", default=None, help="Topic title")
    parser.add_argument("--topic-index", type=int, default=None,
                        help="0-based topic index (loads from Airtable/Excel)")
    parser.add_argument("--from-airtable", action="store_true",
                        help="Load content from Airtable (falls back to Excel)")
    parser.add_argument("--source-content", default="", help="Source post content")
    parser.add_argument("--platform", default="twitter", choices=["twitter", "telegram"])
    parser.add_argument("--bucket", default="trending", choices=["trending", "education", "announcements"])
    parser.add_argument("--week-of", default=None, help="Week start date YYYY-MM-DD")
    parser.add_argument("--target-words", type=int, default=1000, help="Target word count")
    parser.add_argument("--extra-context", default=None, help="Additional context")
    parser.add_argument("--mock", action="store_true", help="Return mock blog without API call")
    args = parser.parse_args()

    client_id = args.client or client_config.get_active_client()

    # Resolve topic from index if provided
    if args.topic_index is not None:
        if not args.week_of:
            parser.error("--week-of is required when using --topic-index")
        loaded = load_topic_by_index(
            topic_index=args.topic_index,
            week_of=args.week_of,
            client_id=client_id,
            platform=args.platform,
            from_airtable=args.from_airtable,
        )
        topic = loaded["topic"]
        source_content = loaded["source_content"]
        bucket = loaded["bucket"]
        platform = loaded["platform"]
        logger.info(f"Loaded topic #{args.topic_index}: '{topic}' (bucket: {bucket})")
    else:
        if not args.topic:
            parser.error("--topic is required when --topic-index is not provided")
        topic = args.topic
        source_content = args.source_content
        bucket = args.bucket
        platform = args.platform

    if args.mock:
        blog = {
            "headline": f"Mock blog: {topic[:50]}",
            "slug": topic_slug(topic),
            "body": f"This is a mock blog post about {topic}.\n\nGenerated in mock mode.",
            "meta_description": f"Mock blog about {topic[:100]}",
            "image_prompts": ["Mock image prompt 1", "Mock image prompt 2"],
            "source_topic": topic,
            "source_platform": platform,
            "word_count": 15,
        }
    else:
        blog = generate_blog(
            topic=topic,
            source_content=source_content,
            platform=platform,
            bucket=bucket,
            client_id=client_id,
            extra_context=args.extra_context,
            target_words=args.target_words,
        )

    path = save_blog(blog, client_id, args.week_of)
    print(f"\nBlog generated:")
    print(f"  Headline: {blog.get('headline')}")
    print(f"  Words: {blog.get('word_count')}")
    print(f"  Saved: {path}")
    print(json.dumps(blog, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
