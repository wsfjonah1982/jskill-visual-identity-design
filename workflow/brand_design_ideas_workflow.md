# Brand Design Ideas Workflow (the default)

Company name + industry + business idea → **5 brand design ideas** → for each idea a **logo**,
a **brand story graphic** and a **business card** → a static **evaluation page** with weighted
scoring → the user picks a winner.

```
1  Inputs (required)        name · industry · business type/idea      ── ask until all three are known
        │
2  Five ideas               brand.json ideas[1..5]                     ── Claude writes; user approves (free)
        │
3  Render 15 images         render_design_ideas.py                     ── proposal → confirm → Seedream 5.0 Pro
        │                     per idea: logo (text→image, square)
        │                               → story graphic (logo as reference, 16:9)
        │                               → business card (logo as reference, 3:2)
        │
   Review                   Claude opens all 15, re-rolls defects, writes ai_review per idea
        │
4  Evaluation page          build_evaluation_page.py --embed           ── free; user scores, shortlists, exports
        │
   Next                     winner → workflow/expand_winner_workflow.md (logo suite, mockups, guidelines)
```

## 1. Inputs: all three are required

| Input | `brand.json` key | Example |
|---|---|---|
| Company name (exact spelling and capitalisation) | `name` | `Ember Lane` |
| Industry | `industry` | `food & beverage` |
| Business type + one-sentence idea | `business_type`, `business_idea` | `restaurant`, "a casual Southeast Asian charcoal-grill restaurant in a city laneway…" |

`business_type` is a short label: `tech`, `resell`, `manufacturing`, `restaurant`, or the closest
row in `references/business-types.md`. If any of the three is missing, **ask for it and don't
proceed**. Never invent a company name. Optional, and worth one question if unknown: audience,
location, real contact details for the card (`contact`), colours or symbols to keep or avoid.

Repeat the inputs back in one sentence (exact name spelling) and get a confirmation.

## 2. Five ideas

```bash
mkdir -p _project/brand _project/output _project/prompt _project/script _project/log
cp prompt/brand.example.json _project/brand/brand.json   # then overwrite every value
```

Write the company fields and five `ideas` per `references/design-ideas.md` (spread across styles,
logo types, palettes and tones; use `references/business-types.md` for what this business
needs and its clichés). Remove the example's `ai_review`.

Show the user a compact table of the five (title, style, one-line concept, palette, logo type)
and let them swap or tweak ideas before anything is rendered.

## 3. Render: one proposal, 15 images

```bash
python scripts/render_design_ideas.py --dry-run
```

This writes all 15 prompt files to `_project/prompt/idea{N}_{logo|story|card}.txt` and the
plan to `_project/script/design_ideas_proposal.txt`, and refuses if any idea is missing a
field. Show the proposal summary (15 Seedream calls, formats, references) and **wait for a
yes**. Then:

```bash
python scripts/render_design_ideas.py
```

Ideas render in parallel (`config.json` `design_set.workers`, default 3). Within an idea, the
logo renders first and is the reference for the story graphic and card. Existing outputs are
skipped, so re-running after a failure only redoes what's missing. Outputs:
`_project/output/idea{N}_logo.png`, `idea{N}_story.png`, `idea{N}_card.png`.

Re-roll one asset (after fixing the idea's text if needed):

```bash
python scripts/render_design_ideas.py --ideas 3 --assets card --force
```

A new logo means its story graphic and card should be redone too (`--ideas 3 --force`).

### Review before showing anything

Read all 15 images. Check: name spelled exactly, the card/story logo matches the idea's logo,
no invented text or extra logos, palette followed (`extract_palette.py` if unsure). Re-roll pure
generation defects (and say so). Then write `ai_review` for each idea
(`references/evaluation-rubric.md`). Scores must use the whole scale.

## 4. Evaluation page

```bash
python scripts/build_evaluation_page.py --embed
```

→ `_project/output/evaluation.html`, a single self-contained file (images embedded as JPEGs).
It shows:
- the company inputs, a live **leaderboard** (the reviewer's weighted totals)
- "How scoring works": criteria, weights and descriptions from `config.json`
- per idea: the three images (click to enlarge), concept, tagline, palette chips, type,
  **1–5 scoring per criterion**, notes,
  shortlist toggle, weighted total
- reviewer name, **Export JSON / CSV**, Import, Reset

Scores persist in the viewer's browser. To combine several reviewers, each exports JSON and
sends the files back. Offer to publish the page if the user wants a link to share with their team.

When the user returns scores (exported JSON or just "I like 2 and 4"), summarise the ranking,
point out the winner's weakest criteria, and offer the next step:
`workflow/expand_winner_workflow.md`.
