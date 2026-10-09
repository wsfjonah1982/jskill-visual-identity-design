# Prompt Best Practices — Visual Identity with Seedream 5.0 Pro

Read this before writing any identity prompt. It covers what is different about identity work
versus ordinary image generation, the prompt formulas per asset type, and which script to use.

---

## 0. The one idea that matters: consistency comes from anchors, not adjectives

An identity is 15–30 assets that must look like one brand. Generative models re-imagine
everything they aren't pinned to. So every asset after the logo is approved is generated
**from references**, never from text alone:

| What must stay identical | How it's pinned |
|---|---|
| Name spelling, palette names, style descriptor, avoid-list | `brand.json` → `{placeholders}` via `scripts/fill_prompt_template.py` — never retyped by hand |
| The logo artwork | The approved logo PNG passed as `--img` (first reference) to every story graphic, card, variation, pattern and mockup |
| Exact colours | A `make_palette_swatch.py --no-labels` swatch passed as an extra `--img` (second reference) |
| Specs (hex, fonts, contrast) | Never generated — rendered exactly by `build_brand_guidelines.py` |

If an asset is generated from text alone after the logo exists, it *will* contain a different
logo. That's the single most common identity failure (`common-issues.md` I-3).

---

## 1. The identity prompt formula (Seedream)

```
[What it is] + [Brand facts: name in quotes, industry, personality]
+ [The creative idea: concept / scene / variation]
+ [Rendering: flat vector | photoreal mockup | editorial photo] + [Style descriptor]
+ [Colour: palette by NAME (hex kept for the record)]
+ [Composition: centred, margin, background]
+ [Text control: exact spelling + "no other text"] + [Negatives]
```

- **Say the medium first.** "Logo design concept…", "Photorealistic brand mockup…",
  "Seamless repeating pattern…". Seedream decides the rendering mode from the first clause.
- **Colour by name, not hex.** Models follow "deep teal-green sea blue" far better than
  `#1F4E5A`. `brand.json`'s `palette[].description` is the prompt word; the hex is for specs.
  For exactness, attach the swatch (§0).
- **Flat vector logos**: always "flat vector, solid flat colour, no gradients, no shadows, no 3D,
  no texture, plain pure white background". Without it Seedream defaults to glossy, beveled,
  mockup-on-paper renders that can't be used as a logo.
- **One logo per image** for anything you'll keep. Grids of 6 concepts in one image look
  efficient but each cell is low-res and they bleed into each other — batch one-per-line instead
  (§3).

## 2. Text rendering rules (brand names)

Seedream 5.0 renders short text well, but a misspelled brand name makes an asset worthless.

- Put the name in straight double quotes and say it once more: `spelled exactly "Ember Lane",
  every letter correct, no extra letters`.
- Keep in-image text to the **name only** for logos; add the tagline later in layout, not in
  generation. Every extra word is another chance to misspell.
- For mockups, explicitly allow only the copy you want (`brand_application.txt` has the slot)
  and forbid the rest: `no other logos, no other brand names, no invented text, no random
  lettering`. Packaging scenes otherwise sprout fake ingredient lists and barcodes.
- Names that are long (> 12 letters), all-caps acronyms with repeated letters, or non-Latin
  scripts fail more often — generate 2–3 and pick, and always **look at the output yourself**
  (Read the PNG) and check the spelling letter by letter before showing the user.

## 3. Which script for which identity task

| Have | Want | Script | Notes |
|---|---|---|---|
| `brand.json` with five ideas | 15 renders: logo → story graphic → card per idea | `render_design_ideas.py` | `--dry-run` first; logo is the reference for its story and card |
| A brief | Moodboard, logo concepts, imagery samples | `generate_image_from_text.py` | One prompt per line → one image per line. Batch concepts with `fill_prompt_template.py --append` |
| A chosen concept | Clean final logo | `generate_image_from_reference.py` | `logo_refine.txt` |
| The approved logo | Variations, pattern, mockups | `generate_image_from_reference.py` | `--img logo.png [swatch.png]`; always logo first |
| An existing logo file | Safe `--img` input | `prepare_reference.py` | Flattens transparency, upscales, pads |
| An image | Its colours as hex | `extract_palette.py` | Free; seeds `brand.json` palette |
| `brand.json` | Exact palette swatch | `make_palette_swatch.py` | Free |
| `brand.json` + assets | The guidelines deliverable | `build_brand_guidelines.py` | Free |

## 4. Aspect ratio / `--format`

Image scripts take `--format <name>` from `config.json`'s `image_formats`:

| Format | Size | Use |
|---|---|---|
| `square` | 2048×2048 | Logos, concepts, symbol, app icon, pattern tile, social avatar |
| `landscape` | 2816×1584 (16:9) | Moodboard, brand story graphic, website hero, signage |
| `wide_3x2` | 2496×1664 | Photography, most product/stationery mockups |
| `portrait` | 1584×2816 (9:16) | Story/reel graphics, posters for phone |
| `post_4x5` | 1824×2280 | Feed posts |
| `print_3x4` | 1776×2368 | Posters, menus, packaging fronts |
| `auto` | `2K` | Model picks the ratio from the prompt wording (`"16:9 widescreen"` etc.) |

The `WxH` sizes `square`, `landscape` and `wide_3x2` were verified live (Kino Kopi run,
2026-10-09: exact dimensions returned). The others follow the same format; if one is ever
rejected, fall back to `--format auto` and state the ratio in the prompt (`common-issues.md` I-0).

## 5. Negative constraints

**Every identity prompt:** `no watermark`. Plus, by asset type:

| Asset | Add |
|---|---|
| Logo / variation / concept | `no tagline, no other text, no gradients, no shadows, no 3D, no texture, no mockup` |
| Moodboard, imagery, pattern | `no text, no words, no logos, no brand names` |
| Mockup | `no other logos, no other brand names, no invented text, no random lettering` + `{avoid}` |

`{avoid}` from `brand.json` renders as "no neon colours, no glossy plastic textures, …" — use it
on mockups and story graphics, where off-brand drift is likeliest.

## 6. Language

Write prompts in English. Brand names stay in their original script inside quotes; if a name is
non-Latin, expect more retries (§2).

## 7. IP, trademark and honesty

- Never prompt "in the style of <existing brand>" or ask for a logo resembling a known mark.
  Describe the *qualities* instead (geometric, warm, heritage…). Generated logos can still
  accidentally resemble existing marks — tell the user a trademark search is needed before
  they adopt one.
- Don't put real third-party brands in mockups (no "on an iPhone", "Starbucks cup") — describe
  generic objects.
- Generated logos are raster PNGs. Say so plainly when delivering: a production logo still needs
  vector redrawing (designer, or an auto-trace tool) before print/signage use.
