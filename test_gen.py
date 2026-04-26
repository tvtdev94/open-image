"""Tests for open-image CLI (gen.py). Pytest, no OpenAI API calls."""

import argparse
import io
import sys
from pathlib import Path

import pytest

import gen


# ---------- Fixtures ----------

@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """Redirect Path.home() to tmp_path so tests never touch real ~/.claude."""
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
    """~/.claude exists, skill missing → installed silently."""
    skill_md = claude_home / ".claude" / "skills" / "open-image" / "SKILL.md"
    assert not skill_md.exists()
    gen.maybe_install_skill_silently()
    assert skill_md.exists()
    content = skill_md.read_text(encoding="utf-8")
    assert content.startswith("---")
    assert "open-image" in content


def test_auto_install_overwrites_old_content(claude_home):
    """Old skill content (e.g. from previous CLI version) → overwritten on next run."""
    skill_md = claude_home / ".claude" / "skills" / "open-image" / "SKILL.md"
    skill_md.parent.mkdir(parents=True)
    old_content = "# old skill from previous version\n"
    skill_md.write_text(old_content, encoding="utf-8")
    gen.maybe_install_skill_silently()
    new = skill_md.read_text(encoding="utf-8")
    assert new != old_content
    assert new.startswith("---")
    assert "open-image CLI v" in new  # version stamp present


def test_auto_install_idempotent_when_content_matches(claude_home, monkeypatch):
    """When on-disk content already matches desired template → no rewrite."""
    skill_md = claude_home / ".claude" / "skills" / "open-image" / "SKILL.md"
    skill_md.parent.mkdir(parents=True)
    skill_md.write_text(gen._render_skill_md(), encoding="utf-8")

    write_calls: list[str] = []
    original_write = Path.write_text

    def track(self, *args, **kwargs):
        write_calls.append(self.name)
        return original_write(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", track)
    gen.maybe_install_skill_silently()
    assert "SKILL.md" not in write_calls


def test_auto_install_swallows_oserror(claude_home, monkeypatch):
    """OSError on write → silent fail, no exception propagates."""
    original_write = Path.write_text

    def maybe_raise(self, *args, **kwargs):
        if self.name == "SKILL.md":
            raise OSError("simulated")
        return original_write(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", maybe_raise)
    gen.maybe_install_skill_silently()  # must NOT raise


# ---------- reinstall_skill_force ----------

def test_reinstall_force_aborts_without_claude_dir(fake_home):
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


def test_resolve_prompt_strips_whitespace():
    args = argparse.Namespace(prompt="  spaced  ", prompt_file=None)
    assert gen.resolve_prompt(args) == "spaced"


def test_resolve_prompt_from_file(tmp_path):
    f = tmp_path / "p.txt"
    f.write_text("from file\n", encoding="utf-8")
    args = argparse.Namespace(prompt=None, prompt_file=str(f))
    assert gen.resolve_prompt(args) == "from file"


def test_resolve_prompt_from_stdin(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("from stdin\n"))
    args = argparse.Namespace(prompt=None, prompt_file=None)
    assert gen.resolve_prompt(args) == "from stdin"


# ---------- --extra JSON validation (via main) ----------

def test_extra_invalid_json_via_main(monkeypatch, fake_home):
    monkeypatch.setattr(sys, "argv", ["gen.py", "--prompt", "x", "--extra", "{not json"])
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with pytest.raises(SystemExit) as exc:
        gen.main()
    assert exc.value.code != 0


def test_extra_not_dict_via_main(monkeypatch, fake_home):
    monkeypatch.setattr(sys, "argv", ["gen.py", "--prompt", "x", "--extra", "[1,2,3]"])
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with pytest.raises(SystemExit) as exc:
        gen.main()
    assert exc.value.code != 0


def test_empty_prompt_via_main(monkeypatch, fake_home):
    monkeypatch.setattr(sys, "argv", ["gen.py", "--prompt", "   "])
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with pytest.raises(SystemExit) as exc:
        gen.main()
    assert exc.value.code != 0


# ---------- --list-models flag (smoke test via main) ----------

def test_list_models_via_main_exits_clean(monkeypatch, fake_home, capsys):
    monkeypatch.setattr(sys, "argv", ["gen.py", "--list-models"])
    gen.main()  # should return cleanly (no SystemExit)
    out = capsys.readouterr().out
    for name in gen.KNOWN_MODELS:
        assert name in out
