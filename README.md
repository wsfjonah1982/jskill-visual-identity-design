# Visual Identity Design Skill

From a **company name, industry and business idea**: five brand design ideas, each rendered as a
**logo, brand story graphic and business card** with **Seedream 5.0 Pro**, compared on a static
**evaluation page with weighted scoring**. The winner can then be expanded into a full identity
(logo suite, mockups, brand guidelines page).

For the full workflow (brief, approval gates, prompt crafting, confirmation before paid calls)
see `SKILL.md`. This file covers plain script usage.

## Setup (new environment)

```bash
pip install -r requirements.txt          # requests>=2.31, Pillow>=10.1 — Python 3.10+
cp credential_tmp.json credential.json   # fill in model_ark_key (+ TOS keys to publish)
python scripts/check_setup.py --live     # verifies Python, packages, config, keys — free
```

- **Ark API key**: `model_ark_key`, from the env var or `credential.json` (the env var wins).
- **TOS publishing** (optional): `tos_access_key_id` / `tos_secret_access_key` / `tos_bucket`,
  from `credential.json` or env vars (`credential.json` wins). `config.json` ships a placeholder
  bucket (`your-bucket-name`) and holds the endpoint/region/key prefix.
- **Network access**: the Ark endpoint (`maas_api_endpoint`) and the TOS endpoint. Pages load
  Google Fonts when viewed.
- `credential.json` and the `_*/` working folders are gitignored, so a fresh clone needs its
  own credentials.
- `config.json` holds all settings (model, image formats, design set, scoring criteria, TOS
  publishing target).

## Project shape

```
_project/
  brand/brand.json     ← company inputs + 5 ideas (start from prompt/brand.example.json)
  input/               ← user's files (existing logo, references)
  prompt/              ← filled prompt files
  output/              ← idea{N}_logo/story/card.png, evaluation.html, brand_guidelines.html
  site/                ← publishable evaluation site (index.html + img/)
  script/              ← proposals
  log/                 ← .log JSON records per generation
_log/                  ← publish/unpublish records
```

## Quick start: the design-ideas round

```bash
mkdir -p _project/brand
cp prompt/brand.example.json _project/brand/brand.json   # set name/industry/business_type/business_idea + 5 ideas
python scripts/render_design_ideas.py --dry-run          # 15 prompts + proposal, no cost
python scripts/render_design_ideas.py                    # 15 Seedream renders: idea{N}_logo/story/card.png
python scripts/build_evaluation_page.py --embed          # _project/output/evaluation.html
```

Re-roll one asset: `python scripts/render_design_ideas.py --ideas 3 --assets card --force`.
Expand the winner: `workflow/expand_winner_workflow.md` (scripts below take `--idea N`).

## Scripts

### Free, local (Pillow only)

```bash
# Fill a template's {brand} placeholders from brand.json; lists <slots> left to fill by hand
python scripts/fill_prompt_template.py --template logo_variation.txt --idea 2 --output _project/prompt/logo_reversed.txt [--append] [--set key=value]

# Exact palette swatch (with labels for presentation, --no-labels for use as a reference image)
python scripts/make_palette_swatch.py [--idea N] [--no-labels] [--output _project/output/palette_ref.png]

# Dominant colours of an image as hex
python scripts/extract_palette.py --img _project/output/logo_primary.png [--count 6]

# Make a user's logo safe as --img: flatten transparency, upscale, pad
python scripts/prepare_reference.py --img _project/input/logo.png --output _project/input/logo_on_white.png [--background "#FFFFFF"] [--pad 0.15]

# Assemble the guidelines page from brand.json + its "assets" list
python scripts/build_brand_guidelines.py [--idea N] [--embed]
```

### Seedream 5.0 Pro (paid)

```bash
# Text → image; one image per non-empty line
python scripts/generate_image_from_text.py --prompt _project/prompt/concepts.txt --format square --output _project/output/concept.png

# Image(s) + prompt → image; logo first, optional palette swatch second
python scripts/generate_image_from_reference.py --img _project/output/logo_primary.png _project/output/palette_ref.png --prompt _project/prompt/app_packaging.txt --format print_3x4 --output _project/output/app_packaging.png
```

`--format` names: `auto`, `square`, `landscape`, `wide_3x2`, `portrait`, `post_4x5`, `print_3x4`
(see `config.json` `image_formats`). These two scripts are also what `render_design_ideas.py`
runs under the hood. Each prints the output path on stdout, progress on stderr, and appends a
JSON record to `_project/log/<output-name>.log`.

### Publish to BytePlus TOS (public-read)

```bash
python scripts/build_evaluation_page.py --output _project/site/index.html --image-dir _project/site/img
python scripts/publish_site.py --dir _project/site --slug <company>-evaluation   # prints the public URL
python scripts/unpublish_site.py --slug <company>-evaluation
```

## Verified live

The Seedream image calls, explicit `WxH` sizes (`square`, `landscape`, `wide_3x2`),
reference-anchored renders, the parent-brand `style_reference`, and TOS publishing were all
used for the Kino Kopi project (2026-10-09). See `references/common-issues.md`.
