---
phase: 1
title: Implement --style + aspect flags in gen.py
status: completed
priority: high
effort: 1h
---

# Phase 1 — Implement `--style` + aspect flags in `gen.py`

## Context links

- Plan: `../plan.md`
- Brainstorm: `../../reports/brainstorm-260427-1941-style-presets-and-aspect-shortcuts.md`
- Source file: `D:/WORKSPACES/open-image/gen.py` (226 dòng hiện tại)

## Overview

Thêm 5 flag mới vào `gen.py`:
- `--style <name>` (8 curated)
- `--list-styles` (info-only printer)
- `--portrait` / `--landscape` / `--square` (mutually-exclusive group)

Plus 2 dict + 1 helper function. Tổng cộng ~40 dòng. `gen.py` sau ~266 dòng → vẫn dưới 350 cap.

## Key insights

- Style fragments dùng generic wording (tránh "Studio Ghibli", "Blade Runner" → copyright noise).
- Aspect flag inject `size` vào extra dict TRƯỚC khi gọi API, KHÔNG override nếu user pass `--extra '{"size":...}'`.
- Slug filename phải derive từ **prompt gốc** (call `slugify(prompt)` BEFORE `apply_style()`).

## Requirements

### Functional

1. `--style 3d-render` → API nhận `"<prompt>, 3D render, octane render, hyperrealistic detail, 8k"`.
2. `--style unknown-name` → `sys.exit("ERROR: Unknown style 'unknown-name'. Run --list-styles.")` exit non-zero.
3. `--list-styles` → in 2-column table (NAME | FRAGMENT) giống `print_models_table()`, exit 0.
4. `--portrait` → inject `extra["size"] = "1024x1792"` chỉ khi `"size" not in extra`.
5. `--portrait --extra '{"size":"512x512"}'` → API nhận `size=512x512` (extra wins).
6. `--portrait --landscape` → argparse error (mutually exclusive).
7. Filename slug derive từ prompt gốc (không có style fragment).

### Non-functional

- Stdlib-only (không thêm dependency).
- Backward compatible — chạy `open-image --prompt "..."` không có flag mới phải hoạt động y như v0.4.0.

## Architecture

```
parse_args()
  ├── --style          → args.style: str | None
  ├── --list-styles    → args.list_styles: bool
  └── mutually_exclusive_group:
        --portrait, --landscape, --square → args.aspect: str | None  (custom dest)

main()
  ├── if args.list_styles: print_styles_table(); return
  ├── prompt = resolve_prompt(args)             # original prompt
  ├── slug = slugify(args.name) if args.name else slugify(prompt)   # ← BEFORE apply_style
  ├── augmented = apply_style(prompt, args.style)                   # validate + append
  ├── extra = json.loads(args.extra)
  ├── extra = merge_aspect_into_extra(extra, args.aspect)           # ← BEFORE API call
  └── client.images.generate(model=..., prompt=augmented, **extra)
```

## Related code files

**Modify:**
- `gen.py` — add KNOWN_STYLES, ASPECT_SIZES, apply_style(), print_styles_table(), merge_aspect_into_extra(), parse_args() update, main() reorder

**Read for context:**
- `gen.py:35-40` — KNOWN_MODELS pattern (template for KNOWN_STYLES)
- `gen.py:60-68` — print_models_table (template for print_styles_table)
- `gen.py:43-57` — parse_args (where to add new flags)
- `gen.py:177-221` — main (where to inject style + aspect logic)

## Implementation steps

### 1. Add KNOWN_STYLES + ASPECT_SIZES dicts (after KNOWN_MODELS, ~line 40)

```python
# Curated prompt fragments appended to user prompt via --style.
# HARD LIMIT: 10 styles. More styles → users should use --extra or fork.
KNOWN_STYLES: dict[str, str] = {
    "3d-render":    "3D render, octane render, hyperrealistic detail, 8k",
    "anime":        "anime style, cel-shaded, vibrant colors, Japanese animation",
    "watercolor":   "watercolor painting, soft edges, paper texture, wet-on-wet",
    "cyberpunk":    "cyberpunk aesthetic, neon lights, rain-slicked streets, neo-noir sci-fi mood",
    "photoreal":    "photorealistic, DSLR, 50mm lens, natural lighting, high detail",
    "sketch":       "pencil sketch, hand-drawn, cross-hatching, white background",
    "oil-painting": "oil painting, thick brushstrokes, classical composition, Rembrandt lighting",
    "minimalist":   "minimalist design, clean lines, negative space, single subject focus",
}

# Aspect ratio shortcuts → size string forwarded to API. Universal across
# gpt-image-* and dall-e-3. dall-e-2 will surface API error for non-square sizes.
ASPECT_SIZES: dict[str, str] = {
    "portrait":  "1024x1792",
    "landscape": "1792x1024",
    "square":    "1024x1024",
}
```

