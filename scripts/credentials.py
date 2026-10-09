"""Shared credential loading for this skill's scripts.

Priority: credential.json first (the artifact this skill ships and documents,
see credential_tmp.json), falling back to an environment variable of the same
name as the credential.json key — only if the key is missing, blank, or the
file doesn't exist at all.
"""
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIAL_PATH = BASE_DIR / "credential.json"


def _load_credential_file() -> dict:
    if not CREDENTIAL_PATH.exists():
        return {}
    with CREDENTIAL_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_credential(key_name: str) -> str:
    """Look up `key_name` in credential.json; if it's missing, blank, or the
    file doesn't exist, fall back to the environment variable of the same
    name (e.g. `tos_bucket` -> $tos_bucket). Raises KeyError if neither
    source has it."""
    value, source = describe_credential(key_name)
    if source == "missing":
        raise KeyError(
            f"`{key_name}` not found in {CREDENTIAL_PATH.name} and ${key_name} is not set. "
            f"Copy credential_tmp.json to credential.json and fill it in, or set ${key_name}."
        )
    return value


BUCKET_PLACEHOLDER = "your-bucket-name"


def load_bucket(config: dict) -> str:
    """The TOS bucket name. credential.json / $tos_bucket wins over config.json,
    so the shipped config.json can carry a placeholder while the real bucket
    stays in the gitignored credential.json."""
    value, _ = describe_credential("tos_bucket")
    if value == "...":  # unfilled credential_tmp.json copy
        value = None
    value = value or config.get("tos_bucket")
    if not value or value == BUCKET_PLACEHOLDER:
        raise KeyError(
            f"No TOS bucket configured. Set `tos_bucket` in {CREDENTIAL_PATH.name} "
            f"(or $tos_bucket, or config.json)."
        )
    return value


TOS_SETTINGS = ("tos_access_key_id", "tos_secret_access_key", "tos_bucket")


def tos_status(config: dict) -> tuple[str, list[str]]:
    """Whether TOS publishing is set up: ('on', []) if every setting is
    present, ('off', [...]) if none is, ('partial', [missing...]) otherwise.
    TOS is optional — when it's off, publish_site.py keeps the page on the
    local file system instead. "..." (an unfilled credential_tmp.json copy)
    and the config.json bucket placeholder count as missing."""
    missing = []
    for key in TOS_SETTINGS:
        value, _ = describe_credential(key)
        if value == "...":
            value = None
        if key == "tos_bucket" and not value:
            value = config.get("tos_bucket")
            if value == BUCKET_PLACEHOLDER:
                value = None
        if not value:
            missing.append(key)
    if not missing:
        return "on", []
    return ("off" if len(missing) == len(TOS_SETTINGS) else "partial"), missing


def describe_credential(key_name: str) -> tuple[str | None, str]:
    """Non-raising counterpart to load_credential — returns (value, source)
    where source is 'credential.json', 'environment variable', or 'missing'.
    Used to report where each credential is coming
    from (or that it's absent) without failing outright."""
    value = _load_credential_file().get(key_name)
    if value:
        return value, "credential.json"
    env_value = os.environ.get(key_name)
    if env_value:
        return env_value, "environment variable"
    return None, "missing"
