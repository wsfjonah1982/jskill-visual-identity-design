import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ark_service import BRAND_PATH, PROJECT_DIR, brand_for_idea, configure_console, load_brand, parse_hex

configure_console()

OUTPUT_PATH = PROJECT_DIR / "output" / "palette_swatch.png"

# Share of the strip each role gets — primary dominates, accents stay small, like a real
# 60/30/10 colour split. Unknown roles get the "neutral" share.
ROLE_WEIGHT = {"primary": 5, "secondary": 3, "neutral": 2, "accent": 1}


def text_colour(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    r, g, b = rgb
    return (20, 20, 20) if (0.299 * r + 0.587 * g + 0.114 * b) > 150 else (250, 250, 250)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render the brand palette from brand.json as an exact-colour swatch image — "
                    "locally with Pillow, no API call, no cost. Generative models only approximate "
                    "colours named in text; passing this swatch as an extra --img reference to "
                    "generate_image_from_reference.py pulls outputs much closer to the real hex values. "
                    "Use --no-labels for that reference use, so no text leaks into generations."
    )
    parser.add_argument("--brand",     default=str(BRAND_PATH), help="Path to brand.json (defaults to _project/brand/brand.json)")
    parser.add_argument("--idea",      default=None, help="Use this design idea's palette (brand.json ideas[].id)")
    parser.add_argument("--output",    default=str(OUTPUT_PATH), help="Output PNG path")
    parser.add_argument("--width",     type=int, default=2048)
    parser.add_argument("--height",    type=int, default=1024)
    parser.add_argument("--no-labels", action="store_true", help="Plain colour blocks only (for use as a generation reference)")
    args = parser.parse_args()

    try:
        brand   = load_brand(Path(args.brand))
        palette = (brand_for_idea(brand, args.idea) if args.idea else brand).get("palette") or []
        if not palette:
            raise ValueError("brand.json has no palette entries")
        colours = [(c, parse_hex(c["hex"])) for c in palette]
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    img  = Image.new("RGB", (args.width, args.height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    weights = [ROLE_WEIGHT.get(c.get("role", "neutral"), ROLE_WEIGHT["neutral"]) for c, _ in colours]
    # Floor each strip at ~60% of an even split, so small accents still fit their label.
    floor   = 0.6 * sum(weights) / len(weights)
    weights = [max(w, floor) for w in weights]
    total   = sum(weights)
    font_l  = ImageFont.load_default(size=max(18, args.height // 22))
    font_s  = ImageFont.load_default(size=max(14, args.height // 32))

    x = 0
    for i, ((entry, rgb), w) in enumerate(zip(colours, weights)):
        x_end = args.width if i == len(colours) - 1 else x + round(args.width * w / total)
        draw.rectangle([x, 0, x_end, args.height], fill=rgb)
        if not args.no_labels:
            ink = text_colour(rgb)
            pad = max(12, args.height // 30)
            draw.text((x + pad, args.height - pad * 5.6), entry.get("name", ""), fill=ink, font=font_l)
            draw.text((x + pad, args.height - pad * 3.6), entry["hex"].upper(), fill=ink, font=font_s)
            draw.text((x + pad, args.height - pad * 2.2), entry.get("role", ""), fill=ink, font=font_s)
        x = x_end

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
