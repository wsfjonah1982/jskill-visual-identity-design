"""Ark REST API client for Seedream image generation, plus the brand-file helpers every
visual-identity script shares.

Plain HTTP calls via `requests`, not a vendor SDK.
"""
import base64
import json
import os
import re
import shutil
import sys
import time
import urllib.request
from pathlib import Path

import requests

BASE_DIR           = Path(__file__).resolve().parent.parent  # skill root — credential.json/config.json live here, not in scripts/
CREDENTIAL_PATH    = BASE_DIR / "credential.json"
CONFIG_PATH        = BASE_DIR / "config.json"
PROJECT_DIR        = BASE_DIR / "_project"
LOG_DIR            = PROJECT_DIR / "log"
BRAND_PATH         = PROJECT_DIR / "brand" / "brand.json"  # the project's single source of truth for name/palette/type/style
PROMPT_LIBRARY_DIR = BASE_DIR / "prompt"  # the skill's predefined prompt templates (see prompt/README.md)

DOWNLOAD_TIMEOUT_S        = 120


def configure_console() -> None:
    """Allow Unicode output on Windows consoles."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    return read_json(CONFIG_PATH)


def load_api_key() -> str:
    env_key = os.environ.get("model_ark_key")
    if env_key:
        return env_key
    if not CREDENTIAL_PATH.exists():
        raise FileNotFoundError(
            f"model_ark_key env var not set, and credential file not found: {CREDENTIAL_PATH}"
        )
    cred = read_json(CREDENTIAL_PATH)
    api_key = cred.get("model_ark_key")
    if not api_key:
        raise KeyError("model_ark_key env var not set and `model_ark_key` missing in credential.json")
    return api_key


def write_log(log_path: Path, data: dict) -> None:
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def resolve_image_size(config: dict, fmt: str | None) -> str:
    """Maps a named format (config.json `image_formats`, e.g. "square") to the Seedream `size`
    value. No format → config.json's `image_size`. Unknown names fail fast rather than silently
    falling back, so a typo never produces an asset at the wrong aspect ratio."""
    if not fmt:
        return config["image_size"]
    formats = config.get("image_formats") or {}
    if fmt not in formats:
        raise KeyError(f"Unknown --format {fmt!r}; config.json image_formats has: {', '.join(formats) or '(none)'}")
    return formats[fmt]


def load_brand(path: Path = BRAND_PATH) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Brand file not found: {path} (copy prompt/brand.example.json to start one)")
    return read_json(path)


def parse_hex(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", value):
        raise ValueError(f"Not a 6-digit hex colour: {value!r}")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def palette_phrase(palette: list[dict]) -> str:
    """"deep roast brown (#3B2A20), oat cream (#F4EBDD)" — names first (models follow colour
    words far better than hex codes), hex kept for the record and for exact-colour reference."""
    return ", ".join(f"{c.get('description') or c.get('name')} ({c['hex'].upper()})" for c in palette)


def brand_for_idea(brand: dict, idea_id) -> dict:
    """The company-level facts in brand.json merged with one entry of its `ideas` list (matched
    by `id`) — the idea's keys win. Every template and builder works on this merged view, so a
    design idea is just "the company + this direction"."""
    ideas = brand.get("ideas") or []
    idea = next((i for i in ideas if str(i.get("id")) == str(idea_id)), None)
    if idea is None:
        raise KeyError(f"No idea with id {idea_id!r} in brand.json (have: {', '.join(str(i.get('id')) for i in ideas) or 'none'})")
    merged = {k: v for k, v in brand.items() if k != "ideas"}
    merged.update(idea)
    return merged


def contact_phrase(contact: dict | None) -> str:
    """Business-card contact line. Real details are printed exactly; with none, ask for
    unreadable placeholder lines — invented names/numbers come out misspelled and look real."""
    if not contact:
        return ("Contact details are shown only as a few short, neat, unreadable grey placeholder "
                "lines — no real words, names or numbers")
    lines = [str(v) for k, v in contact.items() if v]
    return "Contact details printed small and neatly, spelled exactly as: " + " / ".join(f'"{l}"' for l in lines)


def brand_vars(brand: dict) -> dict:
    """Flattens brand.json (or a brand_for_idea() view of it) into the `{key}` placeholders the
    prompt/ templates use."""
    palette    = brand.get("palette") or []
    primary    = next((c for c in palette if c.get("role") == "primary"), palette[0] if palette else None)
    accent     = next((c for c in palette if c.get("role") == "accent"), None)
    logo       = brand.get("logo") or {}
    typography = brand.get("typography") or {}
    story      = brand.get("story") if isinstance(brand.get("story"), dict) else {}
    card       = brand.get("card") or {}
    avoid      = brand.get("avoid") or []
    def colour(c):
        return f"{c.get('description') or c.get('name')} ({c['hex'].upper()})" if c else ""
    scenes = story.get("scenes") or []
    return {
        "name":              brand.get("name", ""),
        "tagline":           brand.get("tagline", ""),
        "industry":          brand.get("industry", ""),
        "business_type":     brand.get("business_type", ""),
        "business_idea":     brand.get("business_idea", ""),
        "audience":          brand.get("audience", ""),
        "idea_title":        brand.get("title", ""),
        "personality":       ", ".join(brand.get("personality") or []),
        "style":             brand.get("style", ""),
        "style_descriptor":  brand.get("style_descriptor", ""),
        "palette":           palette_phrase(palette),
        "primary_color":     colour(primary),
        "accent_color":      colour(accent),
        "logo_type":         logo.get("type", ""),
        "logo_description":  logo.get("description", ""),
        "logo_colors":       logo.get("colors") or colour(primary),
        "symbol":            logo.get("symbol", ""),
        "typography_feel":   typography.get("feel", ""),
        "imagery":           brand.get("imagery", ""),
        "story_headline":    story.get("headline", ""),
        "story_layout":      story.get("layout") or "three connected vignettes flowing left to right",
        "story_scenes":      "; ".join(f"({i}) {sc}" for i, sc in enumerate(scenes, 1)),
        "card_front":        card.get("front", ""),
        "card_back":         card.get("back", ""),
        "card_material":     card.get("material") or "thick premium uncoated card stock",
        "card_scene":        card.get("scene") or "on a clean neutral desk surface",
        "card_contact":      contact_phrase(brand.get("contact")),
        "style_reference_note": (brand.get("style_reference") or {}).get("note", ""),
        "avoid":             ", ".join(f"no {a}" for a in avoid),
    }


def fill_template(text: str, /, **values) -> str:
    """Substitutes `{key}` placeholders. Unlike str.format, braces inside the values (or
    elsewhere in the template) are left alone instead of raising KeyError/ValueError."""
    for key, value in values.items():
        text = text.replace("{" + key + "}", str(value))
    return text


def extract_token_usage(usage: dict | None) -> dict:
    """Normalizes an Ark API `usage` dict into {tokens_in, tokens_out, tokens_total} for
    logging. Different endpoints use different key names — chat completions use
    prompt_tokens/completion_tokens, image generation uses input_images/output_tokens (verified
    live: {"input_images": 0, "generated_images": 1, "output_tokens": 16384, "total_tokens":
    16384} — no prompt_tokens/completion_tokens at all). Missing values are None, not 0, so a
    genuine zero-token value is never confused with "not reported"."""
    usage = usage or {}
    tokens_in = usage.get("prompt_tokens")
    if tokens_in is None:
        tokens_in = usage.get("input_tokens")
    tokens_out = usage.get("completion_tokens")
    if tokens_out is None:
        tokens_out = usage.get("output_tokens")
    return {
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "tokens_total": usage.get("total_tokens"),
    }


def guess_mime_from_path(path) -> str:
    ext = str(path).rsplit(".", 1)[-1].lower() if "." in str(path) else ""
    if ext in ("jpg", "jpeg"):
        return "image/jpeg"
    if ext == "png":
        return "image/png"
    if ext == "gif":
        return "image/gif"
    if ext == "webp":
        return "image/webp"
    return "application/octet-stream"


def file_to_data_url(path) -> str:
    path = Path(path)
    data = path.read_bytes()
    mime = guess_mime_from_path(path)
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def download_file(url: str, output_path) -> float:
    """Downloads file and returns elapsed seconds."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_S) as resp, output_path.open("wb") as f:
        shutil.copyfileobj(resp, f)
    return time.monotonic() - t0


