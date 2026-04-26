# Phase 1 — CHANGELOG.md + README .pth Transparency

## Context Links
- **Brainstorm:** `plans/reports/brainstorm-260426-1144-release-flow-and-security-hardening.md` § 4
- **Files:** `CHANGELOG.md` (NEW), `README.md` (EDIT)

## Overview
- **Priority:** Medium
- **Status:** pending
- **Description:** Tạo CHANGELOG cover 4 versions phát hành. README ghi rõ `.pth` mechanism để user kỹ tính có context.

## Requirements

### Functional
- `CHANGELOG.md` Keep a Changelog format với 4 entries: 0.2.0, 0.3.0, 0.3.1, 0.3.2
- Mỗi entry: date, sections Added/Changed/Fixed/Removed (chỉ section nào có nội dung)
- README thêm note ngắn (~5 dòng) trong "Claude Code integration" section explain:
  - Auto-install qua `.pth` mechanism
  - Chạy mỗi Python startup, ~µs cost
  - Có thể remove bằng cách uninstall package

### Non-functional
- Concise — không spam
- Tone consistent với README hiện tại

## Implementation Steps

### Step 1: Tạo CHANGELOG.md với 4 entries

Outline:
```markdown
# Changelog

All notable changes documented here. Follows [Keep a Changelog](https://keepachangelog.com/).

## [0.3.2] — 2026-04-26
### Added
- Auto-install Claude Code skill via `.pth` mechanism — no CLI invocation needed after `pip install`
- New modules: `open_image_skill.py` (stdlib-only installer), `_open_image_skill_bootstrap.py`
- `setup.py` shim ships `.pth` to wheel purelib root

### Changed
- Skill auto-syncs on every Python startup (idempotent content hash)
- `gen.py` now re-exports skill API from `open_image_skill` module

## [0.3.1] — 2026-04-26
### Added
- Skill auto-update on package upgrade — content sync via version stamp
- Tests for upgrade + idempotency behaviors

### Changed
- README + skill examples lead with `gpt-image-2` (default) and `gpt-image-1`

## [0.3.0] — 2026-04-26
### Added
- `KNOWN_MODELS` info-only registry (`gpt-image-1/2`, `dall-e-2/3`) + `--list-models` flag
- Auto-install Claude Code skill at `~/.claude/skills/open-image/SKILL.md` on first run
- `--install-skill` flag for forced re-install
- pytest dev dependency + 17-test suite

## [0.2.0] — 2026-04-23
### Added
- `--keep` flag: prune old PNGs in `--out-dir` after save (default 50, `0` disables)

## [0.1.0] — 2026-04-23
### Added
- Initial release. Tiny CLI for OpenAI image generation. Prompt in, PNG out.
- Four prompt input methods: `--prompt`, `--prompt-file`, stdin, `$EDITOR`
- Model-agnostic via `--model` flag
- `--extra` JSON escape hatch for arbitrary API params
```

### Step 2: README — thêm transparency note vào "Claude Code integration" section

Sau đoạn explain auto-install, thêm:
```markdown
### How it works (transparency)

`open-image` ships a tiny `.pth` file to your Python `site-packages/` so the skill is synced on every Python startup (idempotent — only writes when content changes). Cost: ~µs per startup. Removing the package via `pip uninstall open-image` removes the `.pth` and stops the auto-sync.
```

## Todo List
- [ ] Create `CHANGELOG.md` with 5 version entries (0.1.0 → 0.3.2)
- [ ] Edit README "Claude Code integration" section, append transparency note
- [ ] Verify markdown renders cleanly (no broken links, balanced fences)
- [ ] `gh` commit hook: stage both files, conventional commit `docs:`

## Success Criteria
- CHANGELOG.md exists, 5 entries có date + section structure
- README dài thêm ~5 dòng, không phá format hiện tại
- Commit message follow `docs:` convention

## Risk Assessment
- **Low risk** — pure docs change, không ảnh hưởng runtime

## Next Steps
→ Phase 2 (test workflow)
