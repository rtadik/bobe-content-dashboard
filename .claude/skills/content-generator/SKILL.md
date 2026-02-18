---
name: content-generator
description: Generate Telegram and Twitter/X content for BoBe from curated crypto/DeFi topics. Use when creating social media posts, threads, or announcements based on trending topics or news. Produces copy aligned with BoBe's transparent, educational, non-hype messaging style. Always reads reference/content-guidelines.md before generating.
---

# Content Generator for BoBe

Generate platform-specific social media content (Twitter/X or Telegram) from crypto/DeFi topics.

## Before Generating

Always read:
- `reference/content-guidelines.md` — tone, voice, what to avoid
- `reference/bobe-keywords.md` — relevant themes and hashtags
- `context/BoBe Context.md` — messaging pillars and ICP

## Input Requirements

Provide as much of the following as available:

- **Topic**: What the post is about (headline or summary)
- **Source**: Where the topic came from (Twitter, Reddit, custom)
- **Key insight**: The core angle or interesting finding
- **Platform target**: Twitter or Telegram
- **Format**: Single post, thread, or long-form (Telegram)

## Content Formats

### Twitter Single Post (≤280 chars)
- Hook first — pain point, bold claim, or question
- One clear insight or value prop
- Optional soft CTA
- 2–3 hashtags max
- No guaranteed returns language

### Twitter Thread (3–5 tweets)
- Tweet 1: Hook/question (standalone, must make people want to read on)
- Tweets 2–3: Education, breakdown, data
- Tweet 4: BoBe connection (how automation/transparency solves this)
- Tweet 5: Soft CTA — "Follow for more" or "bobe.app"

### Telegram Post
- 400–1200 chars
- More educational and explanatory
- Use line breaks generously (not walls of text)
- End with engagement question or CTA
- Can mention BoBe more directly than Twitter

## BoBe Voice Reminders

- Transparent, not hype-driven
- Educational, not salesy
- Risk-aware — never guarantee returns
- Automation-focused — the robot handles what humans struggle with emotionally

**Good:** "Most traders don't fail from bad analysis. They fail from not following the plan."
**Bad:** "BoBe gives you 200% APY guaranteed! Don't miss out!"

## Output Format

Return a JSON object:

```json
{
  "platform": "twitter | telegram",
  "format": "single | thread | long-form",
  "content": "Full content text. For threads, separate tweets with ---",
  "image_prompt": "Detailed image prompt for nano_banana.py using BoBe mascot style",
  "hashtags": ["#DeFi", "#TradingBot", "#CryptoTrading"],
  "topic_slug": "short-topic-identifier-for-filename"
}
```

### Image Prompt Guidelines

For the `image_prompt` field, always use the BoBe brand template from `reference/bobe-brand/README.md`:

Include:
1. The BoBe mascot description (3D clay chibi, glasses, BoBe t-shirt)
2. Scenario matching the topic
3. Background style (dark navy default, or themed)
4. A short headline matching the content hook
5. Style preset: minimal | tech | neon | outdoor | notification

Example:
```
BoBe mascot (3D clay chibi figurine, young Asian man with round dark glasses, white BoBe t-shirt)
sitting confidently at a trading desk with floating holographic green charts, deep dark navy
background (#111B32), blue gradient accents, bold white headline "Steady beats emotional."
top area, BoBe APP logo top-left, cinematic 3D render, social media banner 16:9
```

## Example Output

**Input:** Topic: "DCA bots outperform manual traders in volatile markets" | Platform: Twitter | Format: thread

**Output:**
```json
{
  "platform": "twitter",
  "format": "thread",
  "content": "Most traders have a plan.\n\nThey just can't execute it when it matters.\n\nHere's why automation beats emotion every time 🧵\n---\nIn volatile markets, the average retail trader does the opposite of what they planned.\n\nThey sell at the bottom. They FOMO buy at the top.\n\nNot because they're dumb — but because the market is designed to trigger emotional decisions.\n---\nDCA bots don't feel fear.\nThey don't panic at -20%.\nThey don't chase green candles.\n\nThey just execute the strategy. Every time. 24/7.\n---\nBoBe runs AI-driven DCA and grid strategies on-chain.\n\nYour deposit works while you sleep.\nNo leverage. No manual decisions. Full transparency.\n---\nIf you're tired of making trades you regret — automation isn't cheating.\n\nIt's discipline at scale.\n\nbobe.app",
  "image_prompt": "BoBe mascot (3D clay chibi figurine, young Asian man with round dark glasses, white BoBe t-shirt) sleeping peacefully in a chair while trading screens show green charts in background, deep dark navy background, blue gradient accents, bold white headline 'While you sleep.' top-left, BoBe APP logo top-left corner, cinematic 3D render quality, social media banner 16:9",
  "hashtags": ["#DeFi", "#TradingBot", "#CryptoTrading", "#AutomatedTrading"],
  "topic_slug": "dca-bots-outperform-manual"
}
```
