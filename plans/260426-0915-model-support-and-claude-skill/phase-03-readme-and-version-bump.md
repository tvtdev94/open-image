# Phase 3 — README + Version Bump + Philosophy Reframe

## Context Links
- **Brainstorm:** `plans/reports/brainstorm-260426-0915-model-support-and-claude-skill.md` — Section 6 (File: README.md, pyproject.toml)
- **Target files:** `README.md`, `pyproject.toml`

## Overview
- **Priority:** Medium
- **Status:** pending
- **Description:** Đồng bộ docs với features mới + bump version + reframe Philosophy section để nhất quán với skill markdown.

## Key Insights
- README hiện ghi `"~120 lines"` → cần update con số (~230 dòng) HOẶC bỏ con số đi (giữ generic).
- Philosophy "no plugin system" mâu thuẫn skill auto-install → reframe: "skill is markdown docs, not runtime".
- Bảng Flags cần thêm `--list-models` và `--install-skill`.
- Bảng Models phải đồng bộ KNOWN_MODELS (4 models).

## Requirements

### Functional
- README có section riêng "Claude Code integration" giải thích auto-install + manual `--install-skill`.
- Bảng "Model notes" thay bằng bảng đầy đủ 4 models với notes (đồng bộ `KNOWN_MODELS`).
- Bảng "Flags" thêm 2 dòng cho `--list-models` và `--install-skill`.
- Philosophy section reframed.
- `pyproject.toml` version bump.

### Non-functional
- Giữ tone hiện tại (concise, opinionated, kỹ thuật).
- Không thêm hero/banner mới — đã đủ visuals.
- Không phá link absolute đến `raw.githubusercontent.com` (PyPI requirement).

## Architecture

```
README.md
├── Hero / badges                          ← keep
├── Why another CLI?                       ← keep (update line count)
├── Features
│   ├── Four ways to feed a prompt         ← keep
│   ├── Model-agnostic by design           ← keep
│   └── --extra escape hatch               ← keep
├── Install                                ← keep
├── Setup                                  ← keep
├── Flags                                  ← UPDATE: add --list-models, --install-skill
├── Output                                 ← keep
├── Gallery                                ← keep
├── Error handling                         ← keep
├── Model notes                            ← REPLACE: full table with 4 models
├── [NEW] Claude Code integration          ← INSERT after Model notes
├── Philosophy                             ← UPDATE: reframe plugin system line
└── License                                ← keep

pyproject.toml
└── version = "0.2.0" → "0.3.0"
```

## Related Code Files
- **Modify:** `README.md`, `pyproject.toml`
- **Read:** `KNOWN_MODELS` in `gen.py` (post-Phase-1) để đồng bộ notes

## Implementation Steps

### Step 1: Bump version in `pyproject.toml`
Đổi `version = "0.2.0"` → `version = "0.3.0"`.

### Step 2: Update Flags table in `README.md`
Thêm 2 rows cuối:
```markdown
| `--list-models` | — | List known OpenAI image models with notes, then exit |
| `--install-skill` | — | Re-install Claude Code skill at `~/.claude/skills/open-image/` (overwrites) |
```

### Step 3: Replace "Model notes" section
Thay nội dung bullet list hiện tại bằng:
```markdown
## Models supported

The CLI is model-agnostic — `--model` accepts any string. These are known to work today; pass any future model ID without code change.

| Model | Notes |
|---|---|
| `gpt-image-2` | Default. Requires org verification on OpenAI dashboard. Returns b64_json. |
| `gpt-image-1` | Newer GPT image model. Supports `input_fidelity`, `transparency`, `output_format`. |
| `dall-e-3` | `n=1` only. Sizes: 1024x1024 / 1792x1024 / 1024x1792. `quality`: standard / hd. `style`: vivid / natural. Pass `response_format=b64_json` via `--extra` for offline storage. |
| `dall-e-2` | `n>1` supported. Sizes: 256x256 / 512x512 / 1024x1024. |

Run `open-image --list-models` to print this table at any time.
```

### Step 4: Insert "Claude Code integration" section
Đặt sau "Models supported", trước "Philosophy":
```markdown
---

## Claude Code integration

If you use [Claude Code](https://claude.com/claude-code), `open-image` ships a Claude skill that teaches the agent how to use this CLI — no manual prompt setup.

- **Auto-install:** First time you run any `open-image` command, the skill is silently installed at `~/.claude/skills/open-image/SKILL.md` (only if `~/.claude/` exists, never overwrites).
- **Re-install / update:** After upgrading the package, run once to refresh the skill content:
  ```bash
  open-image --install-skill
  ```

Once installed, Claude Code will know when to call `open-image`, which models exist, how `--extra` works, and how to capture stdout paths.

If you don't use Claude Code, nothing happens — the auto-install gracefully no-ops when `~/.claude/` is absent.
```

### Step 5: Update Philosophy section
Tìm dòng:
```markdown
- **YAGNI** — no MCP server, no HTTP wrapper, no plugin system. If your agent has a shell, it can use this.
```
Thay bằng:
```markdown
- **YAGNI** — no MCP server, no HTTP wrapper, no runtime plugins. The optional Claude Code skill is just markdown — Claude reads it, no daemon, no IPC. If your agent has a shell, it can use this.
```

### Step 6: Update line count mention (optional)
Tìm `"one file, ~120 lines, pure stdlib + openai"` → đổi `~120 lines` → `~230 lines` HOẶC bỏ con số (linh hoạt hơn cho future).

Đề xuất giữ vibe nhưng update: `"one file, ~230 lines, pure stdlib + openai"`.

## Todo List
- [ ] Bump `version` in `pyproject.toml` to `0.3.0`
- [ ] Update Flags table in README (add `--list-models`, `--install-skill`)
- [ ] Replace "Model notes" → "Models supported" with 4-row table
- [ ] Insert "Claude Code integration" section
- [ ] Update Philosophy YAGNI line
- [ ] Update line count in "Why another CLI?" section
- [ ] Verify all `raw.githubusercontent.com` links unchanged
- [ ] Read README in markdown previewer or `head/tail` to spot format bugs

## Success Criteria
- `pyproject.toml` shows `version = "0.3.0"`
- README Flags table has 8 rows (was 6 + 2 new)
- README "Models supported" table has exactly 4 rows
- README "Claude Code integration" section exists between Models and Philosophy
- Philosophy mentions skill = markdown
- README line count check: should be ~250 lines (was 224)
- No broken markdown (check no orphan `---`, balanced code fences)

## Risk Assessment
- **Risk:** Markdown formatting break (table alignment, code fence). **Mitigation:** Read full file after edit, eyeball.
- **Risk:** PyPI re-render images broken. **Mitigation:** Không động vào image links (absolute GitHub raw URLs).
- **Risk:** Line count "~230" stale next refactor. **Mitigation:** Hoặc bỏ luôn con số nếu thấy noisy.

## Security Considerations
Không có — pure docs change.

## Next Steps
→ Phase 4 (Tests)
