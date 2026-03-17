#!/usr/bin/env python3
"""
Bucket Generators

One generator function per content bucket type.
Each returns a list of exactly `bucket_size` (default 7) topic dicts.

Topic dict structure:
{
    "bucket": str,        # bucket type ID
    "topic_num": int,     # position within bucket (1-7)
    "day": str,           # "Mon"–"Sun"
    "date": str,          # "YYYY-MM-DD"
    "topic": str,         # topic title (max 80 chars, no em/en dashes)
    "angle": str,         # Pain Point | Education | Transparency | Product |
                          # Announcement | Social Proof | Behind the Scenes |
                          # Community | Market Commentary
    "source": str,        # Live | Evergreen | Belief Journey | Client Input | Auto
}

Used by pipeline_runner.py which reads content_types from config and dispatches here.
"""

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils import call_gemini as _call_gemini, extract_json_from_llm as _extract_json

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _build_day_dates(week_of: str) -> dict:
    """Return {Mon: YYYY-MM-DD, ..., Sun: YYYY-MM-DD}."""
    week_start = datetime.strptime(week_of, "%Y-%m-%d")
    return {DAYS[i]: (week_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)}


def _make_placeholder_topics(bucket: str, week_of: str, day_dates: dict, angle: str, source: str) -> list:
    """Generate 7 placeholder topic dicts for a bucket."""
    return [
        {
            "bucket": bucket,
            "topic_num": i + 1,
            "day": DAYS[i],
            "date": day_dates[DAYS[i]],
            "topic": f"[{bucket.replace('_',' ').title()} — Pending]",
            "angle": angle,
            "source": source,
        }
        for i in range(7)
    ]


# ── Trending ───────────────────────────────────────────────────────────────────

TRENDING_PROMPT = """\
You are a content strategist for {display_name}.

Brand: {display_name} — {tagline}
Tone: {tone}
Keywords: {keywords}
Messaging pillars: {pillars}

Scraped live topics this week ({n_scraped} found):
{scraped_summary}

Generate exactly 7 trending/reactive content topics (one per day Mon–Sun).
Use scraped live topics where relevant; fill remaining slots with evergreen trending topics.
Each topic should react to a current trend or industry development through the brand lens.
Mix angles: Pain Point, Market Commentary, Trend Reaction.
Vary angles across the 7 days.

RULES:
- Never use em-dashes (—), en-dashes (–), or double-hyphens (--)
- Each topic max 80 chars
- No hype, no guaranteed return claims

Return ONLY a JSON array of exactly 7 objects, no other text:
[
  {{"topic_num": 1, "day": "Mon", "date": "{date_mon}", "topic": "...", "angle": "...", "source": "Live or Evergreen"}},
  ...
]
Days: Mon {date_mon}, Tue {date_tue}, Wed {date_wed}, Thu {date_thu}, Fri {date_fri}, Sat {date_sat}, Sun {date_sun}"""


