---
type: brainstorm
date: 2026-04-27
slug: style-presets-and-aspect-shortcuts
status: approved
target_version: v0.5.0
---

# Brainstorm — Style presets + aspect shortcuts (v0.5.0)

## Problem statement

User muốn `open-image` "đa dạng" hơn: thêm option ảnh 3D, các loại ảnh khác nhau. Sau Q&A clarification, intent thật là:

1. **Style presets** — flag ngắn (vd. `--style 3d-render`) thay vì gõ full prompt fragment ("3D render, octane, 8k...") mỗi lần.
2. **Discoverability fix cho `--extra`** — JSON syntax khó nhớ. Muốn flag tắt `--portrait/--landscape/--square`.

Yêu cầu này **mâu thuẫn nhẹ** với hard rule "API là source of truth" của project. Brutally honest:
- OpenAI API **không có** param `style=3d`. "3D look" thuần là prompt engineering.
- `--extra` đã forward MỌI API param — về mặt kỹ thuật user không thiếu gì.

→ Justify được vì 2 feature này là **client-side UX layer**, không validate / không wrap API param theo nghĩa "che đậy". Style append vào prompt; aspect map sang `size` rồi forward as-is.

## Approaches evaluated

### Approach A — Style presets only (rejected)
Chỉ làm `--style`, bỏ aspect shortcuts. **Pros:** Scope nhỏ. **Cons:** Pain `--extra JSON khó nhớ` không được giải. Half-baked.

### Approach B — Both, gộp release v0.5.0 (CHỌN)
Làm cả `--style` lẫn `--portrait/--landscape/--square` trong cùng release. **Pros:** Giải 2 pain trong 1 lần ship; vẫn dưới 300 dòng `gen.py`. **Cons:** Risk feature creep nếu không hard-limit.

### Approach C — External YAML library (rejected)
50+ styles trong file YAML, user override được qua `~/.config/open-image/styles.yaml`. **Pros:** Linh hoạt. **Cons:** Thêm PyYAML dependency, vi phạm KISS. User đã chọn 5-10 curated → không cần.

### Approach D — Multi-provider rewrite (rejected)
Thêm Gemini Imagen / Flux / MiniMax. **Pros:** "Đa dạng" thật sự. **Cons:** Rewrite hoàn toàn, vi phạm tên `open-image` (đang OpenAI-only). Out of scope.

## Final solution — v0.5.0 design

### Single-file philosophy giữ nguyên

Tất cả thay đổi trong `gen.py` (~280 → ~320 dòng). Không tách module.

### Feature 1: `--style <name>`

Hardcode dict 8 curated styles trong `gen.py`:

```python
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
```

**Composition: append.** `final_prompt = f"{prompt}, {fragment}"`.

**Validation:** Unknown name → `sys.exit("ERROR: Unknown style 'X'. Run --list-styles.")`. Đây là client-side, hợp lệ.

**Decision (Q1 resolved):** Generic fragments (không brand IP). "Studio Ghibli" → "Japanese animation"; "Blade Runner" → "neo-noir sci-fi mood". Tránh copyright noise.

**`--list-styles` flag:** Show **full fragment** (Q2 resolved) — transparency, user thấy chính xác cái gì sẽ append.

### Feature 2: Aspect ratio shortcuts

```python
ASPECT_SIZES = {"portrait": "1024x1792", "landscape": "1792x1024", "square": "1024x1024"}
```

3 flag mutually-exclusive (argparse `add_mutually_exclusive_group`). Internally inject vào extra dict nếu user chưa set `size`:

```python
if aspect and "size" not in extra:
    extra["size"] = ASPECT_SIZES[aspect]
```

**Conflict rule:** `--extra '{"size":...}'` thắng aspect flag (explicit > implicit). Document.

**KHÔNG làm `--hd`:** Quality model-specific (gpt-image-2: high|medium|low|auto; dall-e-3: standard|hd) → wrap = false abstraction. User dùng `--extra '{"quality":"high"}'`.

