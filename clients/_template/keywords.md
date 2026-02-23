# [Client Name] — Keyword Reference

<!-- AI-DRAFT INSTRUCTIONS (for /onboard-client):
Fill every section below using the Q&A answers and config.json scraping keywords.
Primary keywords = most directly product-relevant (top 8-10 from config).
Secondary keywords = broader audience/pain point terms (remaining from config).
Negative keywords = from config negative_keywords.
Subreddits = from config subreddits.
Twitter queries = construct 3-5 ready-to-use Apify queries from primary keywords.
Do not leave placeholder text. When done, remove all AI-DRAFT comment blocks.
-->

Used by the content pipeline to filter and rank scraped posts for relevance.

---

## Primary Keywords (High Relevance)

These directly relate to the core offering. Posts containing these are most likely to be relevant topics:

- [keyword — most directly product-related]
- [keyword]
- [keyword]
- [keyword]
- [keyword]

---

## Secondary Keywords (Medium Relevance)

These relate to the broader audience, their pain points, and adjacent topics:

- [keyword — audience pain point or adjacent topic]
- [keyword]
- [keyword]
- [keyword]
- [keyword]

---

## Negative Keywords (Filter Out)

Exclude posts containing these — they indicate spam, off-topic content, or brand-damaging associations:

- [negative keyword]
- [negative keyword]
- scam
- spam

---

## Subreddits to Monitor

- r/[subreddit — most relevant community]
- r/[subreddit]
- r/[subreddit]

---

## Twitter Search Queries

Ready-to-use queries for the Apify scraper. Copy directly into `--keywords` flag:

1. `"[primary keyword 1]" -scam -spam`
2. `"[primary keyword 2]" [secondary keyword]`
3. `[keyword] [keyword] -[negative keyword]`
4. `"[brand-relevant phrase]"`
5. `[keyword] tips OR guide OR how`
