---
title: Style Presets + Aspect Shortcuts
slug: style-presets-and-aspect-shortcuts
date: 2026-04-27 19:41
status: pending
mode: fast
target_version: v0.5.0
blockedBy: []
blocks: []
---

# Style Presets + Aspect Shortcuts (open-image v0.5.0)

Thêm `--style <name>` (8 curated prompt presets) + `--portrait/--landscape/--square` (aspect shortcuts) cho `open-image` CLI. Single-file philosophy giữ nguyên — tất cả thay đổi nằm trong `gen.py` + `open_image_skill.py` + `test_gen.py` + 3 file docs/release.

## Context

- **Brainstorm report:** `plans/reports/brainstorm-260427-1941-style-presets-and-aspect-shortcuts.md`
- **Stack:** Python 3.10+, stdlib (argparse) + openai SDK, pytest dev dep
- **Scope:** ~40 dòng `gen.py`, +20 dòng skill template, +30 dòng tests, +30 dòng README, +10 dòng CHANGELOG, 1-line pyproject bump
- **Constraints:** KISS/YAGNI/DRY · single-file philosophy · `gen.py < 350 dòng` · stdlib-only · không runtime deps mới · 12 CI jobs xanh trước tag

## Phases

| # | Phase | Status | Files |
|---|---|---|---|
| 1 | Implement `--style` + aspect flags in `gen.py` | pending | `gen.py` |
| 2 | Update skill template + write unit tests | pending | `open_image_skill.py`, `test_gen.py` |
| 3 | Docs + release v0.5.0 | pending | `README.md`, `CHANGELOG.md`, `pyproject.toml`, `gh release` |

## Key constraints (DO NOT VIOLATE)

- **Hard limit 10 styles forever** — nếu user xin thêm → fork hoặc dùng `--extra`. Bloat cap.
- **Slug derive từ prompt GỐC**, không phải augmented (tránh filename siêu dài).
- **`--extra '{"size":...}'` thắng aspect flag** (explicit > implicit).
- **Style validation client-side hợp lệ** — style KHÔNG phải API param, không vi phạm "API source of truth".
- **KHÔNG làm `--hd`** — quality model-specific, wrap = false abstraction.

## Success criteria

- 12/12 CI jobs xanh (Linux/macOS/Windows × Py 3.10-3.13).
- 5 new unit tests pass.
- v0.5.0 live trên PyPI sau `gh release create v0.5.0`.
- SKILL.md auto-sync sau next Python startup post-upgrade.
- README + CHANGELOG ghi rõ feature + flag table.
