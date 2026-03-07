#!/usr/bin/env python3
"""
Content Pipeline - Apify Scraper
Scrapes Twitter and Reddit for content topics relevant to the active client.
Multi-client: reads keywords and negative keywords from client config.

Environment variables (loaded from .env):
  APIFY_API_TOKEN: Your Apify API token

Usage:
  python scripts/apify_scraper.py --platform twitter --keywords "defi,yield,trading bot"
  python scripts/apify_scraper.py --platform reddit --subreddits "defi,cryptocurrency" --keywords "yield,automation"
  python scripts/apify_scraper.py --platform all --mock
  python scripts/apify_scraper.py --client newclient --platform twitter --mock
"""

import os
import json
import sys
import time
import argparse
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent)) if False else None
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import client_config

APIFY_API_TOKEN = os.environ.get("APIFY_API_TOKEN")
APIFY_BASE_URL = "https://api.apify.com/v2"

# Actor IDs confirmed working on free Apify tier (2026-02-18)
TWITTER_ACTOR_ID = "2dZb9qNraqcbL8CXP"  # Twitter Tweets Scraper
REDDIT_ACTOR_ID = "trudax~reddit-scraper"  # Note: may need paid plan; fallback to mock


def _get_negative_keywords(client_id=None):
    """Load negative keywords from client config."""
    return client_config.get_negative_keywords(client_id)


def run_apify_actor(actor_id: str, run_input: dict, timeout: int = 120) -> List[Dict]:
    """Start an Apify actor run and wait for results."""
    if not APIFY_API_TOKEN:
        raise ValueError("APIFY_API_TOKEN not set. Check your .env file.")

    headers = {"Content-Type": "application/json"}
    start_url = f"{APIFY_BASE_URL}/acts/{actor_id}/runs?token={APIFY_API_TOKEN}"

    print(f"  Starting Apify actor: {actor_id}")
    response = requests.post(start_url, json=run_input, headers=headers, timeout=30)
    response.raise_for_status()

    run_id = response.json()["data"]["id"]
    print(f"  Run started: {run_id}")

    # Poll for completion
    status_url = f"{APIFY_BASE_URL}/actor-runs/{run_id}?token={APIFY_API_TOKEN}"
    elapsed = 0
    poll_interval = 5

    while elapsed < timeout:
        time.sleep(poll_interval)
        elapsed += poll_interval
        status_resp = requests.get(status_url, timeout=10)
        status = status_resp.json()["data"]["status"]
        print(f"  Status: {status} ({elapsed}s)")

        if status == "SUCCEEDED":
            break
        elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise RuntimeError(f"Apify actor failed with status: {status}")

    # Fetch results from default dataset
    dataset_id = status_resp.json()["data"]["defaultDatasetId"]
    results_url = f"{APIFY_BASE_URL}/datasets/{dataset_id}/items?token={APIFY_API_TOKEN}"
    items_resp = requests.get(results_url, timeout=30)
    items_resp.raise_for_status()

    return items_resp.json()


def scrape_twitter(keywords: List[str], count: int = 50, since_date: Optional[str] = None) -> List[Dict]:
    """Scrape Twitter for posts matching keywords using Twitter Tweets Scraper actor."""
    # Build search queries and pass as Twitter search URLs (more reliable than searchTerms)
    search_queries = [
        f"{kw} crypto" if i < 3 else kw
        for i, kw in enumerate(keywords[:5])
    ]
    if since_date:
        search_queries = [f"{q} since:{since_date}" for q in search_queries]

    # Try startUrls format first (Twitter search result pages), fall back to searchTerms
    search_urls = [
        {"url": f"https://twitter.com/search?q={urllib.parse.quote(q)}&f=live&lang=en"}
        for q in search_queries
    ]
    run_input = {
        "startUrls": search_urls,
        "maxItems": count,
        "lang": "en",
    }

    raw_items = run_apify_actor(TWITTER_ACTOR_ID, run_input)

    posts = []
    for item in raw_items:
        if item.get("noResults") or item.get("lang") != "en":
            continue
        text = item.get("full_text", item.get("text", ""))
        if not text or len(text) < 30:
            continue

        user = item.get("user", {})
        tweet_id = item.get("id_str", item.get("id", ""))
        screen_name = user.get("screen_name", "") if isinstance(user, dict) else ""

        posts.append({
            "platform": "twitter",
            "id": tweet_id,
            "text": text,
            "author": screen_name,
            "url": item.get("url", f"https://twitter.com/i/web/status/{tweet_id}"),
            "likes": item.get("favorite_count", 0),
            "retweets": item.get("retweet_count", 0),
            "replies": item.get("reply_count", 0),
            "views": item.get("views_count", 0),
            "date": item.get("created_at", ""),
            "engagement": item.get("favorite_count", 0) + item.get("retweet_count", 0) * 3 + item.get("reply_count", 0),
        })

    return posts


