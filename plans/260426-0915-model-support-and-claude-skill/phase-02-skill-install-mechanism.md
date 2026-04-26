# Phase 2 — Skill Template + Auto-Install + `--install-skill`

## Context Links
- **Brainstorm:** `plans/reports/brainstorm-260426-0915-model-support-and-claude-skill.md` — Sections 5.2, 5.3
- **Target file:** `gen.py`

## Overview
- **Priority:** High (core feature của v0.3)
- **Status:** pending
- **Description:** Embed SKILL.md template trong `gen.py` + dual-mode install: silent first-run (idempotent, không phá customization) và manual `--install-skill` (force overwrite).

## Key Insights
- Pip không có true post-install hook chuẩn → "auto" thực hiện qua first-run trigger ở đầu `main()`.
- Auto-install **never overwrites** — chỉ install nếu `SKILL.md` chưa có.
- Manual flag **always overwrites** — phù hợp với user đã cài trước, muốn update.
- Auto-install **không** tạo `~/.claude/` nếu chưa có (user không dùng Claude Code → skip silent).
- Mọi `OSError` trong auto-install bị swallow → không break workflow gen image.
- SKILL.md embed dạng triple-quoted Python string → giữ one-file philosophy.

## Requirements

### Functional
- Constant `SKILL_MD_TEMPLATE: str` chứa nội dung SKILL.md đầy đủ (frontmatter + sections).
- `maybe_install_skill_silently()`:
  - Return early nếu `Path.home() / ".claude"` không tồn tại.
  - Return early nếu `SKILL.md` đã có.
  - Else: mkdir parents + write template.
  - Mọi `OSError` → swallow (`except OSError: pass`).
- `reinstall_skill_force()`:
  - Abort `sys.exit(1)` với message rõ nếu `~/.claude/` không có.
  - Mkdir parents + write template (always overwrite).
  - Print path đã ghi, exit 0.
- `--install-skill` flag → trigger `reinstall_skill_force()` rồi exit.
- `main()` gọi `maybe_install_skill_silently()` đầu tiên (trước `parse_args` HOẶC ngay sau, miễn là chạy mỗi invocation).

### Non-functional
- Auto-install latency: <5ms cho fast-path (file exists check).
- Không log gì ra stdout/stderr trong auto-install (silent).
- Path resolution dùng `Path.home()` để cross-platform (Win: `%USERPROFILE%`, *nix: `$HOME`).

## Architecture

```
gen.py
├── SKILL_MD_TEMPLATE             ← new (~80 dòng triple-quoted)
├── maybe_install_skill_silently  ← new (~12 dòng)
├── reinstall_skill_force         ← new (~10 dòng)
├── parse_args                    ← add --install-skill flag
└── main                          ← gọi maybe_install_skill_silently() trước, branch theo flag
```

## SKILL.md Template Outline

YAML frontmatter:
```yaml
---
name: open-image
description: Generate PNG images via OpenAI image API. Use when user asks to "generate an image", "create a picture", "draw", or pipes prompt text. CLI command `open-image` outputs absolute file paths to stdout.
---
```

Body sections:
1. **What is open-image** (1 paragraph)
2. **When to use** (bullet list of trigger phrases)
3. **When NOT to use** (image editing, non-OpenAI providers)
4. **Quick reference** (5 commands: inline prompt, prompt-file, model swap, --extra, --list-models)
5. **Models supported** (note: agent có thể chạy `open-image --list-models` để query động)
6. **Output convention** (`./output/{YYYYMMDD-HHMMSS}-{uuid8}.png`, stdout paths, `--out-dir`, `--keep`)
7. **Auth** (`OPENAI_API_KEY` env, `--api-key` fallback)
8. **Common errors & fixes** (no key, 403, JSON parse, empty prompt)
9. **Best practices for agents** (use `--prompt-file` cho prompt dài, capture stdout, `--out-dir` per-task)

## Related Code Files
- **Modify:** `gen.py`
- **Read:** `gen.py` (post-Phase-1 state) để insert đúng vị trí

## Implementation Steps

