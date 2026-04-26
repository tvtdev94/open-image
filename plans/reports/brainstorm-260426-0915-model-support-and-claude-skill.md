# Brainstorm — open-image v0.3: Model Support + Claude Code Skill Auto-Install

**Date:** 2026-04-26 09:15
**Branch:** main
**Status:** Design approved, ready for `/ck:plan`

---

## 1. Problem Statement

User muốn 2 việc:
1. Bổ sung "model support" cho `open-image` CLI (bản chất là cải thiện DX quanh `--model`).
2. Khi user `pip install open-image`, tự động cài Claude Code skill vào `~/.claude/skills/open-image/SKILL.md` để Claude Code biết cách dùng CLI mà không cần user dạy lại.

## 2. Current State

- 1 file `gen.py` (~135 dòng), pure stdlib + `openai` SDK.
- `--model` đã model-agnostic (string forward thẳng).
- `--extra` JSON forward verbatim → API là source of truth.
- Triết lý README: *"no MCP server, no HTTP wrapper, no plugin system."*
- `pyproject.toml` dùng `py-modules = ["gen"]`, version 0.2.0.
- Không có test.

## 3. Requirements

### Functional
- `--list-models` in bảng model đã biết + notes, exit 0, không gọi API.
- Skill auto-install lần đầu chạy CLI nếu `~/.claude/` tồn tại và chưa có skill.
- `--install-skill` cho user đã cài trước đó muốn re-install (always overwrite).
- README phải show rõ models supported (`gpt-image-1`, `gpt-image-2`, `dall-e-3`, `dall-e-2`).

### Non-functional
- Giữ "one-file" philosophy → KISS thắng strict 200-line rule.
- Auto-install **không** được fail user workflow (silent on error).
- Auto-install **không** tạo `~/.claude/` nếu chưa có (không xâm phạm filesystem).
- API vẫn là source of truth → không client-side validation, không auto-merge defaults.

## 4. Approaches Evaluated

### Model support — 3 options
| Option | Behavior | Verdict |
|---|---|---|
| A. Full KNOWN_MODELS (defaults + notes + auto-merge + warn) | Tự thêm `response_format: b64_json` cho dall-e-3 | ❌ Magic ngầm, phá "API source of truth" |
| **B. Info-only KNOWN_MODELS (notes only)** ⭐ | `--list-models` in bảng, không merge, không warn | ✅ Chosen — KISS, transparent |
| C. Bỏ luôn KNOWN_MODELS | Skill hardcode list trong SKILL.md | ❌ Mất khả năng query động, dễ stale |

### Install mechanism — 3 options
| Option | Behavior | Verdict |
|---|---|---|
| Setuptools post-install hook | Deprecated, không reliable với pipx/uv | ❌ Rejected (anti-pattern) |
| Subcommand only (`--install-skill`) | User phải chạy thủ công sau pip install | ❌ Không "auto" như user yêu cầu |
| **Auto first-run + manual `--install-skill`** ⭐ | Silent install lần đầu khi gọi CLI; manual flag để re-install | ✅ Chosen |

### Skill scope
| Option | Verdict |
|---|---|
| **Claude Code skill markdown only** ⭐ | ✅ Chosen — đúng yêu cầu, nhất quán với spirit "no runtime plugin" |
| Skill + AGENTS.md | ❌ Scope creep |
| Skill + MCP server | ❌ Mâu thuẫn README |

## 5. Final Solution

### 5.1 Model support (Option B)

```python
# Module-level dict, info-only — không tham gia call args
KNOWN_MODELS = {
    "gpt-image-2": "Default. Requires org verification. Returns b64_json.",
    "gpt-image-1": "Newer GPT image model. Supports input_fidelity, transparency, output_format.",
    "dall-e-3":    "n=1 only. Sizes: 1024x1024 | 1792x1024 | 1024x1792. quality: standard|hd. style: vivid|natural. Pass response_format=b64_json via --extra.",
    "dall-e-2":    "n>1 supported. Sizes: 256x256 | 512x512 | 1024x1024.",
}
```

- New flag `--list-models` → print table + exit 0.
- Unknown model → forward as-is, **không** warn (giữ stderr sạch).
- **Không** auto-merge defaults — user pass `--extra` explicit.

### 5.2 Skill install (dual-mode)

**Auto first-run (silent, idempotent):**
```python
def maybe_install_skill_silently() -> None:
    claude_dir = Path.home() / ".claude"
    if not claude_dir.exists():
        return                           # user không dùng Claude Code
    skill_md = claude_dir / "skills" / "open-image" / "SKILL.md"
    if skill_md.exists():
        return                           # đã có, không động vào
    try:
        skill_md.parent.mkdir(parents=True, exist_ok=True)
        skill_md.write_text(SKILL_MD_TEMPLATE, encoding="utf-8")
    except OSError:
        pass                             # silent fail
```
Gọi đầu `main()`, **trước** parse_args.

**Manual `--install-skill` (force overwrite):**
```python
def reinstall_skill_force() -> None:
    claude_dir = Path.home() / ".claude"
    if not claude_dir.exists():
        sys.exit("ERROR: ~/.claude not found. Install Claude Code first.")
    skill_md = claude_dir / "skills" / "open-image" / "SKILL.md"
    skill_md.parent.mkdir(parents=True, exist_ok=True)
    skill_md.write_text(SKILL_MD_TEMPLATE, encoding="utf-8")
    print(f"Skill installed: {skill_md.resolve()}")
    sys.exit(0)
```

### 5.3 SKILL.md content (embedded as Python literal)

YAML frontmatter (`name`, `description` trigger pattern) + sections:
- When to use / NOT to use
- Quick reference (5 lệnh tiêu biểu)
- Models supported (đồng bộ KNOWN_MODELS)
- Output convention
- Auth / common errors
- Best practices cho agent (`--prompt-file` cho prompt dài, capture stdout, `--out-dir` per-task)

