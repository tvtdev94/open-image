<p align="center">
  <img src="https://raw.githubusercontent.com/tvtdev94/open-image/main/assets/logo-mark.png" alt="open-image" width="140" />
</p>

<h1 align="center">open-image</h1>

<p align="center">
  <b>Tiny CLI for OpenAI image generation. Prompt in, PNG out. Model-agnostic.</b>
</p>

<p align="center">
  <a href="https://pypi.org/project/open-image/"><img src="https://img.shields.io/pypi/v/open-image.svg?color=22d3ee&label=pypi" alt="PyPI version" /></a>
  <a href="https://pypi.org/project/open-image/"><img src="https://img.shields.io/pypi/pyversions/open-image.svg?color=8b5cf6" alt="Python versions" /></a>
  <a href="https://github.com/tvtdev94/open-image/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-22c55e.svg" alt="MIT license" /></a>
  <a href="https://github.com/tvtdev94/open-image/stargazers"><img src="https://img.shields.io/github/stars/tvtdev94/open-image?style=flat&color=d97706" alt="GitHub stars" /></a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/tvtdev94/open-image/main/assets/hero.png" alt="open-image hero" width="100%" />
</p>

---

## Why another CLI?

Every serious image-gen workflow needs a **stable, forgettable command** — one you can pipe into, script around, and re-run six months later without rewriting. The official SDKs are fine for apps; they're heavy for "just give me a PNG."

`open-image` is **~340 lines of Python, pure stdlib + `openai`** — one file for the CLI (`gen.py`), two tiny stdlib-only helpers for the Claude Code skill. No framework, no config, no lock-in to a specific model.

```bash
pip install open-image
export OPENAI_API_KEY=sk-...
open-image --prompt "a red fox in a snowy forest, cinematic"
# → /abs/path/output/20260423-223012-a1b2c3d4.png
```

That's it.

---

## Features

### Four ways to feed a prompt

<p align="center">
  <img src="https://raw.githubusercontent.com/tvtdev94/open-image/main/assets/feature-four-inputs.png" alt="four input methods" width="85%" />
</p>

| Method | Example |
|---|---|
| **Inline** | `open-image --prompt "a red fox in snow"` |
| **File**   | `open-image --prompt-file prompts/scene.txt` |
| **Stdin**  | `echo "a blue cat" \| open-image` |
| **Editor** | `open-image` (no args in a TTY → opens `$EDITOR`, or `notepad` on Windows, `vi` otherwise) |

The resolver picks them in that order. Lines starting with `#` in the editor buffer are stripped — write notes to yourself without polluting the prompt.

---

### Model-agnostic by design

<p align="center">
  <img src="https://raw.githubusercontent.com/tvtdev94/open-image/main/assets/feature-model-agnostic.png" alt="model-agnostic design" width="85%" />
</p>

`--model` is a **flag, not a constant**. The day a new image model ships, swap the string — no code change, no version bump, no fork:

```bash
open-image --model gpt-image-2   --prompt "..."   # default; requires org verification
open-image --model gpt-image-1   --prompt "..."   # transparency, output_format support
open-image --model future-model  --prompt "..."   # whenever it arrives
```

Default is `gpt-image-2`. Change per call, or `alias open-image='open-image --model gpt-image-1'` in your shell if you prefer a different default.

---

### `--extra` escape hatch

<p align="center">
  <img src="https://raw.githubusercontent.com/tvtdev94/open-image/main/assets/feature-extra-param.png" alt="extra param forwarding" width="85%" />
</p>

Any keyword the API accepts, `--extra` forwards verbatim to `openai.images.generate(**params)`. Zero client-side validation — the API is the source of truth:

```bash
open-image \
  --model gpt-image-2 \
  --extra '{"size":"1024x1024","quality":"high"}' \
  --prompt "a lone surfer at dawn, Hokusai woodblock style"

open-image \
  --model gpt-image-1 \
  --extra '{"size":"1024x1024","output_format":"png","transparency":true}' \
  --prompt "a minimalist cat icon on a transparent background"
```

If you pass a wrong key, the API error surfaces verbatim — exactly what you want for debugging. No wrapper in the way.

---

## Install

### From PyPI (recommended)

```bash
pip install open-image
```

### With pipx (isolated global command)

```bash
pipx install open-image
```

### From source

```bash
git clone https://github.com/tvtdev94/open-image
cd open-image
pip install -e .
```

---

## Setup

Set your OpenAI API key (must have image-generation credit):

```bash
# Option A — environment variable (recommended)
export OPENAI_API_KEY=sk-...

# Option B — per-call flag
open-image --api-key sk-... --prompt "..."
```

---

## Flags

