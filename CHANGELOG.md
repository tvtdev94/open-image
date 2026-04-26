# Changelog

All notable changes to `open-image` are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions follow [SemVer](https://semver.org/).

## [0.3.2] — 2026-04-26

### Added
- **True zero-step skill install via `.pth`** — `pip install -U open-image` now ships a `.pth` file to `site-packages/`. Python's site initialization auto-loads it on every interpreter startup, syncing `~/.claude/skills/open-image/SKILL.md` against the installed CLI version. No CLI invocation required.
- New module `open_image_skill.py` — stdlib-only skill template + installer (cheap to import during site init, no OpenAI SDK).
- New module `_open_image_skill_bootstrap.py` — site-init entry point that calls the silent installer.
- `setup.py` shim that injects `open-image-skill.pth` into the wheel's purelib root via `build_py` cmdclass override.
- `MANIFEST.in` to include `.pth` in sdist.

### Changed
- `gen.py` re-exports skill API from `open_image_skill` for backwards-compatible test access (`gen.maybe_install_skill_silently`, etc).
- `pyproject.toml` `py-modules` extended to include the two new modules.

## [0.3.1] — 2026-04-26

### Added
- **Skill auto-update on package upgrade** — content sync via embedded version stamp. `pip install -U open-image` followed by any `open-image` invocation now auto-syncs the skill, no `--install-skill` step required.
- `<!-- Auto-installed by open-image CLI v{version}. Sync'd on each run. -->` marker stamp in `SKILL.md` for visibility.
- Tests for upgrade + idempotency behaviors (`test_auto_install_overwrites_old_content`, `test_auto_install_idempotent_when_content_matches`).

### Changed
- README + skill examples now lead with `gpt-image-2` (default) and `gpt-image-1` instead of legacy `dall-e-3`/`dall-e-2`.
- `__version__` sourced from `importlib.metadata.version("open-image")` — single source of truth from `pyproject.toml`.
- `maybe_install_skill_silently()` switched from "install only if missing" to "sync to current content" (idempotent hash compare).

## [0.3.0] — 2026-04-26

### Added
- `KNOWN_MODELS` info-only registry (`gpt-image-1`, `gpt-image-2`, `dall-e-3`, `dall-e-2`) and `--list-models` flag — prints a quick reference table with notes, exits without calling the API.
- Auto-install Claude Code skill at `~/.claude/skills/open-image/SKILL.md` on first CLI run (only if `~/.claude/` exists, never overwrites).
- `--install-skill` flag for forced re-install (always overwrites).
- `pytest>=7.0` optional dev dependency.
- `test_gen.py` — first test suite (17 tests covering models, install logic, prompt resolution, JSON validation).

### Changed
- README — new "Models supported" table and "Claude Code integration" section.
- Philosophy section reframed: skill is markdown only, not a runtime plugin.

## [0.2.0] — 2026-04-23

### Added
- `--keep N` flag — prune old PNGs in `--out-dir` after save, keeping only the newest N (default 50; `0` disables pruning).

### Fixed
- README image links use absolute GitHub raw URLs so they render on PyPI.

## [0.1.0] — 2026-04-23

### Added
- Initial release. Tiny CLI for OpenAI image generation. Prompt in, PNG out.
- Four prompt input methods: `--prompt`, `--prompt-file`, stdin pipe, `$EDITOR` fallback.
- Model-agnostic via `--model` flag (default `gpt-image-2`).
- `--extra` JSON escape hatch for arbitrary `images.generate(**params)` keyword args.
- Output convention: `./output/{YYYYMMDD-HHMMSS}-{uuid8}.png`, absolute paths to stdout.
- API key via `OPENAI_API_KEY` env or `--api-key` flag.
- Built-in `max_retries=2` on the OpenAI client.