def generate_trending_topics(config: dict, week_of: str, day_dates: dict,
                              scraped_posts: list = None, mock: bool = False) -> list:
    """
    Generate 7 trending topics from scraped posts + evergreen fallback.
    Returns list of 7 topic dicts with bucket="trending".
    """
    client_id = config.get("client_id", "bobe")
    display_name = config.get("display_name", client_id)

    if mock:
        return [
            {
                "bucket": "trending",
                "topic_num": i + 1,
                "day": DAYS[i],
                "date": day_dates[DAYS[i]],
                "topic": f"Mock trending topic {i + 1}: industry insight for testing",
                "angle": ["Pain Point", "Market Commentary", "Trend Reaction"][i % 3],
                "source": "Evergreen",
            }
            for i in range(7)
        ]

    scraped_posts = scraped_posts or []
    # Rich summary: include platform, engagement, and full text snippet
    def _post_summary(p):
        platform = p.get("platform", "").upper()
        sub = f" r/{p['subreddit']}" if p.get("subreddit") else ""
        engagement = p.get("engagement", 0)
        text = p.get("text", p.get("topic", ""))[:120]
        return f"  [{platform}{sub} | {engagement} eng] {text}"

    scraped_summary = (
        "\n".join(_post_summary(p) for p in scraped_posts[:20])
        or "  (none — use 100% evergreen)"
    )

    import client_config as cc
    keywords = ", ".join(cc.get_keywords(client_id)[:12])
    tone = config.get("content", {}).get("tone", "educational")
    pillars = "; ".join(config.get("content", {}).get("messaging_pillars", []))
    tagline = config.get("tagline", "")

    prompt = TRENDING_PROMPT.format(
        display_name=display_name, tagline=tagline, tone=tone,
        keywords=keywords, pillars=pillars,
        n_scraped=len(scraped_posts), scraped_summary=scraped_summary,
        date_mon=day_dates["Mon"], date_tue=day_dates["Tue"],
        date_wed=day_dates["Wed"], date_thu=day_dates["Thu"],
        date_fri=day_dates["Fri"], date_sat=day_dates["Sat"], date_sun=day_dates["Sun"],
    )

    try:
        response = _call_gemini(prompt, client_id)
        topics = _extract_json(response)
        for i, t in enumerate(topics):
            t["bucket"] = "trending"
            t["topic_num"] = i + 1
            if not t.get("date"):
                t["date"] = day_dates.get(t.get("day", "Mon"), week_of)
            # Attach best-matching scraped post so content generation can reference it
            if scraped_posts:
                topic_words = set(t["topic"].lower().split())
                best, best_score = None, 0
                for p in scraped_posts:
                    post_text = p.get("text", "").lower()
                    score = sum(1 for w in topic_words if len(w) > 4 and w in post_text)
                    score += p.get("engagement", 0) / 500  # slight engagement boost
                    if score > best_score:
                        best, best_score = p, score
                if best and best_score > 0:
                    t["source_post"] = {
                        "platform": best.get("platform", ""),
                        "text": best.get("text", "")[:500],
                        "url": best.get("url", ""),
                        "engagement": best.get("engagement", 0),
                        "subreddit": best.get("subreddit", ""),
                    }
        return topics[:7]
    except Exception as e:
        print(f"  Warning: trending topic generation failed ({e}), using placeholders")
        return _make_placeholder_topics("trending", week_of, day_dates, "Pain Point", "Evergreen")


# ── Education ─────────────────────────────────────────────────────────────────

EDUCATION_TOPIC_PROMPT = """\
You are a content strategist for {display_name}.

The following are 7 belief stages in the buyer journey for {display_name}.
Each stage represents a belief a cold prospect must progressively hold before becoming a customer.

{belief_stages}

For each belief stage (1–7), write ONE social media topic title that teaches that belief
to the target audience without being preachy or salesy. The topic should be a statement
or question that naturally leads someone to develop that belief.

Tone: {tone}
Target audience: {audience}

RULES:
- Never use em-dashes (—), en-dashes (–), or double-hyphens (--)
- Each topic max 80 chars
- Vary the framing: sometimes a question, sometimes a bold statement, sometimes a relatable scenario
- Week of {week_of}: assign topics Mon–Sun (1 per day)

Return ONLY a JSON array of exactly 7 objects, no other text:
[
  {{"topic_num": 1, "day": "Mon", "date": "{date_mon}", "topic": "...", "angle": "Education", "source": "Belief Journey"}},
  ...
]
Days: Mon {date_mon}, Tue {date_tue}, Wed {date_wed}, Thu {date_thu}, Fri {date_fri}, Sat {date_sat}, Sun {date_sun}"""


