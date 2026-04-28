"""Tests for open-image CLI (gen.py). Pytest, no OpenAI API calls."""

import argparse
import base64
import io
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

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


# ---------- slugify ----------

@pytest.mark.parametrize("text, expected", [
    ("a red fox in snowy forest", "a-red-fox-in-snowy-forest"),
    ("Hello, World!", "hello-world"),
    ("  multi  spaces  ", "multi-spaces"),
    ("ALL CAPS", "all-caps"),
    ("café résumé", "cafe-resume"),
    ("con cáo đỏ trong tuyết", "con-cao-do-trong-tuyet"),
    ("Đường phố Sài Gòn", "duong-pho-sai-gon"),
    ("hổ mang chúa", "ho-mang-chua"),
    ("fox-painting (v2)", "fox-painting-v2"),
    ("", "image"),
    ("   ", "image"),
    ("🦊", "image"),
    ("a" * 60, "a" * 40),
    ("one two three four five six seven eight nine ten eleven", "one-two-three-four-five-six-seven-eight"),
])
def test_slugify(text, expected):
    assert gen.slugify(text) == expected


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


# ---------- KNOWN_STYLES + KNOWN_ASPECTS ----------

def test_known_styles_within_hard_limit():
    """Hard cap of 10 styles forever — see CLAUDE.md / brainstorm doc."""
    assert len(gen.KNOWN_STYLES) <= 10


def test_known_styles_values_are_nonempty_strings():
    for name, frag in gen.KNOWN_STYLES.items():
        assert isinstance(frag, str), f"{name} fragment must be str"
        assert len(frag) > 0, f"{name} fragment must not be empty"


def test_aspect_sizes_are_widthxheight_strings():
    for name, size in gen.ASPECT_SIZES.items():
        assert "x" in size, f"{name} size must look like WIDTHxHEIGHT"


# ---------- apply_style ----------

def test_apply_style_appends_fragment():
    result = gen.apply_style("a cat", "3d-render")
    assert result == "a cat, " + gen.KNOWN_STYLES["3d-render"]


def test_apply_style_unknown_exits_with_helpful_message():
    with pytest.raises(SystemExit) as exc:
        gen.apply_style("a cat", "nonexistent-style")
    assert "--list-styles" in str(exc.value)


def test_apply_style_none_passes_prompt_through():
    assert gen.apply_style("a cat", None) == "a cat"


# ---------- merge_aspect_into_extra ----------

def test_merge_aspect_injects_size_when_extra_has_no_size():
    result = gen.merge_aspect_into_extra({}, "portrait")
    assert result["size"] == "1024x1792"


def test_merge_aspect_does_not_override_explicit_size():
    result = gen.merge_aspect_into_extra({"size": "512x512"}, "portrait")
    assert result["size"] == "512x512"


def test_merge_aspect_none_returns_extra_unchanged():
    result = gen.merge_aspect_into_extra({"quality": "high"}, None)
    assert result == {"quality": "high"}


# ---------- slug invariant when style is applied ----------

def test_slug_derived_from_original_prompt_not_augmented():
    """Filename slug must use the user's original prompt, not the style-augmented one."""
    original = "a red fox in snow"
    augmented = gen.apply_style(original, "3d-render")
    assert gen.slugify(original) == "a-red-fox-in-snow"
    # Sanity: the augmented prompt would slug to something noisier.
    assert gen.slugify(augmented) != gen.slugify(original)


# ---------- --list-styles flag ----------

def test_list_styles_via_main_exits_clean(monkeypatch, fake_home, capsys):
    monkeypatch.setattr(sys, "argv", ["gen.py", "--list-styles"])
    gen.main()
    out = capsys.readouterr().out
    for name in gen.KNOWN_STYLES:
        assert name in out


# ---------- mutually exclusive aspect flags ----------

def test_aspect_flags_are_mutually_exclusive(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["gen.py", "--prompt", "x", "--portrait", "--landscape"])
    with pytest.raises(SystemExit) as exc:
        gen.parse_args()
    assert exc.value.code != 0


# ---------- Skill template content (regression guard) ----------