def scrape_reddit(subreddits: List[str], keywords: List[str], count: int = 50) -> List[Dict]:
    """Scrape Reddit using the native JSON API (no Apify required)."""
    headers = {"User-Agent": "ContentBot/1.0 (social media research)"}
    all_posts = []
    seen_ids = set()

    # Search each subreddit with top keywords (cap at 4 keywords to avoid rate limits)
    for sub in subreddits:
        for kw in keywords[:4]:
            url = (
                f"https://www.reddit.com/r/{sub}/search.json"
                f"?q={urllib.parse.quote(kw)}&restrict_sr=1&sort=hot&t=month&limit=10"
            )
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read())
                children = data.get("data", {}).get("children", [])
                for child in children:
                    pd = child.get("data", {})
                    post_id = pd.get("id", "")
                    if not post_id or post_id in seen_ids:
                        continue
                    seen_ids.add(post_id)
                    title = pd.get("title", "").strip()
                    selftext = (pd.get("selftext") or "").strip()
                    # Combine title + body excerpt as the post text
                    text = title + (f"\n{selftext[:400]}" if selftext and selftext != "[removed]" else "")
                    score = pd.get("score", 0)
                    num_comments = pd.get("num_comments", 0)
                    all_posts.append({
                        "platform": "reddit",
                        "id": post_id,
                        "text": text,
                        "title": title,
                        "author": pd.get("author", ""),
                        "url": "https://reddit.com" + pd.get("permalink", ""),
                        "likes": score,
                        "retweets": 0,
                        "replies": num_comments,
                        "views": 0,
                        "subreddit": pd.get("subreddit", sub),
                        "engagement": score + num_comments * 2,
                        "date": datetime.fromtimestamp(pd.get("created_utc", 0)).isoformat() if pd.get("created_utc") else "",
                    })
            except Exception as e:
                print(f"  Reddit r/{sub} '{kw}': {e}")

        if len(all_posts) >= count:
            break

    return all_posts[:count]


def filter_by_relevance(posts: List[Dict], keywords: List[str], client_id: str = None) -> List[Dict]:
    """Filter posts by relevance to keywords, excluding negative keywords."""
    filtered = []
    kw_lower = [k.lower() for k in keywords]
    neg_keywords = _get_negative_keywords(client_id)
    neg_lower = [n.lower() for n in neg_keywords]

    for post in posts:
        text = post.get("text", "").lower()

        # Skip if contains negative keywords
        if any(neg in text for neg in neg_lower):
            continue

        # Score by keyword matches
        matches = sum(1 for kw in kw_lower if kw in text)
        if matches > 0:
            post["relevance_score"] = matches
            filtered.append(post)

    return filtered


def rank_by_engagement(posts: List[Dict]) -> List[Dict]:
    """Rank posts by combined engagement and relevance score."""
    return sorted(
        posts,
        key=lambda p: p.get("engagement", 0) * p.get("relevance_score", 1),
        reverse=True
    )


def get_top_topics(posts: List[Dict], n: int = 3) -> List[Dict]:
    """Return top N posts as topic candidates."""
    return posts[:n]


