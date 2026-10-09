# Expand the Winner (after the evaluation round)

The user picked an idea on the evaluation page. This turns it into a full identity system:
logo suite, pattern, imagery, more mockups, and the brand guidelines page. Everything
works off the winning idea through `--idea N`, which merges that idea over the company facts in
`brand.json`.

## Steps

**1. Lock the logo.** Copy `_project/output/idea{N}_logo.png` → `_project/output/logo_primary.png`.
If the evaluation flagged weaknesses (low `versatile` or `craft`), do one refinement first:

```bash
python scripts/fill_prompt_template.py --idea N --template logo_refine.txt --output _project/prompt/logo_refine.txt
# fill the <Change: …> slot from the low-scoring criteria / user notes
python scripts/generate_image_from_reference.py --img _project/output/idea{N}_logo.png --prompt _project/prompt/logo_refine.txt --format square --output _project/output/logo_primary.png
```

Want a fresh round of logo options inside the winning direction? `logo_concept.txt` with
`--idea N --append`, one line per variant, batched through `generate_image_from_text.py`.

**2. Finalise palette & type** in the winning idea's entry in `brand.json` (add `usage` notes per
colour, `typography.notes`, `logo.rationale`, `logo.usage` do/don'ts):

```bash
python scripts/make_palette_swatch.py --idea N
python scripts/make_palette_swatch.py --idea N --no-labels --output _project/output/palette_ref.png
python scripts/build_brand_guidelines.py --idea N   # early preview: colour + type + the 3 renders
```

**3. System assets.** Follow `references/asset-catalog.md` Stages B (variations) → C (pattern,
imagery) → D (applications), always with `--idea N` on `fill_prompt_template.py` and the
approved `logo_primary.png` as the first `--img`. One batch proposal for the whole stage.

**4. Guidelines.** Add an `"assets"` block to the winning idea's entry in `brand.json` (shape in
`references/asset-catalog.md` Stage E). Without one, the builder uses the idea's three renders.
Then:

```bash
python scripts/build_brand_guidelines.py --idea N --embed
```

Deliver with the notes from `SKILL.md` "Delivering" (raster logos need a vector redraw; trademark
search before adoption; CMYK must be proofed).
