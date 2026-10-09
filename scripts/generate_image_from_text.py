import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from ark_service import (
    ArkImageService, download_file, extract_token_usage, BASE_DIR, LOG_DIR, configure_console,
    load_config, load_api_key, write_log, resolve_image_size,
)

configure_console()

PROMPT_PATH     = BASE_DIR / "_project" / "prompt" / "picture.txt"
OUTPUT_PATH     = BASE_DIR / "_project" / "output" / "output.png"


def read_prompts(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    prompts = [line.strip() for line in text.splitlines() if line.strip()]
    if not prompts:
        raise ValueError(f"Prompt file is empty: {path}")
    return prompts


def generate_image(service: ArkImageService, prompt: str, model_id: str, size: str, watermark: bool) -> tuple[str, dict]:
    images, usage = service.generate_image(model_id=model_id, prompt=prompt, size=size, watermark=watermark)
    url = images[0]["url"] if images else None
    if not url:
        raise RuntimeError(f"No image URL returned for prompt: {prompt!r}")
    return url, usage


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", default=str(PROMPT_PATH), help="Path to prompt text file (one prompt per line)")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output image file path (e.g. out.png)")
    parser.add_argument("--format", default=None, help="Named output format from config.json image_formats (e.g. square, landscape, portrait). Defaults to config.json image_size")
    parser.add_argument("--log-dir", default=str(LOG_DIR), help="Directory for the .log JSON record (defaults to _project/log)")
    args = parser.parse_args()

    prompt_path  = Path(args.prompt)
    output_base  = Path(args.output)
    log_path     = Path(args.log_dir) / f"{output_base.name}.log"

    output_base.parent.mkdir(parents=True, exist_ok=True)

    try:
        config    = load_config()
        model_id  = config["image_model_id"]
        size      = resolve_image_size(config, args.format)
        watermark = config.get("watermark", False)
        base_url  = config["maas_api_endpoint"]

        api_key = load_api_key()
        prompts = read_prompts(prompt_path)
        service = ArkImageService(base_url=base_url, api_key=api_key)

        print(f"Prompt file: {prompt_path} ({len(prompts)} prompt(s))", file=sys.stderr)
        print(f"Model: {model_id}  Size: {size}", file=sys.stderr)
        print(f"Output: {output_base}\n", file=sys.stderr)

        results = []
        for i, prompt in enumerate(prompts, start=1):
            t_img = time.monotonic()
            if len(prompts) == 1:
                output_path = output_base
            else:
                output_path = output_base.with_stem(f"{output_base.stem}_{i:03d}")

            print(f"[{i}/{len(prompts)}] Generating: {prompt[:80]}{'...' if len(prompt) > 80 else ''}", file=sys.stderr)

            try:
                image_url, usage = generate_image(service, prompt, model_id, size, watermark)
                dl_s = download_file(image_url, output_path)
                elapsed = time.monotonic() - t_img

                print(f"  Saved: {output_path}  ({elapsed:.1f}s, download {dl_s:.1f}s)", file=sys.stderr)

                entry = {
                    "timestamp":   datetime.now(timezone.utc).isoformat(),
                    "model":       model_id,
                    "size":        size,
                    "index":       i,
                    "prompt":      prompt,
                    "output":      str(output_path),
                    "image_url":   image_url,
                    **extract_token_usage(usage),
                    "usage":       usage,
                    "elapsed_s":   round(elapsed, 2),
                    "download_s":  round(dl_s, 2),
                    "status":      "succeeded",
                }
            except Exception as exc:
                elapsed = time.monotonic() - t_img
                print(f"  Failed: {exc}", file=sys.stderr)
                entry = {
                    "timestamp":  datetime.now(timezone.utc).isoformat(),
                    "model":      model_id,
                    "size":       size,
                    "index":      i,
                    "prompt":     prompt,
                    "elapsed_s":  round(elapsed, 2),
                    "status":     "failed",
                    "error":      str(exc),
                }

            write_log(log_path, entry)
            results.append(entry)

        succeeded = sum(1 for r in results if r["status"] == "succeeded")

        for r in results:
            if r["status"] == "succeeded":
                print(r["output"])

        return 0 if succeeded == len(prompts) else 1

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
