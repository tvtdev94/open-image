# Release Guide — for AI agents and humans

**Audience:** future AI sessions + maintainers. Read this before running a release.
**TL;DR:** edit version → commit → `gh release create` → done. PyPI auto-publish in ~30s.

---

## 1. Release a new version (the only steps you need)

```bash
# 1. Bump version in pyproject.toml
#    e.g. version = "0.3.3" → version = "0.4.0"

# 2. Add a [X.Y.Z] entry at the TOP of CHANGELOG.md (Keep a Changelog format)
#    Sections to use as needed: Added / Changed / Fixed / Removed / Security

# 3. Run tests locally (must pass)
python -m pytest -q

# 4. Commit + push
git add pyproject.toml CHANGELOG.md
git commit -m "release: vX.Y.Z - <one-line summary>"
git push origin main

# 5. Create GitHub release (this triggers the auto-publish workflow)
SHA=$(git rev-parse HEAD)
gh release create vX.Y.Z --target "$SHA" \
  --title "vX.Y.Z - <human-friendly title>" \
  --notes "<short notes; reference CHANGELOG.md for details>"

# 6. Verify (optional, ~30s wait)
gh run watch                                  # latest workflow run
curl -sf "https://pypi.org/pypi/open-image/X.Y.Z/json" | python -m json.tool | grep version
```

That's it. **DO NOT** run `python -m build` or `twine upload` manually. The workflow handles it.

---

## 2. What happens automatically

```
gh release create vX.Y.Z
   → tag pushed to github
   → .github/workflows/release.yml fires (event: push tags 'v*.*.*')
   → ubuntu runner: checkout → setup-python 3.12 → pip install build → python -m build
   → uploads sdist + wheel to PyPI via pypa/gh-action-pypi-publish@release/v1
   → auth via secret PYPI_API_TOKEN (already configured)
   → skip-existing: true (idempotent — re-running same tag won't error)
```

Total time: ~30 seconds from `gh release create` to PyPI live.

---

## 3. Files in the release pipeline

| File | Purpose | Touch when… |
|---|---|---|
| `pyproject.toml` | `version = "X.Y.Z"` is the source of truth | Every release |
| `CHANGELOG.md` | Human-readable history (Keep a Changelog format) | Every release |
| `.github/workflows/release.yml` | Auto-publish on tag push | Almost never (pin updates only) |
| `.github/workflows/test.yml` | CI matrix (3 OS × 4 Python) on push/PR | Almost never |
| `setup.py` | `build_py` cmdclass injects `.pth` to wheel purelib | Never (working setup) |
| `MANIFEST.in` | Includes `.pth` + `setup.py` in sdist | Never |
| `open-image-skill.pth` | One-line site-init trigger | Never |
| `open_image_skill.py` | Skill template + installer (stdlib-only) | When skill content changes |
| `_open_image_skill_bootstrap.py` | Imports skill module + calls installer | Never |
| `gen.py` | OpenAI CLI logic + re-exports skill API | When CLI features change |
| `test_gen.py` | pytest suite (44 tests) | When adding/changing functionality |
| `~/.pypirc` | NOT used by pipeline | Can be deleted; only used for local manual upload |

---

## 4. Credentials

- **GitHub secret `PYPI_API_TOKEN`** — set via `gh secret set PYPI_API_TOKEN --body <token>`. Already configured. Never echoed in logs.
- **No local credential file required** for releases (pipeline is the only release path).
- **Rotation:** if token leaks, regenerate on https://pypi.org/manage/account/token/, then `gh secret set PYPI_API_TOKEN --body <new-token>`. Workflow uses it automatically.

---

## 5. Versioning rules (SemVer)

| Change | Bump | Example |
|---|---|---|
| Bug fix, no new feature | PATCH | `0.3.3 → 0.3.4` |
| New feature, backward-compatible | MINOR | `0.3.3 → 0.4.0` |
| Breaking change | MAJOR | `0.x → 1.0.0` |
| Pre-1.0: any breaking change | bump MINOR (project still in 0.x) | `0.3.x → 0.4.0` |

Skill template version stamp (`<!-- Auto-installed by open-image CLI vX.Y.Z. ... -->`) is sourced from `pyproject.toml` via `importlib.metadata` — single source of truth.

---

## 6. The skill auto-update mechanism (how `pip install -U` updates the Claude Code skill)

