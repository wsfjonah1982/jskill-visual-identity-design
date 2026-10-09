---
name: visual-identity-design
description: >
  Brand visual identity design with Seedream 5.0 Pro image generation via the BytePlus ARK API. From a company name, industry and business idea (tech, resell, manufacturing,
  restaurant, …) it proposes five distinct brand design ideas, renders a logo, a brand story
  graphic and a business card for each, and builds a static HTML evaluation page with weighted
  scoring so the user can compare and pick a winner. It can then expand the winner into a full
  identity (logo suite, mockups, brand guidelines page). Use this skill whenever the user wants a
  logo, branding, brand identity, brand design options, a rebrand, business cards or brand
  mockups, e.g. "design a logo for my café", "branding ideas for my startup", "show me brand
  options for my factory". Use it even if they don't mention Seedream. Always use it before writing a logo/brand prompt from
  memory or running its scripts directly: the inputs, the ideas file and the review steps it
  manages are what keep the results consistent and comparable.
---

# Visual Identity Design Skill

## Overview

The default flow has four steps:

1. **Inputs.** The user must provide the **company name**, **industry**, and **business type/idea**
   (tech, resell, manufacturing, restaurant, …).
2. **Five brand design ideas.** Claude writes five genuinely different directions (style, logo,
   palette, type, story, card design).
3. **Three designs per idea.** A **logo**, a **brand story graphic** and a **business card** are
   rendered with Seedream 5.0 Pro (15 images), each idea's story and card anchored on its own logo.
4. **Evaluation page.** A static HTML page shows all designs side by side with a **weighted 1–5
   scoring system**, a live leaderboard, notes, shortlisting and JSON/CSV export.

After the user picks a winner, the skill can expand it into a full identity: logo suite,
patterns, mockups and a brand guidelines page.

The full recipe is `workflow/brand_design_ideas_workflow.md`. Settings (models, image formats,
the design set, the scoring criteria and weights, publishing target) live in `config.json`.
**Every paid generation is confirmed with the user first** (Step 3).

---

## Workflow

### Step 0: Read `config.json`

Note `image_model_id`, `image_formats`, `design_set` (which assets each idea gets, their
template, `--format` and reference), `evaluation_criteria` (the scoring rubric the page uses)
and the `styles` menu. To change what is rendered or how it's scored, edit `config.json`. Never
use ad-hoc overrides.

### Step 1: Collect the three required inputs

| Required | `brand.json` key |
|---|---|
| Company name (exact spelling/capitalisation) | `name` |
| Industry | `industry` |
| Business type + one-sentence business idea | `business_type` (`tech` / `resell` / `manufacturing` / `restaurant` / … see `references/business-types.md`), `business_idea` |

**If any is missing, ask, and don't proceed.** Never invent a company name. In the same message
you may ask for optional details that sharpen the ideas: audience, location, colours or symbols
to keep or avoid, and real contact details for the card (otherwise the card shows neat
placeholder lines).

Repeat the inputs back in one sentence (exact name spelling) before writing any file.

### Step 2: Write five design ideas

Create `_project/brand/brand.json` from `prompt/brand.example.json` (a complete worked example: a
restaurant with five ideas) and replace every value. Write five ideas per
`references/design-ideas.md`:

- **Spread them.** Vary style, logo type, palette temperature and tone. Default slate: category
  classic · modern clean · bold differentiator · premium refined · warm/playful/local.
- **Make them fit the business.** Use `references/business-types.md` for what customers must
  feel, what works, and the clichés to put in `avoid`.
- **Make them renderable.** Concrete `logo.description` with the name in quotes, a 2–6 word
  `story.headline`, three visual `story.scenes`, `card.front`/`back`/`material`/`scene`, and
  colour `description`s. These fields are the only creative input to the renders.
- If the brief says to follow a parent/existing brand's style (sub-brand, brand extension), set a
  company-level `style_reference` image + note (`references/design-ideas.md` §2) so every logo
  is generated from it.
- Use `references/identity-styles.md` for `style_descriptor` text and font pairings, and
  `references/design-principles.md` for logo-type, colour-role and contrast decisions.

Show the user a compact table of the five ideas and let them swap or tweak ideas **before**
rendering. Text changes are free; re-renders are not.

### Step 3: Proposal, confirm, render the 15 designs

```bash
python scripts/render_design_ideas.py --dry-run
```

