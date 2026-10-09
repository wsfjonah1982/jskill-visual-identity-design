# Asset Catalog — what to generate, with which template, at which format

Ready-to-paste values for the `<creative slots>` in `prompt/` templates. This is the
**expansion** stage: use it after the design-ideas round has a winner
(`workflow/expand_winner_workflow.md`), passing `--idea N` to `fill_prompt_template.py`.
Keep the output names below and `build_brand_guidelines.py` picks everything up.

All paths below are relative to the skill root; `_project/` is the working folder.

---

## Stage A — Direction (cheap, batchable)

| Asset | Template | Script / format | Output |
|---|---|---|---|
| Moodboard (1–2 directions) | `moodboard.txt` | `generate_image_from_text.py --format landscape` | `output/moodboard.png` (`_001`, `_002` when batched) |
| Logo concepts (3–6) | `logo_concept.txt` (`--append`, one line each) | `generate_image_from_text.py --format square` | `output/concept_001.png` … |

## Stage B — Logo suite (all from the approved logo)

| Asset | Template | `--format` | `--img` | Output |
|---|---|---|---|---|
| Final logo | `logo_refine.txt` | `square` | chosen concept | `output/logo_primary.png` |
| Variations | `logo_variation.txt` (one run each) | see below | `logo_primary.png` | see below |

### Logo variations — paste into the `<variation>` slot

| Variation | `<variation>` text | `<what changes>` | `--format` | Output |
|---|---|---|---|---|
| Reversed | `reversed: the whole logo in solid <neutral by name> on a solid flat <primary by name> background filling the frame` | `the colours` | `square` | `logo_reversed.png` |
| Monochrome | `monochrome: the whole logo in solid pure black on plain white` | `the colour` | `square` | `logo_mono.png` |
| Symbol only | `symbol only: just the symbol, without the wordmark, larger, centred` | `the wordmark is removed` | `square` | `logo_symbol.png` |
| Wordmark only | `wordmark only: just the name, without the symbol` | `the symbol is removed` | `landscape` | `logo_wordmark.png` |
| Horizontal lockup | `horizontal lockup: symbol on the left, wordmark on the right, vertically centred, on one line` | `the arrangement` | `landscape` | `logo_horizontal.png` |
| Stacked lockup | `stacked lockup: symbol centred above the wordmark` | `the arrangement` | `square` | `logo_stacked.png` |
| App icon | `app icon: the symbol only, in <neutral>, centred inside a rounded-square tile filled with solid <primary>, tile filling most of the frame, on white` | `the container shape and colours` | `square` | `logo_app_icon.png` |

Write the colour words into the `<variation>` slot by hand, using the winning idea's palette
`description`s from `brand.json`.

## Stage C — Graphic language & imagery

| Asset | Template | `--format` | `--img` | Output |
|---|---|---|---|---|
| Pattern | `brand_pattern.txt` | `square` | `logo_primary.png` (+ swatch) | `pattern.png` |
| Imagery samples (2–4) | `brand_imagery.txt` (`--append`) | `wide_3x2` | — | `imagery_001.png` … |
| Palette swatch (exact, free) | — `make_palette_swatch.py` | — | — | `palette_swatch.png` (+ `--no-labels` → `palette_ref.png` for references) |

## Stage D — Applications (pick the 3–6 that matter for this business)

Template `brand_application.txt`; `--img _project/output/logo_primary.png [_project/output/palette_ref.png]`.
For dark surfaces pass `logo_reversed.png` instead of the primary.

| Application | `<scene>` starter | `<method>` | `--format` | Output |
|---|---|---|---|---|
| Business card | `a pair of thick uncoated business cards, one face-up one face-down, on a <surface>` | `letterpress printed` | `wide_3x2` | `app_business_card.png` |
| Stationery set | `a flat-lay of letterhead, envelope and business card on a <surface>, top-down` | `printed` | `wide_3x2` | `app_stationery.png` |
| Packaging | `<product container — bottle / box / bag / jar> on <surface> in <setting>` | `printed / foil-stamped / debossed` | `print_3x4` | `app_packaging.png` |
| Shopping bag | `a matte paper shopping bag with rope handles, standing on <surface>` | `printed` | `print_3x4` | `app_bag.png` |
| Storefront | `the storefront of a small shop on a <street type>, daytime, straight-on` | `painted / dimensional signage above the door` | `wide_3x2` | `app_storefront.png` |
| Interior wall | `a reception wall in a <interior> with soft light` | `dimensional cut letters` | `wide_3x2` | `app_wall.png` |
| Apparel / merch | `a <tee / cap / tote> laid flat on <surface>` | `embroidered / screen-printed` | `square` | `app_merch.png` |
| Cup | `a <takeaway cup / ceramic mug> on a café counter` | `printed` | `square` | `app_cup.png` |
| Website hero | `a laptop screen showing the brand's homepage hero section — large headline area, a brand photo, generous spacing — on a clean desk` | `in the site header` | `landscape` | `app_website.png` |
| Mobile app | `a hand holding a phone showing the app's home screen` | `as the app's header and icon` | `portrait` | `app_mobile.png` |
| Social post | `a single social media feed post graphic in the brand style with <content>` | `in the corner` | `post_4x5` | `app_social.png` |
| Billboard / poster | `a large poster on a <city wall / bus shelter>` | `printed` | `print_3x4` | `app_poster.png` |
| Vehicle | `a <van / delivery bike> parked on a quiet street, side view` | `vinyl livery` | `wide_3x2` | `app_vehicle.png` |

Screens and posters naturally carry text — fill the allow-list copy slot precisely or expect
invented words (`common-issues.md` I-6). Real device/brand names never go in the prompt.

## Stage E — Guidelines

Register approved assets in the winning idea's entry in `brand.json` (paths relative to
`_project/`):

```json
"assets": {
  "cover":        { "file": "output/logo_reversed.png", "caption": "Primary logo, reversed" },
  "moodboard":    [ { "file": "output/moodboard.png", "caption": "Moodboard", "wide": true } ],
  "logo":         [ { "file": "output/logo_primary.png", "caption": "Primary" }, { "file": "output/logo_mono.png", "caption": "Monochrome" } ],
  "pattern":      [ { "file": "output/pattern.png", "caption": "Pattern" } ],
  "imagery":      [ { "file": "output/idea2_story.png", "caption": "Brand story", "wide": true } ],
  "applications": [ { "file": "output/idea2_card.png", "caption": "Business card" }, { "file": "output/app_packaging.png", "caption": "Packaging" } ]
}
```

Then `python scripts/build_brand_guidelines.py --idea N --embed` → `output/brand_guidelines.html`.

---

## Scope presets

| Ask | Deliver |
|---|---|
| "Logo / branding / brand identity" for a new business (default) | `workflow/brand_design_ideas_workflow.md`: 5 ideas × (logo, story graphic, business card) + evaluation page |
| "Expand the winner" / "full brand kit" | After the ideas round: B → C → D → E here |
| "Rebrand / extend my logo" | `workflow/existing_logo_rollout_workflow.md` |
| "Brand mockups" | D only, from their logo |

Estimate the number of paid calls for the chosen scope and include it in the proposal
(e.g. "~14 image generations").
