"""Publish a finished static page/site (from <project>/site/) to BytePlus TOS
object storage, public-read — via tos_client.py's plain-HTTP TOS4-HMAC-SHA256
signing, no vendor SDK.

TOS is optional. If none of its settings are configured, the site stays on the
local file system instead: it's copied to <local_publish_dir>/<slug>/ when
config.json sets `local_publish_dir` (a mounted share, synced folder, web root,
...), and otherwise simply left in <project>/site/. A partly-configured TOS is
an error, not a silent fallback. --local-dir DIR skips TOS for this run and
copies to DIR/<slug>/.

Usage:
    python scripts/publish_site.py --dir _project/site --slug kino-kopi-evaluation
    python scripts/publish_site.py --dir _project/site --slug kino-kopi-evaluation --local-dir /mnt/share/sites
    python scripts/publish_site.py --dir _project/site --slug kino-kopi-evaluation --overwrite   # republish

Prints where the site now lives to stdout on success: the public URL with TOS,
or a file:// URI to the index file when kept locally (per --index-name).

A slug that already holds a site is refused unless --overwrite is passed, so one
project (or another environment) can't silently replace another's page.

After uploading, any object left under the site's prefix that isn't part of
this build (a file the rebuild dropped or renamed) is deleted, so nothing
stale stays public. Pass --keep-stale to skip that.

HTML is uploaded with Cache-Control: no-cache so a republish shows up
immediately; other assets get a short max-age.
"""
import argparse
import json
import mimetypes
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

# A generated site should never carry these along when published.
EXCLUDE_DIR_NAMES = {".git", ".claude", "__pycache__"}

CACHE_HTML = "no-cache"
CACHE_ASSET = "public, max-age=3600"


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    return read_json(CONFIG_PATH)


def load_tos_credentials() -> tuple[str, str]:
    access_key = load_credential("tos_access_key_id")
    secret_key = load_credential("tos_secret_access_key")
    return access_key, secret_key


def publish_local(source_dir: Path, slug: str, root: Path | None, index_name: str,
                  overwrite: bool = False) -> tuple[Path, int]:
    """Keep the site on the local file system. With no `root` it stays where it
    was built; otherwise <root>/<slug>/ is replaced with a fresh copy (the local
    equivalent of the stale-object pruning the TOS path does). Returns the index
    file's path and the number of files copied (0 when left in place)."""
    source = source_dir.resolve()
    if root is None:
        return source / index_name, 0
    dest = root / slug
    if dest == source:
        return source / index_name, 0
    if dest.is_relative_to(source) or source.is_relative_to(dest):
        raise ValueError(f"Local publish folder {dest} overlaps the build folder {source}.")
    if not root.is_dir():
        raise NotADirectoryError(f"Local publish folder doesn't exist: {root}")
    if dest.exists():
        if not overwrite:
            raise FileExistsError(f"{dest} already holds a site. Pass --overwrite to replace it, "
                                  f"or pick another --slug.")
        shutil.rmtree(dest)
    shutil.copytree(source, dest, ignore=shutil.ignore_patterns(*EXCLUDE_DIR_NAMES))
    return dest / index_name, sum(1 for f in dest.rglob("*") if f.is_file())