def generate_education_topics(config: dict, week_of: str, day_dates: dict,
                               mock: bool = False) -> list:
    """
    Generate 7 education topics from the client's belief-journey.md.
    Returns list of 7 topic dicts with bucket="education".
    """
    client_id = config.get("client_id", "bobe")
    display_name = config.get("display_name", client_id)

    if mock:
        return [
            {
                "bucket": "education",
                "topic_num": i + 1,
                "day": DAYS[i],
                "date": day_dates[DAYS[i]],
                "topic": f"Mock education topic {i + 1}: belief-building concept",
                "angle": "Education",
                "source": "Belief Journey",
            }
            for i in range(7)
        ]

    import client_config as cc
    belief_path = cc.get_belief_journey_path(client_id)

    if not belief_path.exists():
        print(f"  Warning: belief-journey.md not found at {belief_path}, using evergreen education fallback")
        return _generate_education_evergreen(config, week_of, day_dates)

    belief_content = belief_path.read_text(encoding="utf-8")

    # Extract belief stages section
    belief_stages = belief_content
    if "## Belief Stage" in belief_content:
        start = belief_content.index("## Belief Stage")
        belief_stages = belief_content[start:start + 3000]

    tone = config.get("content", {}).get("tone", "educational")
    audience_info = ""
    context_path = cc.get_context_path(client_id)
    if context_path.exists():
        ctx = context_path.read_text(encoding="utf-8")
        audience_info = ctx[:400]

    prompt = EDUCATION_TOPIC_PROMPT.format(
        display_name=display_name, belief_stages=belief_stages[:2000],
        tone=tone, audience=audience_info[:300], week_of=week_of,
        date_mon=day_dates["Mon"], date_tue=day_dates["Tue"],
        date_wed=day_dates["Wed"], date_thu=day_dates["Thu"],
        date_fri=day_dates["Fri"], date_sat=day_dates["Sat"], date_sun=day_dates["Sun"],
    )

    try:
        response = _call_gemini(prompt, client_id)
        topics = _extract_json(response)
        for i, t in enumerate(topics):
            t["bucket"] = "education"
            t["topic_num"] = i + 1
            if not t.get("date"):
                t["date"] = day_dates.get(t.get("day", "Mon"), week_of)
        return topics[:7]
    except Exception as e:
        print(f"  Warning: education topic generation failed ({e}), using evergreen fallback")
        return _generate_education_evergreen(config, week_of, day_dates)


def _generate_education_evergreen(config: dict, week_of: str, day_dates: dict) -> list:
    """Fallback: generate 7 education topics from config context without belief-journey.md."""
    client_id = config.get("client_id", "bobe")
    display_name = config.get("display_name", client_id)
    pillars = config.get("content", {}).get("messaging_pillars", [])
    tone = config.get("content", {}).get("tone", "educational")

    prompt = f"""You are a content strategist for {display_name}.
Brand pillars: {"; ".join(pillars)}
Tone: {tone}

Generate 7 educational belief-building topics (Mon–Sun) that help a cold prospect
understand and trust this product. Each topic should address a different aspect of
why the product is valuable, trustworthy, and right for them.

RULES: No em-dashes (—), en-dashes (–), or double-hyphens. Each topic max 80 chars.

Return ONLY a JSON array of 7 objects:
[{{"topic_num": 1, "day": "Mon", "date": "{day_dates['Mon']}", "topic": "...", "angle": "Education", "source": "Evergreen"}}, ...]
Days: {', '.join(f'{d} {day_dates[d]}' for d in DAYS)}"""

    try:
        response = _call_gemini(prompt, client_id)
        topics = _extract_json(response)
        for i, t in enumerate(topics):
            t["bucket"] = "education"
            t["topic_num"] = i + 1
            if not t.get("date"):
                t["date"] = day_dates.get(t.get("day", "Mon"), week_of)
        return topics[:7]
    except Exception:
        return _make_placeholder_topics("education", week_of, day_dates, "Education", "Evergreen")


# ── Announcements ─────────────────────────────────────────────────────────────

ANNOUNCEMENT_ANGLES = [
    ("Direct announcement", "What's new"),
    ("User benefit", "What this means for you"),
    ("Behind-the-scenes", "How we built/decided this"),
    ("Social proof", "Why our users love this"),
    ("Educational", "Why this matters for the industry"),
    ("Before vs after", "How things have changed"),
    ("Future vision", "Where this is taking us"),
]

ANNOUNCEMENT_ANGLES_PROMPT = """\
You are a content strategist for {display_name}.

The client has submitted this weekly announcement:
"{announcement_text}"

Generate {count} different content TOPIC TITLES based on this announcement.
Each topic approaches the announcement from a different angle.
Use these angles (pick the first {count}):
{angles_list}

Tone: {tone}

RULES:
- Never use em-dashes (—), en-dashes (–), or double-hyphens (--)
- Each topic max 80 chars
- Topics should feel natural, not like a press release

Return ONLY a JSON array of exactly {count} objects, no other text:
[
  {{"topic_num": 1, "day": "Mon", "date": "{date_mon}", "topic": "...", "angle": "Announcement", "source": "Client Input"}},
  ...
]
Days: {days_list}"""


