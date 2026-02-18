#!/usr/bin/env python3
"""
BoBe Weekly Content Pipeline Orchestrator

Called in stages by .claude/commands/weekly-pipeline.md:

  Stage 1 — scrape topics:
    python scripts/weekly_pipeline.py --action scrape --week-of 2026-02-16 --count 100 --output /tmp/weekly_topics.json

  Stage 2 — create workbook:
    python scripts/weekly_pipeline.py --action create-workbook --week-of 2026-02-16

  Stage 3 — save one content item (called once per topic by Claude):
    python scripts/weekly_pipeline.py --action save-content \
      --week-of 2026-02-16 \
      --content-file /tmp/weekly_content_1.json

  Stage 4 — finalize (macOS notification + summary):
    python scripts/weekly_pipeline.py --action finalize --week-of 2026-02-16

Content JSON format for save-content:
{
  "date": "2026-02-16",
  "day": "Mon",
  "topic": "Topic text here",
  "platform": "Twitter",
  "format": "thread",
  "content": "English content...",
  "image_prompt": "Detailed prompt for nano_banana.py...",
  "image_path": "outputs/content/images/2026-02-16-weekly/2026-02-16_mon_topic-slug_twitter.png",
  "hashtags": ["#DeFi", "#TradingBot"],
  "content_ru": "Russian content...",
  "image_prompt_ru": "Russian image prompt with Cyrillic headline...",
  "image_path_ru": "outputs/content/images/2026-02-16-weekly/2026-02-16_mon_topic-slug_twitter_ru.png",
  "hashtags_ru": ["#DeFi", "#Крипто"],
  "status": "Draft"
}
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# Make scripts/ importable as a package
sys.path.insert(0, str(Path(__file__).parent))

from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter
from dotenv import load_dotenv

load_dotenv()

# Import styling helpers from excel_manager
from excel_manager import (
    style_header_cell, style_data_cell,
    COLOR_DARK_BG, COLOR_BLUE, COLOR_GREEN, COLOR_WHITE, COLOR_LIGHT_ROW,
)

OUTPUT_DIR = Path(__file__).parent.parent / "outputs" / "content"

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
POSTS_PER_DAY = 3

WEEKLY_KEYWORDS = [
    "trading bot", "yield", "DCA strategy", "automated trading",
    "on-chain yield", "crypto automation", "AI trading", "grid bot",
    "passive crypto", "crypto bot", "DeFi yield", "USDT yield",
    "risk management crypto", "emotional trading", "crypto strategy",
]


def get_week_of(date_str=None):
    """Return Monday of the current (or specified) week as YYYY-MM-DD."""
    if date_str:
        d = datetime.strptime(date_str, "%Y-%m-%d")
    else:
        d = datetime.now()
    monday = d - timedelta(days=d.weekday())
    return monday.strftime("%Y-%m-%d")


def scrape_weekly_topics(week_of, count=100, mock=False, output_path=None):
    """
    Scrape Twitter for the past 7 days using apify_scraper.
    Falls back gracefully if scraping fails.
    Returns ranked list of topic dicts.
    """
    from apify_scraper import (
        scrape_twitter, filter_by_relevance, rank_by_engagement, mock_scrape
    )

    if mock:
        print("Running in MOCK mode — no API calls.")
        posts = []
        for _ in range(5):
            posts += mock_scrape("twitter")
        filtered = filter_by_relevance(posts, WEEKLY_KEYWORDS)
        ranked = rank_by_engagement(filtered)
        if output_path:
            with open(output_path, "w") as f:
                json.dump(ranked, f, indent=2, default=str)
        print(f"Mock: {len(ranked)} topics generated.")
        return ranked

    since_date = (datetime.strptime(week_of, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")
    print(f"Scraping Twitter for past 7 days (since {since_date})...")

    all_posts = []
    try:
        tweets = scrape_twitter(WEEKLY_KEYWORDS, count=count, since_date=since_date)
        print(f"  Got {len(tweets)} tweets")
        all_posts.extend(tweets)
    except Exception as e:
        print(f"  Twitter scraping failed: {e}")

    filtered = filter_by_relevance(all_posts, WEEKLY_KEYWORDS)
    ranked = rank_by_engagement(filtered)
    print(f"  {len(ranked)} relevant posts after filtering")

    if output_path:
        with open(output_path, "w") as f:
            json.dump(ranked, f, indent=2, default=str)
        print(f"  Saved to: {output_path}")

    return ranked


def create_weekly_workbook(week_of):
    """
    Create outputs/content/{week_of}-weekly-content.xlsx with:
    - Sheet 1: Topics (same columns as daily, Week Of instead of Date)
    - Sheet 2: Content (adds Day column as column B)
    """
    wb = Workbook()

    # --- Sheet 1: Topics ---
    ws1 = wb.active
    ws1.title = "Topics"

    topic_headers = [
        "Week Of", "Platform", "Topic Summary", "Original Text",
        "Author", "URL", "Engagement Score", "Relevance Score", "Source Type",
    ]
    topic_col_widths = [12, 10, 35, 60, 20, 40, 16, 16, 14]

    for i, (header, width) in enumerate(zip(topic_headers, topic_col_widths), 1):
        cell = ws1.cell(row=1, column=i, value=header)
        style_header_cell(cell)
        ws1.column_dimensions[get_column_letter(i)].width = width

    ws1.row_dimensions[1].height = 35
    ws1.freeze_panes = "A2"

    # --- Sheet 2: Content (with Day column) ---
    ws2 = wb.create_sheet("Content")

    content_headers = [
        "Date", "Day", "Topic", "Platform Target", "Format",
        "Content", "Image Prompt", "Image Path", "Hashtags",
        "Content_RU", "Image_Prompt_RU", "Image_Path_RU", "Hashtags_RU", "Status",
    ]
    content_col_widths = [12, 6, 30, 14, 10, 70, 50, 40, 35, 70, 50, 40, 35, 12]

    for i, (header, width) in enumerate(zip(content_headers, content_col_widths), 1):
        cell = ws2.cell(row=1, column=i, value=header)
        style_header_cell(cell)
        ws2.column_dimensions[get_column_letter(i)].width = width

    ws2.row_dimensions[1].height = 35
    ws2.freeze_panes = "A2"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{week_of}-weekly-content.xlsx"
    wb.save(str(path))
    return str(path)


def append_content_row(week_of, content_item):
    """
    Append one content row to the weekly workbook's Content sheet.
    content_item must have: date, day, topic, platform, format, content,
                            image_prompt, image_path, hashtags, status
    """
    path = OUTPUT_DIR / f"{week_of}-weekly-content.xlsx"
    if not path.exists():
        raise FileNotFoundError(f"Weekly workbook not found: {path}. Run --action create-workbook first.")

    wb = load_workbook(str(path))
    ws = wb["Content"]
    next_row = ws.max_row + 1
    row_idx = next_row - 2  # for alternating color (0-based after header)

    hashtags = content_item.get("hashtags", [])
    hashtag_str = ", ".join(hashtags) if isinstance(hashtags, list) else str(hashtags)

    hashtags_ru = content_item.get("hashtags_ru", [])
    hashtag_ru_str = ", ".join(hashtags_ru) if isinstance(hashtags_ru, list) else str(hashtags_ru)

    values = [
        content_item.get("date", ""),
        content_item.get("day", ""),
        content_item.get("topic", ""),
        content_item.get("platform", ""),
        content_item.get("format", ""),
        content_item.get("content", ""),
        content_item.get("image_prompt", ""),
        content_item.get("image_path", ""),
        hashtag_str,
        content_item.get("content_ru", ""),
        content_item.get("image_prompt_ru", ""),
        content_item.get("image_path_ru", ""),
        hashtag_ru_str,
        content_item.get("status", "Draft"),
    ]

    for col_idx, value in enumerate(values, 1):
        cell = ws.cell(row=next_row, column=col_idx, value=value)
        style_data_cell(cell, row_idx)

    ws.row_dimensions[next_row].height = 80
    wb.save(str(path))


def finalize(week_of):
    """Send macOS notification and print completion summary."""
    path = OUTPUT_DIR / f"{week_of}-weekly-content.xlsx"
    row_count = 0

    if path.exists():
        wb = load_workbook(str(path), read_only=True, data_only=True)
        if "Content" in wb.sheetnames:
            row_count = wb["Content"].max_row - 1  # subtract header
        wb.close()

    msg = f"{row_count} content items ready in {week_of}-weekly-content.xlsx"
    title = "BoBe Weekly Pipeline Complete"

    # macOS notification via osascript
    script = f'display notification "{msg}" with title "{title}"'
    subprocess.run(["osascript", "-e", script], capture_output=True)

    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"  Week of: {week_of}")
    print(f"  {row_count} content rows saved")
    print(f"  File: outputs/content/{week_of}-weekly-content.xlsx")
    print(f"  View: /view-content week:{week_of}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="BoBe Weekly Pipeline Orchestrator")
    parser.add_argument("--action",
                        choices=["scrape", "create-workbook", "save-content", "finalize"],
                        required=True,
                        help="Pipeline stage to execute")
    parser.add_argument("--week-of", default=None,
                        help="Monday of target week (YYYY-MM-DD). Defaults to current week's Monday.")
    parser.add_argument("--count", type=int, default=100,
                        help="Max posts to scrape (--action scrape only)")
    parser.add_argument("--output", default=None,
                        help="Output JSON path (--action scrape only)")
    parser.add_argument("--content-file", default=None,
                        help="Path to content JSON file (--action save-content only)")
    parser.add_argument("--mock", action="store_true",
                        help="Use mock data instead of real API calls")

    args = parser.parse_args()
    week_of = get_week_of(args.week_of) if args.week_of else get_week_of()

    if args.action == "scrape":
        scrape_weekly_topics(week_of, count=args.count, mock=args.mock, output_path=args.output)

    elif args.action == "create-workbook":
        path = create_weekly_workbook(week_of)
        print(f"Weekly workbook created: {path}")

    elif args.action == "save-content":
        if not args.content_file:
            print("Error: --content-file is required for save-content action")
            sys.exit(1)
        with open(args.content_file) as f:
            item = json.load(f)
        append_content_row(week_of, item)
        print(f"Saved: [{item.get('day', '?')}] {item.get('topic', '')[:60]} ({item.get('platform', '')})")

    elif args.action == "finalize":
        finalize(week_of)


if __name__ == "__main__":
    main()