| Flag | Default | Purpose |
|---|---|---|
| `--prompt` | — | Inline prompt text |
| `--prompt-file` | — | Path to a file containing the prompt |
| `--model` | `gpt-image-2` | Any OpenAI image model (`gpt-image-2`, `gpt-image-1`, `dall-e-3`, `dall-e-2`, …) |
| `--extra` | `{}` | JSON object forwarded to `images.generate` |
| `--out-dir` | `./output` | Where to save PNGs (auto-created) |
| `--api-key` | `$OPENAI_API_KEY` | Override via flag if not in env |
| `--keep` | `50` | Keep only N newest PNGs in `--out-dir` after save; `0` disables pruning |
| `--list-models` | — | List known OpenAI image models with notes, then exit |
| `--install-skill` | — | Re-install Claude Code skill at `~/.claude/skills/open-image/` (overwrites) |

---

## Output

```
./output/{YYYYMMDD-HHMMSS}-{uuid8}.png
```

One PNG per `response.data` item (so `n=4` → four files). Absolute path(s) printed to stdout, one per line — friendly to `xargs`, `fzf`, `wl-copy`, whatever you pipe into.

```bash
open-image --prompt "a corgi" | tee -a log.txt
open-image --prompt "a corgi" | head -n1 | xargs -I{} open {}    # macOS preview
```

---

## Gallery

All generated by `open-image` with `gpt-image-2`:

<p align="center">
  <img src="https://raw.githubusercontent.com/tvtdev94/open-image/main/assets/sample-triptych.png" alt="sample gallery" width="100%" />
</p>

<table>
  <tr>
    <td><img src="https://raw.githubusercontent.com/tvtdev94/open-image/main/assets/sample-bee-lotus.png" alt="bee on a lotus at sunrise" /></td>
    <td><img src="https://raw.githubusercontent.com/tvtdev94/open-image/main/assets/sample-cyberpunk-market.png" alt="cyberpunk Hanoi night market" /></td>
  </tr>
  <tr>
    <td align="center"><sub><i>A close-up cinematic macro of a bee hovering over a lotus at sunrise.</i></sub></td>
    <td align="center"><sub><i>A bustling night market in a cyberpunk Hanoi alleyway.</i></sub></td>
  </tr>
</table>

---

## Error handling

Every error path exits with a clear, actionable message:

- **No API key** → `ERROR: No API key. Set OPENAI_API_KEY env or pass --api-key.`
- **`--extra` not valid JSON** → parser error with column offset
- **Empty prompt** → `ERROR: Empty prompt.`
- **API failure** (auth, model access, invalid params) → API error string forwarded verbatim
- **Un-writable `--out-dir`** → `PermissionError` surfaced with the path

---

## Models supported

The CLI is model-agnostic — `--model` accepts any string. These are the models known at write time; pass any future model ID without a code change.

| Model | Notes |
|---|---|
| `gpt-image-2` | Default. Requires org verification on OpenAI dashboard. Returns `b64_json`. |
| `gpt-image-1` | Newer GPT image model. Supports `input_fidelity`, `transparency`, `output_format`. |
| `dall-e-3` | `n=1` only. Sizes: `1024x1024` / `1792x1024` / `1024x1792`. `quality`: `standard` / `hd`. `style`: `vivid` / `natural`. Pass `response_format=b64_json` via `--extra` for offline storage. |
| `dall-e-2` | `n>1` supported. Sizes: `256x256` / `512x512` / `1024x1024`. |

Run `open-image --list-models` to print this table at any time.

---

## Claude Code integration

If you use [Claude Code](https://claude.com/claude-code), `open-image` ships a Claude skill that teaches the agent how to use this CLI — no manual prompt setup.

- **Zero-step install:** `pip install open-image` is enough. On the next Python startup (any Python invocation on that machine — no CLI required), the skill is silently written to `~/.claude/skills/open-image/SKILL.md`. Skipped entirely if `~/.claude/` doesn't exist.
- **Auto-update on upgrade:** `pip install -U open-image` → next Python startup → skill content auto-syncs to the new version. No manual step.
- **Force re-install** (rarely needed, e.g. after editing the skill): `open-image --install-skill`.

Once installed, Claude Code knows when to call `open-image`, which models exist, how `--extra` works, and how to capture the stdout paths.

#### How it works (transparency)

`open-image` ships a tiny `.pth` file to your Python `site-packages/` so the skill is synced on every Python startup (idempotent — only writes when content changes). Cost: a couple of `stat()` calls per Python startup, sub-millisecond. Removing the package via `pip uninstall open-image` removes the `.pth` and stops the sync.

---

## Philosophy

Three principles:

- **YAGNI** — no MCP server, no HTTP wrapper, no runtime plugins. The optional Claude Code skill is just markdown — Claude reads it, no daemon, no IPC. If your agent has a shell, it can use this.
- **KISS** — argparse + stdlib + one SDK call. Zero abstractions between you and the API.
- **DRY** — `--extra` means the tool never needs a new flag per new API param.

The whole tool fits in your head. When a future model adds a parameter, you already know how to use it.

---

## License

MIT © 2026 [tvtdev94](https://github.com/tvtdev94)