def generate_announcement_placeholders(config: dict, week_of: str, day_dates: dict,
                                        announcement_text: str = "", mock: bool = False,
                                        count: int = 7) -> list:
    """
    Generate announcement topic dicts.
    count: number of topics to generate (default 7, use 1 for testing).
    If announcement_text is provided: generates angles from it via Gemini.
    If not: returns placeholder rows with status "Pending Input".
    """
    count = min(count, 7)  # cap at 7 (one per day)
    client_id = config.get("client_id", "bobe")
    display_name = config.get("display_name", client_id)

    if not announcement_text:
        return [
            {
                "bucket": "announcements",
                "topic_num": i + 1,
                "day": DAYS[i],
                "date": day_dates[DAYS[i]],
                "topic": "[Announcement — Awaiting client input]",
                "angle": "Announcement",
                "source": "Pending",
                "status": "Pending Input",
            }
            for i in range(count)
        ]

    if mock:
        return [
            {
                "bucket": "announcements",
                "topic_num": i + 1,
                "day": DAYS[i],
                "date": day_dates[DAYS[i]],
                "topic": f"Mock announcement angle {i + 1}: {announcement_text[:40]}",
                "angle": "Announcement",
                "source": "Client Input",
            }
            for i in range(count)
        ]

    tone = config.get("content", {}).get("tone", "educational")
    angles_list = "\n".join(f"{i+1}. {a[0]} (\"{a[1]}\")" for i, a in enumerate(ANNOUNCEMENT_ANGLES[:count]))
    days_used = DAYS[:count]
    days_list = ", ".join(f"{d} {day_dates[d]}" for d in days_used)

    prompt = ANNOUNCEMENT_ANGLES_PROMPT.format(
        display_name=display_name, announcement_text=announcement_text[:1000],
        tone=tone, count=count, angles_list=angles_list, days_list=days_list,
        date_mon=day_dates.get("Mon", ""), date_tue=day_dates.get("Tue", ""),
        date_wed=day_dates.get("Wed", ""), date_thu=day_dates.get("Thu", ""),
        date_fri=day_dates.get("Fri", ""), date_sat=day_dates.get("Sat", ""),
        date_sun=day_dates.get("Sun", ""),
    )

    try:
        response = _call_gemini(prompt, client_id)
        topics = _extract_json(response)
        for i, t in enumerate(topics):
            t["bucket"] = "announcements"
            t["topic_num"] = i + 1
            if not t.get("date"):
                t["date"] = day_dates.get(t.get("day", "Mon"), week_of)
        return topics[:count]
    except Exception as e:
        print(f"  Warning: announcement topic generation failed ({e}), using placeholders")
        return generate_announcement_placeholders(config, week_of, day_dates, announcement_text="", count=count)


# ── Social Proof ──────────────────────────────────────────────────────────────