### Critical detail — slug derivation

Slug filename derive từ **prompt gốc**, không phải augmented → tránh `a-cat-3d-render-octane-render-...png`.

```python
slug = slugify(args.name) if args.name else slugify(prompt)  # ORIGINAL
augmented = apply_style(prompt, args.style)                  # AFTER slug
```

## Files modified

| File | Change | Lines |
|---|---|---|
| `gen.py` | +KNOWN_STYLES, +ASPECT_SIZES, +apply_style(), +3 aspect flags, +--style, +--list-styles | +40 |
| `open_image_skill.py` | Update SKILL_MD_TEMPLATE: thêm section "Styles" + "Aspect ratio shortcuts" + bump examples | +20 |
| `test_gen.py` | 5 unit tests | +30 |
| `pyproject.toml` | `version = "0.5.0"` | 1 |
| `CHANGELOG.md` | v0.5.0 entry | +10 |
| `README.md` | Documentation: bảng styles, aspect flags, gallery sample mới (optional) | +30 |

## Test plan

5 unit tests trong `test_gen.py`:

1. `test_apply_style_appends_fragment` — `"a cat"` + `"3d-render"` → `"a cat, 3D render, ..."`
2. `test_apply_style_unknown_exits` — unknown style → `SystemExit`, message gợi ý `--list-styles`
3. `test_apply_style_none_passthrough` — `style=None` → prompt unchanged
4. `test_aspect_injects_size_when_extra_missing_size` — `--portrait` + `extra={}` → `extra["size"] == "1024x1792"`
5. `test_aspect_does_not_override_explicit_extra_size` — `--portrait` + `extra={"size":"512x512"}` → `512x512` thắng

Plus integration: slug phải derive từ prompt gốc, không augmented.

## Implementation considerations

- **Single-file:** giữ `gen.py < 350 lines`. Hiện 226 → sau ~266 + helpers ~50 = ~316. OK.
- **Stdlib-only:** Không thêm dependency.
- **CI:** 12 jobs (Linux/macOS/Windows × Py 3.10-3.13) phải pass trước tag.
- **Skill auto-sync:** sau `pip install -U open-image v0.5.0`, next Python startup tự update SKILL.md (cơ chế `.pth` đã có).

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Style + prompt user double-style ("watercolor cat" + `--style watercolor`) | Low | Document; user tự chịu |
| 8 styles không hợp gu → unused code | Medium | Đo adoption qua issue tracker; remove ở v1.0 nếu chết |
| dall-e-2 không support 1024x1792 → API error | Low | Acceptable per "API source of truth" — error verbatim |
| Feature creep: user xin thêm 20-50 styles | High | **Hard limit 10 styles forever.** Hơn → fork hoặc dùng `--extra`. |
| `--style` validation breaks "API source of truth" rule | Low | Style KHÔNG phải API param → rule không apply. Document trong CLAUDE.md. |

## Success metrics

- v0.5.0 ship qua pipeline (12 CI jobs xanh).
- README + SKILL.md update đầy đủ.
- 1 tuần sau release: ≥1 user feedback (issue / star) đề cập style flag.
- 0 regression trên existing tests.

## Next steps

1. (Optional) Run `/ck:plan` để tạo phased plan dir tại `plans/260427-1941-style-presets-and-aspect-shortcuts/`.
2. Implement theo file table phía trên.
3. Run tests local (`pytest test_gen.py`).
4. Commit + push → CI xanh → tag v0.5.0 → pipeline publish PyPI.

## Unresolved questions

- **Style fragment wording cuối cùng** có cần A/B test với generated images không? (Có thể skip — re-tune sau v0.5.0 nếu output kém quality.)
- **Có muốn add gallery sample mới** (3D, anime, cyberpunk samples) vào README + assets/ không? Cost: vài API call + commit binary. (Recommendation: skip ở v0.5.0, add ở v0.5.1 nếu user feedback tích cực.)