def mock_scrape(platform: str) -> List[Dict]:
    """Return mock data for testing without API calls."""
    mock_data = [
        {
            "platform": platform,
            "id": "mock_001",
            "text": "DCA bots have been printing quietly while everyone panics. Automation > emotion in 2026 #DeFi #TradingBot",
            "author": "crypto_trader_x",
            "url": "https://twitter.com/mock/1",
            "likes": 342,
            "retweets": 87,
            "replies": 24,
            "engagement": 603,
            "relevance_score": 3,
            "date": datetime.now().isoformat(),
        },
        {
            "platform": platform,
            "id": "mock_002",
            "text": "Why most traders fail: they can't stick to their own rules. Grid bots don't have that problem. On-chain yield strategies are changing the game.",
            "author": "defi_analyst",
            "url": "https://twitter.com/mock/2",
            "likes": 218,
            "retweets": 54,
            "replies": 31,
            "engagement": 430,
            "relevance_score": 4,
            "date": datetime.now().isoformat(),
        },
        {
            "platform": platform,
            "id": "mock_003",
            "text": "Just reviewed 3 automated trading platforms for passive crypto yield. Thread on what actually matters when evaluating these tools",
            "author": "yield_researcher",
            "url": "https://twitter.com/mock/3",
            "likes": 156,
            "retweets": 43,
            "replies": 19,
            "engagement": 285,
            "relevance_score": 3,
            "date": datetime.now().isoformat(),
        },
        {
            "platform": platform,
            "id": "mock_004",
            "text": "Risk management is the most underrated skill in crypto. Automated strategies with defined stop-losses outperform manual trading consistently.",
            "author": "risk_mgmt_pro",
            "url": "https://twitter.com/mock/4",
            "likes": 98,
            "retweets": 31,
            "replies": 12,
            "engagement": 191,
            "relevance_score": 2,
            "date": datetime.now().isoformat(),
        },
        {
            "platform": platform,
            "id": "mock_005",
            "text": "USDT yield on DeFi: what's actually sustainable in 2026? Quick breakdown of strategies that have proven track records vs. ones that are just APY theater.",
            "author": "defi_realist",
            "url": "https://twitter.com/mock/5",
            "likes": 87,
            "retweets": 22,
            "replies": 8,
            "engagement": 153,
            "relevance_score": 3,
            "date": datetime.now().isoformat(),
        },
    ]
    return mock_data


def main():
    parser = argparse.ArgumentParser(description="Scrape Twitter/Reddit for content topics")
    parser.add_argument("--platform", choices=["twitter", "reddit", "all"], default="all",
                        help="Platform to scrape")
    parser.add_argument("--keywords", default=None,
                        help="Comma-separated keywords (overrides client config)")
    parser.add_argument("--subreddits", default=None,
                        help="Comma-separated subreddits (overrides client config)")
    parser.add_argument("--count", type=int, default=50,
                        help="Max posts to scrape per platform")
    parser.add_argument("--days", type=int, default=None,
                        help="Filter posts from the last N days (adds since:YYYY-MM-DD to Twitter queries)")
    parser.add_argument("--top", type=int, default=30,
                        help="Number of top topics to return")
    parser.add_argument("--mock", action="store_true",
                        help="Use mock data instead of real API calls")
    parser.add_argument("--output", default=None,
                        help="Save results to JSON file")
    client_config.add_client_arg(parser)

    args = parser.parse_args()
    active_client = client_config.resolve_client(args)

    # Load keywords from config if not overridden via CLI
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",")]
    else:
        keywords = client_config.get_keywords(active_client)

    if args.subreddits:
        subreddits = [s.strip() for s in args.subreddits.split(",")]
    else:
        subreddits = client_config.get_subreddits(active_client)

    config = client_config.load_config(active_client)
    display_name = config.get("display_name", active_client)
    print(f"\nScraping for client: {display_name}")

    all_posts = []

    if args.mock:
        print("Running in MOCK mode, no API calls made.")
        all_posts = mock_scrape(args.platform if args.platform != "all" else "twitter")
        all_posts += mock_scrape("reddit")
    else:
        if args.platform in ("twitter", "all"):
            since_date = None
            if args.days:
                since_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
                print(f"\nScraping Twitter for: {keywords} (since {since_date})")
            else:
                print(f"\nScraping Twitter for: {keywords}")
            try:
                tweets = scrape_twitter(keywords, args.count, since_date=since_date)
                print(f"  Got {len(tweets)} tweets")
                all_posts.extend(tweets)
            except Exception as e:
                print(f"  Twitter scraping failed: {e}")

        if args.platform in ("reddit", "all"):
            print(f"\nScraping Reddit subreddits: {subreddits}")
            try:
                reddit_posts = scrape_reddit(subreddits, keywords, args.count)
                print(f"  Got {len(reddit_posts)} Reddit posts")
                all_posts.extend(reddit_posts)
            except Exception as e:
                print(f"  Reddit scraping failed: {e}")

    # Filter and rank
    print(f"\nFiltering {len(all_posts)} posts by relevance...")
    filtered = filter_by_relevance(all_posts, keywords, client_id=active_client)
    ranked = rank_by_engagement(filtered)
    top_topics = get_top_topics(ranked, args.top)

    print(f"\n--- TOP {len(top_topics)} TOPICS ---\n")
    for i, post in enumerate(top_topics, 1):
        print(f"{i}. [{post['platform'].upper()}] Engagement: {post.get('engagement', 0)} | Relevance: {post.get('relevance_score', 0)}")
        print(f"   {post['text'][:120]}...")
        print(f"   URL: {post['url']}\n")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(top_topics, f, indent=2, default=str)
        print(f"Results saved to: {args.output}")

    return top_topics


if __name__ == "__main__":
    main()
