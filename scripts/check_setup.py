"""Check that this skill can run in the current environment: Python version, packages,
config.json, credentials, and (optionally) that the Ark API key and TOS keys are accepted.
Every check is free: the live checks only look up a task id / object prefix that doesn't exist.

Usage:
    python scripts/check_setup.py           # local checks only
    python scripts/check_setup.py --live    # also verify the Ark key and TOS keys over the network
"""
import argparse
import importlib
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

OK, WARN, FAIL = "ok  ", "warn", "FAIL"
results: list[tuple[str, str, str]] = []


def report(status: str, item: str, detail: str = "") -> None:
    results.append((status, item, detail))


def check_python() -> None:
    v = sys.version_info
    report(OK if v >= (3, 10) else FAIL, "Python", f"{v.major}.{v.minor}.{v.micro} (needs 3.10+)")


def check_packages() -> None:
    for module, pip_name, minimum in (("requests", "requests", (2, 31)), ("PIL", "Pillow", (10, 1))):
        try:
            mod = importlib.import_module(module)
        except ImportError:
            report(FAIL, pip_name, "not installed: pip install -r requirements.txt")
            continue
        version = getattr(mod, "__version__", "0")
        parts = tuple(int(p) for p in version.split(".")[:2] if p.isdigit())
        report(OK if parts >= minimum else FAIL, pip_name,
               f"{version} (needs {'.'.join(map(str, minimum))}+)")


def check_config() -> dict:
    path = BASE_DIR / "config.json"
    if not path.exists():
        report(FAIL, "config.json", "missing")
        return {}
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report(FAIL, "config.json", f"invalid JSON: {exc}")
        return {}
    missing = [k for k in ("maas_api_endpoint", "image_model_id", "image_formats", "design_set", "evaluation_criteria")
               if k not in config]
    report(FAIL if missing else OK, "config.json", f"missing keys: {', '.join(missing)}" if missing else "")
    for a in (config.get("design_set") or {}).get("assets", []):
        if not (BASE_DIR / "prompt" / a.get("template", "")).exists():
            report(FAIL, "design_set template", f"prompt/{a.get('template')} not found")
    return config


def credential(key: str, env_first: bool) -> tuple[str | None, str]:
    cred_path = BASE_DIR / "credential.json"
    file_value = None
    if cred_path.exists():
        try:
            file_value = json.loads(cred_path.read_text(encoding="utf-8")).get(key)
        except json.JSONDecodeError:
            pass
    if file_value == "...":
        file_value = None
    env_value = os.environ.get(key)
    order = [(env_value, "env var"), (file_value, "credential.json")]
    if not env_first:
        order.reverse()
    for value, source in order:
        if value:
            return value, source
    return None, "missing"


def check_credentials(config: dict) -> None:
    key, source = credential("model_ark_key", env_first=True)
    report(OK if key else FAIL, "model_ark_key", source if key else
           "set $model_ark_key or add it to credential.json (copy credential_tmp.json)")
    tos = {k: credential(k, env_first=False) for k in ("tos_access_key_id", "tos_secret_access_key")}
    have = [k for k, (v, _) in tos.items() if v]
    if len(have) == 2:
        bucket = tos_bucket(config)
        report(OK if bucket else FAIL, "TOS keys", f"publishing to {bucket}" if bucket else
               "keys set but no bucket: add tos_bucket to credential.json")
    elif not have:
        report(WARN, "TOS keys", "not set — publishing is optional; pages stay local")
    else:
        report(FAIL, "TOS keys", "only one of tos_access_key_id / tos_secret_access_key is set")


def tos_bucket(config: dict) -> str | None:
    """Same resolution as publish_site.py: credential.json / $tos_bucket, then config.json,
    ignoring the shipped placeholder."""
    from credentials import load_bucket
    try:
        return load_bucket(config)
    except KeyError:
        return None


def check_live(config: dict) -> None:
    import requests
    key, _ = credential("model_ark_key", env_first=True)
    if key and config.get("maas_api_endpoint"):
        try:
            r = requests.get(config["maas_api_endpoint"].rstrip("/") + "/contents/generations/tasks/setup-check-0",
                             headers={"Authorization": f"Bearer {key}"}, timeout=30)
            # 404 = authenticated (the task just doesn't exist); 401/403 = bad key.
            report(OK if r.status_code == 404 else FAIL, "Ark API key (live)",
                   "accepted" if r.status_code == 404 else f"HTTP {r.status_code}: {r.text[:120]}")
        except requests.RequestException as exc:
            report(FAIL, "Ark API key (live)", f"network error: {exc}")
    ak, _ = credential("tos_access_key_id", env_first=False)
    sk, _ = credential("tos_secret_access_key", env_first=False)
    bucket = tos_bucket(config)
    if ak and sk and bucket:
        try:
            from tos_client import list_objects
            list_objects(config["tos_endpoint"], config["tos_region"], bucket, ak, sk,
                         prefix="setup-check-nonexistent/")
            report(OK, "TOS keys (live)", f"bucket {bucket} reachable")
        except Exception as exc:
            report(FAIL, "TOS keys (live)", str(exc)[:160])


def main() -> int:
    parser = argparse.ArgumentParser(description="Check this skill's environment (free).")
    parser.add_argument("--live", action="store_true", help="Also verify the Ark API key and TOS keys over the network")
    args = parser.parse_args()

    check_python()
    check_packages()
    config = check_config()
    check_credentials(config)
    if args.live and not any(s == FAIL and i in ("requests", "config.json") for s, i, _ in results):
        check_live(config)

    for status, item, detail in results:
        print(f"[{status}] {item:<22} {detail}")
    failed = sum(1 for s, _, _ in results if s == FAIL)
    print(f"\n{'Ready.' if not failed else f'{failed} problem(s) to fix.'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
