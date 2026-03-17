---
name: blog-writer
description: |
  Generate blog posts from approved social media content for the active client.
  Use when the user clicks "Blog+" on a post, asks to create a blog from a topic,
  or wants to expand social content into long-form articles. Produces 800-1500 word
  blog posts aligned with the client's tone and messaging. Runs /humanizer on all
  output to remove AI writing patterns. Reads client config and content guidelines
  before generating.
---

# Blog Writer

Generate long-form blog posts from social media content (Twitter threads, Telegram posts) for the active client.

## Before Generating

1. Determine the active client:
   ```bash
   cat .active-client 2>/dev/null || echo "bobe"
   ```

2. Always read:
   - `clients/{active_client}/config.json`
   - `clients/{active_client}/content-guidelines.md`
   - `clients/{active_client}/context.md`

## Input Requirements

- **Source post**: The approved Twitter thread or Telegram post content (required)
- **Topic**: The topic title from the content card (required)
- **Bucket**: Which bucket this came from (trending, education, announcements)
- **Target length**: 800-1500 words (default: 1000)
- **Additional context**: Any extra context the client wants included (optional)

## Blog Structure

### Standard Blog Format (800-1500 words)

1. **Headline** (8-12 words, specific, not clickbait)
   - Use the topic as a starting point but make it blog-appropriate
   - No colons in headlines. No "How X is Changing Y" formulas.

2. **Opening paragraph** (2-3 sentences)
   - Start with a concrete observation, data point, or scenario
   - No "In today's rapidly evolving..." openings
   - Hook the reader with something specific, not generic

3. **Body sections** (3-4 sections, each 150-300 words)
   - Each section has a lowercase heading (not title case)
   - Expand on the social post's key points with depth
   - Add context the short-form content couldn't include
   - Use specific examples, numbers, or scenarios
   - Vary paragraph length (1-4 sentences)

4. **Client connection** (1 paragraph)
   - Naturally connect the topic to the client's product/service
   - Use messaging pillars from content-guidelines.md
   - No hard sell. Educational positioning only.

5. **Closing** (2-3 sentences)
   - End with a thought, question, or forward-looking statement
   - Soft CTA from config.json cta_examples
   - No "In conclusion..." or "The future looks bright..."

## Voice Rules

- Match the client's configured tone and voice exactly
- Write like a knowledgeable person talking to a peer, not a brand talking to consumers
- Have opinions. React to the topic, don't just report it.
- Vary rhythm: short punchy sentences mixed with longer ones
- Use "you" naturally. Use "we" when speaking as the brand.
- No guaranteed return claims for financial products
- No em-dashes, en-dashes, or double-hyphens as punctuation

## Mandatory Post-Processing

After generating the blog draft, ALWAYS run /humanizer on the output. This is not optional. The blog must pass the humanizer's anti-AI audit before delivery.

The humanizer will:
1. Remove AI vocabulary (delve, crucial, landscape, tapestry, etc.)
2. Fix rule-of-three patterns
3. Remove significance inflation
4. Add natural voice and personality
5. Verify the text sounds human when read aloud

## Image Prompts for Blog

Generate 2-3 image prompt suggestions for the blog post:
- Use the client's approved image style preference (from Baserow/config)
- Include mascot, logo, and brand colors from config
- Each prompt should illustrate a different section of the blog
- Format: `{mascot_description} in {scenario}, {background_style}, headline '{section_heading}', {logo_description}`

## Output Format

Return a JSON object:

```json
{
  "headline": "The blog headline",
  "slug": "the-blog-headline-as-url-slug",
  "body": "Full blog text in markdown format",
  "meta_description": "150-char SEO meta description",
  "image_prompts": [
    "Image prompt for hero image",
    "Image prompt for section illustration"
  ],
  "source_topic": "Original topic title",
  "source_platform": "twitter|telegram",
  "word_count": 1050
}
```

## Example

**Input:** Topic: "DCA bots outperform manual traders in volatile markets" | Source: Twitter thread about automation vs. emotional trading | Bucket: trending

**Output (after /humanizer):**
```json
{
  "headline": "Your trading plan works until you don't follow it",
  "slug": "trading-plan-works-until-you-dont-follow-it",
  "body": "Every trader has a plan. Most of them abandon it the moment a red candle shows up on the 15-minute chart.\n\nI've watched this pattern play out hundreds of times...\n\n## the gap between knowing and doing\n\nYou know you should DCA. You know you shouldn't panic sell...\n\n## what automation actually solves\n\nThe pitch for trading bots isn't that they're smarter than you...\n\n## the numbers nobody talks about\n\nA 2024 analysis of 50,000 retail accounts showed...\n\n## where BoBe fits\n\nBoBe runs AI-driven DCA and grid strategies on-chain...\n\nIf your trading strategy only works when the market goes up, it's not a strategy. Learn more at bobe.app",
  "meta_description": "Why most traders abandon their strategy at the worst moment, and what automated DCA bots do differently.",
  "image_prompts": [
    "BoBe mascot (3D clay chibi figurine, young Asian man with round dark glasses, white BoBe t-shirt) looking at two screens, one showing red panic charts, one showing steady green automated lines, deep navy background, headline 'plan vs. panic', BoBe logo top-left, minimal clean style",
    "BoBe mascot sleeping peacefully while trading screens show steady green lines, deep navy background, headline 'discipline at scale', BoBe logo top-left, tech style"
  ],
  "source_topic": "DCA bots outperform manual traders in volatile markets",
  "source_platform": "twitter",
  "word_count": 1020
}
```