### 2. Add `apply_style()` helper

```python
def apply_style(prompt: str, style: str | None) -> str:
    """Append style fragment to prompt. Returns prompt unchanged if style is None."""
    if style is None:
        return prompt
    fragment = KNOWN_STYLES.get(style)
    if fragment is None:
        sys.exit(
            f"ERROR: Unknown style '{style}'. Run --list-styles to see options."
        )
    return f"{prompt}, {fragment}"
```

### 3. Add `merge_aspect_into_extra()` helper

```python
def merge_aspect_into_extra(extra: dict, aspect: str | None) -> dict:
    """Inject size from aspect shortcut. User's explicit --extra size wins."""
    if aspect and "size" not in extra:
        extra["size"] = ASPECT_SIZES[aspect]
    return extra
```

### 4. Add `print_styles_table()` printer

```python
def print_styles_table() -> None:
    """Print known styles with full fragments in an aligned 2-column table."""
    width = max(len(name) for name in KNOWN_STYLES) + 2
    print(f"{'STYLE'.ljust(width)}FRAGMENT (appended to prompt)")
    print(f"{'-' * (width - 2)}  {'-' * 60}")
    for name, frag in KNOWN_STYLES.items():
        print(f"{name.ljust(width)}{frag}")
    print()
    print("Usage: open-image --style <name> --prompt \"...\"")
```

### 5. Update `parse_args()` — add 5 flags

```python
p.add_argument("--style", help=f"Append a curated style fragment. One of: {', '.join(KNOWN_STYLES)}.")
p.add_argument("--list-styles", action="store_true", help="List known styles with fragments, then exit.")
aspect_group = p.add_mutually_exclusive_group()
aspect_group.add_argument("--portrait",  action="store_const", dest="aspect", const="portrait",  help="Shortcut for size=1024x1792.")
aspect_group.add_argument("--landscape", action="store_const", dest="aspect", const="landscape", help="Shortcut for size=1792x1024.")
aspect_group.add_argument("--square",    action="store_const", dest="aspect", const="square",    help="Shortcut for size=1024x1024.")
```

### 6. Update `main()` — handle --list-styles + style/aspect logic

```python
if args.list_styles:
    print_styles_table()
    return

# ... existing api_key + extra parsing ...

extra = merge_aspect_into_extra(extra, args.aspect)

# ... existing client = OpenAI(...) ...

augmented_prompt = apply_style(prompt, args.style)

try:
    response = client.images.generate(model=args.model, prompt=augmented_prompt, **extra)
except Exception as e:
    sys.exit(f"ERROR: API call failed: {e}")

slug = slugify(args.name) if args.name else slugify(prompt)  # original prompt
```

## Todo list

- [x] Add `KNOWN_STYLES` + `ASPECT_SIZES` dicts
- [x] Implement `apply_style()`
- [x] Implement `merge_aspect_into_extra()`
- [x] Implement `print_styles_table()`
- [x] Update `parse_args()` — 5 new flags
- [x] Update `main()` — list-styles handler + style/aspect call sites
- [x] Verify slug derives from original prompt (not augmented)
- [x] `python -c "import gen; gen.parse_args.__doc__"` — syntax check
- [x] Manual smoke: `open-image --list-styles` → table prints
- [x] Manual smoke: `open-image --style 3d-render --prompt "a cat"` → image generated, filename uses original slug

## Success criteria

- `gen.py` < 350 dòng total.
- `python gen.py --list-styles` exits 0, prints 8 styles.
- `python gen.py --style invalid --prompt "x"` exits non-zero with helpful message.
- `python gen.py --portrait --landscape --prompt "x"` → argparse error.
- Backward compat: `python gen.py --prompt "..."` works as before.

## Risks

| Risk | Mitigation |
|---|---|
| `dest="aspect"` collision với existing arg | grep `dest=` in gen.py — none currently. Safe. |
| `args.aspect` defaults `None` properly when no flag | `add_mutually_exclusive_group` + `action="store_const"` → None default if no flag passed. Confirmed by argparse behavior. |
| Style validation breaks existing CI tests | New flag, doesn't affect existing flow. Existing tests unchanged. |

## Security considerations

- N/A — no new I/O surface, no new auth path.
- Style fragments hardcoded (not user input from external file) → no injection risk.

## Next steps

→ Phase 2: Update skill template + write 5 unit tests covering style/aspect logic.
