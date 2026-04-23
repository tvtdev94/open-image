# open-image

Tiny CLI for OpenAI image generation. Prompt in, PNG out. Model-agnostic.

- **One file, ~120 lines.** Pure stdlib + `openai` SDK.
- **Model-agnostic.** `--model` is a flag, not a constant. Swap `dall-e-3` → `gpt-image-2` → whatever ships next without editing code.
- **`--extra` escape hatch.** Forward any API parameter as JSON (`size`, `quality`, `style`, `n`, `response_format`, …). No client-side validation gets in your way.
- **Four prompt inputs.** `--prompt`, `--prompt-file`, stdin pipe, or `$EDITOR` fallback.

## Samples

Generated with `dall-e-3` at `quality=hd`:

| `assets/sample-bee-lotus.png` | `assets/sample-cyberpunk-market.png` |
|---|---|
| ![bee on lotus](assets/sample-bee-lotus.png) | ![cyberpunk hanoi](assets/sample-cyberpunk-market.png) |

## Install

```bash
pip install open-image
```

Or from source:

```bash
git clone https://github.com/tvtdev94/open-image
cd open-image
pip install -e .
```

## Setup

Set your OpenAI API key (needs image-generation credit):

```bash
export OPENAI_API_KEY=sk-...
# or pass --api-key on every call
```

## Usage

```bash
# 1. Inline prompt
open-image --prompt "a red fox in a snowy forest, cinematic"

# 2. Prompt from file
open-image --prompt-file prompts/scene.txt

# 3. Pipe from stdin
echo "a blue cat reading a book" | open-image

# 4. No args in a TTY — opens $EDITOR (notepad on Windows, vi otherwise)
open-image
```

Output: absolute path of the PNG(s) printed to stdout, one per line. Default save directory: `./output/{YYYYMMDD-HHMMSS}-{uuid8}.png`.

## Flags

| Flag | Default | Purpose |
|---|---|---|
| `--prompt` | — | Inline prompt text |
| `--prompt-file` | — | Path to a file containing the prompt |
| `--model` | `gpt-image-2` | Any OpenAI image model (`dall-e-3`, `dall-e-2`, `gpt-image-1`, …) |
| `--extra` | `{}` | JSON dict forwarded to `images.generate` |
| `--out-dir` | `./output` | Where to save PNGs (auto-created) |
| `--api-key` | `$OPENAI_API_KEY` | Override via flag if not in env |

## Forwarding model-specific params

Any keyword the API accepts, `--extra` forwards:

```bash
open-image \
  --model dall-e-3 \
  --extra '{"size":"1792x1024","quality":"hd","style":"vivid"}' \
  --prompt "a lone surfer at dawn, Hokusai woodblock style"

open-image \
  --model dall-e-2 \
  --extra '{"size":"512x512","n":4}' \
  --prompt "abstract watercolor"
```

The CLI does not validate these — the API does. If a parameter is wrong the API error surfaces verbatim, which is exactly what you want for debugging.

## Error handling

- No API key → exit with actionable message.
- `--extra` not valid JSON → exit with parser error.
- Empty prompt → exit.
- API failure (auth, model access, invalid params) → exit with the API error string.

## Model notes

- **`gpt-image-2`** requires an organization verification step on the OpenAI dashboard. First call returns 403 until verified.
- **`dall-e-3`** works out of the box. Always set `response_format: "b64_json"` in `--extra` if you want to avoid a short-lived URL fetch; the tool handles both, but b64 is more robust.
- **`dall-e-2`** supports `n > 1` and smaller sizes, ideal for batch ideation.

## License

MIT © 2026 tvtdev94
