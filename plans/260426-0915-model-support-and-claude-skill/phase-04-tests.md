# Phase 4 — Tests (`test_gen.py` + pytest dev dep)

## Context Links
- **Brainstorm:** `plans/reports/brainstorm-260426-0915-model-support-and-claude-skill.md` — Section 6 (File: test_gen.py)
- **Target files:** `test_gen.py` (new), `pyproject.toml` (add dev dep)

## Overview
- **Priority:** Medium
- **Status:** pending
- **Description:** Pytest suite cover các phần thêm mới (KNOWN_MODELS, install logic, list-models output) + smoke tests cho existing helpers. Không gọi OpenAI API.

## Key Insights
- Repo hiện không có test → đây là test file đầu tiên.
- Không call OpenAI API trong test → mock bằng `monkeypatch` hoặc skip path tới `client.images.generate`.
- Test install logic phải redirect `Path.home()` về `tmp_path` để tránh đụng `~/.claude/` thật của dev.
- Pytest = optional dev dependency, không bắt buộc cho user thường.

## Requirements

### Functional
- Test `KNOWN_MODELS` có đủ 4 keys + values là str non-empty.
- Test `print_models_table()` in stdout chứa 4 model IDs.
- Test `maybe_install_skill_silently()`:
  - Skip khi `~/.claude/` không có (đảm bảo không tạo dir).
  - Skip khi `SKILL.md` đã có (preserve content).
  - Install khi `~/.claude/` có và skill chưa có.
- Test `reinstall_skill_force()`:
  - Abort với SystemExit khi `~/.claude/` không có.
  - Overwrite content khi đã có file.
- Test `resolve_prompt()` 3 paths: inline, file, stdin.
- Test `--extra` invalid JSON → SystemExit.
- Test `--extra` not dict (e.g., list) → SystemExit.

### Non-functional
- Test runtime <1s tổng.
- Không tạo file nào trong real `~/.claude/`.
- Không cần `OPENAI_API_KEY` để chạy tests.

## Architecture

```
test_gen.py (new, ~150 dòng)
├── Fixtures
│   ├── fake_home(tmp_path, monkeypatch)        ← redirect Path.home()
│   └── claude_home(fake_home)                  ← creates {fake_home}/.claude
├── KNOWN_MODELS tests                          ← keys + value types
├── print_models_table tests                    ← capsys
├── maybe_install_skill_silently tests          ← 3 scenarios
├── reinstall_skill_force tests                 ← 2 scenarios
├── resolve_prompt tests                        ← 3 input methods
└── extra JSON validation tests                 ← parse error + non-dict

pyproject.toml
└── [project.optional-dependencies]
    └── dev = ["pytest>=7.0"]
```

## Related Code Files
- **Create:** `test_gen.py`
- **Modify:** `pyproject.toml` (add optional-dependencies)
- **Read:** `gen.py` (post-Phase-2 state) để biết function signatures

## Implementation Steps

### Step 1: Add pytest as optional dev dependency in `pyproject.toml`
```toml
[project.optional-dependencies]
dev = ["pytest>=7.0"]
```

### Step 2: Create `test_gen.py` with fixtures + tests

