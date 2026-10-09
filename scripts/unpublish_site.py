"""Unpublish a previously-published site from BytePlus TOS — the counterpart
to publish_site.py, for when a build is superseded or was published by
mistake. Removes every object under the site's key prefix, via
tos_client.py's plain-HTTP TOS4-HMAC-SHA256 signing — no vendor SDK.

When TOS isn't configured (or with --local-dir), it removes the local copy at
<local_publish_dir>/<slug>/ instead. It never deletes the local build (e.g. <project>/site/).

Usage:
    python scripts/unpublish_site.py --slug kino-kopi-evaluation
"""
import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from credentials import load_bucket, load_credential, tos_status
from site_paths import local_publish_root, site_prefix, validate_slug

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
LOG_DIR = BASE_DIR / "_log"


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    return read_json(CONFIG_PATH)


def write_log(log_path: Path, data: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True, help="URL slug of the published site to unpublish")
    parser.add_argument("--local-dir", help="Remove LOCAL_DIR/<slug>/ instead of the TOS copy")
    args = parser.parse_args()

    try:
        validate_slug(args.slug)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    log_path = LOG_DIR / f"unpublish-{args.slug}.log"

    try:
        config = load_config()
        state, missing = tos_status(config)
        if state == "partial" and not args.local_dir:
            raise RuntimeError(f"TOS is only partly configured (missing: {', '.join(missing)}).")
        if state == "off" or args.local_dir:
            root = local_publish_root(config, args.local_dir)
            if root is None:
                print("TOS isn't configured and no local_publish_dir is set, so nothing was published "
                      "— the local build is left alone.")
                return 0
            dest = root / args.slug
            if dest.resolve().is_relative_to(BASE_DIR.resolve()):
                # Published copies live outside the skill; anything inside it is a build or project folder.
                raise ValueError(f"{dest} is inside the skill folder (a build, not a published copy) — not deleting it.")
            removed = dest.is_dir()
            if removed:
                shutil.rmtree(dest)
            write_log(log_path, {
                "timestamp": datetime.now(timezone.utc).isoformat(), "slug": args.slug,
                "target": "local", "path": str(dest), "removed": removed, "status": "succeeded",
            })
            print(f"Removed {dest}" if removed else f"Nothing at {dest} — already removed or never published.")
            return 0

        from tos_client import delete_object, list_objects  # needs `requests`; TOS only

        endpoint = config["tos_endpoint"]
        region = config["tos_region"]
        bucket = load_bucket(config)
        key_prefix = site_prefix(config, args.slug)

        access_key = load_credential("tos_access_key_id")
        secret_key = load_credential("tos_secret_access_key")

        keys = list_objects(endpoint, region, bucket, access_key, secret_key, prefix=key_prefix + "/")

        if not keys:
            print(f"Nothing found under {key_prefix}/ — already empty or never published.", file=sys.stderr)
        else:
            for k in keys:
                delete_object(endpoint, region, bucket, k, access_key, secret_key)
                print(f"  deleted: {k}", file=sys.stderr)

        write_log(log_path, {
            "timestamp": datetime.now(timezone.utc).isoformat(), "slug": args.slug,
            "key_prefix": key_prefix, "deleted_count": len(keys), "status": "succeeded",
        })
        print(f"{len(keys)} object(s) deleted from {key_prefix}/")
        return 0

    except Exception as exc:
        write_log(log_path, {
            "timestamp": datetime.now(timezone.utc).isoformat(), "slug": args.slug,
            "status": "failed", "error": str(exc),
        })
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
