"""Shared slug validation, TOS key-prefix building, and local publish paths for
publish_site.py and unpublish_site.py, so both always
target exactly the same objects or folders.

A slug becomes part of an object-key prefix, and unpublish deletes everything
under that prefix — so an empty slug, or one containing "/" or "..", could
reach other sites' files. Only short lowercase kebab-case slugs are accepted.
"""
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
DEFAULT_PREFIX_TEMPLATE = "site/manual/{slug}"


def validate_slug(slug: str) -> str:
    if not SLUG_RE.fullmatch(slug or ""):
        raise ValueError(
            f"Invalid slug {slug!r}: use 1-64 lowercase letters, digits, and hyphens "
            f"(not starting or ending with a hyphen), e.g. 'kino-kopi-evaluation'."
        )
    return slug


def site_prefix(config: dict, slug: str) -> str:
    """Object-key prefix for a site, with no trailing slash."""
    validate_slug(slug)
    template = config.get("tos_key_prefix_template", DEFAULT_PREFIX_TEMPLATE)
    if "{slug}" not in template:
        raise ValueError(f"tos_key_prefix_template must contain '{{slug}}', got {template!r}")
    prefix = template.replace("{slug}", slug).strip("/")
    if not prefix.endswith(slug):
        raise ValueError(f"tos_key_prefix_template must end with '{{slug}}', got {template!r}")
    return prefix


def local_publish_root(config: dict, override: str | None = None) -> Path | None:
    """Where pages go when TOS isn't configured: `override` (a --local-dir
    argument, relative to the current directory) or config.json's
    `local_publish_dir` (relative to the skill folder) — e.g. a mounted share,
    a synced folder, or a web server's document root. None means the build
    simply stays in its build folder (e.g. <project>/site/)."""
    if override:
        return Path(override).resolve()
    configured = (config.get("local_publish_dir") or "").strip()
    if not configured:
        return None
    root = Path(configured)
    return (root if root.is_absolute() else BASE_DIR / root).resolve()
