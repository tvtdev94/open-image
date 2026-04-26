"""OpenAI image generation CLI. Prompt in, PNG out."""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

from openai import OpenAI

# Skill template + installer live in their own stdlib-only module so the
# `.pth`-driven site-init bootstrap doesn't have to import openai.
# Re-exported below for backwards-compatible test access via `gen.X`.
from open_image_skill import (  # noqa: F401  (re-exports)
    __version__,
    SKILL_MD_TEMPLATE,
    _render_skill_md,
    maybe_install_skill_silently,
    reinstall_skill_force,
)


# Info-only registry of OpenAI image models known at write time.
# Powers `--list-models`. Does NOT participate in API call args:
# `--model` is still forwarded as-is and unknown values are accepted silently
# so that future models work without a code change.
KNOWN_MODELS: dict[str, str] = {
    "gpt-image-2": "Default. Requires org verification on OpenAI dashboard. Returns b64_json.",
    "gpt-image-1": "Newer GPT image model. Supports input_fidelity, transparency, output_format params.",
    "dall-e-3":    "n=1 only. Sizes: 1024x1024 | 1792x1024 | 1024x1792. quality: standard|hd. style: vivid|natural. Pass response_format=b64_json via --extra for offline storage.",
    "dall-e-2":    "n>1 supported. Sizes: 256x256 | 512x512 | 1024x1024.",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate images via OpenAI images API."
    )
    p.add_argument("--prompt", help="Inline prompt text.")
    p.add_argument("--prompt-file", help="Path to a file containing the prompt.")
    p.add_argument("--model", default="gpt-image-2", help="Model name (default: gpt-image-2).")
    p.add_argument("--extra", default="{}", help="JSON dict of extra API params forwarded to images.generate.")
    p.add_argument("--out-dir", default="./output", help="Output directory (default: ./output).")
    p.add_argument("--api-key", help="OpenAI API key; falls back to $OPENAI_API_KEY.")
    p.add_argument("--keep", type=int, default=50, help="Keep only N newest PNGs in --out-dir after save; 0 disables pruning (default: 50).")
    p.add_argument("--name", help="Custom slug for output filename. Overrides auto-derived slug from prompt.")
    p.add_argument("--list-models", action="store_true", help="List known OpenAI image models with notes, then exit.")
    p.add_argument("--install-skill", action="store_true", help="Re-install Claude Code skill at ~/.claude/skills/open-image/ (overwrites).")
    return p.parse_args()


def print_models_table() -> None:
    """Print known models with notes in an aligned 2-column table."""
    width = max(len(name) for name in KNOWN_MODELS) + 2
    print(f"{'MODEL'.ljust(width)}NOTES")
    print(f"{'-' * (width - 2)}  {'-' * 60}")
    for name, notes in KNOWN_MODELS.items():
        print(f"{name.ljust(width)}{notes}")
    print()
    print("Note: --model accepts any string. Unknown models forwarded to API as-is.")


# Vietnamese horn/stroke letters lack NFKD decompositions, so a plain
# ASCII fold drops them entirely. Map them to ASCII before normalizing.
_VIETNAMESE_FOLD = str.maketrans({
    "đ": "d", "Đ": "D",
    "ơ": "o", "Ơ": "O",
    "ư": "u", "Ư": "U",
})


def slugify(text: str, max_len: int = 40) -> str:
    """Derive a kebab-case ASCII slug from text for use in filenames.

    Strips diacritics (NFKD ASCII fold + manual Vietnamese fold), lowercases,
    drops non-alphanumeric characters, joins whitespace-separated words with
    hyphens up to max_len *without splitting mid-word*. Falls back to a
    truncated single word if the only word exceeds max_len, or to 'image'
    if the result is empty (e.g., emoji-only or all-non-ASCII input).
    """
    decomposed = unicodedata.normalize("NFKD", text).translate(_VIETNAMESE_FOLD)
    folded = decomposed.encode("ascii", "ignore").decode()
    cleaned = re.sub(r"[^a-z0-9\s-]", "", folded.lower())
    words = cleaned.split()
    if not words:
        return "image"
    out: list[str] = []
    used = 0
    for word in words:
        # +1 accounts for the hyphen separator (not added before the first word).
        cost = len(word) + (1 if out else 0)
        if used + cost > max_len:
            if not out:
                # Single word longer than max_len → hard-truncate to fit.
                return word[:max_len]
            break
        out.append(word)
        used += cost
    return "-".join(out) or "image"


def open_editor_for_prompt() -> str:
    editor = os.getenv("EDITOR") or ("notepad" if sys.platform == "win32" else "vi")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as tf:
        tf.write("# Enter your prompt below. Lines starting with # are ignored.\n")
        tmp_path = tf.name
    try:
        subprocess.run([editor, tmp_path], check=True)
        content = Path(tmp_path).read_text(encoding="utf-8")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    lines = [ln for ln in content.splitlines() if not ln.lstrip().startswith("#")]
    return "\n".join(lines).strip()


def resolve_prompt(args: argparse.Namespace) -> str:
    if args.prompt is not None:
        return args.prompt.strip()
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8").strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return open_editor_for_prompt()


def resolve_api_key(args: argparse.Namespace) -> str:
    key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        sys.exit("ERROR: No API key. Set OPENAI_API_KEY env or pass --api-key.")
    return key


def save_images(response, out_dir: Path, slug: str) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    saved: list[Path] = []
    for item in response.data:
        uid = uuid.uuid4().hex[:8]
        fpath = out_dir / f"{timestamp}-{slug}-{uid}.png"
        b64 = getattr(item, "b64_json", None)
        url = getattr(item, "url", None)
        if b64:
            fpath.write_bytes(base64.b64decode(b64))
        elif url:
            with urllib.request.urlopen(url) as resp:
                fpath.write_bytes(resp.read())
        else:
            sys.exit("ERROR: API response item has neither b64_json nor url.")
        saved.append(fpath.resolve())
    return saved


def prune_old_images(out_dir: Path, keep: int) -> None:
    if keep <= 0:
        return
    pngs = sorted(out_dir.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    for stale in pngs[keep:]:
        try:
            stale.unlink()
        except OSError:
            pass


def main() -> None:
    # First-run skill auto-install (silent, idempotent, never blocks).
    maybe_install_skill_silently()

    args = parse_args()

    if args.list_models:
        print_models_table()
        return

    if args.install_skill:
        reinstall_skill_force()
        return

    prompt = resolve_prompt(args)
    if not prompt:
        sys.exit("ERROR: Empty prompt.")

    api_key = resolve_api_key(args)

    try:
        extra = json.loads(args.extra)
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR: --extra invalid JSON: {e}")
    if not isinstance(extra, dict):
        sys.exit("ERROR: --extra must be a JSON object (dict).")

    client = OpenAI(api_key=api_key, max_retries=2)

    try:
        response = client.images.generate(model=args.model, prompt=prompt, **extra)
    except Exception as e:
        sys.exit(f"ERROR: API call failed: {e}")

    slug = slugify(args.name) if args.name else slugify(prompt)
    out_dir = Path(args.out_dir)
    try:
        paths = save_images(response, out_dir, slug)
    except PermissionError as e:
        sys.exit(f"ERROR: Cannot write to output dir: {e}")

    prune_old_images(out_dir, args.keep)

    for p in paths:
        print(p)


if __name__ == "__main__":
    main()
