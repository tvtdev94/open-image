---
title: Model Support + Claude Code Skill Auto-Install
slug: model-support-and-claude-skill
date: 2026-04-26 09:15
status: completed
mode: fast
blockedBy: []
blocks: []
---

# Model Support + Claude Code Skill Auto-Install (open-image v0.3)

Cải thiện DX quanh `--model` (info-only KNOWN_MODELS + `--list-models`) và auto-install Claude Code skill (silent first-run + manual `--install-skill` re-install).

## Context

- **Brainstorm report:** `plans/reports/brainstorm-260426-0915-model-support-and-claude-skill.md`
- **Stack:** Python 3.10+, `openai` SDK, argparse stdlib, pytest (dev)
- **Scope:** Update `gen.py` (~135 → ~230 dòng, one-file), `pyproject.toml`, `README.md`, new `test_gen.py`
- **Constraints:** KISS/YAGNI/DRY · giữ one-file philosophy · API là source of truth · không runtime deps mới

## Phases

| # | Phase | Status | File |
|---|---|---|---|
| 1 | KNOWN_MODELS + `--list-models` flag | done | [phase-01-known-models-and-list-flag.md](phase-01-known-models-and-list-flag.md) |
| 2 | Skill template + auto-install + `--install-skill` | done | [phase-02-skill-install-mechanism.md](phase-02-skill-install-mechanism.md) |
| 3 | README + version bump + Philosophy reframe | done | [phase-03-readme-and-version-bump.md](phase-03-readme-and-version-bump.md) |
| 4 | Tests (`test_gen.py` + pytest dev dep) | done — 17/17 pass | [phase-04-tests.md](phase-04-tests.md) |

## Key Design (chốt từ brainstorm)

- **KNOWN_MODELS info-only:** `dict[str, str]` (model_id → notes). Không tham gia call args, không auto-merge defaults, không warn unknown model. Power `--list-models`.
- **Auto-install skill:** silent first-run đầu `main()`, chỉ install nếu `~/.claude/` tồn tại VÀ `SKILL.md` chưa có. Mọi exception swallow.
- **Manual `--install-skill`:** force overwrite, abort nếu `~/.claude/` không có (explicit action).
- **SKILL.md embedded** trong `gen.py` dạng triple-quoted Python literal (~80 dòng markdown).
- **Triết lý reframe:** "no runtime plugins. Optional Claude Code skill is just markdown."

## Dependencies

- Python >= 3.10 (existing)
- `openai>=1.0.0` (existing)
- `pytest>=7.0` (new, optional dev)

## Acceptance Criteria (overview)

- `--list-models` in bảng 4 models, exit 0, không gọi API
- Auto-install không phá user workflow (silent fail OK)
- Manual `--install-skill` overwrite + in path đã ghi
- `pytest` pass tất cả tests
- README updated với bảng models + Claude Code integration section
- Version bump 0.2.0 → 0.3.0