### Step 1: Embed SKILL_MD_TEMPLATE
Đặt sau `KNOWN_MODELS`:
```python
SKILL_MD_TEMPLATE = """\
---
name: open-image
description: Generate PNG images via OpenAI image API. ...
---

# open-image — OpenAI image generation CLI

[full content here]
"""
```
- Dùng `"""\` (backslash đầu) để skip leading newline.
- Đảm bảo không có f-string interpolation accidentally (escape `{` nếu có ví dụ JSON).

### Step 2: Implement `maybe_install_skill_silently()`
```python
def maybe_install_skill_silently() -> None:
    """Install Claude Code skill silently on first run if applicable.
    Skips if ~/.claude doesn't exist (user not using Claude Code) or
    skill already present (preserve user customization).
    """
    claude_dir = Path.home() / ".claude"
    if not claude_dir.exists():
        return
    skill_md = claude_dir / "skills" / "open-image" / "SKILL.md"
    if skill_md.exists():
        return
    try:
        skill_md.parent.mkdir(parents=True, exist_ok=True)
        skill_md.write_text(SKILL_MD_TEMPLATE, encoding="utf-8")
    except OSError:
        pass  # Silent fail; never block image generation
```

### Step 3: Implement `reinstall_skill_force()`
```python
def reinstall_skill_force() -> None:
    """Manual re-install: always overwrite. Abort if ~/.claude not found."""
    claude_dir = Path.home() / ".claude"
    if not claude_dir.exists():
        sys.exit(
            "ERROR: ~/.claude not found. Install Claude Code first, "
            "then re-run `open-image --install-skill`."
        )
    skill_md = claude_dir / "skills" / "open-image" / "SKILL.md"
    skill_md.parent.mkdir(parents=True, exist_ok=True)
    skill_md.write_text(SKILL_MD_TEMPLATE, encoding="utf-8")
    print(f"Skill installed: {skill_md.resolve()}")
```

### Step 4: Add `--install-skill` flag in `parse_args`
```python
p.add_argument(
    "--install-skill",
    action="store_true",
    help="Re-install Claude Code skill at ~/.claude/skills/open-image/ (overwrites).",
)
```

### Step 5: Wire up in `main()`
```python
def main() -> None:
    maybe_install_skill_silently()  # First-run auto-install (silent)
    args = parse_args()

    if args.list_models:
        print_models_table()
        return

    if args.install_skill:
        reinstall_skill_force()
        return

    # ... existing logic (resolve_prompt, generate, save, prune)
```

## Todo List
- [ ] Draft SKILL.md content (markdown only, ~80 dòng)
- [ ] Embed as `SKILL_MD_TEMPLATE` constant in `gen.py`
- [ ] Implement `maybe_install_skill_silently()`
- [ ] Implement `reinstall_skill_force()`
- [ ] Add `--install-skill` flag to argparse
- [ ] Wire calls in `main()` (auto trước parse_args, manual sau list_models check)
- [ ] Manual test: clean `~/.claude/skills/open-image/` rồi chạy `python gen.py --help` → SKILL.md xuất hiện
- [ ] Manual test: chạy lại → SKILL.md không bị modify (mtime check)
- [ ] Manual test: `python gen.py --install-skill` → overwrite + print path
- [ ] Manual test: rename `~/.claude` tạm thời → auto skip, manual abort với error
- [ ] Verify `python -m py_compile gen.py` pass

## Success Criteria
- Lần đầu chạy bất kỳ `open-image` command với `~/.claude/` tồn tại → SKILL.md được tạo silent
- Lần thứ 2 chạy → SKILL.md không bị động vào (preserve user edits)
- `--install-skill` luôn overwrite, in path, exit 0
- `--install-skill` không có `~/.claude/` → exit 1 với error message
- Auto-install OSError không crash CLI (test: read-only home dir)
- File `gen.py` vẫn compile sạch

## Risk Assessment
- **Risk:** SKILL.md template có f-string accidentally → SyntaxError. **Mitigation:** Dùng plain `"""..."""`, escape `{` thành `{{` chỉ nếu chuyển sang f-string.
- **Risk:** User chạy CLI với `umask` lạ → file mode kỳ. **Mitigation:** Dùng `write_text` default mode, không chmod. Không là blocker cho markdown.
- **Risk:** Auto-install runs every invocation (~2 stat calls) → trên slow filesystem có thể chậm. **Mitigation:** Negligible (<1ms typical). Có thể optimize sau nếu cần.
- **Risk:** Skill content drift giữa code và CLI. **Mitigation:** Skill ref `--list-models` thay vì hardcode → giảm drift.

## Security Considerations
- Path traversal: dùng `Path.home() / ".claude"` cố định, không nhận user input → safe.
- File permissions: SKILL.md là markdown text, không chứa secrets → safe.
- Race condition: 2 process cùng install lần đầu → cuối cùng 1 file ghi xong, an toàn (text idempotent).

## Next Steps
→ Phase 3 (README + version bump + Philosophy reframe)
