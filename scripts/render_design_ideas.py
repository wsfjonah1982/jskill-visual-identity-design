import argparse
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from ark_service import (
    BRAND_PATH, PROMPT_LIBRARY_DIR, brand_for_idea, brand_vars, configure_console, fill_template,
    load_brand, load_config, resolve_image_size, validate_idea_ids,
)

configure_console()

SCRIPTS_DIR        = Path(__file__).resolve().parent
AUTO_PLACEHOLDER   = re.compile(r"\{([a-z_]+)\}")
MANUAL_PLACEHOLDER = re.compile(r"<[^<>\n]+>")


def output_name(idea_id, asset_id: str) -> str:
    return f"idea{idea_id}_{asset_id}.png"


def build_prompts(brand: dict, ideas: list, assets: list, prompt_dir: Path) -> tuple[dict, list[str]]:
    """Fills every (idea, asset) template from brand.json. Returns ({(idea, asset): prompt
    path}, problems). Problems are anything that would make a paid call wrong: unknown
    placeholders, leftover <slots>, or a single-line template that became multi-line."""
    paths, problems = {}, []
    prompt_dir.mkdir(parents=True, exist_ok=True)
    for idea in ideas:
        values = brand_vars(brand_for_idea(brand, idea["id"]))
        for asset in assets:
            template = (PROMPT_LIBRARY_DIR / asset["template"]).read_text(encoding="utf-8").strip()
            text = fill_template(template, **values)
            where = f"idea {idea['id']} / {asset['id']}"
            unknown = sorted(set(AUTO_PLACEHOLDER.findall(text)))
            if unknown:
                problems.append(f"{where}: unknown placeholders {', '.join(unknown)}")
            empty = sorted(k for k in set(AUTO_PLACEHOLDER.findall(template)) if k in values and not str(values[k]).strip()
                           and k not in ("avoid", "tagline", "style_reference_note"))
            if empty:
                problems.append(f"{where}: brand.json leaves these empty: {', '.join(empty)}")
            slots = MANUAL_PLACEHOLDER.findall(text)
            if slots:
                problems.append(f"{where}: unfilled slots {', '.join(dict.fromkeys(slots))}")
            if asset.get("reference") is None and "\n" in text:
                problems.append(f"{where}: text-to-image prompt must be one line (each line becomes an image)")
            path = prompt_dir / f"idea{idea['id']}_{asset['id']}.txt"
            path.write_text(text + "\n", encoding="utf-8")
            paths[(idea["id"], asset["id"])] = path
    return paths, problems


def style_reference(merged: dict, project_dir: Path) -> Path | None:
    """brand.json `style_reference.file` (company-level, or overridden per idea; null disables):
    an image — e.g. a parent brand's logo — that assets with no reference of their own are
    generated from, so a sub-brand inherits its parent's visual language."""
    ref = merged.get("style_reference") or {}
    if not ref.get("file"):
        return None
    path = (project_dir / ref["file"]).resolve()
    # The file is uploaded to the image API, so it must be an image inside the project folder.
    if not path.is_relative_to(project_dir.resolve()) or path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError(f"style_reference.file must be an image inside the project folder: {ref['file']}")
    return path


