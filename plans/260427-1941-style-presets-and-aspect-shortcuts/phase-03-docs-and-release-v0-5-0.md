---
phase: 3
title: Docs + release v0.5.0
status: completed
priority: high
effort: 30m
dependsOn: phase-02
---

# Phase 3 — Docs + release v0.5.0

## Context links

- Plan: `../plan.md`
- Brainstorm: `../../reports/brainstorm-260427-1941-style-presets-and-aspect-shortcuts.md`
- Phase 1 + 2 must be merged + green CI before this phase.
- Release pipeline guide: `D:/WORKSPACES/open-image/docs/release-guide.md`

## Overview

Documentation update + version bump + tag → triggers GitHub Actions auto-publish to PyPI. ~30 phút work, ~30 giây pipeline run.

## Key insights

- Pipeline tự handle build + upload — KHÔNG run `python -m build` hoặc `twine upload` thủ công.
- Tag SHA phải là full SHA (`git rev-parse HEAD`), không short SHA — pipeline check.
- Tag phải point vào commit có `release.yml` (đã có từ v0.3.3+ → safe).
- Skill template version stamp tự sync qua `importlib.metadata` — chỉ cần bump `pyproject.toml`.

## Requirements

### Functional

1. README.md có section/bảng cho `--style` (8 styles) và aspect flags.
2. README.md flag table update với 5 flag mới.
3. CHANGELOG.md có entry `## [0.5.0] - 2026-04-27` với section "Added".
4. `pyproject.toml` bump `version = "0.5.0"`.
5. `python -m pytest -q` xanh local.
6. `gh release create v0.5.0` triggers `.github/workflows/release.yml`.
7. PyPI có v0.5.0 trong < 1 phút sau release.

### Non-functional

- Commit message theo conventional format: `release: v0.5.0 - style presets and aspect shortcuts`.
- KHÔNG commit `~/.pypirc`, `.env`, hoặc token.
- KHÔNG dùng `--no-verify`.
- 12 CI jobs phải xanh trước tag.

## Architecture

```
Local
  ├── README.md         (+30 dòng: bảng styles, aspect flags, list-styles example)
  ├── CHANGELOG.md      (+10 dòng: [0.5.0] entry)
  └── pyproject.toml    (1 line: version="0.5.0")
       │
       ▼
  git commit → git push origin main
       │
       ▼
  CI test workflow (12 jobs) — must pass
       │
       ▼
  gh release create v0.5.0 --target $(git rev-parse HEAD)
       │
       ▼
  release.yml fires → build sdist+wheel → publish PyPI (skip-existing: true)
       │
       ▼
  Verify: curl pypi.org/pypi/open-image/0.5.0/json
       │
       ▼
  Next Python startup on user machines → .pth → silent SKILL.md update
```

## Related code files

**Modify:**
- `README.md` — add Styles section, aspect flags table, --list-styles example, update Flags table
- `CHANGELOG.md` — prepend `[0.5.0]` entry
- `pyproject.toml` — bump version

