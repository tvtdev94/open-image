# CLAUDE.md — project instructions for AI agents

## What this project is

`open-image` — tiny Python CLI that generates PNGs from text prompts via OpenAI's image API. Single-file CLI philosophy + auto-installing Claude Code skill. Published on PyPI as `open-image`.

## Read these before doing anything substantive

| Task | Read first |
|---|---|
| Releasing a new version (PyPI publish) | **[`docs/release-guide.md`](docs/release-guide.md)** — has the exact commands |
| Understanding the auto-skill-install mechanism | `docs/release-guide.md` § 6 + `open_image_skill.py` source |
| Adding a new CLI feature | `gen.py` (~200 lines) + `test_gen.py` |
| Changing skill content | `open_image_skill.py` `SKILL_MD_TEMPLATE` constant |
| Reading recent design decisions | `plans/reports/brainstorm-*.md` (newest first) |
| Versioning rules | `docs/release-guide.md` § 5 |

## Architecture in 30 seconds

```
gen.py                          # OpenAI CLI: arg parsing, image gen, save, prune
open_image_skill.py             # Skill template + silent installer (stdlib only)
_open_image_skill_bootstrap.py  # Site-init bootstrap that calls the installer
open-image-skill.pth            # Triggers bootstrap on every Python startup (lives in site-packages)
setup.py                        # build_py override that ships the .pth into wheel purelib
```

When `pip install open-image` runs, the wheel's `.pth` lands in `site-packages/`. Python's `site.py` auto-loads it on every interpreter startup → bootstrap → silent install of `~/.claude/skills/open-image/SKILL.md`. **No CLI invocation required.** Idempotent (only writes on content mismatch).

## Release flow (the 5-second version)

```bash
# Bump pyproject.toml + CHANGELOG.md, then:
git commit -am "release: vX.Y.Z" && git push
gh release create vX.Y.Z --target $(git rev-parse HEAD) --title "..." --notes "..."
# → PyPI gets vX.Y.Z in ~30 seconds via .github/workflows/release.yml
```

**DO NOT** run `python -m build` or `twine upload` manually. Pipeline handles it.

## Hard rules

- Honor YAGNI / KISS / DRY. This codebase is intentionally tiny — resist scope creep.
- Single-file philosophy for `gen.py` (~280 lines is fine). Extract only when stdlib-only modules are required (e.g., `open_image_skill.py` for cheap site-init import).
- API is the source of truth: never client-side validate model names or `--extra` params. Forward and let the OpenAI API error surface.
- Auto-install must be silent and never block CLI execution. Swallow all `OSError` in `maybe_install_skill_silently`.
- Tests must pass on **all 12 CI jobs** (Linux/macOS/Windows × Python 3.10/3.11/3.12/3.13) before tagging.
- Never commit `~/.pypirc`, tokens, API keys, or `.env` files.
- Never write to `~/.claude/` if `~/.claude/` doesn't exist (don't bootstrap a Claude Code config dir for users who don't use it).

## Plans + reports

- Active and historical plans: `plans/{date}-{slug}/`
- Brainstorm + agent reports: `plans/reports/{type}-{date}-{slug}.md`
- Plans frontmatter uses `status: pending|in-progress|completed|cancelled` and `blockedBy/blocks` for cross-plan deps.

## When in doubt

Read `docs/release-guide.md`. It has answers for: how to release, what files do what, how to verify, common pitfalls, and how to migrate to PyPI Trusted Publishing.