```python
"""Tests for open-image CLI (gen.py). Pytest, no OpenAI API calls."""

import argparse
import json
import sys
from pathlib import Path

import pytest

import gen


# ---------- Fixtures ----------

@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """Redirect Path.home() to tmp_path so tests don't touch real ~/.claude."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def claude_home(fake_home):
    """fake_home with .claude/ pre-created (simulating Claude Code installed)."""
    (fake_home / ".claude").mkdir()
    return fake_home


# ---------- KNOWN_MODELS ----------

def test_known_models_has_required_keys():
    expected = {"gpt-image-2", "gpt-image-1", "dall-e-3", "dall-e-2"}
    assert expected.issubset(set(gen.KNOWN_MODELS.keys()))


def test_known_models_values_are_nonempty_strings():
    for name, notes in gen.KNOWN_MODELS.items():
        assert isinstance(notes, str), f"{name} notes must be str"
        assert len(notes) > 0, f"{name} notes must not be empty"


# ---------- print_models_table ----------

def test_print_models_table_lists_all_models(capsys):
    gen.print_models_table()
    out = capsys.readouterr().out
    for name in gen.KNOWN_MODELS:
        assert name in out


# ---------- maybe_install_skill_silently ----------

def test_auto_install_skips_when_no_claude_dir(fake_home):
    """No ~/.claude → no-op, no dir created."""
    gen.maybe_install_skill_silently()
    assert not (fake_home / ".claude").exists()


def test_auto_install_creates_skill_when_claude_exists(claude_home):
    """~/.claude exists, skill missing → installed."""
    skill_md = claude_home / ".claude" / "skills" / "open-image" / "SKILL.md"
    assert not skill_md.exists()
    gen.maybe_install_skill_silently()
    assert skill_md.exists()
    assert skill_md.read_text(encoding="utf-8").startswith("---")


def test_auto_install_preserves_existing_skill(claude_home):
    """Skill already exists → not overwritten (preserves user customization)."""
    skill_md = claude_home / ".claude" / "skills" / "open-image" / "SKILL.md"
    skill_md.parent.mkdir(parents=True)
    custom = "# my custom skill\n"
    skill_md.write_text(custom, encoding="utf-8")
    gen.maybe_install_skill_silently()
    assert skill_md.read_text(encoding="utf-8") == custom


def test_auto_install_swallows_oserror(claude_home, monkeypatch):
    """OSError on write → silent fail, no exception propagates."""
    def raise_oserror(*args, **kwargs):
        raise OSError("simulated")
    monkeypatch.setattr(Path, "write_text", raise_oserror)
    # Should NOT raise
    gen.maybe_install_skill_silently()


# ---------- reinstall_skill_force ----------

def test_reinstall_force_aborts_without_claude_dir(fake_home, capsys):
    with pytest.raises(SystemExit) as exc:
        gen.reinstall_skill_force()
    assert exc.value.code != 0


def test_reinstall_force_overwrites_existing(claude_home, capsys):
    skill_md = claude_home / ".claude" / "skills" / "open-image" / "SKILL.md"
    skill_md.parent.mkdir(parents=True)
    skill_md.write_text("# old content\n", encoding="utf-8")
    gen.reinstall_skill_force()
    new_content = skill_md.read_text(encoding="utf-8")
    assert new_content != "# old content\n"
    assert new_content.startswith("---")
    out = capsys.readouterr().out
    assert "Skill installed" in out


# ---------- resolve_prompt ----------

def test_resolve_prompt_inline():
    args = argparse.Namespace(prompt="hello world", prompt_file=None)
    assert gen.resolve_prompt(args) == "hello world"


def test_resolve_prompt_from_file(tmp_path):
    f = tmp_path / "p.txt"
    f.write_text("from file\n", encoding="utf-8")
    args = argparse.Namespace(prompt=None, prompt_file=str(f))
    assert gen.resolve_prompt(args) == "from file"


def test_resolve_prompt_from_stdin(monkeypatch):
    import io
    monkeypatch.setattr(sys, "stdin", io.StringIO("from stdin\n"))
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    args = argparse.Namespace(prompt=None, prompt_file=None)
    assert gen.resolve_prompt(args) == "from stdin"


# ---------- --extra JSON validation ----------
# Note: validation happens inline in main(); we test by simulating json.loads
# behavior, since main() is tightly coupled. Lightweight smoke test instead.

def test_extra_invalid_json_via_main(monkeypatch, fake_home):
    """--extra with invalid JSON should sys.exit before API call."""
    argv = ["gen.py", "--prompt", "x", "--extra", "{not json"]
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with pytest.raises(SystemExit) as exc:
        gen.main()
    assert "invalid JSON" in str(exc.value).lower() or exc.value.code != 0


def test_extra_not_dict_via_main(monkeypatch, fake_home):
    """--extra as JSON list (not dict) should sys.exit."""
    argv = ["gen.py", "--prompt", "x", "--extra", "[1,2,3]"]
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with pytest.raises(SystemExit) as exc:
        gen.main()
    assert exc.value.code != 0
```

### Step 3: Verify install + run
```bash
pip install -e ".[dev]"
pytest -v
```

## Todo List
- [ ] Add `[project.optional-dependencies] dev = ["pytest>=7.0"]` to `pyproject.toml`
- [ ] Create `test_gen.py` with fixtures + ~12 tests
- [ ] Run `pip install -e ".[dev]"` to install pytest
- [ ] Run `pytest -v` → verify all tests pass
- [ ] Confirm no test creates files in real `~/.claude/` (smoke check: `ls ~/.claude/skills/open-image/` mtime stable)
- [ ] Add `__pycache__/`, `.pytest_cache/` to `.gitignore` if missing

## Success Criteria
- `pytest -v` exits 0 với 12+ tests pass
- 0 tests touch real `~/.claude/` directory
- Tests run trong <1s (fast feedback)
- No external network calls (no `requests`, no real `openai.images.generate`)
- `pyproject.toml` build vẫn OK (`python -m build` không crash)

## Risk Assessment
- **Risk:** `gen.main()` được gọi trong test có thể trigger import side effects. **Mitigation:** Module-level code chỉ là constants, function definitions, và `if __name__ == "__main__"` guard → safe.
- **Risk:** stdin test trên Windows vs Unix khác nhau. **Mitigation:** `monkeypatch.setattr(sys.stdin, "isatty", ...)` works cross-platform.
- **Risk:** `monkeypatch.setattr(Path, "home", ...)` có thể leak sang tests khác. **Mitigation:** monkeypatch tự revert sau test, pytest đảm bảo.
- **Risk:** `--extra invalid JSON` test message check fragile. **Mitigation:** Check `exc.value.code != 0` thay vì exact string match.

## Security Considerations
- Tests không có credential — không cần `OPENAI_API_KEY` thật.
- `monkeypatch.setenv` chỉ set trong test scope, không leak.

## Next Steps
→ Plan complete. Run `/ck:cook` để execute từ Phase 1.
