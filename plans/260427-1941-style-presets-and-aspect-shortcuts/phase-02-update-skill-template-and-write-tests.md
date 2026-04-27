---
phase: 2
title: Update skill template + write unit tests
status: pending
priority: high
effort: 45m
dependsOn: phase-01
---

# Phase 2 — Update skill template + write unit tests

## Context links

- Plan: `../plan.md`
- Brainstorm: `../../reports/brainstorm-260427-1941-style-presets-and-aspect-shortcuts.md`
- Phase 1: `phase-01-implement-style-and-aspect-flags.md`
- Source: `D:/WORKSPACES/open-image/open_image_skill.py`, `D:/WORKSPACES/open-image/test_gen.py`

## Overview

2 jobs song song được:
1. Cập nhật `SKILL_MD_TEMPLATE` trong `open_image_skill.py` — thêm section "Styles" + "Aspect ratio shortcuts" để Claude Code agent biết flag mới.
2. Thêm 5 unit tests trong `test_gen.py` cover apply_style, merge_aspect_into_extra, slug-from-original-prompt invariant.

## Key insights

- Skill template version stamp tự sync qua `.pth` mechanism — không cần touch bootstrap code.
- Tests phải hit pure functions (không call OpenAI API) — `apply_style`, `merge_aspect_into_extra` là pure → trivial test.
- Slug invariant test: dùng `slugify(prompt)` direct, KHÔNG cần mock OpenAI client.

## Requirements

### Functional — Skill template

- Thêm section "Styles" liệt kê 8 style names + cách dùng `--style`.
- Thêm section "Aspect ratio shortcuts" với bảng `--portrait/--landscape/--square`.
- Update Quick reference example: thêm 1 dòng `open-image --style 3d-render --portrait --prompt "..."`.

### Functional — Tests

5 tests mới trong `test_gen.py`:

1. `test_apply_style_appends_fragment` — `apply_style("a cat", "3d-render")` → `"a cat, 3D render, octane render, hyperrealistic detail, 8k"`
2. `test_apply_style_unknown_exits` — `apply_style("x", "nope")` raises `SystemExit`, message chứa `"--list-styles"`
3. `test_apply_style_none_passthrough` — `apply_style("a cat", None)` → `"a cat"`
4. `test_merge_aspect_injects_size_when_extra_missing` — `merge_aspect_into_extra({}, "portrait")` → `{"size": "1024x1792"}`
5. `test_merge_aspect_does_not_override_explicit_size` — `merge_aspect_into_extra({"size": "512x512"}, "portrait")` → `{"size": "512x512"}`

Bonus integration assertion (có thể inline vào 1 trong 5 test trên hoặc tách):
- `test_slug_uses_original_prompt_not_augmented` — verify `slugify("a cat")` == slug ngay cả khi style được apply.

### Non-functional

- Tests phải pass trên cả 12 CI jobs (Linux/macOS/Windows × Py 3.10-3.13).
- Không thêm test dependency mới (pytest đã có).
- Tests chạy < 1 giây tổng (pure function tests).

## Architecture

```
open_image_skill.py
  └── SKILL_MD_TEMPLATE (string)
        ├── existing sections (When to use, Quick reference, Models, Output, Auth, Errors, Best practices)
        └── NEW sections:
              ├── ## Styles
              └── ## Aspect ratio shortcuts

test_gen.py
  ├── existing tests (slugify, install, models table, etc.)
  └── NEW tests:
        ├── test_apply_style_*  (3 tests)
        ├── test_merge_aspect_* (2 tests)
        └── (optional) test_slug_uses_original_prompt
```

## Related code files

**Modify:**
- `open_image_skill.py` — extend `SKILL_MD_TEMPLATE` (~20 dòng thêm)
- `test_gen.py` — append 5 test functions (~30 dòng thêm)

**Read for context:**
- `open_image_skill.py:24-102` — current SKILL_MD_TEMPLATE
- `test_gen.py` — existing test patterns (import style, pytest conventions)

## Implementation steps

### 1. Update `SKILL_MD_TEMPLATE` (open_image_skill.py)

Insert sau section "Models supported", trước "Output":

````markdown
## Styles

Append a curated style fragment to your prompt with `--style <name>`. Run `open-image --list-styles` for the current list with full fragments.

| Style | Best for |
|---|---|
| `3d-render` | Octane/Cinema 4D-look 3D scenes |
| `anime` | Cel-shaded Japanese animation aesthetic |
| `watercolor` | Soft watercolor paintings |
| `cyberpunk` | Neon, rain-slicked, neo-noir sci-fi |
| `photoreal` | DSLR-style photo realism |
| `sketch` | Hand-drawn pencil sketches |
| `oil-painting` | Classical oil painting |
| `minimalist` | Clean lines, negative space |

