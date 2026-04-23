---
type: brainstorm
date: 2026-04-23 22:09
slug: mcp-api-extension-decision
decision: reject
---

# Brainstorm: Có nên thêm MCP / HTTP API cho `gen.py`?

## Context

Tool hiện tại: `gen.py` CLI, gọi OpenAI images API, output PNG. User hỏi có nên mở rộng thêm MCP server + HTTP API để AI agent dùng không.

## Evaluated Options

| # | Hướng | Effort | Verdict |
|---|---|---|---|
| A | Giữ CLI | 0 | ✅ **Chọn** |
| B | CLI + MCP server (path output) | S | ❌ YAGNI |
| C | CLI + MCP (inline image) | S-M | ❌ user không cần inline |
| D | CLI + MCP + HTTP API | M | ❌ over-engineer |

## Decision: Option A — Keep CLI only

### Rationale

1. **Agent target = Claude Code (có Bash)** → `bash python gen.py ...` đã work. Đã verify qua 4 test case thật, ảnh sinh OK.
2. **Output = path file** → user không khai thác benefit inline-image của MCP → MCP chỉ còn lợi ích "typed schema" marginal.
3. **YAGNI**: thêm MCP = extra file + dependency (`fastmcp`/SDK) + maintenance, không giải quyết pain thực tế.
4. **Không remote use case** → HTTP API không có lý do.

### Cost tránh được

- ~100-300 LoC wrapper
- `fastmcp` hoặc `mcp` SDK dependency
- Stdio lifecycle debug
- 2 interface phải sync khi đổi schema

## When to Revisit

Thêm MCP **khi nào** một trong các điều kiện sau xuất hiện:
- Bắt đầu dùng Claude Desktop (hoặc agent không có Bash)
- Muốn agent thấy image inline trong tool result (đỡ step Read file)
- Build ecosystem nhiều tool chung 1 MCP entry

Thêm HTTP API **khi nào**:
- Deploy ra server, gọi từ remote agent / web UI
- Multi-user / team share

## Implementation Considerations (nếu revisit)

Nếu sau này thêm, nguyên tắc:
- Refactor `gen.py` → `core.py` (resolve_prompt / generate / save) + `cli.py` + `mcp.py`, share core
- MCP tool schema: `generate_image(prompt, model, size, n, out_dir) -> {paths: [...]}`
- Giữ CLI làm golden path để test nhanh không qua MCP client

## Success Criteria

- Plan `260423-2148-openai-image-cli-tool` đóng ở trạng thái CLI-only
- Không phát sinh code thêm
- Quyết định log lại để tránh re-debate

## Unresolved Questions

None.
