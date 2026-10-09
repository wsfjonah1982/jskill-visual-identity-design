# Writing the Five Design Ideas

Each idea is one complete brand direction: a style, a logo concept, a palette, type, a story
and a business card design. Ideas live in `brand.json` → `ideas[]` and are the only creative
input to the 15 renders, so everything the images need must be written here. There are no
hand-filled template slots in this stage.

---

## 1. Spread: five genuinely different directions

Five versions of one idea waste four renders. Vary at least **three** of these between any two
ideas:

| Axis | Range |
|---|---|
| Style direction (`identity-styles.md`) | 5 different styles |
| Logo type | wordmark · symbol + wordmark · emblem/badge · lettermark · abstract mark |
| Palette temperature | warm · cool · neutral/monochrome · bright · dark |
| Tone | classic · modern · bold · premium · playful/local |
| Concept source | the name's meaning · what the business makes/does · where it's from · how it makes people feel · the founder's story |

Default slate (adapt to the business, `business-types.md` last section):
1. **Category classic**: what customers expect, done exceptionally.
2. **Modern clean**: geometric/minimal, scales to app icon and signage.
3. **Bold differentiator**: deliberately unlike competitors.
4. **Premium refined**: supports higher prices.
5. **Warm / playful / local culture**: personality and community.

## 2. Fields to fill per idea

```json
{
  "id": 1,
  "title": "Hearth Heritage",                       // 2–3 words, shown on the evaluation page
  "summary": "One sentence the client understands.",
  "rationale": "Why this fits the business — and its trade-off.",
  "style": "Heritage / Vintage Craft",              // from config.json styles
  "style_descriptor": "…",                          // from identity-styles.md, adapted
  "personality": ["authentic", "warm", "generous"],
  "tagline": "Grilled the old way",                 // shown on the page, NOT rendered (except as story headline if you reuse it)
  "palette": [ { "name", "hex", "role", "description" } ],   // 3–5 colours; roles primary/secondary/neutral/accent
  "typography": { "display", "body", "feel" },      // Google Fonts names; `feel` is what the prompt uses
  "logo": { "type", "description", "colors" },      // description = one concrete visual sentence, name in quotes
  "story": { "headline", "narrative", "scenes": [3 items], "layout" },
  "card": { "front", "back", "material", "scene" },
  "imagery": "…",                                   // photo/illustration feel for the story graphic
  "avoid": ["…"]                                    // business-type clichés + anything off-direction
}
```

Company-level fields (`name`, `industry`, `business_type`, `business_idea`, `audience`,
`contact`) sit at the top of `brand.json` and are shared by all ideas.

**Sub-brands / "follow the style of X":** add a company-level `style_reference`:

```json
"style_reference": {
  "file": "input/parent_logo_clean.png",
  "note": "The reference image is the logo of the parent company X; carry over its visual DNA — <what to keep> — while creating the new logo described next; do not reproduce the reference unchanged."
}
```

Each idea's logo is then generated *from* that image (the note is injected into `idea_logo.txt`).
Clean the reference first: remove sublines/legal text (paint over, don't crop through the symbol),
pad it, and never quote that text in `avoid`, since naming text can make the model render it. An idea
can opt out with `"style_reference": null`.

## 3. Writing each field so it renders well

- **`logo.description`**: describe what is *drawn*, concretely: shapes, arrangement, and the
  name in double quotes. "a round badge with \"Ember Lane\" arched across the top and a small
  grill with three flame curls in the centre", not "a logo that evokes warmth and heritage".
  One symbol idea only.
- **`logo.colors`**: 1–2 colours by description, which colour goes where. Logos with 4+
  colours fail the versatility criterion anyway.
- **`story.headline`**: 2–6 words. It's the only text rendered in the story graphic besides the
  logo, and short headlines are spelled right far more often.
- **`story.scenes`**: exactly 3 concrete, visual moments (who, what, where, light). Not
  abstract values. They should read as a sequence: origin → process → outcome.
- **`card.front` / `card.back`**: say what goes on each side and on which background colour.
  Use "placeholder contact lines" unless the user gave real details. Then fill
  company-level `contact` (`{"person", "title", "phone", "email", "web"}`) and they're
  printed exactly.
- **`card.material` / `card.scene`**: material sells the tier (letterpress cotton vs. smooth
  matte vs. kraft). The scene should hint at the business (a café table, a workbench, a desk).
- **`avoid`**: 3–5 items: the business-type clichés plus whatever would pull the idea off its
  direction.
- **Colours**: write `description` specifically ("deep oxblood red", not "red"). That word is
  what the model follows.

## 4. Presenting the ideas before rendering

Show the user a compact table of the five (title, style, one-line concept, palette names,
logo type) and ask for a go-ahead or swaps **before** the 15-image render. Changing an idea
in text is free; changing it after rendering costs three generations.

## 5. After rendering: Claude's review (`ai_review`)

Open every image (Read the PNGs) and add to each idea:

```json
"ai_review": {
  "scores": { "fit": 4, "distinct": 3, "memorable": 4, "versatile": 3, "craft": 4, "story": 4, "card": 5, "coherence": 4 },
  "comment": "Two sentences: biggest strength, biggest weakness.",
  "flags": ["Name misspelled on the card back ('Embr Lane')"]
}
```

Scoring rules are in `evaluation-rubric.md`. Flags are for generation defects the user must
know about (misspellings, wrong logo on card, invented text, artefacts). Re-roll a flagged
asset before building the page if it's a pure generation defect, and say you did.