This writes one prompt per asset (`_project/prompt/idea{N}_{logo|story|card}.txt`) and the plan
to `_project/script/design_ideas_proposal.txt`. It refuses if an idea is missing a field or a
template placeholder is unresolved. Show the proposal summary (number of Seedream calls, formats,
references) and **wait for the user's yes**. Then:

```bash
python scripts/render_design_ideas.py
```

Per idea: logo (text→image, `square`) → brand story graphic (logo as reference, `landscape`) →
business card (logo as reference, `wide_3x2`). Ideas run in parallel; existing outputs are
skipped, so a re-run after a failure only redoes what's missing. To re-roll one asset:
`--ideas 3 --assets card --force`. A re-rolled logo means re-rolling its story and card too.

### Step 4: Review every image, then build the evaluation page

**Read all 15 images before showing anything.** Check that the name is spelled exactly, the
logo on the story/card matches the idea's logo, there is no invented text or extra logos, and the
palette was followed. Re-roll pure generation defects and say you did
(`references/common-issues.md`). Then add an `ai_review` (scores, comment, flags) to each idea
per `references/evaluation-rubric.md`, using the whole 1–5 scale.

```bash
python scripts/build_evaluation_page.py --embed
```

→ `_project/output/evaluation.html`, a single self-contained file. It shows:
- the company inputs and a live leaderboard
- the criteria and weights
- per idea: the three designs (click to enlarge), concept, palette chips, type, 1–5 scoring per
  criterion, notes, a shortlist toggle and the weighted total out of 100
- reviewer name, Export JSON/CSV, Import, Reset

**The page is client-facing: it never mentions Claude or shows the `ai_review`.** Scores persist
in each viewer's browser. Present the page in chat with your review ranking (labelled as a
reference), the main flags, and how to score and export.

**Publishing to TOS** (when the user asks to publish or share it):

```bash
python scripts/build_evaluation_page.py --output _project/site/index.html --image-dir _project/site/img
python scripts/publish_site.py --dir _project/site --slug <company>-evaluation
```

→ `https://<tos_bucket>.<tos_endpoint>/site/brand/<slug>/index.html`, public-read, with HTML set
to no-cache so a republish shows immediately. Stale files under the prefix are pruned, and
`unpublish_site.py --slug <slug>` takes it down. Publishing makes the page public, so confirm
first, especially when it carries a real company's trademark. Before publishing, grep the built
HTML for "claude".

