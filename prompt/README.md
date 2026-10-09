# Predefined Prompt Templates

Reusable prompt skeletons. Each template has up to two kinds of slot:

- **`{brand_key}`**: filled automatically from `brand.json` (with `--idea N`, from that design
  idea merged over the company facts). These are the facts that must be identical across
  assets, so they are never retyped by hand.
- **`<creative slot>`**: a per-asset creative decision Claude fills by hand in the output file.
  The filler lists any that are left over.

`brand.example.json` is a complete worked `brand.json`: a fictional restaurant, "Ember Lane",
with five design ideas. Copy it to `_project/brand/brand.json` to start a project, then replace
every value.

## Design-ideas round (the default flow)

These three have **no `<slots>`**. Every value comes from the idea's fields in `brand.json`, so
`scripts/render_design_ideas.py` fills and renders all 15 in one batch. They're wired up in
`config.json` → `design_set`.

| File | Asset | Script (run by the batch) | `--format` | Reference |
|---|---|---|---|---|
| `idea_logo.txt` | Logo (single-line) | `generate_image_from_text.py` | `square` | — |
| `idea_story.txt` | Brand story graphic: 3-scene poster + headline + logo | `generate_image_from_reference.py` | `landscape` | the idea's logo |
| `idea_card.txt` | Business card, front + back mockup | `generate_image_from_reference.py` | `wide_3x2` | the idea's logo |

Fields they use: `logo.type/description/colors`, `typography.feel`, `style_descriptor`,
`personality`, `palette[].description`, `story.headline/scenes/layout`, `imagery`,
`card.front/back/material/scene`, `contact`, `avoid`, plus company `name/industry/business_idea`.

## Expansion stage (after a winner is picked)

Fill with `python scripts/fill_prompt_template.py --idea N --template <file> --output _project/prompt/<asset>.txt`,
then fill the `<slots>` (values in `references/asset-catalog.md`).

| File | Stage | Script | `--format` | `--img` |
|---|---|---|---|---|
| `moodboard.txt` | Direction (single-line) | `generate_image_from_text.py` | `landscape` | — |
| `logo_concept.txt` | More logo options in the winning direction (single-line, `--append` per variant) | `generate_image_from_text.py` | `square` | — |
| `logo_refine.txt` | Clean final logo | `generate_image_from_reference.py` | `square` | chosen logo |
| `logo_variation.txt` | Reversed, mono, symbol, lockups, app icon | `generate_image_from_reference.py` | per variation | approved logo |
| `brand_pattern.txt` | Pattern from the symbol (single-line) | `generate_image_from_reference.py` | `square` | logo (+ swatch) |
| `brand_imagery.txt` | Photography samples (single-line) | `generate_image_from_text.py` | `wide_3x2` | — |
| `brand_application.txt` | Mockups: packaging, signage, merch, screens | `generate_image_from_reference.py` | per application | logo (+ swatch) |

## Format rule

`generate_image_from_text.py` makes **one image per non-empty line**, so single-line templates
must stay one line. Every other script reads the whole file as one prompt.

## Placeholders `fill_prompt_template.py` provides

Company/idea: `{name}` `{industry}` `{business_type}` `{business_idea}` `{audience}` `{idea_title}`
`{tagline}` `{personality}` `{style}` `{style_descriptor}` `{imagery}` `{avoid}`
`{style_reference_note}` (from company-level `style_reference.note`; empty if none)
Colour: `{palette}` `{primary_color}` `{accent_color}` `{logo_colors}`
Logo/type: `{logo_type}` `{logo_description}` `{symbol}` `{typography_feel}`
Story: `{story_headline}` `{story_scenes}` `{story_layout}`
Card: `{card_front}` `{card_back}` `{card_material}` `{card_scene}` `{card_contact}`
Anything else: `--set key=value`.

Typography specimens and exact colour specs are deliberately **not** generated. No image model
renders an exact font or hex value; `build_brand_guidelines.py` renders them from `brand.json`.