**Read for context:**
- `docs/release-guide.md` — exact command sequence (don't deviate)
- `CHANGELOG.md` — Keep a Changelog format reference (existing entries)
- `README.md` — existing flag table style + sections to mimic

## Implementation steps

### 1. Update `pyproject.toml`

```diff
- version = "0.4.0"
+ version = "0.5.0"
```

### 2. Prepend CHANGELOG entry

```markdown
## [0.5.0] - 2026-04-27

### Added
- `--style <name>` flag with 8 curated prompt presets (`3d-render`, `anime`, `watercolor`, `cyberpunk`, `photoreal`, `sketch`, `oil-painting`, `minimalist`). Style fragment is appended to the prompt.
- `--list-styles` flag to print known styles + full fragments.
- `--portrait`, `--landscape`, `--square` mutually-exclusive aspect ratio shortcuts (1024×1792 / 1792×1024 / 1024×1024). User's explicit `--extra '{"size":...}'` always wins.

### Changed
- Slug filename derives from the original prompt (not the style-augmented prompt) — keeps filenames sane when using `--style`.
- Claude Code skill template updated with new sections for `--style` and aspect shortcuts.
```

### 3. Update README.md

**Insert new section after "Model-agnostic by design", before "--extra escape hatch":**

```markdown
### Curated styles + aspect shortcuts

Quick prompt modifiers — no need to memorize style fragments or `--extra` JSON:

```bash
# Style: appends "3D render, octane render, hyperrealistic detail, 8k" to your prompt
open-image --style 3d-render --prompt "a cat astronaut"

# Aspect: shortcut for --extra '{"size":"1024x1792"}'
open-image --portrait --prompt "a tall waterfall"

# Combine: portrait 3D render
open-image --style 3d-render --portrait --prompt "a cat astronaut"

# List all styles with full fragments
open-image --list-styles
```

8 styles: `3d-render`, `anime`, `watercolor`, `cyberpunk`, `photoreal`, `sketch`, `oil-painting`, `minimalist`. Hard-capped at 10 forever — for more variety use `--extra` or your own prompt.

3 aspect flags: `--portrait` (1024×1792), `--landscape` (1792×1024), `--square` (1024×1024). Mutually exclusive. `--extra '{"size":...}'` overrides if both passed.
```

**Update Flags table** — append rows:

```markdown
| `--style` | — | Append a curated prompt fragment (run `--list-styles` to see all) |
| `--list-styles` | — | List known styles with full fragments, then exit |
| `--portrait` | — | Shortcut for `--extra '{"size":"1024x1792"}'` |
| `--landscape` | — | Shortcut for `--extra '{"size":"1792x1024"}'` |
| `--square` | — | Shortcut for `--extra '{"size":"1024x1024"}'` |
```

### 4. Run tests local

```bash
python -m pytest -q
# All tests must pass before tag
```

### 5. Commit + push

```bash
git add pyproject.toml CHANGELOG.md README.md gen.py open_image_skill.py test_gen.py
git commit -m "release: v0.5.0 - style presets and aspect shortcuts"
git push origin main
```

### 6. Wait for CI green (test.yml — 12 jobs)

```bash
gh run watch
# Wait until conclusion: success
```

### 7. Create GitHub release (triggers PyPI publish)

```bash
SHA=$(git rev-parse HEAD)
gh release create v0.5.0 --target "$SHA" \
  --title "v0.5.0 — style presets + aspect shortcuts" \
  --notes "Style presets (--style) + aspect ratio shortcuts (--portrait/--landscape/--square). 8 curated styles. See CHANGELOG.md for details."
```

### 8. Verify PyPI live (~30 giây sau)

```bash
gh run watch  # release.yml run
curl -sf "https://pypi.org/pypi/open-image/0.5.0/json" | python -c "import sys, json; print(json.load(sys.stdin)['info']['version'])"
# Expected: 0.5.0
```

### 9. Verify skill auto-sync

```bash
python -m venv /tmp/check && /tmp/check/bin/pip install --upgrade open-image
/tmp/check/bin/python -c "print('hello')"  # triggers .pth bootstrap
grep "CLI v" ~/.claude/skills/open-image/SKILL.md
# Expected: marker shows "v0.5.0"
grep -E "## Styles|## Aspect" ~/.claude/skills/open-image/SKILL.md
# Expected: both new sections present
```

## Todo list

- [x] Bump `pyproject.toml` to `0.5.0`
- [x] Prepend `[0.5.0]` entry to `CHANGELOG.md`
- [x] Add "Curated styles + aspect shortcuts" section to README
- [x] Update README Flags table with 5 new rows
- [x] Run `python -m pytest -q` — all pass
- [x] Commit with `release: v0.5.0 - ...` message
- [x] Push to origin/main
- [x] Wait for test.yml CI green (12 jobs)
- [x] `gh release create v0.5.0 --target $(git rev-parse HEAD) ...`
- [x] Wait for release.yml green
- [x] Verify PyPI v0.5.0 live
- [x] Verify skill auto-sync on a clean install

## Success criteria

- v0.5.0 trên PyPI: `pip install open-image==0.5.0` works.
- 12 CI test jobs xanh.
- 1 release workflow xanh.
- SKILL.md trên fresh install có "## Styles" + "## Aspect ratio shortcuts" + version stamp `v0.5.0`.
- README có flag table updated + new section.
- CHANGELOG có `[0.5.0]` entry với 4 bullet points.

## Risks

| Risk | Mitigation |
|---|---|
| CI fail trên Windows do path encoding trong tests mới | Tests dùng pure Python strings (no Path) → safe across OS. |
| `gh release create` fail nếu tag đã exists | Tag mới `v0.5.0` chưa từng push → safe. Nếu retry, `skip-existing: true` ở publish step. |
| Pypi publish race với cache lag | Đợi 1 phút trước verify. Acceptable. |
| Forgot bump version → publish vẫn là old | Pipeline build từ pyproject.toml — nếu quên bump, sdist tên `open-image-0.4.0.tar.gz`, PyPI reject duplicate. Defense in depth. |
| Forgot update skill template → user nâng cấp nhưng skill không có style flags | Phase 2 đã update. Verify step 9 sẽ catch nếu sót. |

## Security considerations

- KHÔNG commit token, dotenv, hoặc credentials.
- Pipeline dùng GitHub secret `PYPI_API_TOKEN` — không expose trong logs.
- Conventional commit message — không leak debug info.

## Next steps

→ (Optional) `/ck:journal` để ghi technical journal entry post-release.
→ (Optional) Sau 1-2 tuần thu feedback adoption → quyết định iterate v0.5.x hoặc giữ ổn định.
