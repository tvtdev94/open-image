"""open-image Claude Code skill: template + silent installer.

Pure stdlib (+ importlib.metadata) so this module can be imported during
Python's site initialization via the `open-image-skill.pth` mechanism
without pulling in the OpenAI SDK or other heavy dependencies.

Public surface:
- __version__              CLI version (sourced from package metadata)
- SKILL_MD_TEMPLATE        raw template string with `{version}` placeholder
- maybe_install_skill_silently()   sync skill to current version, no-op on error
- reinstall_skill_force()  explicit force install, aborts loudly on error
"""

import sys
from pathlib import Path

try:
    from importlib.metadata import version as _pkg_version
    __version__ = _pkg_version("open-image")
except Exception:
    __version__ = "dev"


SKILL_MD_TEMPLATE = """\
---
name: open-image
description: Generate PNG images via OpenAI image API. Use when user asks to generate an image, create a picture, draw, make an image, or pipes prompt text. CLI command `open-image` outputs absolute file paths to stdout.
---
<!-- Auto-installed by open-image CLI v{version}. Sync'd on each Python startup. -->

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

# Custom filename slug (otherwise auto-derived from prompt)
open-image --prompt "a red fox in snow" --name "fox-portrait"

# List known models with notes
open-image --list-models
```

## Models supported

Run `open-image --list-models` for the current list with notes. The CLI is model-agnostic — `--model` accepts any string and unknown models are forwarded to the API as-is, so new OpenAI image models work without an upgrade.

## Output

- PNGs saved to `./output/{YYYYMMDD-HHMMSS}-{slug}-{uuid8}.png` where `{slug}` is auto-derived from the prompt (kebab-case, ASCII-folded, max 40 chars). Pass `--name "my-slug"` to override.
- Override directory with `--out-dir`
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
3. Use `--out-dir ./task-XXX/` to keep per-task outputs separate; pass `--name <slug>` for predictable filenames when scripting
4. For deterministic offline storage with `dall-e-3`, pass `--extra '{"response_format":"b64_json"}'`
5. Check exit code — non-zero means generation failed
"""


def _render_skill_md() -> str:
    """Return the SKILL.md template with the current CLI version stamped in."""
    return SKILL_MD_TEMPLATE.replace("{version}", __version__)


def maybe_install_skill_silently() -> None:
    """Sync the Claude Code skill (silent, idempotent).

    No-ops if ~/.claude is absent (user is not running Claude Code) or the
    on-disk content already matches the desired template (already in sync).
    Otherwise the skill is rewritten — so upgrading the package upgrades
    the skill on the next Python startup, with zero manual steps. Any I/O
    error is swallowed so this can run safely during site initialization.
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
    explicit user action, so failing loudly is correct.
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