```
User runs `pip install -U open-image`
   → pip extracts wheel into site-packages/
       includes: gen.py, open_image_skill.py, _open_image_skill_bootstrap.py, open-image-skill.pth
   → On the next Python startup (anywhere on that machine):
       site.py reads open-image-skill.pth at site-packages root
       → executes `import _open_image_skill_bootstrap`
       → bootstrap calls open_image_skill.maybe_install_skill_silently()
       → if ~/.claude/ exists AND content of SKILL.md ≠ desired template:
           rewrite ~/.claude/skills/open-image/SKILL.md
       → idempotent: if already in sync, skip
   → User has no manual step. Skill matches the installed CLI version.
```

Tested end-to-end (see `plans/reports/brainstorm-260426-1144-...` and v0.3.3 release).

---

## 7. Common pitfalls (with fixes)

| Symptom | Likely cause | Fix |
|---|---|---|
| `gh release create` fails: "tag is not a valid tag" | Used short SHA (e.g. `7f35133`). | Use full SHA: `--target $(git rev-parse <short_sha>)` |
| Release workflow doesn't trigger after tag push | Tag points to a commit BEFORE `release.yml` existed | Tag a newer commit; or push a new tag from main |
| `twine` complains "version already exists" | Re-running same tag | OK — workflow has `skip-existing: true`, exits 0 |
| Tests pass locally but fail in CI on Linux/macOS | Path / encoding / OS-specific assumption | Read CI log; make tests use `Path` + `tmp_path`, not hardcoded strings |
| `pip install open-image` returns old version after release | PyPI JSON cache lag (rare, <1 min) | Wait briefly, or `pip install --no-cache-dir` |
| Skill not appearing on a fresh machine | `~/.claude/` doesn't exist (Claude Code not installed) | Auto-install correctly skips. Install Claude Code first. |
| Workflow shows "trusted publisher" hint warning | Cosmetic only — we use token, not OIDC | Ignore. To switch to OIDC, see § 8. |

---

## 8. (Optional) Migrate to PyPI Trusted Publishing (no token at all)

Token-based publish works. To eliminate the token entirely:

1. https://pypi.org/manage/project/open-image/settings/publishing/ → "Add a new publisher" (GitHub):
   - Owner: `tvtdev94`
   - Repository: `open-image`
   - Workflow filename: `release.yml`
   - Environment: (leave blank)
2. Edit `.github/workflows/release.yml`:
   - Add `permissions: id-token: write` to the job
   - Remove `password: ${{ secrets.PYPI_API_TOKEN }}` from the publish step
3. `gh secret remove PYPI_API_TOKEN`
4. Revoke the old token at https://pypi.org/manage/account/token/

The workflow then uses GitHub OIDC tokens instead — no long-lived credentials anywhere.

---

## 9. Verifying a release succeeded

```bash
# 1. Did the workflow finish?
gh run list --workflow=release.yml --limit=1
# → conclusion should be "success"

# 2. Is the version live on PyPI?
curl -sf "https://pypi.org/pypi/open-image/X.Y.Z/json" | python -c "import sys, json; print(json.load(sys.stdin)['info']['version'])"
# → should print X.Y.Z

# 3. Does pip install pick it up?
python -m venv /tmp/check && /tmp/check/bin/pip install --upgrade open-image
/tmp/check/bin/pip show open-image | grep Version
# → Version: X.Y.Z

# 4. Does the .pth auto-update the skill?
/tmp/check/bin/python -c "print('hello')"     # any Python invocation triggers .pth
grep "CLI v" ~/.claude/skills/open-image/SKILL.md
# → marker should match X.Y.Z
```

---

## 10. Don't do these

- ❌ Manual `python -m build && twine upload` to PyPI — bypasses CI, no audit trail
- ❌ Push tags before `release.yml` exists at that commit — workflow won't trigger
- ❌ Skip `python -m pytest` before tagging — broken release goes live
- ❌ Edit `release.yml` and bump version in same PR without testing on a fork first
- ❌ Commit `~/.pypirc`, `.env`, or any token to git
- ❌ Use `--no-verify` on git push to bypass hooks
- ❌ Delete a published version on PyPI (PyPI blocks re-uploading the same version even after delete)

---

## Reference

- Implementation report: `plans/reports/brainstorm-260426-1144-release-flow-and-security-hardening.md`
- Phase plans: `plans/260426-1144-release-flow-and-security-hardening/phase-*.md`
- Original CLI brainstorm: `plans/reports/brainstorm-260426-0915-model-support-and-claude-skill.md`
- Project changelog: `CHANGELOG.md`