def write_log(log_path: Path, data: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="Local directory to publish (e.g. _project/site)")
    parser.add_argument("--slug", required=True, help="URL slug — files land under <tos_key_prefix_template>/")
    parser.add_argument("--index-name", default="index.html", help="Entry file to report the public URL for")
    parser.add_argument("--keep-stale", action="store_true",
                        help="Don't delete objects under the site prefix that aren't in this build")
    parser.add_argument("--overwrite", action="store_true",
                        help="Replace a site already published under this slug (refused otherwise)")
    parser.add_argument("--local-dir",
                        help="Skip TOS and copy the site to LOCAL_DIR/<slug>/ (overrides config's local_publish_dir)")
    args = parser.parse_args()

    try:
        validate_slug(args.slug)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    source_dir = Path(args.dir)
    log_path = LOG_DIR / f"publish-{args.slug}.log"

    try:
        if not source_dir.is_dir():
            raise NotADirectoryError(f"Not a directory: {source_dir}")

        config = load_config()
        state, missing = tos_status(config)
        if state == "partial" and not args.local_dir:
            raise RuntimeError(
                f"TOS is only partly configured (missing: {', '.join(missing)}). Fill those in to "
                f"publish to TOS, or remove the other TOS settings to keep sites local.")
        if state == "off" or args.local_dir:
            root = local_publish_root(config, args.local_dir)
            if not any(p.is_file() for p in source_dir.rglob("*")):
                raise RuntimeError(f"No files found in {source_dir} — nothing to publish.")
            index_path, copied = publish_local(source_dir, args.slug, root, args.index_name, args.overwrite)
            location = index_path.as_uri()
            write_log(log_path, {
                "timestamp": datetime.now(timezone.utc).isoformat(), "slug": args.slug,
                "dir": str(source_dir), "target": "local", "local_root": str(root) if root else None,
                "file_count": copied, "status": "succeeded", "location": location,
            })
            why = "--local-dir given" if args.local_dir else "TOS isn't configured"
            if root is None:
                print(f"{why} and no local_publish_dir is set — the site stays in {index_path.parent}.",
                      file=sys.stderr)
            elif not copied:
                print(f"{why} — the site is already in place at {index_path.parent}.", file=sys.stderr)
            else:
                print(f"{why} — {copied} file(s) copied to {index_path.parent}.", file=sys.stderr)
            if not index_path.is_file():
                print(f"Warning: {index_path.name} not found there.", file=sys.stderr)
            print(location)
            return 0

        from tos_client import delete_object, list_objects, put_object  # needs `requests`; TOS only

        endpoint = config["tos_endpoint"]
        region = config["tos_region"]
        bucket = load_bucket(config)
        key_prefix = site_prefix(config, args.slug)

        access_key, secret_key = load_tos_credentials()

        existing = list_objects(endpoint, region, bucket, access_key, secret_key, prefix=key_prefix + "/")
        if existing and not args.overwrite:
            raise FileExistsError(
                f"{len(existing)} object(s) already published under {key_prefix}/. Pass --overwrite to "
                f"replace that site, or pick another --slug (e.g. add -v2 or the date).")

        published = []
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file():
                continue
            if EXCLUDE_DIR_NAMES & set(path.relative_to(source_dir).parts[:-1]):
                continue
            rel = path.relative_to(source_dir).as_posix()
            is_html = path.suffix.lower() in (".html", ".htm")
            mime_type = "text/html" if is_html else (
                mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            )
            key = f"{key_prefix}/{rel}"
            data = path.read_bytes()
            put_object(endpoint, region, bucket, key, access_key, secret_key, data, mime_type,
                       cache_control=CACHE_HTML if is_html else CACHE_ASSET)
            published.append(rel)
            print(f"  published: {rel}  ({mime_type}, {len(data)} bytes)", file=sys.stderr)

        if not published:
            raise RuntimeError(f"No files found in {source_dir} — nothing published, nothing pruned.")

        pruned = []
        if not args.keep_stale:
            current = {f"{key_prefix}/{rel}" for rel in published}
            for k in existing:
                if k not in current:
                    delete_object(endpoint, region, bucket, k, access_key, secret_key)
                    pruned.append(k)
                    print(f"  removed stale: {k[len(key_prefix) + 1:]}", file=sys.stderr)

        public_url = f"https://{bucket}.{endpoint}/{key_prefix}/{args.index_name}"

        write_log(log_path, {
            "timestamp": datetime.now(timezone.utc).isoformat(), "slug": args.slug,
            "dir": str(source_dir), "target": "tos", "key_prefix": key_prefix, "file_count": len(published),
            "pruned_count": len(pruned),
            "status": "succeeded", "public_url": public_url,
        })

        print(f"\n{len(published)} files published, {len(pruned)} stale removed.", file=sys.stderr)
        print(public_url)
        return 0

    except Exception as exc:
        write_log(log_path, {
            "timestamp": datetime.now(timezone.utc).isoformat(), "slug": args.slug,
            "dir": str(source_dir), "status": "failed", "error": str(exc),
        })
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