def generate_social_proof_topics(config: dict, week_of: str, day_dates: dict,
                                  client_input: str = "", mock: bool = False) -> list:
    """
    Generate 7 social proof topics.
    If client_input provided: derives topics from testimonials/results text.
    Otherwise: generates auto community-voice topics using brand's value props.
    """
    client_id = config.get("client_id", "bobe")
    display_name = config.get("display_name", client_id)

    if mock:
        return [
            {
                "bucket": "social_proof",
                "topic_num": i + 1,
                "day": DAYS[i],
                "date": day_dates[DAYS[i]],
                "topic": f"Mock social proof topic {i + 1}",
                "angle": "Social Proof",
                "source": "Client Input" if client_input else "Auto",
            }
            for i in range(7)
        ]

    tone = config.get("content", {}).get("tone", "educational")
    pillars = "; ".join(config.get("content", {}).get("messaging_pillars", []))

    if client_input:
        source_context = f"Based on these user results/testimonials:\n{client_input[:800]}"
        source_label = "Client Input"
    else:
        source_context = f"Auto-generate community voice posts about: {pillars}"
        source_label = "Auto"

    prompt = f"""You are a content strategist for {display_name}.
Tone: {tone}
{source_context}

Generate 7 social proof topic titles (Mon–Sun) that build trust through community voice,
user results, and real experiences. Frame them as "what users say" or "community results"
even if auto-generated (frame as hypothetical community conversation).

RULES: No em-dashes, en-dashes, or double-hyphens. Each topic max 80 chars.

Return ONLY a JSON array of 7 objects:
[{{"topic_num": 1, "day": "Mon", "date": "{day_dates['Mon']}", "topic": "...", "angle": "Social Proof", "source": "{source_label}"}}, ...]
Days: {', '.join(f'{d} {day_dates[d]}' for d in DAYS)}"""

    try:
        response = _call_gemini(prompt, client_id)
        topics = _extract_json(response)
        for i, t in enumerate(topics):
            t["bucket"] = "social_proof"
            t["topic_num"] = i + 1
            if not t.get("date"):
                t["date"] = day_dates.get(t.get("day", "Mon"), week_of)
        return topics[:7]
    except Exception as e:
        print(f"  Warning: social proof topic generation failed ({e}), using placeholders")
        return _make_placeholder_topics("social_proof", week_of, day_dates, "Social Proof", "Auto")


# ── Behind the Scenes ─────────────────────────────────────────────────────────

def generate_behind_the_scenes_topics(config: dict, week_of: str, day_dates: dict,
                                       client_input: str = "", mock: bool = False) -> list:
    """
    Generate 7 behind-the-scenes topics.
    If client_input provided: derives from team/process content.
    Otherwise: generates auto topics about brand philosophy and decision-making.
    """
    client_id = config.get("client_id", "bobe")
    display_name = config.get("display_name", client_id)

    if mock:
        return [
            {
                "bucket": "behind_the_scenes",
                "topic_num": i + 1,
                "day": DAYS[i],
                "date": day_dates[DAYS[i]],
                "topic": f"Mock behind-the-scenes topic {i + 1}",
                "angle": "Behind the Scenes",
                "source": "Client Input" if client_input else "Auto",
            }
            for i in range(7)
        ]

    tone = config.get("content", {}).get("tone", "educational")
    pillars = "; ".join(config.get("content", {}).get("messaging_pillars", []))

    if client_input:
        source_context = f"Based on this team/process update:\n{client_input[:800]}"
        source_label = "Client Input"
    else:
        source_context = f"Brand philosophy and decision-making around: {pillars}"
        source_label = "Auto"

    prompt = f"""You are a content strategist for {display_name}.
Tone: {tone}
{source_context}

Generate 7 behind-the-scenes topic titles (Mon–Sun) that build trust through transparency
about how the product is built, why decisions are made, and what the team values.

RULES: No em-dashes, en-dashes, or double-hyphens. Each topic max 80 chars.

Return ONLY a JSON array of 7 objects:
[{{"topic_num": 1, "day": "Mon", "date": "{day_dates['Mon']}", "topic": "...", "angle": "Behind the Scenes", "source": "{source_label}"}}, ...]
Days: {', '.join(f'{d} {day_dates[d]}' for d in DAYS)}"""

    try:
        response = _call_gemini(prompt, client_id)
        topics = _extract_json(response)
        for i, t in enumerate(topics):
            t["bucket"] = "behind_the_scenes"
            t["topic_num"] = i + 1
            if not t.get("date"):
                t["date"] = day_dates.get(t.get("day", "Mon"), week_of)
        return topics[:7]
    except Exception as e:
        print(f"  Warning: behind-the-scenes topic generation failed ({e}), using placeholders")
        return _make_placeholder_topics("behind_the_scenes", week_of, day_dates, "Behind the Scenes", "Auto")


# ── Community Engagement ─────────────────────────────────────────────────────

