# Brand Assets

Place your brand assets in this directory:

## Required

- `logo.png` — Primary logo (transparent background preferred)

## Recommended

- Banner examples (1-4 images showing desired style)
- Color reference image
- Mascot/character reference images

## How These Are Used

Reference images are sent to the image generation API alongside text prompts. The AI uses them to reproduce your brand's visual identity (logo placement, character appearance, color palette) accurately in generated content images.

The `reference_images` array in `config.json` controls which images from this directory are included. You can have up to 10 reference images.
