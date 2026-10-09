import argparse
import re
import sys
from pathlib import Path

from ark_service import (
    BRAND_PATH, PROMPT_LIBRARY_DIR, brand_for_idea, brand_vars, configure_console, fill_template, load_brand,
)

configure_console()

AUTO_PLACEHOLDER   = re.compile(r"\{([a-z_]+)\}")
MANUAL_PLACEHOLDER = re.compile(r"<[^<>\n]+>")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fill a prompt/ template's {brand placeholders} from the project's brand.json "
                    "and write the result to a project prompt file. No API call, no cost. "
                    "<angle-bracket> placeholders are creative slots left for Claude to fill by "
                    "hand afterwards — the script lists any that remain."
    )
    parser.add_argument("--template", required=True, help="Template name in prompt/ (e.g. logo_concept.txt) or a path")
    parser.add_argument("--brand",    default=str(BRAND_PATH), help="Path to brand.json (defaults to _project/brand/brand.json)")
    parser.add_argument("--idea",     default=None, help="Fill from this design idea (brand.json ideas[].id) merged over the company facts")
    parser.add_argument("--set",      action="append", default=[], metavar="KEY=VALUE",
                        help="Override or add a {placeholder} value; repeatable")
    parser.add_argument("--output",   required=True, help="Where to write the filled prompt (e.g. _project/prompt/logo_concepts.txt)")
    parser.add_argument("--append",   action="store_true",
                        help="Append to --output instead of overwriting — builds a multi-line batch file for generate_image_from_text.py")
    args = parser.parse_args()

    template_path = Path(args.template)
    if not template_path.exists():
        template_path = PROMPT_LIBRARY_DIR / args.template
    if not template_path.exists():
        print(f"Error: template not found: {args.template} (looked in {PROMPT_LIBRARY_DIR})", file=sys.stderr)
        return 1

    try:
        brand  = load_brand(Path(args.brand))
        values = brand_vars(brand_for_idea(brand, args.idea) if args.idea else brand)
        for item in args.set:
            key, sep, value = item.partition("=")
            if not sep:
                raise ValueError(f"--set expects KEY=VALUE, got {item!r}")
            values[key.strip()] = value.strip()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    text = fill_template(template_path.read_text(encoding="utf-8").strip(), **values)

    unknown = sorted(set(AUTO_PLACEHOLDER.findall(text)))
    if unknown:
        print(f"Error: template uses placeholders brand.json doesn't provide: {', '.join(unknown)} "
              f"— add them to brand.json or pass --set", file=sys.stderr)
        return 1
    empty = sorted(k for k in set(AUTO_PLACEHOLDER.findall(template_path.read_text(encoding="utf-8")))
                   if not str(values.get(k, "")).strip())
    if empty:
        print(f"Warning: these placeholders filled in EMPTY — check brand.json: {', '.join(empty)}", file=sys.stderr)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if args.append and output_path.exists() and output_path.read_text(encoding="utf-8").strip():
        with output_path.open("a", encoding="utf-8") as f:
            f.write("\n" + text + "\n")
    else:
        output_path.write_text(text + "\n", encoding="utf-8")

    manual = MANUAL_PLACEHOLDER.findall(text)
    if manual:
        print(f"Still to fill by hand in {output_path}: {', '.join(dict.fromkeys(manual))}", file=sys.stderr)
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