When the user returns their scores or picks, summarise the ranking, name the winner's weakest
criteria (that's the refinement brief), and offer the next step.

### Step 5 (optional): Expand the winner

`workflow/expand_winner_workflow.md`: lock or refine the logo, then the logo suite, pattern,
imagery and mockups (`references/asset-catalog.md`), then
`build_brand_guidelines.py --idea N --embed`. Every template is filled with
`fill_prompt_template.py --idea N`, so brand facts are never retyped. Each stage gets one batch
proposal and a confirmation.

### Delivering: always say plainly

- Generated logos are **raster concepts**. Production use needs a vector redraw.
- A **trademark search** is needed before adopting any generated mark.
- Colours on screen are not proofed for print (CMYK values in the guidelines are a naive
  conversion).

---

## Other requests

| Request | Workflow |
|---|---|
| New brand / logo / branding (default) | `workflow/brand_design_ideas_workflow.md` |
| Expand a chosen idea into a full identity | `workflow/expand_winner_workflow.md` |
| They already have a logo: variations, mockups, guidelines | `workflow/existing_logo_rollout_workflow.md` |

## References (load as needed)

| Need | File |
|---|---|
| The three required inputs; what each business type needs; clichés | `references/business-types.md` |
| How to write five distinct, renderable ideas; the `ai_review` format | `references/design-ideas.md` |
| Scoring scale, criteria, rules for Claude's scores, reading results | `references/evaluation-rubric.md` |
| Prompt rules for identity work: consistency via references, brand-name spelling, formats, negatives, IP | `references/best-practices.md`. **Read before writing or editing prompts.** |
| Logo types, logo quality checks, colour roles and contrast, type pairing | `references/design-principles.md` |
| Style directions → `style_descriptor`, palette and fonts | `references/identity-styles.md` |
| Expansion assets: templates, formats, output names | `references/asset-catalog.md` |
| Something came back wrong (misspelled name, logo changed on the card, colour drift, API errors) | `references/common-issues.md` |
| Prompt templates and placeholders | `prompt/README.md` |

---

## Scripts

| Script | Cost | Does |
|---|---|---|
| `render_design_ideas.py [--dry-run] [--ideas] [--assets] [--force] [--workers]` | paid (Seedream) | Prompts + proposal + the per-idea logo → story → card renders |
| `build_evaluation_page.py [--embed]` | free | The scoring page |
| `fill_prompt_template.py --template T [--idea N] [--set k=v] [--append]` | free | Fills a `prompt/` template from `brand.json` |
| `generate_image_from_text.py --format F` / `generate_image_from_reference.py --img … --format F` | paid (Seedream) | Single image generations (expansion stage) |
| `make_palette_swatch.py [--idea N] [--no-labels]`, `extract_palette.py`, `prepare_reference.py` | free | Exact swatch, colours from an image, safe reference from a user's logo |
| `build_brand_guidelines.py [--idea N] [--embed]` | free | Brand guidelines HTML |
| `publish_site.py --dir <site> --slug <slug>` / `unpublish_site.py --slug <slug>` | TOS storage | Publish/remove a static page on BytePlus TOS (public-read) |

Generation scripts print the output path on stdout, progress on stderr, and append a JSON
record to `_project/log/<output>.log` (prompt, size, tokens, timing, status).

---

## Configuration (`config.json`)

| Key | Meaning | Recorded default |
|---|---|---|
| `maas_api_endpoint` | BytePlus ARK API base URL | `https://ark.ap-southeast.bytepluses.com/api/v3` |
| `image_model_id` | Seedream model | `dola-seedream-5-0-pro-260628` |
| `image_size` / `image_formats` | Default size / named sizes for `--format` | `2K` / `auto`, `square` 2048×2048, `landscape` 2816×1584, `wide_3x2` 2496×1664, `portrait` 1584×2816, `post_4x5` 1824×2280, `print_3x4` 1776×2368 |
| `design_set` | Ideas count, parallel workers, and per-idea assets (template, format, reference) | 5 ideas, 3 workers; logo (`square`) → story (`landscape`, ref logo) → card (`wide_3x2`, ref logo) |
| `evaluation_criteria` | Scoring criteria + weights (sum 100) used by the page | fit 20, distinct 15, memorable 15, versatile 10, craft 15, story 10, card 10, coherence 5 |
| `watermark` | Watermark on outputs | `false` |
| `styles` / `default_style` | Style menu | 12 styles / `Modern Geometric` |
| `tos_endpoint` / `tos_region` / `tos_bucket` / `tos_key_prefix_template` | Publishing target | `tos-ap-southeast-1.bytepluses.com` / `ap-southeast-1` / `portobuild` / `site/brand/{slug}` |
| `local_publish_dir` | Where `publish_site.py` copies the site when TOS keys aren't set (empty = leave it in place) | `""` |

This column is a snapshot. `config.json` is the source of truth; update this table whenever
you change it on the user's instruction.

Secrets: `model_ark_key` (env var first, then `credential.json`), plus `tos_access_key_id` /
`tos_secret_access_key` for publishing (`credential.json` first, then env vars). Copy
`credential_tmp.json`; `credential.json` is gitignored. Prerequisites: Python 3.10+ and
`pip install -r requirements.txt` (`requests`, `Pillow>=10.1`). In a new environment, run
`python scripts/check_setup.py --live` first. It's free and checks packages, config and both keys.

---

## Project folder

| Folder | Holds |
|---|---|
| `_project/brand/brand.json` | Company inputs + the five ideas (+ `ai_review`, and later the winner's `assets`) |
| `_project/prompt/` | Filled prompt files, one per asset |
| `_project/script/` | Proposals (`design_ideas_proposal.txt`, `<output>_proposal.txt`) |
| `_project/output/` | `idea{N}_logo/story/card.png`, `evaluation.html`, later expansion assets and `brand_guidelines.html` |
| `_project/log/` | `.log` JSON record per output |
| `_project/input/` | The user's files (existing logo, references) |
| `_project/site/` | The publishable evaluation site (`index.html` + `img/`), built for TOS |
| `_log/` (skill root) | `publish-<slug>.log` records from `publish_site.py` / `unpublish_site.py` |

Archive or clear `_project/` before starting another company. If the environment needs another
location, keep the same `brand/ prompt/ script/ output/ log/` shape and pass `--brand <path>`.
The batch renderer and page builders derive every other folder from where `brand/brand.json`
sits.