Style is **appended** to the user prompt: `--prompt "a cat" --style 3d-render` → API receives `"a cat, 3D render, octane render, hyperrealistic detail, 8k"`. Don't double-style (avoid combining with prompts that already contain style words).

## Aspect ratio shortcuts

Skip the `--extra` JSON for common sizes:

| Flag | Equivalent | Size |
|---|---|---|
| `--portrait` | `--extra '{"size":"1024x1792"}'` | 1024×1792 |
| `--landscape` | `--extra '{"size":"1792x1024"}'` | 1792×1024 |
| `--square` | `--extra '{"size":"1024x1024"}'` | 1024×1024 |

Mutually exclusive — pass at most one. If you also pass `--extra '{"size":...}'`, your `--extra` value wins (explicit beats implicit).

Note: `dall-e-2` only supports square sizes (256/512/1024). Non-square aspect flags will surface API error verbatim.
````

Update Quick reference block (add 1 line):

```bash
# Style + aspect shortcut combo
open-image --style 3d-render --portrait --prompt "a cat astronaut"
```

### 2. Append tests to `test_gen.py`

```python
import pytest
from gen import apply_style, merge_aspect_into_extra, KNOWN_STYLES, slugify


class TestApplyStyle:
    def test_appends_fragment(self):
        result = apply_style("a cat", "3d-render")
        assert result == "a cat, " + KNOWN_STYLES["3d-render"]

    def test_unknown_exits_with_helpful_message(self):
        with pytest.raises(SystemExit) as exc:
            apply_style("a cat", "nonexistent-style")
        assert "--list-styles" in str(exc.value)

    def test_none_passes_prompt_through_unchanged(self):
        assert apply_style("a cat", None) == "a cat"


class TestMergeAspectIntoExtra:
    def test_injects_size_when_extra_has_no_size(self):
        result = merge_aspect_into_extra({}, "portrait")
        assert result["size"] == "1024x1792"

    def test_does_not_override_explicit_size(self):
        result = merge_aspect_into_extra({"size": "512x512"}, "portrait")
        assert result["size"] == "512x512"

    def test_no_aspect_returns_extra_unchanged(self):
        result = merge_aspect_into_extra({"quality": "high"}, None)
        assert result == {"quality": "high"}


def test_slug_derived_from_original_prompt_not_augmented():
    """Filename slug must use the user's original prompt, not the style-augmented one."""
    original = "a red fox in snow"
    augmented = apply_style(original, "3d-render")
    assert slugify(original) == "a-red-fox-in-snow"
    assert slugify(augmented) != slugify(original)  # sanity: augmented would differ
```

### 3. Run pytest local

```bash
python -m pytest -q test_gen.py
# Expected: all existing tests + 7 new tests pass
```

### 4. Verify SKILL.md regenerates correctly

```bash
python -c "from open_image_skill import _render_skill_md; print(_render_skill_md())" | grep -E "Styles|Aspect ratio"
# → both sections present
```

## Todo list

- [ ] Update `SKILL_MD_TEMPLATE` with Styles + Aspect ratio sections
- [ ] Update Quick reference example block
- [ ] Add `TestApplyStyle` class (3 tests)
- [ ] Add `TestMergeAspectIntoExtra` class (3 tests)
- [ ] Add `test_slug_derived_from_original_prompt_not_augmented`
- [ ] Run `python -m pytest -q test_gen.py` — all pass
- [ ] Verify rendered SKILL.md contains new sections via stdout check

## Success criteria

- All existing tests + 7 new tests pass locally.
- `_render_skill_md()` output contains "## Styles" + "## Aspect ratio shortcuts" headings.
- Skill template diff cleanly applies — no stale section duplication.

## Risks

| Risk | Mitigation |
|---|---|
| Test imports `apply_style` before Phase 1 lands → ImportError | Sequencing: Phase 1 must merge before running these tests. Document in todo. |
| Skill template version mismatch in CI snapshot tests | No snapshot test of full SKILL.md exists. Spot-checks via grep are sufficient. |
| Test counts the pre-augmented slug — if augmented happens to equal original slug for short prompts, sanity assert fails | Use prompt that's clearly distinct after augmentation ("a red fox in snow" → 31 chars; augmented → 60+ chars). Safe. |

## Security considerations

- N/A — pure function tests, no I/O.

## Next steps

→ Phase 3: Update README + CHANGELOG + bump pyproject version + run release pipeline.