def generate_community_engagement_topics(config: dict, week_of: str, day_dates: dict,
                                          mock: bool = False) -> list:
    """
    Generate 7 community engagement topics (discussion starters, polls, questions).
    Fully auto-generated.
    """
    client_id = config.get("client_id", "bobe")
    display_name = config.get("display_name", client_id)

    if mock:
        return [
            {
                "bucket": "community_engagement",
                "topic_num": i + 1,
                "day": DAYS[i],
                "date": day_dates[DAYS[i]],
                "topic": f"Mock community topic {i + 1}: engagement question",
                "angle": "Community",
                "source": "Auto",
            }
            for i in range(7)
        ]

    tone = config.get("content", {}).get("tone", "educational")
    pillars = "; ".join(config.get("content", {}).get("messaging_pillars", []))
    tagline = config.get("tagline", "")

    prompt = f"""You are a content strategist for {display_name} — {tagline}.
Tone: {tone}
Pillars: {pillars}

Generate 7 community engagement topic titles (Mon–Sun) designed to spark conversation.
Mix formats: polls ("Which do you prefer: A or B?"), questions ("What's your biggest challenge with X?"),
debate starters ("Hot take: ..."), and opinion invites ("Unpopular opinion about ...").
All topics must be relevant to the brand's audience and industry.

RULES: No em-dashes, en-dashes, or double-hyphens. Each topic max 80 chars.

Return ONLY a JSON array of 7 objects:
[{{"topic_num": 1, "day": "Mon", "date": "{day_dates['Mon']}", "topic": "...", "angle": "Community", "source": "Auto"}}, ...]
Days: {', '.join(f'{d} {day_dates[d]}' for d in DAYS)}"""

    try:
        response = _call_gemini(prompt, client_id)
        topics = _extract_json(response)
        for i, t in enumerate(topics):
            t["bucket"] = "community_engagement"
            t["topic_num"] = i + 1
            if not t.get("date"):
                t["date"] = day_dates.get(t.get("day", "Mon"), week_of)
        return topics[:7]
    except Exception as e:
        print(f"  Warning: community engagement topic generation failed ({e}), using placeholders")
        return _make_placeholder_topics("community_engagement", week_of, day_dates, "Community", "Auto")


# ── Market Commentary ─────────────────────────────────────────────────────────

def generate_market_commentary_topics(config: dict, week_of: str, day_dates: dict,
                                       scraped_posts: list = None, mock: bool = False) -> list:
    """
    Generate 7 market commentary topics (broader industry analysis through brand lens).
    Uses scraped posts if available, otherwise generates from brand context.
    """
    client_id = config.get("client_id", "bobe")
    display_name = config.get("display_name", client_id)

    if mock:
        return [
            {
                "bucket": "market_commentary",
                "topic_num": i + 1,
                "day": DAYS[i],
                "date": day_dates[DAYS[i]],
                "topic": f"Mock market commentary topic {i + 1}: industry perspective",
                "angle": "Market Commentary",
                "source": "Live" if scraped_posts else "Evergreen",
            }
            for i in range(7)
        ]

    import client_config as cc
    keywords = ", ".join(cc.get_keywords(client_id)[:10])
    tone = config.get("content", {}).get("tone", "educational")
    tagline = config.get("tagline", "")

    scraped_posts = scraped_posts or []
    scraped_summary = (
        "\n".join(f"  - {p.get('text', p.get('topic', ''))[:100]}" for p in scraped_posts[:15])
        or "  (none — use industry evergreen context)"
    )

    prompt = f"""You are a content strategist for {display_name} — {tagline}.
Tone: {tone}
Keywords: {keywords}

Scraped industry posts ({len(scraped_posts)} found):
{scraped_summary}

Generate 7 market commentary topic titles (Mon–Sun) that offer {display_name}'s perspective
on broader industry trends, macro developments, and market dynamics.
These are NOT announcements — they are thoughtful takes on what's happening in the industry.

RULES: No em-dashes, en-dashes, or double-hyphens. Each topic max 80 chars.

Return ONLY a JSON array of 7 objects:
[{{"topic_num": 1, "day": "Mon", "date": "{day_dates['Mon']}", "topic": "...", "angle": "Market Commentary", "source": "Live or Evergreen"}}, ...]
Days: {', '.join(f'{d} {day_dates[d]}' for d in DAYS)}"""

    try:
        response = _call_gemini(prompt, client_id)
        topics = _extract_json(response)
        for i, t in enumerate(topics):
            t["bucket"] = "market_commentary"
            t["topic_num"] = i + 1
            if not t.get("date"):
                t["date"] = day_dates.get(t.get("day", "Mon"), week_of)
        return topics[:7]
    except Exception as e:
        print(f"  Warning: market commentary topic generation failed ({e}), using placeholders")
        return _make_placeholder_topics("market_commentary", week_of, day_dates, "Market Commentary", "Evergreen")


