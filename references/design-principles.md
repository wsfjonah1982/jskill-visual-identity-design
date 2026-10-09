# Identity Design Principles — the strategy before the pixels

Generation is cheap; a wrong direction isn't. Use this file in the brief and direction stages to
make (and explain) real design decisions, then encode them in `brand.json`.

---

## 1. The brief — what to find out

Ask only what's missing; 3–5 questions is plenty. In priority order:

1. **Name** (exact spelling, capitalisation) and **what the business does** in one sentence.
2. **Audience** — who buys, and what they compare it with.
3. **Personality** — 3–5 adjectives. If the user struggles, offer contrasting pairs:
   classic ↔ modern, playful ↔ serious, premium ↔ accessible, calm ↔ energetic, crafted ↔ techy.
4. **Constraints** — existing logo/colours to keep, competitors to avoid looking like, where it
   will mostly live (packaging, app, signage, social).
5. **Must-haves / must-avoids** — colours, symbols, clichés (→ `brand.json` `avoid`).

Write the answers into `brand.json` (`industry`, `audience`, `personality`, `positioning`,
`voice`, `avoid`) before any generation.

## 2. Logo types — pick deliberately

| Type | What | Choose when | Watch out |
|---|---|---|---|
| Wordmark | The name in distinctive type | Short, distinctive name (≤ 10 letters); new brand needing name recognition | Needs memorable letterforms, not just a font |
| Lettermark / monogram | Initials | Long name; established brand | Means nothing to a new audience |
| Symbol + wordmark (combination) | Icon beside/above the name | Most new brands — flexible, symbol can later stand alone | Keep symbol and type visually related (stroke weight, curves) |
| Abstract mark | Non-literal shape | Tech, multi-product, global | Hard to own without explanation; easy to resemble others |
| Pictorial mark | Recognisable object | Simple, ownable object linked to the name | Literal clichés (globe, lightbulb, swoosh, leaf for "eco") |
| Emblem / badge | Text inside a shape | Heritage, craft, food & drink, education | Poor at small sizes — always design a simplified secondary mark |
| Mascot | Character | Consumer, kids, community | Expensive to keep consistent; out of scope for a logo-only ask |

**Concept exploration**: generate 3–6 concepts that differ in *idea*, not just colour —
e.g. one wordmark, one symbol built from the name's meaning, one from its first letter, one
abstract. Variants of one idea waste the exploration round.

## 3. What makes a logo work (check every concept against these)

- **Simple** — describable in one sentence; survives at 16px (favicon). Squint test.
- **Distinctive** — not the category cliché (coffee bean, house roof, leaf, speech bubble).
- **Scalable** — no hairlines or tiny counters that vanish small; no detail that only works big.
- **Versatile** — works in one colour, reversed, and on photos (with a panel).
- **Appropriate** — matches the personality adjectives; a law firm's mark shouldn't bounce.
- **Timeless over trendy** — avoid the gradient/3D/glitch effect of the year in the core mark;
  put trends in campaigns, not the logo.

When presenting concepts, give each a one-line rationale and say which of these it's strongest
and weakest on. Recommend one.

## 4. Colour

- **Roles, not just colours.** Every palette entry gets a `role`: `primary` (the brand's
  colour, ~60% of brand moments), `secondary` (~30%), `neutral` (backgrounds, text), `accent`
  (≤10%, calls to action). 3–6 colours total; more is a rainbow, not a palette.
- **Own one colour.** The primary should be distinctive in the category (a deep teal in a
  category of white-and-green, not another green).
- **Contrast is a requirement**: body text on background ≥ 4.5:1 (WCAG AA); large text and
  UI ≥ 3:1. `build_brand_guidelines.py` computes these — if the primary fails on white for
  text, say so and define a darker text tone.
- **Name each colour twice**: a brand name (`"Deep Tide"`) for the guidelines and a plain
  `description` (`"deep teal-green sea blue"`) for prompts.
- **Associations** are cultural and loose, use them as tie-breakers only: blue trust/calm,
  green growth/nature, red energy/urgency, yellow optimism, black luxury/authority,
  earth tones craft/organic, purple creativity/premium.
- Seed from an approved concept or moodboard with `extract_palette.py`, then tune by hand.

## 5. Typography

- Two families max: a **display** (name, headlines — carries personality) and a **body**
  (everything else — neutral, legible). One family with weights is also fine.
- Pair by **contrast with one shared trait** (serif display + sans body with similar x-height;
  geometric sans + humanist sans is weak).
- Prefer Google Fonts for `brand.json` `typography.display/body` — the guidelines page loads them
  live. If the user has licensed fonts, record their names anyway; the page falls back.
- The wordmark in a generated logo is *lettering*, not a font — write `typography.feel` as a
  description ("soft flared modern serif") for prompts, and pick the closest real font for the
  guidelines.

Starter pairings (all Google Fonts):

| Feel | Display | Body |
|---|---|---|
| Warm, editorial | Fraunces | Inter |
| Luxury, fashion | Playfair Display / Bodoni Moda | Jost |
| Modern geometric | Outfit / Sora | Inter |
| Swiss, neutral | Inter Tight | Inter |
| Friendly, rounded | Nunito / Baloo 2 | Nunito Sans |
| Tech, precise | Space Grotesk | IBM Plex Sans |
| Heritage, craft | Cormorant Garamond / Libre Caslon Display | Source Sans 3 |
| Bold, brutalist | Archivo Black / Anton | Archivo |
| Retro 70s | Shrikhand / Fraunces (soft, high optical size) | DM Sans |
| Japanese minimal | Zen Kaku Gothic New / Noto Serif JP | Noto Sans JP |

## 6. The identity system — beyond the logo

A complete identity typically includes (pick per scope; see `asset-catalog.md`):

1. Logo suite — primary, reversed, mono, symbol, horizontal/stacked lockups, app icon
2. Colour palette with roles and contrast
3. Typography
4. Graphic language — pattern, shapes, line style derived from the symbol
5. Imagery direction — photography/illustration style
6. Applications — the 3–6 touchpoints that matter most for *this* business
7. Guidelines — the HTML page tying it together, with do/don't rules

For a small ask ("just a logo"), deliver 1 + the colour/type it implies, and offer the rest.

## 7. Clear space & minimum size (write into `brand.json` `logo.usage`)

- Clear space: usually the height of a distinctive element (the symbol, the cap height, the
  letter "o") on all sides.
- Minimum size: where the symbol's smallest detail still reads — typically 20–30mm print,
  100–150px screen for a combination mark; 16px for the symbol-only favicon.
- Don'ts: recolour outside the palette, stretch, rotate, outline, add effects, place on busy
  imagery without a panel, rearrange lockup parts.
