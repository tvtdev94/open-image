---
title: OpenAI Image CLI Tool
slug: openai-image-cli-tool
date: 2026-04-23 21:48
status: completed
mode: fast
blockedBy: []
blocks: []
---

# OpenAI Image CLI Tool

CLI Python script gọi OpenAI images API: prompt → PNG file. Model name là param để swap model mới không sửa code.

## Context

- **Brainstorm report:** `plans/reports/brainstorm-260423-2148-openai-image-cli-tool.md`
- **Stack:** Python 3.10+, `openai` SDK, argparse stdlib
- **Scope:** 1 file `gen.py` (~150 lines dự kiến), 3 file config

## Phases

| # | Phase | Status | File |
|---|---|---|---|
| 1 | Project setup & scaffolding | done | [phase-01-project-setup.md](phase-01-project-setup.md) |
| 2 | Core implementation (`gen.py`) | done | [phase-02-core-implementation.md](phase-02-core-implementation.md) |
| 3 | Manual testing (4 input methods) | partial (API-required tests blocked — no key with credit) | [phase-03-manual-testing.md](phase-03-manual-testing.md) |

## Key Design (chốt từ brainstorm)

- `--model` param (default `gpt-image-2`) — đường lui future-proof
- `--extra` JSON string — forward params tùy ý (size/quality/n/...)
- Prompt input 4 cách: `--prompt` > `--prompt-file` > stdin > `$EDITOR` fallback
- API key: `--api-key` > env `OPENAI_API_KEY`
- Output: `./output/{YYYYMMDD-HHMMSS}-{uuid8}.png`
- SDK retry: `max_retries=2` ở client init

## Dependencies

- Python >= 3.10
- `openai` (official SDK, version >= 1.x)
- OpenAI API key có credit image generation

## Success Criteria

- 4 input methods hoạt động đúng
- Đổi `--model gpt-image-3` (khi có) → chạy không sửa code
- `--extra` forward params unknown → API ăn OK
- Code < 200 dòng trong `gen.py` (tách module nếu vượt)
- Lưu file đúng path, print absolute path stdout