# ── Dispatcher ────────────────────────────────────────────────────────────────

BUCKET_GENERATORS = {
    "trending": generate_trending_topics,
    "education": generate_education_topics,
    "announcements": generate_announcement_placeholders,
    "social_proof": generate_social_proof_topics,
    "behind_the_scenes": generate_behind_the_scenes_topics,
    "community_engagement": generate_community_engagement_topics,
    "market_commentary": generate_market_commentary_topics,
}

BUCKET_DISPLAY_NAMES = {
    "trending": "Trending",
    "education": "Education",
    "announcements": "Announcements",
    "social_proof": "Social Proof",
    "behind_the_scenes": "Behind the Scenes",
    "community_engagement": "Community",
    "market_commentary": "Market Commentary",
}


def generate_bucket(bucket_type: str, config: dict, week_of: str, day_dates: dict,
                    scraped_posts: list = None, client_inputs: dict = None,
                    mock: bool = False) -> list:
    """
    Dispatch to the correct generator for a given bucket_type.

    Args:
        bucket_type: One of the 7 supported type IDs
        config: Client config dict
        week_of: YYYY-MM-DD week start
        day_dates: {Mon: YYYY-MM-DD, ...}
        scraped_posts: For trending/market_commentary buckets
        client_inputs: Dict from {week_of}-bucket-inputs.json
                       e.g. {"announcements": {"text": "..."}, "social_proof": {"text": "..."}}
        mock: Dry run flag

    Returns:
        List of 7 topic dicts
    """
    client_inputs = client_inputs or {}

    if bucket_type == "trending":
        return generate_trending_topics(config, week_of, day_dates, scraped_posts, mock)
    elif bucket_type == "education":
        return generate_education_topics(config, week_of, day_dates, mock)
    elif bucket_type == "announcements":
        # Support both single-input mode (list of texts) and legacy mode (single text)
        ann_data = client_inputs.get("announcements", {})
        if isinstance(ann_data, dict) and "texts" in ann_data:
            # New mode: list of individual announcement texts, 1 topic per text
            texts = ann_data["texts"]
            all_topics = []
            for i, txt in enumerate(texts[:7]):
                topics = generate_announcement_placeholders(
                    config, week_of, day_dates, txt, mock, count=1
                )
                if topics:
                    t = topics[0]
                    t["topic_num"] = i + 1
                    t["day"] = DAYS[i]
                    t["date"] = day_dates[DAYS[i]]
                    all_topics.append(t)
            # Fill remaining slots with placeholders
            for j in range(len(all_topics), 7):
                all_topics.append({
                    "bucket": "announcements",
                    "topic_num": j + 1,
                    "day": DAYS[j],
                    "date": day_dates[DAYS[j]],
                    "topic": "[Announcement — Awaiting client input]",
                    "angle": "Announcement",
                    "source": "Pending",
                    "status": "Pending Input",
                })
            return all_topics
        else:
            text = ann_data.get("text", "") if isinstance(ann_data, dict) else ""
            return generate_announcement_placeholders(config, week_of, day_dates, text, mock)
    elif bucket_type == "social_proof":
        text = client_inputs.get("social_proof", {}).get("text", "")
        return generate_social_proof_topics(config, week_of, day_dates, text, mock)
    elif bucket_type == "behind_the_scenes":
        text = client_inputs.get("behind_the_scenes", {}).get("text", "")
        return generate_behind_the_scenes_topics(config, week_of, day_dates, text, mock)
    elif bucket_type == "community_engagement":
        return generate_community_engagement_topics(config, week_of, day_dates, mock)
    elif bucket_type == "market_commentary":
        return generate_market_commentary_topics(config, week_of, day_dates, scraped_posts, mock)
    else:
        print(f"  Warning: unknown bucket_type '{bucket_type}', using placeholders")
        day_dates = day_dates or _build_day_dates(week_of)
        return _make_placeholder_topics(bucket_type, week_of, day_dates, "Education", "Auto")