## 6. Implementation Outline

### File: `gen.py` (~135 → ~230 dòng)

Order trong file:
1. Imports
2. `KNOWN_MODELS` dict
3. `SKILL_MD_TEMPLATE` triple-quoted string (~80 dòng markdown)
4. `parse_args()` — thêm `--list-models`, `--install-skill`
5. `print_models_table()` — formatter
6. `maybe_install_skill_silently()` — first-run helper
7. `reinstall_skill_force()` — manual flag handler
8. Existing functions (resolve_prompt, save_images, prune, …)
9. `main()` — gọi `maybe_install_skill_silently()` đầu tiên, sau đó branch theo flag

### File: `pyproject.toml`
- `version = "0.2.0"` → `"0.3.0"`

### File: `README.md`
- Update "Model notes" section → bảng đầy đủ 4 models với notes (gpt-image-1, gpt-image-2, dall-e-3, dall-e-2)
- Thêm section "Claude Code integration":
  - Auto-install lần đầu chạy CLI
  - `open-image --install-skill` để re-install
  - Path: `~/.claude/skills/open-image/SKILL.md`
- Re-frame "Philosophy" section: thay *"no plugin system"* → *"no runtime plugins. Optional Claude Code skill is just markdown — Claude reads it, no daemon, no IPC."*
- Thêm dòng cho `--list-models` trong bảng Flags

### File: `test_gen.py` (new)
Pytest, không cần OpenAI SDK call:
- `test_known_models_keys()` — kiểm tra keys + value là str
- `test_resolve_prompt_inline()` — args.prompt có giá trị
- `test_resolve_prompt_file()` — đọc file
- `test_extra_invalid_json_exits()` — sys.exit khi JSON sai
- `test_extra_not_dict_exits()` — sys.exit khi list/string
- `test_install_skill_writes_to_home(tmp_path, monkeypatch)` — monkeypatch `Path.home`, assert file ghi đúng path + nội dung
- `test_auto_install_skips_when_no_claude_dir(tmp_path, monkeypatch)` — không tạo gì khi `~/.claude` không có
- `test_auto_install_skips_when_skill_exists(tmp_path, monkeypatch)` — pre-create SKILL.md với nội dung khác, gọi auto → không bị overwrite
- `test_reinstall_force_overwrites(tmp_path, monkeypatch)` — pre-create SKILL.md, gọi force → bị overwrite
- `test_list_models_table_contains_all_keys(capsys)` — stdout chứa 4 model IDs

Cần dependency: `pytest` (dev only). Thêm `[project.optional-dependencies] dev = ["pytest>=7.0"]` vào `pyproject.toml`.

## 7. Risks & Mitigation

| Risk | Severity | Mitigation |
|---|---|---|
| `gen.py` 230 dòng vượt 200-line guideline | Low | 80 dòng là markdown literal, không phải logic. KISS thắng. Document trade-off trong CLAUDE.md nếu cần. |
| `KNOWN_MODELS` notes stale khi OpenAI ra model mới | Medium | Notes là info, không tham gia logic → sai notes không break gì. PR community + bump patch version. |
| Auto-install chạy mỗi invocation (2 stat calls) | Negligible | µs scale, no observable impact |
| User đã sửa SKILL.md custom → bị overwrite | Low | Auto-install **không** overwrite (chỉ install nếu chưa có). Manual `--install-skill` mới ghi đè. |
| Triết lý README "no plugin system" | Low | Re-frame: skill = markdown docs, không runtime |
| pip không có true post-install → vẫn có khoảng "trễ 1 lần chạy" | Low | First-run trigger fire ngay khi user chạy CLI lần đầu, transparent. README giải thích. |

## 8. Acceptance Criteria

- [ ] `open-image --list-models` in bảng 4 models với notes, exit 0, không gọi API
- [ ] `open-image --model unknown-xyz --prompt "x"` không warn, vẫn forward tới API
- [ ] `open-image --model dall-e-3 --prompt "x"` **không** tự thêm `response_format` (user phải pass `--extra`)
- [ ] Lần đầu chạy `open-image --prompt "x"` với `~/.claude/` tồn tại → silent install SKILL.md
- [ ] Lần thứ 2 chạy → SKILL.md không bị overwrite
- [ ] `~/.claude/` không tồn tại → auto-install skip silent, CLI chạy bình thường
- [ ] `open-image --install-skill` với `~/.claude/` → overwrite SKILL.md, in path, exit 0
- [ ] `open-image --install-skill` không có `~/.claude/` → exit 1 với error rõ ràng
- [ ] `python gen.py --help` không crash
- [ ] `pytest` pass tất cả tests trong `test_gen.py`
- [ ] README cập nhật bảng models + Claude Code integration section
- [ ] Version bump 0.2.0 → 0.3.0

## 9. Out of Scope

- Multi-provider (Gemini/Flux/Stability) — phá triết lý one-SDK
- MCP server — mâu thuẫn README
- AGENTS.md template — không phải Claude Code
- Project-level skill (`.claude/skills/` trong cwd) — user yêu cầu user-level
- Image editing / variation — CLI chỉ text→image
- Setuptools post-install hook — anti-pattern pip
- Auto-merge defaults — phá "API source of truth"
- Client-side param validation — phá "API source of truth"

## 10. Unresolved Questions

Không có.

## 11. Next Steps

→ Trigger `/ck:plan` với report này làm context, tạo plan dir `plans/260426-0915-model-support-and-claude-skill/` với phases:
1. KNOWN_MODELS + `--list-models`
2. Skill template + auto-install + `--install-skill`
3. README + version bump + Philosophy reframe
4. Tests
