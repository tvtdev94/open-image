---
phase: 2
title: Core Implementation (gen.py)
status: done
priority: high
effort: M
---

# Phase 2: Core Implementation — `gen.py`

## Overview

Implement CLI tool 1 file Python. Start monolith, tách module chỉ khi vượt 200 dòng.

## File to Create

`gen.py` — main CLI entry point

## Component Design

### 1. Argparse setup
```
--prompt          str, optional, inline prompt
--prompt-file     str, optional, path to prompt text
--model           str, default "gpt-image-2"
--extra           str, default "{}", JSON dict of extra API params
--out-dir         str, default "./output"
--api-key         str, optional, fallback to env OPENAI_API_KEY
```

### 2. Prompt resolver (4 cách, ưu tiên theo thứ tự)
```python
def resolve_prompt(args) -> str:
    # 1. --prompt inline
    if args.prompt:
        return args.prompt
    # 2. --prompt-file
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8").strip()
    # 3. stdin (pipe)
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    # 4. $EDITOR fallback
    return open_editor_for_prompt()
```

### 3. `$EDITOR` fallback
```python
def open_editor_for_prompt() -> str:
    editor = os.getenv("EDITOR") or ("notepad" if sys.platform == "win32" else "vi")
    with tempfile.NamedTemporaryFile(
        mode="w+", suffix=".txt", delete=False, encoding="utf-8"
    ) as tf:
        tf.write("# Enter your prompt below. Lines starting with # are ignored.\n")
        tmp_path = tf.name
    subprocess.run([editor, tmp_path], check=True)
    content = Path(tmp_path).read_text(encoding="utf-8")
    os.unlink(tmp_path)
    # strip # comment lines
    lines = [l for l in content.splitlines() if not l.strip().startswith("#")]
    return "\n".join(lines).strip()
```

### 4. API key resolver
```python
def resolve_api_key(args) -> str:
    key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        sys.exit("ERROR: No API key. Set OPENAI_API_KEY env or pass --api-key.")
    return key
```

### 5. OpenAI call
```python
client = OpenAI(api_key=api_key, max_retries=2)
extra = json.loads(args.extra)  # try/except → print lỗi rõ
params = {"model": args.model, "prompt": prompt, **extra}
response = client.images.generate(**params)
```

### 6. Output writer
```python
def save_images(response, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for item in response.data:
        uid = uuid.uuid4().hex[:8]
        fpath = out_dir / f"{timestamp}-{uid}.png"
        if item.b64_json:
            fpath.write_bytes(base64.b64decode(item.b64_json))
        elif item.url:
            fpath.write_bytes(urllib.request.urlopen(item.url).read())
        saved.append(fpath.resolve())
    return saved
```

### 7. Main flow
```python
def main():
    args = parse_args()
    prompt = resolve_prompt(args)
    if not prompt:
        sys.exit("ERROR: Empty prompt.")
    api_key = resolve_api_key(args)
    try:
        extra = json.loads(args.extra)
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR: --extra invalid JSON: {e}")
    client = OpenAI(api_key=api_key, max_retries=2)
    try:
        response = client.images.generate(
            model=args.model, prompt=prompt, **extra
        )
    except Exception as e:
        sys.exit(f"ERROR: API call failed: {e}")
    paths = save_images(response, Path(args.out_dir))
    for p in paths:
        print(p)
```

## Implementation Steps

1. Import stdlib: `argparse`, `os`, `sys`, `json`, `base64`, `uuid`, `subprocess`, `tempfile`, `urllib.request`, `pathlib.Path`, `datetime`
2. Import third-party: `from openai import OpenAI`
3. Viết `parse_args()` — argparse với 6 flags
4. Viết `resolve_prompt(args)` — 4-way priority
5. Viết `open_editor_for_prompt()` — tempfile + subprocess
6. Viết `resolve_api_key(args)` — CLI > env
7. Viết `save_images(response, out_dir)` — handle cả b64 và url
8. Viết `main()` — orchestrate
9. Guard `if __name__ == "__main__": main()`
10. Check dòng code → nếu > 200 tách module (`cli.py`, `prompt_loader.py`, `image_client.py`, `output_writer.py`)
11. `python gen.py --help` chạy OK
12. Smoke test: `python gen.py --prompt "a cat"` → file xuất hiện trong `output/`

## Todo

- [x] argparse với 6 flags, `--help` hiển thị đúng
- [x] `resolve_prompt` ưu tiên đúng 4 cách
- [x] `$EDITOR` fallback chạy trên Windows (notepad) & Linux/Mac (vi/$EDITOR) — code path viết; manual interactive test chưa chạy
- [x] API key resolver: CLI > env, fail rõ nếu thiếu
- [x] `--extra` JSON parse: try/except, error message rõ
- [x] OpenAI client init với `max_retries=2`
- [x] Save image: handle cả `b64_json` và `url`
- [x] Filename format đúng: `{YYYYMMDD-HHMMSS}-{uuid8}.png`
- [x] `output/` auto-create nếu chưa có
- [x] Print absolute path stdout (1 dòng / ảnh)
- [x] Code < 200 dòng → gen.py = 120 dòng
- [x] Compile check: `python -c "import gen"` không lỗi syntax

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| JSON `--extra` sai format | try/except `json.JSONDecodeError`, print hint |
| `$EDITOR` không tồn tại | fallback `notepad`/`vi`, catch `FileNotFoundError` |
| API param không tương thích model | Không validate client-side, forward API error rõ |
| `output/` không ghi được | `mkdir(parents=True, exist_ok=True)`, catch `PermissionError` |
| Prompt rỗng sau resolve | Check `if not prompt` → exit rõ |
| Windows path với ký tự lạ | Dùng `pathlib.Path` throughout |

## Success Criteria

- `python gen.py --prompt "test"` sinh ảnh thành công
- `python gen.py --prompt-file prompts/test.txt` đọc file OK
- `echo "test" | python gen.py` đọc stdin OK
- `python gen.py` (không args) → mở editor
- `python gen.py --model gpt-image-2 --extra '{"size":"1024x1024"}'` forward params
- Print absolute path đúng ảnh lưu

## Next

→ Phase 3: Manual testing tất cả 4 input methods