def test_skill_template_includes_new_v060_sections():
    """SKILL.md must advertise --input-image edit endpoint and self-upgrade workflow.

    Loads open_image_skill.py from this repo directly, so a stale globally-installed
    open-image (shadowed via the .pth bootstrap pre-load) cannot mask a regression.
    """
    import importlib.util
    skill_path = Path(__file__).parent / "open_image_skill.py"
    spec = importlib.util.spec_from_file_location("_local_open_image_skill", skill_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    md = module.SKILL_MD_TEMPLATE
    assert "## Image edit" in md
    assert "## Self-upgrade" in md
    assert "--input-image" in md
    assert "open-image upgrade" in md


# ---------- --input-image / --mask (image edit endpoint) ----------

def _fake_image_response() -> MagicMock:
    item = MagicMock()
    item.b64_json = base64.b64encode(b"PNG").decode()
    item.url = None
    response = MagicMock()
    response.data = [item]
    return response


@patch("gen.OpenAI")
def test_input_image_routes_to_edit_endpoint(mock_openai_cls, tmp_path, monkeypatch, fake_home):
    img = tmp_path / "in.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    out_dir = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", [
        "gen.py", "--input-image", str(img), "--prompt", "add hat",
        "--out-dir", str(out_dir),
    ])
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.images.edit.return_value = _fake_image_response()
    gen.main()
    mock_client.images.edit.assert_called_once()
    mock_client.images.generate.assert_not_called()


@patch("gen.OpenAI")
def test_mask_passed_to_edit_when_provided(mock_openai_cls, tmp_path, monkeypatch, fake_home):
    img = tmp_path / "in.png"
    mask = tmp_path / "m.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    mask.write_bytes(b"\x89PNG\r\n\x1a\n")
    out_dir = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", [
        "gen.py", "--input-image", str(img), "--mask", str(mask),
        "--prompt", "fill", "--out-dir", str(out_dir),
    ])
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.images.edit.return_value = _fake_image_response()
    gen.main()
    kwargs = mock_client.images.edit.call_args.kwargs
    assert kwargs["mask"] == mask
    assert kwargs["image"] == img


@patch("gen.OpenAI")
def test_input_image_with_style_uses_augmented_prompt(mock_openai_cls, tmp_path, monkeypatch, fake_home):
    img = tmp_path / "in.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    out_dir = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", [
        "gen.py", "--input-image", str(img), "--style", "cyberpunk",
        "--prompt", "city street", "--out-dir", str(out_dir),
    ])
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.images.edit.return_value = _fake_image_response()
    gen.main()
    kwargs = mock_client.images.edit.call_args.kwargs
    assert kwargs["prompt"].startswith("city street, ")
    assert "cyberpunk" in kwargs["prompt"]


@patch("gen.OpenAI")
def test_input_image_with_aspect_passes_size_to_edit(mock_openai_cls, tmp_path, monkeypatch, fake_home):
    img = tmp_path / "in.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    out_dir = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", [
        "gen.py", "--input-image", str(img), "--portrait",
        "--prompt", "edit", "--out-dir", str(out_dir),
    ])
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.images.edit.return_value = _fake_image_response()
    gen.main()
    kwargs = mock_client.images.edit.call_args.kwargs
    assert kwargs["size"] == "1024x1792"


def test_mask_without_input_image_errors(tmp_path, monkeypatch, fake_home):
    mask = tmp_path / "m.png"
    mask.write_bytes(b"\x89PNG\r\n\x1a\n")
    monkeypatch.setattr(sys, "argv", [
        "gen.py", "--mask", str(mask), "--prompt", "x",
    ])
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with pytest.raises(SystemExit) as exc:
        gen.main()
    assert "requires --input-image" in str(exc.value)


def test_input_image_path_not_found_errors_clearly(tmp_path, monkeypatch, fake_home):
    missing = tmp_path / "nope.png"
    monkeypatch.setattr(sys, "argv", [
        "gen.py", "--input-image", str(missing), "--prompt", "x",
    ])
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with pytest.raises(SystemExit) as exc:
        gen.main()
    assert str(missing) in str(exc.value)


