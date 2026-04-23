---
type: brainstorm
date: 2026-04-23 21:48
slug: openai-image-cli-tool
status: approved
---

# Brainstorm: OpenAI Image Generation CLI Tool

## Problem Statement

User có OpenAI API key, cần tool CLI Python: input prompt → output ảnh. Yêu cầu đường lui: tên model là param để swap model tương lai (gpt-image-3, dall-e-4...) không cần sửa code.

## Requirements

**Functional:**
- Nhận prompt qua 4 cách: `--prompt` inline, `--prompt-file`, stdin pipe, $EDITOR fallback
- Gọi OpenAI images API với model configurable
- Lưu ảnh ra file local, print absolute path stdout
- Hỗ trợ params tùy ý qua `--extra` JSON (future-proof cho params model mới)

**Non-functional:**
- KISS: 1 file Python, < 200 dòng (tách module nếu vượt)
- Min deps: chỉ `openai` SDK
- Scriptable + interactive đều chạy được
- Error messages rõ ràng (auth, content policy, rate limit)

## Evaluated Approaches

### Form factor
| Approach | Chọn | Lý do |
|---|---|---|
| CLI Python | ✓ | Script, automate, min deps |
| Web UI FastAPI | ✗ | Over-engineering, cần server |
| Python lib | ✗ | Không có CLI entry |
| REST wrapper | ✗ | Overkill cho cá nhân |

### Model abstraction (đường lui)
| Approach | Chọn | Lý do |
|---|---|---|
| `--model` + `--extra` JSON | ✓ | Model mới + params mới đều pass qua không cần update code |
| Chỉ `--model`, params cố định | ✗ | Vỡ khi model mới có params riêng |
| Config YAML profiles | ✗ | Over-engineering |

### Input method (prompt dài)
| Approach | Chọn | Lý do |
|---|---|---|
| CLI inline + file + stdin + $EDITOR | ✓ | Cover tất cả use case: script, reuse, pipe, interactive |
| Chỉ CLI inline | ✗ | Awkward với prompt dài, PowerShell escape khó |
| Web UI textarea | ✗ | Không chọn form factor web |

### Retry
| Approach | Chọn | Lý do |
|---|---|---|
| SDK built-in `max_retries=2` | ✓ | 0 dòng code thêm, SDK đã handle |
| Fail fast | ✗ | Rate limit transient nên retry nhẹ là hợp lý |
| Custom exponential | ✗ | Over-engineering |

### Filename
| Approach | Chọn | Lý do |
|---|---|---|
| `{timestamp}-{uuid-short}.png` | ✓ | Unique tuyệt đối, sort theo time OK |
| `{timestamp}-{slug}.png` | ✗ | Có thể conflict khi gen cùng prompt trong 1s |
| Chỉ timestamp | ✗ | Conflict nếu n>1 |

## Final Solution

### Usage
```bash
# Inline prompt
python gen.py --prompt "a red fox in snow"

# File prompt (reuse, git-track prompts)
python gen.py --prompt-file prompts/fox.txt

# Pipe
cat prompts/fox.txt | python gen.py

# Interactive: mở $EDITOR (default notepad Windows / vi Linux)
python gen.py

# Đổi model + extra params
python gen.py --prompt "..." --model gpt-image-2 \
              --extra '{"size":"2048x2048","quality":"high","n":2}'
```

### CLI args
| Flag | Default | Note |
|---|---|---|
| `--prompt` | none | Inline text |
| `--prompt-file` | none | Path to txt |
| `--model` | `gpt-image-2` | Override cho model mới |
| `--extra` | `{}` | JSON string, merge vào API params |
| `--out-dir` | `./output` | Thư mục lưu ảnh |
| `--api-key` | env `OPENAI_API_KEY` | CLI > env |

### File structure
```
C:\w\open-image\
├── gen.py              # main (~150 lines predicted)
├── requirements.txt    # openai>=1.x
├── prompts/            # optional, user lưu prompt dài
├── output/             # auto-created, ảnh output
├── .env.example        # OPENAI_API_KEY=sk-...
└── .gitignore          # .env, output/, __pycache__, prompts/*.local.txt
```

### Flow
1. Parse args (argparse stdlib)
2. Resolve prompt: `--prompt` > `--prompt-file` > stdin (nếu piped) > $EDITOR tempfile
3. Resolve API key: `--api-key` > env `OPENAI_API_KEY` > fail
4. Parse `--extra` JSON → dict
5. Build params: `{model, prompt, **extra}` → `client.images.generate(**params)` (client init với `max_retries=2`)
6. Response: mỗi image → decode b64_json hoặc download url
7. Save: `{out_dir}/{YYYYMMDD-HHMMSS}-{uuid4_short}.png`
8. Print absolute path(s) stdout

### Modularization rule
- Start: 1 file `gen.py`
- Nếu vượt 200 dòng → tách:
  - `cli.py` — argparse setup
  - `prompt_loader.py` — 4 cách resolve prompt
  - `image_client.py` — OpenAI wrapper
  - `output_writer.py` — save file + filename gen

## Implementation Considerations

- **JSON parse error** trong `--extra`: try/except, print lỗi rõ
- **$EDITOR trên Windows**: default `notepad`, Linux dùng `$EDITOR` env hoặc `vi`
- **stdin detection**: `sys.stdin.isatty()` — false khi piped
- **n > 1 trong extra**: loop save nhiều file
- **b64 vs url response**: gpt-image-2 default b64, dall-e default url → handle cả hai
- **Filename collision**: uuid4 hex 8 ký tự đủ unique
- **Slug/escape prompt trong filename**: không dùng slug (đã chọn uuid) → tránh bug ký tự đặc biệt

## Risks

| Risk | Mitigation |
|---|---|
| `--extra` JSON sai format | try/except, print lỗi + show example |
| API param không compatible với model | Forward API error message rõ ràng |
| `$EDITOR` không tồn tại | Fallback `notepad`/`vi`, catch `FileNotFoundError` |
| Output dir không ghi được | Tạo dir trước với `mkdir(parents=True, exist_ok=True)` |
| Prompt rỗng sau resolve | Validate, fail với message rõ |

## Success Criteria

- 1 lệnh sinh 1 ảnh, lưu đúng path
- 4 input methods đều hoạt động
- Đổi `--model gpt-image-3` khi model mới ra → chạy không sửa code
- `--extra` chứa param mới (chưa biết hôm nay) → forward đến API OK
- Code dưới 200 dòng trong 1 file (hoặc tách module hợp lý nếu vượt)

## Next Steps

- Chạy `/ck:plan` với context này → tạo plan chi tiết có phases + TODO
- Hoặc implement thẳng 1 file `gen.py` nếu scope nhỏ đủ

## Unresolved Questions

None — tất cả đã chốt qua 3 vòng Q&A.
