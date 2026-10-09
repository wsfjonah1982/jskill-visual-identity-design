# Common Issues & Workarounds — Visual Identity (Seedream 5.0 Pro)

Check this when a generation comes back wrong, and proactively add the relevant constraint when
a prompt matches a known risk. `V-*` entries are API-level issues (already handled in the
scripts); `I-*` entries are identity-specific.

**Verification status.** Verified live (Kino Kopi run, 2026-10-09, 16 Seedream calls, 0 API failures):
1. Explicit `WxH` sizes from `image_formats`: `2048x2048`, `2816x1584`, `2496x1664` came back
   at exactly those dimensions (I-0 has not occurred)
2. `--format` combined with reference images in `generate_image_from_reference.py`
3. `style_reference` (parent-brand logo as the logo reference): logos inherited the parent's
   lettering and symbol language. Timing: ~100s per reference-anchored logo, ~55–65s per
   story/card.

Seen in that run: 1 misspelled story headline in 15 (I-1, fixed by one re-roll), and
small invented text on props such as jerseys and cans in story scenes (I-6).

---

## API-level

| Code | Issue | Fix |
|---|---|---|
| V-1 | `expected the height to be at least 300px` | Run `scripts/prepare_reference.py` (upscales to ≥1024px) |
| V-2 | Image call `Read timed out` | Already 300s timeout; just retry |
| V-3 | Token usage `null` in logs | Expected when the API didn't report it — `null` is "not reported", never `0` |
| V-4 | Watermark/platform logo | `no watermark`; confirm `watermark: false` in config |


---

## I-0: Explicit size rejected (`InvalidParameter … size`)

**Symptom**: an image script fails immediately mentioning `size`.

**Cause**: `config.json`'s `image_formats` uses Seedream's documented `WxH` form; the exact pixel
limits for `dola-seedream-5-0-pro` haven't been confirmed live in this skill.

**Fix**: re-run with `--format auto` (sends `2K`) and state the ratio in the prompt text
(`"square 1:1 composition"`, `"16:9 widescreen"`) — 2K lets the model pick the ratio from the
prompt. Then correct the
offending entry in `config.json` and note the working value here.

---

## I-1: Brand name misspelled / letters invented

**Symptom**: "Embr Lane", "Ember Lanee", a stray glyph, or the name rendered twice.

**Fix**: quotes + "spelled exactly … every letter correct, no extra letters" (all logo templates
already do this); keep only the name in the image; re-roll 2–3 and pick. Long names: try a
lettermark or stacked lockup. **Always Read the output image and check the spelling yourself
before presenting it** — never assume.

---

## I-2: Logo comes back as a mockup / 3D / glossy render

**Symptom**: the "logo" is embossed on paper, has a drop shadow, bevel, gradient, or sits in a
photographed scene.

**Fix**: lead with "Flat vector logo", keep the full negative list (`no mockup, no gradients, no
shadows, no 3D, no texture, no photo`), and "plain pure white background". Don't use words like
"premium", "luxury", "realistic" in logo prompts — put luxury in the letterforms
("high-contrast didone serif"), not the render.

---

## I-3: Logo redrawn differently in variations / mockups

**Symptom**: the mockup's logo has a different symbol, font, or spelling than the approved one.

**Cause**: the asset was generated from text, or the logo wasn't the first reference, or the
logo is tiny in the scene.

**Fix**: always `generate_image_from_reference.py --img <approved_logo.png> ...` with the logo
**first**; keep "Reproduce the logo exactly … Do not redraw, restyle or add to it"; make the logo
reasonably large in the scene (a bottle front, not a distant sign). For scenes where the logo
must be small, generate the scene **without** the logo and composite it afterwards — the
reliable professional route.

---

## I-4: Colours drift from the palette

**Symptom**: teal becomes generic blue; the coral accent takes over the whole layout.

**Fix**: (1) describe colours by name in `brand.json` `description` — specific, e.g. "deep
teal-green sea blue", not "blue"; (2) attach `make_palette_swatch.py --no-labels` output as the
second `--img`; (3) state proportion for the accent: "coral used only as a small accent".
Verify with `extract_palette.py --img <output>` and compare to `brand.json`.

---

## I-5: Swatch text / palette blocks leak into the output

**Symptom**: the mockup contains colour bars or hex codes.

**Fix**: use `--no-labels` swatches only, and say in the prompt that the second reference is
"a colour reference only — do not reproduce its blocks". Drop the swatch if it persists; name
colours instead.

---

## I-6: Mockup invents extra text, fake brands, barcodes

**Fix**: the allow-list line in `brand_application.txt` (`The only branding visible is the
{name} logo…`), plus `no invented text, no random lettering`. Avoid prompting objects that
naturally carry dense text (nutrition labels, newspapers, screens full of UI) unless the copy is
specified.

---

## I-7: Transparent background needed

**Symptom**: user wants a transparent PNG logo; Seedream outputs opaque images.

**Fix**: generate on plain pure white (or a flat brand colour) and remove the background
afterwards (any background-removal tool, or vectorise). Don't prompt "transparent background" —
it produces a fake checkerboard pattern baked into the pixels.

---

## I-8: Generated logo resembles an existing brand

**Fix**: never reference existing brands in prompts (`best-practices.md` §7). If a result looks
familiar, discard it. Always tell the user that a trademark search is required before adopting
any generated mark.

---

## Quick reference

| Code | Issue | Quick fix |
|---|---|---|
| I-0 | Explicit size rejected | `--format auto` + ratio in prompt |
| I-1 | Name misspelled | Quotes + "spelled exactly"; name only; re-roll; check it yourself |
| I-2 | Logo rendered as mockup/3D | "Flat vector logo" first + full negative list |
| I-3 | Logo changes across assets | Approved logo as first `--img`; composite if tiny |
| I-4 | Colour drift | Named colours + swatch reference + accent proportion |
| I-5 | Swatch leaks into image | `--no-labels`; "colour reference only" |
| I-6 | Invented text/brands in mockups | Allow-list copy + `no invented text` |
| I-7 | Needs transparency | Generate on white, remove bg after; never prompt "transparent" |
| I-8 | Looks like an existing mark | Discard; trademark search before adoption |
