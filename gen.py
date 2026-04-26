"""OpenAI image generation CLI. Prompt in, PNG out."""

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

from openai import OpenAI


# CLI version, sourced from installed package metadata so the skill
# template can stamp the version it ships with. Falls back to "dev"
# when running from source without a pip install.
try:
    from importlib.metadata import version as _pkg_version
    __version__ = _pkg_version("open-image")
except Exception:
    __version__ = "dev"


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


# Embedded Claude Code skill written to ~/.claude/skills/open-image/SKILL.md.
# Auto-installed on every CLI run (silent, idempotent) — content is sync'd
# to the installed CLI version so upgrading the package upgrades the skill
# automatically. The {version} placeholder is filled by _render_skill_md().
SKILL_MD_TEMPLATE = """\
---
name: open-image
description: Generate PNG images via OpenAI image API. Use when user asks to generate an image, create a picture, draw, make an image, or pipes prompt text. CLI command `open-image` outputs absolute file paths to stdout.
---
<!-- Auto-installed by open-image CLI v{version}. Sync'd on each run. -->

# open-image — OpenAI image generation CLI

Tiny CLI that generates PNGs from text prompts via OpenAI's image API. Installed as the `open-image` shell command.

## When to use

- User asks to generate an image, create a picture, draw, or make an image
- User has a `.txt` file with a prompt and wants the image
- User wants batch variations (e.g., 4 images of the same prompt)
- Any text-to-image workflow on OpenAI models

## When NOT to use

- Image editing or variation of an existing image (this CLI is text-to-image only)
- Non-OpenAI providers (Gemini, Stability, Flux, MiniMax) — use a different tool
- Embedding generation, vision analysis, OCR — wrong tool

## Quick reference

```bash
# Inline prompt (default model: gpt-image-2)
open-image --prompt "a red fox in snow"

# From file (good for long prompts)
open-image --prompt-file scene.txt

# Forward extra params on the default model (size, quality)
open-image --model gpt-image-2 --extra '{"size":"1024x1024","quality":"high"}' --prompt "..."

# Use gpt-image-1 with transparency / output_format
open-image --model gpt-image-1 --extra '{"output_format":"png","transparency":true}' --prompt "a minimalist cat icon"

# List known models with notes
open-image --list-models
```

## Models supported

Run `open-image --list-models` for the current list with notes. The CLI is model-agnostic — `--model` accepts any string and unknown models are forwarded to the API as-is, so new OpenAI image models work without an upgrade.

## Output

- PNGs saved to `./output/{YYYYMMDD-HHMMSS}-{uuid8}.png` (override with `--out-dir`)
- Absolute paths printed to stdout, one per line — pipe-friendly
- Old PNGs auto-pruned (keeps newest 50; tweak with `--keep N`, disable with `--keep 0`)

## Auth

- Set `OPENAI_API_KEY` env var (recommended)
- Or pass `--api-key sk-...` per call

## Common errors

| Error | Fix |
|---|---|
| `No API key` | `export OPENAI_API_KEY=sk-...` or pass `--api-key` |
| `403` on `gpt-image-2` | Verify your org on OpenAI dashboard |
| `--extra invalid JSON` | Check quoting; use single quotes around the JSON |
| `Empty prompt` | Pass `--prompt`, `--prompt-file`, or pipe via stdin |

## Best practices for agents

1. For prompts >200 chars, write to a temp file and use `--prompt-file` (avoids shell escaping)
2. Capture stdout to get image paths: `path=$(open-image --prompt "..." | head -1)`
3. Use `--out-dir ./task-XXX/` to keep per-task outputs separate
4. For deterministic offline storage with `dall-e-3`, pass `--extra '{"response_format":"b64_json"}'`
5. Check exit code — non-zero means generation failed
"""


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


def _render_skill_md() -> str:
    """Materialize the skill template with the current CLI version stamp."""
    return SKILL_MD_TEMPLATE.replace("{version}", __version__)


def maybe_install_skill_silently() -> None:
    """Sync the Claude Code skill on every CLI run (silent, idempotent).

    No-ops if ~/.claude is absent (user is not running Claude Code) or if
    the on-disk content already matches the desired template (already in
    sync). Otherwise the skill is rewritten — this means upgrading the
    package upgrades the skill on the next CLI invocation, with no manual
    `--install-skill` step. Any I/O error is swallowed.
    """
    claude_dir = Path.home() / ".claude"
    if not claude_dir.exists():
        return
    skill_md = claude_dir / "skills" / "open-image" / "SKILL.md"
    desired = _render_skill_md()
    try:
        if skill_md.exists() and skill_md.read_text(encoding="utf-8") == desired:
            return
        skill_md.parent.mkdir(parents=True, exist_ok=True)
        skill_md.write_text(desired, encoding="utf-8")
    except OSError:
        pass


def reinstall_skill_force() -> None:
    """Force re-install the Claude Code skill (always overwrites).

    Aborts with a clear error if ~/.claude is missing — this is an
    explicit action, so failing loudly is correct.
    """
    claude_dir = Path.home() / ".claude"
    if not claude_dir.exists():
        sys.exit(
            "ERROR: ~/.claude not found. Install Claude Code first, "
            "then re-run `open-image --install-skill`."
        )
    skill_md = claude_dir / "skills" / "open-image" / "SKILL.md"
    skill_md.parent.mkdir(parents=True, exist_ok=True)
    skill_md.write_text(_render_skill_md(), encoding="utf-8")
    print(f"Skill installed: {skill_md.resolve()}")


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


def save_images(response, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    saved: list[Path] = []
    for item in response.data:
        uid = uuid.uuid4().hex[:8]
        fpath = out_dir / f"{timestamp}-{uid}.png"
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

    out_dir = Path(args.out_dir)
    try:
        paths = save_images(response, out_dir)
    except PermissionError as e:
        sys.exit(f"ERROR: Cannot write to output dir: {e}")

    prune_old_images(out_dir, args.keep)

    for p in paths:
        print(p)


if __name__ == "__main__":
    main()
