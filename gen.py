"""OpenAI image generation CLI. Prompt in, PNG out."""

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

from openai import OpenAI


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate images via OpenAI images API."
    )
    p.add_argument("--prompt", help="Inline prompt text.")
    p.add_argument("--prompt-file", help="Path to a file containing the prompt.")
    p.add_argument("--model", default="gpt-image-2", help="Model name (default: gpt-image-2).")
    p.add_argument("--extra", default="{}", help="JSON dict of extra API params forwarded to images.generate.")
    p.add_argument("--out-dir", default="./output", help="Output directory (default: ./output).")
    p.add_argument("--api-key", help="OpenAI API key; falls back to $OPENAI_API_KEY.")
    p.add_argument("--keep", type=int, default=50, help="Keep only N newest PNGs in --out-dir after save; 0 disables pruning (default: 50).")
    return p.parse_args()


def open_editor_for_prompt() -> str:
    editor = os.getenv("EDITOR") or ("notepad" if sys.platform == "win32" else "vi")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as tf:
        tf.write("# Enter your prompt below. Lines starting with # are ignored.\n")
        tmp_path = tf.name
    try:
        subprocess.run([editor, tmp_path], check=True)
        content = Path(tmp_path).read_text(encoding="utf-8")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    lines = [ln for ln in content.splitlines() if not ln.lstrip().startswith("#")]
    return "\n".join(lines).strip()


def resolve_prompt(args: argparse.Namespace) -> str:
    if args.prompt is not None:
        return args.prompt.strip()
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8").strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return open_editor_for_prompt()


def resolve_api_key(args: argparse.Namespace) -> str:
    key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        sys.exit("ERROR: No API key. Set OPENAI_API_KEY env or pass --api-key.")
    return key


def save_images(response, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    saved: list[Path] = []
    for item in response.data:
        uid = uuid.uuid4().hex[:8]
        fpath = out_dir / f"{timestamp}-{uid}.png"
        b64 = getattr(item, "b64_json", None)
        url = getattr(item, "url", None)
        if b64:
            fpath.write_bytes(base64.b64decode(b64))
        elif url:
            with urllib.request.urlopen(url) as resp:
                fpath.write_bytes(resp.read())
        else:
            sys.exit("ERROR: API response item has neither b64_json nor url.")
        saved.append(fpath.resolve())
    return saved


def prune_old_images(out_dir: Path, keep: int) -> None:
    if keep <= 0:
        return
    pngs = sorted(out_dir.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    for stale in pngs[keep:]:
        try:
            stale.unlink()
        except OSError:
            pass


def main() -> None:
    args = parse_args()

    prompt = resolve_prompt(args)
    if not prompt:
        sys.exit("ERROR: Empty prompt.")

    api_key = resolve_api_key(args)

    try:
        extra = json.loads(args.extra)
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR: --extra invalid JSON: {e}")
    if not isinstance(extra, dict):
        sys.exit("ERROR: --extra must be a JSON object (dict).")

    client = OpenAI(api_key=api_key, max_retries=2)

    try:
        response = client.images.generate(model=args.model, prompt=prompt, **extra)
    except Exception as e:
        sys.exit(f"ERROR: API call failed: {e}")

    out_dir = Path(args.out_dir)
    try:
        paths = save_images(response, out_dir)
    except PermissionError as e:
        sys.exit(f"ERROR: Cannot write to output dir: {e}")

    prune_old_images(out_dir, args.keep)

    for p in paths:
        print(p)


if __name__ == "__main__":
    main()
