import argparse
import sys
from pathlib import Path

from PIL import Image

from ark_service import configure_console, parse_hex

configure_console()

MIN_SIDE    = 300   # Ark rejects reference images shorter than this (references/common-issues.md V-1)
TARGET_SIDE = 1024  # upscale small inputs to at least this, so a logo's edges stay clean


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Make an existing logo or brand asset safe to pass as --img: flattens "
                    "transparency onto a solid background (transparent PNG logos otherwise arrive "
                    "with undefined/black backgrounds), upscales anything small, and writes a PNG. "
                    "Local, free. SVG isn't supported — export the SVG to PNG first."
    )
    parser.add_argument("--img",        required=True, help="Input image (PNG/JPG/WEBP/GIF)")
    parser.add_argument("--output",     required=True, help="Output PNG path (e.g. _project/input/logo_on_white.png)")
    parser.add_argument("--background", default="#FFFFFF", help="Hex colour to flatten transparency onto")
    parser.add_argument("--pad",        type=float, default=0.0,
                        help="Extra margin around the artwork as a fraction of its size (e.g. 0.2), so a tight logo crop gets breathing room")
    args = parser.parse_args()

    src = Path(args.img)
    if not src.exists():
        print(f"Error: image not found: {src}", file=sys.stderr)
        return 1
    if src.suffix.lower() == ".svg":
        print("Error: SVG isn't supported — export it to PNG (e.g. 2048px wide) and pass that", file=sys.stderr)
        return 1

    try:
        bg  = parse_hex(args.background)
        img = Image.open(src)
        img.seek(0)  # first frame of an animated GIF
        img = img.convert("RGBA")
        flat = Image.new("RGB", img.size, bg)
        flat.paste(img, mask=img.split()[3])

        if args.pad > 0:
            px, py = round(flat.width * args.pad), round(flat.height * args.pad)
            padded = Image.new("RGB", (flat.width + 2 * px, flat.height + 2 * py), bg)
            padded.paste(flat, (px, py))
            flat = padded

        short = min(flat.size)
        if short < TARGET_SIDE:
            scale = TARGET_SIDE / short
            flat = flat.resize((round(flat.width * scale), round(flat.height * scale)), Image.LANCZOS)
            print(f"Upscaled {short}px short side → {min(flat.size)}px "
                  f"({'was below the API minimum of ' + str(MIN_SIDE) + 'px' if short < MIN_SIDE else 'for cleaner edges'})",
                  file=sys.stderr)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    flat.save(out.with_suffix(".png"))
    print(str(out.with_suffix(".png")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
