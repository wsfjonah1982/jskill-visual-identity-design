import argparse
import base64
import html
import os
import sys
import urllib.parse
from pathlib import Path

from ark_service import BRAND_PATH, PROJECT_DIR, brand_for_idea, configure_console, guess_mime_from_path, load_brand, parse_hex

configure_console()

OUTPUT_PATH = PROJECT_DIR / "output" / "brand_guidelines.html"

# Sections in page order: (key in brand.json "assets", heading, intro)
ASSET_SECTIONS = [
    ("moodboard",    "Mood",         "The visual territory the identity was drawn from."),
    ("logo",         "Logo",         "The primary lockup and its approved variations."),
    ("pattern",      "Graphic language", "Supporting shapes, patterns and textures built from the mark."),
    ("imagery",      "Imagery",      "How the brand looks in photography and illustration."),
    ("applications", "Applications", "The identity at work across real touchpoints."),
]


# ---- colour maths -----------------------------------------------------------------------------

def rel_luminance(rgb):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((rel_luminance(a), rel_luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def wcag_label(ratio):
    return "AAA" if ratio >= 7 else "AA" if ratio >= 4.5 else "AA large" if ratio >= 3 else "fail"


def cmyk(rgb):
    """Naive RGB→CMYK — a starting point for print, not a colour-managed conversion."""
    r, g, b = (v / 255 for v in rgb)
    k = 1 - max(r, g, b)
    if k >= 1:
        return (0, 0, 0, 100)
    return tuple(round(v * 100) for v in ((1 - r - k) / (1 - k), (1 - g - k) / (1 - k), (1 - b - k) / (1 - k), k))


def ink_for(rgb):
    return "#111111" if contrast(rgb, (17, 17, 17)) >= contrast(rgb, (255, 255, 255)) else "#FFFFFF"


# ---- html helpers -----------------------------------------------------------------------------

def esc(v) -> str:
    return html.escape(str(v or ""))


def media_src(file: Path, out_dir: Path, embed: bool) -> str:
    if embed:
        return f"data:{guess_mime_from_path(file)};base64,{base64.b64encode(file.read_bytes()).decode('ascii')}"
    return urllib.parse.quote(Path(os.path.relpath(file, out_dir)).as_posix())


def font_link(family: str) -> str:
    if not family:
        return ""
    q = urllib.parse.quote_plus(family)
    # One <link> per family: a family Google Fonts doesn't host fails alone, not the whole request.
    return f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family={q}&display=swap">'


def render_assets(items, project_dir: Path, out_dir: Path, embed: bool, missing: list) -> str:
    cards = []
    for item in items:
        if isinstance(item, str):
            item = {"file": item}
        file = Path(item["file"])
        if not file.is_absolute():
            file = project_dir / file
        if not file.exists():
            missing.append(str(file))
            continue
        src = media_src(file, out_dir, embed)
        cap = esc(item.get("caption"))
        media = f'<img src="{src}" alt="{cap}" loading="lazy">'
        wide = " wide" if item.get("wide") else ""
        cards.append(f'<figure class="asset{wide}">{media}<figcaption>{cap}</figcaption></figure>')
    return f'<div class="grid">{"".join(cards)}</div>' if cards else ""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assemble the brand guidelines page (HTML) from brand.json and the generated "
                    "assets it lists under \"assets\". Local, free. Colour specs (HEX/RGB/CMYK, WCAG "
                    "contrast) and type specimens are rendered from brand.json directly — exact, "
                    "unlike anything a generative model draws."
    )
    parser.add_argument("--brand",  default=str(BRAND_PATH), help="Path to brand.json (defaults to _project/brand/brand.json)")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output HTML path")
    parser.add_argument("--idea",   default=None, help="Build the guidelines for this design idea (brand.json ideas[].id), e.g. the evaluation winner")
    parser.add_argument("--embed",  action="store_true", help="Inline images as base64 so the HTML is a single shareable file")
    args = parser.parse_args()

    brand_path = Path(args.brand)
    try:
        brand = load_brand(brand_path)
        if args.idea:
            brand = brand_for_idea(brand, args.idea)
        palette = [(c, parse_hex(c["hex"])) for c in brand.get("palette") or []]
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    project_dir = brand_path.resolve().parent.parent  # brand.json lives in <project>/brand/
    out_path    = Path(args.output).resolve()
    out_dir     = out_path.parent
    assets      = brand.get("assets") or {}
    if args.idea and not assets:
        # An idea from the design-ideas round: start from its three renders.
        n = args.idea
        assets = {
            "cover":        {"file": f"output/idea{n}_logo.png", "caption": "Logo"},
            "logo":         [{"file": f"output/idea{n}_logo.png", "caption": "Primary logo"}],
            "imagery":      [{"file": f"output/idea{n}_story.png", "caption": "Brand story", "wide": True}],
            "applications": [{"file": f"output/idea{n}_card.png", "caption": "Business card"}],
        }
    typography  = brand.get("typography") or {}
    logo        = brand.get("logo") or {}
    missing: list[str] = []

    primary = next((rgb for c, rgb in palette if c.get("role") == "primary"), palette[0][1] if palette else (17, 17, 17))
    accent  = next((rgb for c, rgb in palette if c.get("role") == "accent"), primary)
    primary_hex = "#{:02X}{:02X}{:02X}".format(*primary)
    accent_hex  = "#{:02X}{:02X}{:02X}".format(*accent)
    display = typography.get("display", "")
    body    = typography.get("body", "")

    # --- cover -------------------------------------------------------------------------------
    cover_logo = ""
    if assets.get("cover"):
        cover_logo = render_assets([assets["cover"]], project_dir, out_dir, args.embed, missing)

    # --- essence -----------------------------------------------------------------------------
    traits = "".join(f"<li>{esc(t)}</li>" for t in brand.get("personality") or [])
    essence_rows = [
        ("Story", (brand.get("story") or {}).get("narrative") if isinstance(brand.get("story"), dict) else brand.get("story")), ("Audience", brand.get("audience")),
        ("Voice", brand.get("voice")), ("Industry", brand.get("industry")),
    ]
    essence = "".join(f"<dt>{k}</dt><dd>{esc(v)}</dd>" for k, v in essence_rows if v)

    # --- logo rules --------------------------------------------------------------------------
    rules = logo.get("usage") or {}
    do_list   = "".join(f"<li>{esc(r)}</li>" for r in rules.get("do") or [])
    dont_list = "".join(f"<li>{esc(r)}</li>" for r in rules.get("dont") or [])
    logo_rules = ""
    if logo.get("rationale") or do_list or dont_list:
        logo_rules = f"""
        <p class="lede">{esc(logo.get('rationale'))}</p>
        <div class="rules">
          {'<div><h4>Do</h4><ul>' + do_list + '</ul></div>' if do_list else ''}
          {'<div><h4>Don’t</h4><ul class="dont">' + dont_list + '</ul></div>' if dont_list else ''}
        </div>"""

    # --- colour ------------------------------------------------------------------------------
    swatches = []
    for c, rgb in palette:
        ink = ink_for(rgb)
        on_white, on_black = contrast(rgb, (255, 255, 255)), contrast(rgb, (0, 0, 0))
        swatches.append(f"""
        <div class="swatch">
          <div class="chip" style="background:{esc(c['hex'])};color:{ink}">
            <span class="role">{esc(c.get('role'))}</span><strong>{esc(c.get('name'))}</strong>
          </div>
          <dl class="spec">
            <dt>HEX</dt><dd>{esc(c['hex'].upper())}</dd>
            <dt>RGB</dt><dd>{', '.join(map(str, rgb))}</dd>
            <dt>CMYK</dt><dd>{', '.join(map(str, cmyk(rgb)))}</dd>
            <dt>On white</dt><dd>{on_white:.1f}:1 · {wcag_label(on_white)}</dd>
            <dt>On black</dt><dd>{on_black:.1f}:1 · {wcag_label(on_black)}</dd>
          </dl>
          <p class="note">{esc(c.get('usage'))}</p>
        </div>""")
    pairs = []
    for i, (a, ra) in enumerate(palette):
        for b, rb in palette[i + 1:]:
            r = contrast(ra, rb)
            if r >= 3:
                pairs.append(f'<div class="pair" style="background:{esc(a["hex"])};color:{esc(b["hex"])}">'
                             f'<span>Aa</span><small>{esc(b.get("name"))} on {esc(a.get("name"))} · {r:.1f}:1 {wcag_label(r)}</small></div>')

    # --- type --------------------------------------------------------------------------------
    type_rows = []
    for role, fam in (("Display", display), ("Body", body)):
        if fam:
            css = "var(--display)" if role == "Display" else "var(--body)"
            type_rows.append(f"""
            <div class="type-row">
              <div class="type-meta"><span class="role">{role}</span><strong>{esc(fam)}</strong></div>
              <div class="type-sample" style="font-family:{css}">
                <p class="big">{esc(brand.get('name'))}</p>
                <p>{esc(brand.get('tagline') or 'The quick brown fox jumps over the lazy dog.')}</p>
                <p class="glyphs">ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz 0123456789</p>
              </div>
            </div>""")
    type_note = f'<p class="lede">{esc(typography.get("notes"))}</p>' if typography.get("notes") else ""

    # --- asset sections ----------------------------------------------------------------------
    numbered = []
    def add_section(sid, title, inner):
        if inner.strip():
            numbered.append((sid, title, inner))

    add_section("essence", "Brand essence", f"""
        {'<p class="lede">' + esc(brand.get('positioning')) + '</p>' if brand.get('positioning') else ''}
        {'<ul class="traits">' + traits + '</ul>' if traits else ''}
        <dl class="essence">{essence}</dl>""")
    for key, title, intro in ASSET_SECTIONS:
        grid = render_assets(assets.get(key) or [], project_dir, out_dir, args.embed, missing)
        extra = logo_rules if key == "logo" else ""
        if grid or extra:
            add_section(key, title, f'<p class="intro">{intro}</p>{grid}{extra}')
        if key == "logo":  # colour + type sit right after the logo
            add_section("colour", "Colour", f"""
                <p class="intro">Contrast ratios are WCAG 2.x; CMYK is a naive conversion — proof it before print.</p>
                <div class="swatches">{''.join(swatches)}</div>
                {'<h3>Accessible pairings</h3><div class="pairs">' + ''.join(pairs) + '</div>' if pairs else ''}""")
            add_section("type", "Typography", type_note + "".join(type_rows))

    toc  = "".join(f'<li><a href="#{sid}"><span>{i:02d}</span>{esc(t)}</a></li>' for i, (sid, t, _) in enumerate(numbered, 1))
    body_html = "".join(
        f'<section id="{sid}"><header class="sec-head"><span class="num">{i:02d}</span><h2>{esc(t)}</h2></header>{inner}</section>'
        for i, (sid, t, inner) in enumerate(numbered, 1)
    )

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(brand.get('name'))} Brand Guidelines</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
{font_link(display)}
{font_link(body) if body != display else ''}
<style>
  :root {{
    --brand: {primary_hex}; --brand-ink: {ink_for(primary)}; --accent: {accent_hex};
    --paper: #FAFAF7; --ink: #151515; --muted: #6B6B66; --line: #E4E3DE;
    --display: "{esc(display)}", ui-serif, Georgia, serif;
    --body: "{esc(body)}", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  }}
  * {{ box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; }}
  body {{ margin: 0; background: var(--paper); color: var(--ink); font: 16px/1.6 var(--body); }}
  .cover {{ min-height: 92vh; background: var(--brand); color: var(--brand-ink); display: grid;
           grid-template-rows: auto 1fr auto; padding: clamp(24px, 5vw, 72px); gap: 32px; }}
  .cover .eyebrow {{ letter-spacing: .18em; text-transform: uppercase; font-size: 13px; opacity: .8; }}
  .cover h1 {{ font: 400 clamp(48px, 10vw, 128px)/0.95 var(--display); margin: 0; align-self: end; }}
  .cover p {{ font-size: clamp(18px, 2.2vw, 24px); max-width: 40ch; margin: 16px 0 0; opacity: .9; }}
  .cover .grid {{ grid-template-columns: minmax(0, 520px); }}
  .cover figcaption {{ display: none; }}
  nav {{ border-bottom: 1px solid var(--line); background: var(--paper); position: sticky; top: 0; z-index: 2; }}
  nav ul {{ list-style: none; margin: 0 auto; padding: 0 clamp(16px, 4vw, 48px); display: flex; gap: 24px;
           overflow-x: auto; max-width: 1200px; }}
  nav a {{ display: block; padding: 14px 0; color: var(--muted); text-decoration: none; white-space: nowrap; font-size: 14px; }}
  nav a span {{ color: var(--brand); margin-right: 6px; font-variant-numeric: tabular-nums; }}
  nav a:hover {{ color: var(--ink); }}
  main {{ max-width: 1200px; margin: 0 auto; padding: 0 clamp(16px, 4vw, 48px) 96px; }}
  section {{ padding: 80px 0 24px; border-bottom: 1px solid var(--line); scroll-margin-top: 48px; }}
  .sec-head {{ display: flex; align-items: baseline; gap: 16px; margin-bottom: 24px; }}
  .num {{ color: var(--brand); font-variant-numeric: tabular-nums; font-size: 14px; }}
  h2 {{ font: 400 clamp(32px, 5vw, 56px)/1.05 var(--display); margin: 0; }}
  h3 {{ font: 600 18px/1.3 var(--body); margin: 40px 0 16px; }}
  h4 {{ margin: 0 0 8px; font-size: 14px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); }}
  .intro {{ color: var(--muted); max-width: 60ch; margin: 0 0 24px; }}
  .lede {{ font-size: 20px; max-width: 60ch; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 320px), 1fr)); gap: 20px; }}
  .asset {{ margin: 0; }}
  .asset.wide {{ grid-column: 1 / -1; }}
  .asset img {{ width: 100%; display: block; border-radius: 6px; background: #fff; border: 1px solid var(--line); }}
  figcaption {{ font-size: 13px; color: var(--muted); margin-top: 8px; }}
  .traits {{ display: flex; flex-wrap: wrap; gap: 8px; padding: 0; list-style: none; margin: 0 0 32px; }}
  .traits li {{ border: 1px solid var(--brand); color: var(--ink); padding: 6px 14px; border-radius: 999px; font-size: 14px; }}
  .essence {{ display: grid; grid-template-columns: minmax(90px, 160px) 1fr; gap: 12px 24px; max-width: 820px; }}
  .essence dt {{ color: var(--muted); font-size: 14px; }} .essence dd {{ margin: 0; }}
  .rules {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr)); gap: 24px; margin-top: 32px; }}
  .rules ul {{ margin: 0; padding-left: 18px; }} .rules .dont li::marker {{ content: "✕  "; color: #C0392B; }}
  .swatches {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 220px), 1fr)); gap: 20px; }}
  .chip {{ aspect-ratio: 4 / 3; border-radius: 6px; padding: 16px; display: flex; flex-direction: column;
          justify-content: flex-end; border: 1px solid var(--line); }}
  .chip strong {{ font-size: 18px; }} .role {{ font-size: 11px; text-transform: uppercase; letter-spacing: .12em; opacity: .75; }}
  .spec {{ display: grid; grid-template-columns: auto 1fr; gap: 2px 12px; font-size: 13px; margin: 12px 0 4px;
          font-variant-numeric: tabular-nums; }}
  .spec dt {{ color: var(--muted); }} .spec dd {{ margin: 0; }}
  .note {{ font-size: 13px; color: var(--muted); margin: 4px 0 0; }}
  .pairs {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 200px), 1fr)); gap: 12px; }}
  .pair {{ border-radius: 6px; padding: 16px; border: 1px solid var(--line); }}
  .pair span {{ font: 400 40px/1 var(--display); display: block; }} .pair small {{ font-size: 12px; }}
  .type-row {{ display: grid; grid-template-columns: minmax(0, 200px) 1fr; gap: 24px; padding: 24px 0; border-top: 1px solid var(--line); }}
  .type-meta strong {{ display: block; font-size: 18px; }}
  .type-sample p {{ margin: 0 0 8px; overflow-wrap: anywhere; }} .type-sample .big {{ font-size: clamp(36px, 6vw, 72px); line-height: 1.05; }}
  .type-sample .glyphs {{ color: var(--muted); font-size: 15px; }}
  footer {{ max-width: 1200px; margin: 0 auto; padding: 32px clamp(16px, 4vw, 48px); color: var(--muted); font-size: 13px; }}
  @media (max-width: 640px) {{ .type-row, .essence {{ grid-template-columns: 1fr; }} }}
  @media print {{ nav {{ display: none; }} section {{ break-inside: avoid-page; }} .cover {{ min-height: auto; }} }}
</style>
</head>
<body>
<header class="cover">
  <span class="eyebrow">Brand guidelines{(' · ' + esc(brand.get('version'))) if brand.get('version') else ''}</span>
  <div>{cover_logo}</div>
  <div><h1>{esc(brand.get('name'))}</h1>{'<p>' + esc(brand.get('tagline')) + '</p>' if brand.get('tagline') else ''}</div>
</header>
<nav><ul>{toc}</ul></nav>
<main>{body_html}</main>
<footer>{esc(brand.get('name'))} brand guidelines · Imagery generated with Seedream 5.0 Pro — review every asset before external use.</footer>
</body>
</html>
"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    if missing:
        print(f"Warning: {len(missing)} asset(s) listed in brand.json not found, skipped: {', '.join(missing)}", file=sys.stderr)
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
