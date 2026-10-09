# Existing Logo Rollout Workflow (extend / refresh a brand the user already has)

The user has a logo (and maybe colours). The job is the system around it — variations,
applications, guidelines — **without changing the logo**. Skip concept exploration.

## Steps

**1. Prepare the logo as a reference**

```bash
python scripts/prepare_reference.py --img _project/input/their_logo.png --output _project/input/logo_on_white.png --pad 0.15
```

Transparent PNGs get flattened (white default; `--background "#1F4E5A"` for a light logo), tiny
files get upscaled past the API's 300px minimum. SVG → ask the user for a PNG export, or export
it yourself if a converter is available.

**2. Capture what exists in `brand.json`**

- `name`, `industry`, etc. from the user.
- Palette: `python scripts/extract_palette.py --img _project/input/logo_on_white.png`, then confirm
  the real values with the user — their brand book beats extraction.
- `logo.description`: describe the existing logo precisely (symbol, letterforms, colours). It's
  used in prompts, so be concrete.
- Style: match `style_descriptor` to what the logo already is (`identity-styles.md`) — don't
  impose a new direction.

**3. Decide: use as-is, or clean it up?**

If the source is low quality (blurry, JPEG artefacts, on a photo), one optional
`logo_refine.txt` run can produce a clean flat version — but it **will** subtly redraw the logo.
Ask first, and compare side by side. For a brand with a registered mark, prefer using the
original file as-is.

The prepared (or refined) file is the `--img` anchor for everything after; copy it to
`_project/output/logo_primary.png` so the asset-catalog commands work unchanged.

**4. System, applications, guidelines** — `references/asset-catalog.md` Stages B (variations only) → C → D → E, exactly as in
`expand_winner_workflow.md` steps 3–5 (without `--idea`, since this brand.json has no ideas), with one batched proposal for the image work.

## Watch for

- Variations of a detailed emblem drift more than a simple mark (I-3) — for emblem logos,
  prefer reversed/mono done by flat recolouring in an editor over generation, and say so.
- A logo with fine text (taglines, "EST. 1987") inside it will lose that text in small
  placements — keep those mockups close-up.
