---
phase: 3
title: Manual Testing
status: partial
priority: medium
effort: S
---

# Phase 3: Manual Testing

## Overview

Test 4 input methods + model/extra swap + error paths. Không viết unit test (YAGNI cho 1 script CLI nhỏ).

## Prerequisites

- `.env` có `OPENAI_API_KEY` hợp lệ (có credit image gen)
- `pip install -r requirements.txt` chạy xong

## Test Matrix

### A. Input methods (golden path)

| # | Command | Expected |
|---|---|---|
| A1 | `python gen.py --prompt "a red fox"` | Sinh 1 ảnh trong `output/`, print path |
| A2 | Tạo `prompts/test.txt` có text, `python gen.py --prompt-file prompts/test.txt` | Đọc file, sinh ảnh |
| A3 | `echo "a blue cat" \| python gen.py` | Đọc stdin, sinh ảnh |
| A4 | `python gen.py` (không args, TTY) | Mở notepad/editor, gõ prompt, save & close → sinh ảnh |

### B. Model & extra params

| # | Command | Expected |
|---|---|---|
| B1 | `python gen.py --prompt "test" --model gpt-image-2` | Chạy OK |
| B2 | `python gen.py --prompt "test" --extra '{"size":"1024x1024"}'` | Forward size |
| B3 | `python gen.py --prompt "test" --extra '{"n":2}'` | Sinh 2 ảnh, 2 file khác nhau |
| B4 | `python gen.py --prompt "test" --model dall-e-3 --extra '{"size":"1024x1024","quality":"standard"}'` | Model khác vẫn chạy (test đường lui) |

### C. Error paths

| # | Command | Expected |
|---|---|---|
| C1 | Bỏ env + không `--api-key` | Exit với message "No API key..." |
| C2 | `python gen.py --prompt "x" --extra 'not-json'` | Exit với "invalid JSON" |
| C3 | `python gen.py --prompt "x" --model fake-model-xyz` | Forward API error rõ |
| C4 | `python gen.py --prompt ""` (empty) | Exit với "Empty prompt" |

### D. Output correctness

| # | Check | Expected |
|---|---|---|
| D1 | File sinh trong `output/` đúng format `{YYYYMMDD-HHMMSS}-{8hex}.png` | Tên match regex |
| D2 | File là PNG hợp lệ (mở xem được) | Ảnh hiển thị đúng |
| D3 | `--out-dir ./custom-dir` | Ảnh lưu vào `custom-dir/`, auto-create |
| D4 | Gen 2 lần liên tiếp | 2 file không trùng tên (uuid khác) |

## Todo

- [ ] A1 inline prompt — BLOCKED: cần API key + credit
- [ ] A2 prompt-file — BLOCKED: cần API key + credit
- [ ] A3 stdin pipe — path reach tới API call (xác nhận 401 forward đúng); sinh ảnh chưa test
- [ ] A4 $EDITOR fallback — interactive, user chạy tay
- [ ] B1 default model — BLOCKED: cần API key + credit
- [ ] B2 extra size — BLOCKED: cần API key + credit
- [ ] B3 extra n>1 sinh nhiều file — BLOCKED: cần API key + credit
- [ ] B4 model khác (dall-e-3) — BLOCKED: cần API key + credit
- [x] C1 no API key error
- [x] C2 invalid JSON error
- [x] C3 fake model error forward — xác nhận bằng fake key (API error surface rõ)
- [x] C4 empty prompt error
- [ ] D1 filename format đúng — BLOCKED: cần file sinh thật
- [ ] D2 PNG hợp lệ — BLOCKED
- [ ] D3 custom out-dir — BLOCKED
- [ ] D4 2 file không trùng — BLOCKED

## Bug Handling

Nếu test fail → quay lại phase 2, fix, test lại. Không pass thì không tick ✓.

## Success Criteria

- 16/16 test case pass
- Tool stable trên Windows (PowerShell + Git Bash)
- Đường lui `--model` + `--extra` verify được với model khác (B4)

## Deliverable

Tool `gen.py` ready-to-use. Document usage ngắn trong README.md (nếu user muốn, không bắt buộc).