def run_asset(idea_id, asset: dict, prompt: Path, out_dir: Path, log_dir: Path,
              style_ref: Path | None = None) -> tuple[bool, str]:
    output = out_dir / output_name(idea_id, asset["id"])
    if asset.get("reference"):
        ref = out_dir / output_name(idea_id, asset["reference"])
        if not ref.exists():
            return False, f"reference {ref.name} missing"
        cmd = [sys.executable, str(SCRIPTS_DIR / "generate_image_from_reference.py"), "--img", str(ref)]
    elif style_ref:
        cmd = [sys.executable, str(SCRIPTS_DIR / "generate_image_from_reference.py"), "--img", str(style_ref)]
    else:
        cmd = [sys.executable, str(SCRIPTS_DIR / "generate_image_from_text.py")]
    cmd += ["--prompt", str(prompt), "--output", str(output), "--format", asset["format"], "--log-dir", str(log_dir)]
    t0 = time.monotonic()
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    secs = time.monotonic() - t0
    if proc.returncode != 0:
        tail = (proc.stderr.strip().splitlines() or ["(no output)"])[-1]
        return False, f"failed after {secs:.0f}s — {tail}"
    return True, f"{output.name} ({secs:.0f}s)"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render the design-idea set: for every idea in brand.json, the assets listed in "
                    "config.json design_set (by default logo → brand story graphic → business card, "
                    "the latter two anchored on that idea's logo). Writes one prompt file per asset "
                    "and a proposal file first; --dry-run stops there (no API cost)."
    )
    parser.add_argument("--brand",   default=str(BRAND_PATH), help="Path to brand.json (defaults to _project/brand/brand.json)")
    parser.add_argument("--ideas",   default=None, help="Comma-separated idea ids to render (default: all)")
    parser.add_argument("--assets",  default=None, help="Comma-separated asset ids to render (default: all in config design_set)")
    parser.add_argument("--dry-run", action="store_true", help="Write prompts + proposal only — no generation")
    parser.add_argument("--force",   action="store_true", help="Regenerate assets whose output already exists (default: skip them)")
    parser.add_argument("--workers", type=int, default=None, help="Ideas rendered in parallel (default: config design_set.workers)")
    args = parser.parse_args()

    brand_path  = Path(args.brand).resolve()
    project_dir = brand_path.parent.parent  # <project>/brand/brand.json
    prompt_dir, out_dir = project_dir / "prompt", project_dir / "output"
    script_dir, log_dir = project_dir / "script", project_dir / "log"

    try:
        config     = load_config()
        design_set = config["design_set"]
        brand      = load_brand(brand_path)
        validate_idea_ids(brand)
        missing = [k for k in ("name", "industry", "business_type", "business_idea") if not str(brand.get(k, "")).strip()]
        if missing:
            raise ValueError(f"brand.json is missing required company inputs: {', '.join(missing)}")
        ideas  = brand.get("ideas") or []
        expected = design_set.get("idea_count")
        if expected and len(ideas) != expected:
            print(f"Warning: brand.json has {len(ideas)} idea(s); config.json design_set.idea_count is {expected}", file=sys.stderr)
        if args.ideas:
            wanted = {s.strip() for s in args.ideas.split(",")}
            ideas  = [i for i in ideas if str(i.get("id")) in wanted]
        assets = design_set["assets"]
        if args.assets:
            wanted = {s.strip() for s in args.assets.split(",")}
            assets = [a for a in assets if a["id"] in wanted]
        if not ideas or not assets:
            raise ValueError("nothing to render — check --ideas / --assets and brand.json ideas")
        for a in assets:
            resolve_image_size(config, a["format"])  # fail fast on a bad format name
        if any(a["id"] == "card" for a in assets) and not any(
                (brand_for_idea(brand, i["id"]).get("contact") or {}).values() for i in ideas):
            print("Note: brand.json has no contact details, so the business cards will show grey "
                  "placeholder lines. Add a \"contact\" object (name, title, phone, email, address) "
                  "to print real details.", file=sys.stderr)
        style_refs = {i["id"]: style_reference(brand_for_idea(brand, i["id"]), project_dir) for i in ideas}
        missing_refs = sorted({str(p) for p in style_refs.values() if p and not p.exists()})
        if missing_refs:
            raise FileNotFoundError(f"style_reference file(s) not found: {', '.join(missing_refs)}")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    prompts, problems = build_prompts(brand, ideas, assets, prompt_dir)

    # --- proposal ----------------------------------------------------------------------------
    jobs = [(i, a) for i in ideas for a in assets]
    todo = [(i, a) for i, a in jobs if args.force or not (out_dir / output_name(i["id"], a["id"])).exists()]
    lines = [
        f"Design ideas render — {brand['name']} ({brand['industry']}, {brand['business_type']})",
        f"Written: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"Model:   {config['image_model_id']}   watermark: {config.get('watermark', False)}",
        f"Calls:   {len(todo)} image generation(s)" + (f" ({len(jobs) - len(todo)} already exist, skipped)" if len(todo) < len(jobs) else ""),
        "",
    ]
    for idea in ideas:
        lines.append(f"Idea {idea['id']}: {idea.get('title', '')} — {idea.get('style', '')}")
        lines.append(f"  {idea.get('summary', '')}")
        for a in assets:
            out = output_name(idea["id"], a["id"])
            state = "generate" if (idea, a) in todo else "exists, skip"
            ref = (f"  ref: {output_name(idea['id'], a['reference'])}" if a.get("reference")
                   else f"  style ref: {style_refs[idea['id']].name}" if style_refs[idea["id"]] else "")
            lines.append(f"  - {a['label']:<20} {out:<18} --format {a['format']:<10}{ref}  [{state}]")
        lines.append("")
    if problems:
        lines += ["PROBLEMS — fix brand.json before generating:"] + [f"  ! {p}" for p in problems]
    # A run with nothing left to generate is a status check — don't overwrite the real plan.
    proposal = script_dir / ("design_ideas_proposal.txt" if todo else "design_ideas_status.txt")
    script_dir.mkdir(parents=True, exist_ok=True)
    proposal.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines), file=sys.stderr)
    print(f"\nPrompts: {prompt_dir}\nProposal: {proposal}", file=sys.stderr)

    if problems:
        print(f"Error: {len(problems)} problem(s) in the prompts — not generating", file=sys.stderr)
        return 1
    if args.dry_run or not todo:
        print(str(proposal))
        return 0

    # --- generate ----------------------------------------------------------------------------
    # Ideas run in parallel; within one idea the order matters (story/card use its logo).
    def render_idea(idea):
        results = []
        for a in assets:
            if (idea, a) not in todo:
                continue
            ok, msg = run_asset(idea["id"], a, prompts[(idea["id"], a["id"])], out_dir, log_dir, style_refs[idea["id"]])
            print(f"[idea {idea['id']}] {a['label']}: {'ok' if ok else 'FAILED'} — {msg}", file=sys.stderr)
            results.append((idea["id"], a["id"], ok))
            if not ok and a["id"] in {x.get("reference") for x in assets}:
                print(f"[idea {idea['id']}] skipping the rest — they depend on {a['id']}", file=sys.stderr)
                break
        return results

    workers = max(1, args.workers or design_set.get("workers", 1))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = [r for rs in pool.map(render_idea, ideas) for r in rs]

    failed = [f"idea{i}_{a}" for i, a, ok in results if not ok]
    done   = len(results) - len(failed)
    print(f"\nDone: {done} generated, {len(failed)} failed{': ' + ', '.join(failed) if failed else ''}", file=sys.stderr)
    for i, a, ok in results:
        if ok:
            print(str(out_dir / output_name(i, a)))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
