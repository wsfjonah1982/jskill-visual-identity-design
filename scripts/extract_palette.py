import argparse
import json
import sys
from pathlib import Path

from PIL import Image

from ark_service import configure_console

configure_console()


def is_background(rgb: tuple[int, int, int], threshold: int) -> bool:
    """Near-white or near-black — the canvas logos and mockups sit on, not a brand colour."""
    return all(v >= 255 - threshold for v in rgb) or all(v <= threshold for v in rgb)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pull the dominant colours out of an image (an approved logo concept, a "
                    "moodboard, an existing brand asset) as hex values — locally with Pillow, no API "
                    "call. Use it to turn a concept the user picked into concrete palette entries "
                    "for brand.json, or to check how far a generation drifted from the palette."
    )
    parser.add_argument("--img",   required=True, help="Input image")
    parser.add_argument("--count", type=int, default=6, help="Number of colours to return")
    parser.add_argument("--keep-background", action="store_true",
                        help="Keep near-white/near-black colours (dropped by default)")
    parser.add_argument("--threshold", type=int, default=18, help="How close to pure white/black counts as background")
    args = parser.parse_args()

    path = Path(args.img)
    if not path.exists():
        print(f"Error: image not found: {path}", file=sys.stderr)
        return 1

    img = Image.open(path).convert("RGB")
    img.thumbnail((400, 400))
    # Over-quantize, then drop background clusters and keep the top `count` by pixel share.
    quant  = img.quantize(colors=max(args.count * 3, 12), method=Image.Quantize.MEDIANCUT)
    lut    = quant.getpalette()
    counts = sorted(quant.getcolors(), reverse=True)
    total  = sum(n for n, _ in counts)

    colours = []
    for n, idx in counts:
        rgb = tuple(lut[idx * 3: idx * 3 + 3])
        if not args.keep_background and is_background(rgb, args.threshold):
            continue
        colours.append({"hex": "#{:02X}{:02X}{:02X}".format(*rgb), "share": round(n / total, 3)})
        if len(colours) == args.count:
            break

    print(json.dumps(colours, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
