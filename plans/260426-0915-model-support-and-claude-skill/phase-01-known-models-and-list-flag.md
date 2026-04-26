# Phase 1 — KNOWN_MODELS + `--list-models` Flag

## Context Links
- **Brainstorm:** `plans/reports/brainstorm-260426-0915-model-support-and-claude-skill.md` — Section 5.1
- **Target file:** `gen.py`

## Overview
- **Priority:** Medium
- **Status:** pending
- **Description:** Thêm bảng metadata info-only cho models OpenAI đã biết + flag `--list-models` để in bảng. Không tham gia call args, không auto-merge, không warn unknown — giữ "API là source of truth".

## Key Insights
- Hiện `--model` là string tự do, forward thẳng. KNOWN_MODELS chỉ phục vụ `--list-models` (info), không thay đổi behavior gọi API.
- Forward unknown model **không** warn (giữ stderr sạch, pipe-friendly).
- Skill markdown sẽ tham chiếu `--list-models` thay vì hardcode model list → giảm stale risk.

## Requirements

### Functional
- `KNOWN_MODELS: dict[str, str]` chứa 4 models: `gpt-image-2`, `gpt-image-1`, `dall-e-3`, `dall-e-2`. Value là 1-2 câu notes (size, n constraint, response_format, special params).
- `--list-models` flag: in bảng aligned 2 cột (model_id | notes), exit 0, **không** gọi OpenAI API.
- Khi `--list-models` được pass, các flag khác (`--prompt`, `--api-key`, ...) bị bỏ qua.
- Model lạ không trong KNOWN_MODELS: forward as-is, không warn, không error.

### Non-functional
- Không thêm dependency.
- Không phá backward compat (`open-image --prompt "..."` vẫn work y cũ).
- KNOWN_MODELS là module-level constant, dễ update khi OpenAI ra model mới.

## Architecture

```
gen.py
├── KNOWN_MODELS dict           ← new (~10 dòng)
├── parse_args()                ← add --list-models flag
├── print_models_table()        ← new (~10 dòng)
└── main()                      ← branch sớm nếu args.list_models
```

## Related Code Files
- **Modify:** `gen.py`
- **Read:** `gen.py` hiện tại (135 dòng) để hiểu argparse structure

## Implementation Steps

### Step 1: Define KNOWN_MODELS
Thêm sau imports, trước `parse_args`:
```python
KNOWN_MODELS: dict[str, str] = {
    "gpt-image-2": "Default. Requires org verification on OpenAI dashboard. Returns b64_json.",
    "gpt-image-1": "Newer GPT image model. Supports input_fidelity, transparency, output_format params.",
    "dall-e-3":    "n=1 only. Sizes: 1024x1024 | 1792x1024 | 1024x1792. quality: standard|hd. style: vivid|natural. Pass response_format=b64_json via --extra for offline storage.",
    "dall-e-2":    "n>1 supported. Sizes: 256x256 | 512x512 | 1024x1024.",
}
```

### Step 2: Add `--list-models` flag in `parse_args`
```python
p.add_argument(
    "--list-models",
    action="store_true",
    help="List known OpenAI image models with notes, then exit.",
)
```

### Step 3: Implement `print_models_table()`
```python
def print_models_table() -> None:
    """Print known models with notes in aligned 2-column format."""
    width = max(len(name) for name in KNOWN_MODELS) + 2
    print(f"{'MODEL'.ljust(width)}NOTES")
    print(f"{'-' * (width - 2)}  {'-' * 60}")
    for name, notes in KNOWN_MODELS.items():
        print(f"{name.ljust(width)}{notes}")
    print()
    print("Note: --model accepts any string. Unknown models forwarded to API as-is.")
```

### Step 4: Branch in `main()`
Đầu `main()`, sau `args = parse_args()`:
```python
if args.list_models:
    print_models_table()
    return
```

## Todo List
- [ ] Add `KNOWN_MODELS` dict at module level
- [ ] Add `--list-models` flag to argparse
- [ ] Implement `print_models_table()`
- [ ] Branch early in `main()` for `--list-models`
- [ ] Run `python gen.py --list-models` → verify output table
- [ ] Run `python gen.py --help` → verify new flag in help text
- [ ] Run `python gen.py --model unknown-xyz --prompt "test"` (without API key) → verify forwards to API call attempt (will fail at auth, that's OK)

## Success Criteria
- `python gen.py --list-models` in 4 models đủ + footer note, exit 0
- Output bảng aligned, không lỗi format
- `python gen.py --help` show `--list-models` in help text
- Existing CLI behavior không thay đổi (regression check)
- File `gen.py` vẫn compile sạch (`python -m py_compile gen.py`)

## Risk Assessment
- **Risk:** KNOWN_MODELS notes stale khi OpenAI ra model mới. **Mitigation:** Notes là info, sai không break logic. PR community + bump patch version.
- **Risk:** User có model whitelist khác → bị confused vì list không exhaustive. **Mitigation:** Footer note rõ "any string forwarded as-is".

## Security Considerations
Không có — pure print operation, không I/O ngoài.

## Next Steps
→ Phase 2 (Skill template + auto-install)