def test_mask_path_not_found_errors_clearly(tmp_path, monkeypatch, fake_home):
    img = tmp_path / "cat.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    missing_mask = tmp_path / "missing-mask.png"
    monkeypatch.setattr(sys, "argv", [
        "gen.py", "--input-image", str(img), "--mask", str(missing_mask), "--prompt", "x",
    ])
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with pytest.raises(SystemExit) as exc:
        gen.main()
    assert str(missing_mask) in str(exc.value)


# ---------- --upgrade flag + 'upgrade' subcommand ----------

@patch("gen.subprocess.call")
def test_upgrade_flag_invokes_pip_install(mock_call, monkeypatch, fake_home):
    mock_call.return_value = 0
    monkeypatch.setattr(sys, "argv", ["gen.py", "--upgrade"])
    with pytest.raises(SystemExit) as exc:
        gen.main()
    assert exc.value.code == 0
    mock_call.assert_called_once_with(
        [sys.executable, "-m", "pip", "install", "--upgrade", "open-image"]
    )


@patch("gen.subprocess.call")
def test_upgrade_subcommand_invokes_pip_install(mock_call, monkeypatch, fake_home):
    mock_call.return_value = 0
    monkeypatch.setattr(sys, "argv", ["gen.py", "upgrade"])
    with pytest.raises(SystemExit) as exc:
        gen.main()
    assert exc.value.code == 0
    mock_call.assert_called_once_with(
        [sys.executable, "-m", "pip", "install", "--upgrade", "open-image"]
    )


@patch("gen.subprocess.call")
def test_upgrade_detects_pipx_install(mock_call, monkeypatch, fake_home, tmp_path):
    mock_call.return_value = 0
    pipx_python = tmp_path / "pipx" / "venvs" / "open-image" / "bin" / "python"
    pipx_python.parent.mkdir(parents=True)
    pipx_python.touch()
    monkeypatch.setattr(sys, "executable", str(pipx_python))
    monkeypatch.setattr(sys, "argv", ["gen.py", "--upgrade"])
    with pytest.raises(SystemExit):
        gen.main()
    mock_call.assert_called_once_with(["pipx", "upgrade", "open-image"])


@patch("gen.subprocess.call")
def test_upgrade_propagates_exit_code(mock_call, monkeypatch, fake_home):
    mock_call.return_value = 2
    monkeypatch.setattr(sys, "argv", ["gen.py", "--upgrade"])
    with pytest.raises(SystemExit) as exc:
        gen.main()
    assert exc.value.code == 2


@patch("gen.subprocess.call")
def test_upgrade_pipx_substring_false_positive_falls_back_to_pip(mock_call, monkeypatch, fake_home, tmp_path):
    """Path containing 'pipx' / 'open-image' as substrings of dir names (not exact path components)
    must NOT trigger pipx detection — substring match would falsely route to pipx upgrade."""
    mock_call.return_value = 0
    fake = tmp_path / "my-pipx-clone" / "open-image-fork" / "venv" / "bin" / "python"
    fake.parent.mkdir(parents=True)
    fake.touch()
    monkeypatch.setattr(sys, "executable", str(fake))
    monkeypatch.setattr(sys, "argv", ["gen.py", "--upgrade"])
    with pytest.raises(SystemExit):
        gen.main()
    assert mock_call.call_args[0][0][:3] == [str(fake), "-m", "pip"]


def test_input_image_rejects_extra_image_collision(tmp_path, monkeypatch, fake_home):
    img = tmp_path / "cat.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    monkeypatch.setattr(sys, "argv", [
        "gen.py", "--input-image", str(img), "--prompt", "x",
        "--extra", '{"image":"oops.png"}',
    ])
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with pytest.raises(SystemExit) as exc:
        gen.main()
    msg = str(exc.value)
    assert "image" in msg
    assert "--input-image" in msg


def test_input_image_rejects_extra_mask_collision(tmp_path, monkeypatch, fake_home):
    img = tmp_path / "cat.png"
    mask = tmp_path / "m.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    mask.write_bytes(b"\x89PNG\r\n\x1a\n")
    monkeypatch.setattr(sys, "argv", [
        "gen.py", "--input-image", str(img), "--mask", str(mask), "--prompt", "x",
        "--extra", '{"mask":"oops.png"}',
    ])
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with pytest.raises(SystemExit) as exc:
        gen.main()
    assert "mask" in str(exc.value)