class ArkImageService:
    """Seedream image generation/edit client."""

    def __init__(self, base_url: str, api_key: str):
        self._url = base_url.rstrip('/') + '/images/generations'
        self._headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }

    def generate_image(self, model_id: str, prompt: str, image: list[str] | str | None = None,
                        size: str | None = None, watermark: bool | None = None) -> tuple[list[dict], dict]:
        """Returns (images, usage) — usage is the Ark API's token-usage dict, if the response
        included one (image models are not always token-billed), or {} otherwise."""
        img_count = len(image) if isinstance(image, list) else (1 if image else 0)
        print(f"Image generation: model={model_id} prompt_len={len(prompt)} images={img_count} "
              f"size={size} watermark={watermark}", file=sys.stderr)

        payload = {
            'model': model_id,
            'prompt': prompt,
            'response_format': 'url',
        }
        if image:
            payload['image'] = image
        if size is not None:
            payload['size'] = size
        if watermark is not None:
            payload['watermark'] = watermark

        resp = requests.post(self._url, headers=self._headers, json=payload, timeout=300)
        if resp.status_code != 200:
            raise RuntimeError(f"Ark API error {resp.status_code}: {resp.text}")
        data = resp.json()

        images = [
            {'url': img.get('url'), 'b64_json': img.get('b64_json')}
            for img in (data.get('data') or [])
        ]
        usage = data.get('usage') or {}
        print(f"Image generation done: count={len(images)} usage={usage}", file=sys.stderr)
        return images, usage
