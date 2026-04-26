# Brainstorm — Production Release Flow + Security Hardening (B + D)

**Date:** 2026-04-26 11:44
**Branch:** main
**Status:** Design approved, ready for `/ck:plan`

---

## 1. Problem Statement

`open-image` v0.3.2 đã chín về features. Cần:
- **B (Production-grade release):** CHANGELOG, git tags, GitHub Actions CI, PyPI auto-publish on tag
- **D (Security):** Loại bỏ PyPI token (đã leak qua chat history) bằng trusted publishing OIDC

## 2. Current State Gaps

| Gap | Impact |
|---|---|
| Không có CHANGELOG | User phải đoán changes giữa versions |
| Chưa tag git releases (v0.3.0/0.3.1/0.3.2) | GitHub Releases page trống |
| Test chỉ chạy local trên Windows | Cross-platform regressions không detect được (đặc biệt `.pth` trên *nix) |
| Manual `python -m build && twine upload` | Rủi ro typo, inconsistent release process |
| PyPI token plain-text trong `~/.pypirc` + đã leak chat | Critical security exposure |

## 3. Approaches Evaluated

### Release flow
| Option | Verdict |
|---|---|
| Manual scripts (build + upload) | ❌ Status quo, không scale, error-prone |
| GitHub Actions với PyPI token in secrets | ⚠️ Loại bỏ chat-leak nhưng vẫn còn token in GitHub secrets |
| **GitHub Actions với PyPI Trusted Publishing (OIDC)** ⭐ | ✅ Zero token, GitHub xác thực qua OIDC, best practice 2024+ |

### CI matrix
| Option | Verdict |
|---|---|
| Linux only | ❌ `.pth` cross-platform claim không verified |
| Linux + Windows | ⚠️ Bỏ qua macOS — nhiều dev dùng Mac |
| **Linux + macOS + Windows × Python 3.10/3.11/3.12/3.13** ⭐ | ✅ 12 jobs, miễn phí cho public repo |

### Security
| Option | Verdict |
|---|---|
| Chỉ revoke + tạo token mới | ⚠️ Vẫn có token cần bảo vệ |
| **Revoke + setup trusted publishing → loại bỏ token vĩnh viễn** ⭐ | ✅ Permanent fix, no future leak risk |

## 4. Final Solution

### Files to create/modify

| File | Action | Purpose |
|---|---|---|
| `CHANGELOG.md` | NEW | Keep a Changelog format, cover 0.2.0 → 0.3.2 |
| `README.md` | EDIT | Thêm note về `.pth` mechanism (transparency) |
| `.github/workflows/test.yml` | NEW | Test matrix (3 OS × 4 Python versions) |
| `.github/workflows/release.yml` | NEW | Build + publish via OIDC trusted publishing on tag |

### Workflow triggers

**`test.yml`:**
- `push` to `main` + `pull_request`
- Steps: checkout → setup-python → `pip install -e .[dev]` → `pytest -v`

**`release.yml`:**
- `push` tag matching `v*.*.*`
- Steps: checkout → setup-python → `python -m build` → `twine check` → upload via `pypa/gh-action-pypi-publish` (no token needed)
- Use `--skip-existing` để safe khi push retroactive tags
- `permissions: id-token: write` để OIDC hoạt động

### Manual steps (write guide cho user)

User cần thao tác lần đầu trên pypi.org:
1. **Revoke token cũ:** https://pypi.org/manage/account/token/
2. **Configure trusted publisher:** https://pypi.org/manage/project/open-image/settings/publishing/ → "Add a new publisher":
   - Owner: `tvtdev94`
   - Repository: `open-image`
   - Workflow filename: `release.yml`
   - Environment: (để trống)
3. **Sau khi setup**, xóa `~/.pypirc` để clean up

### Tag historical versions

Sau khi trusted publisher đã setup, push tags retroactively:
```bash
gh release create v0.3.0 <commit_sha> --title "v0.3.0" --notes "..."
gh release create v0.3.1 <commit_sha> --title "v0.3.1" --notes "..."
gh release create v0.3.2 <commit_sha> --title "v0.3.2" --notes "..."
```

Hoặc dùng git tag + push:
```bash
git tag v0.3.0 4d55360   # initial commit (or appropriate)
git tag v0.3.1 3fb16c3
git tag v0.3.2 9e777b0
git push origin --tags
```

Workflow chạy 3 lần, mỗi lần `--skip-existing` → idempotent, an toàn.

## 5. Implementation Outline

Chia 4 phases:

1. **CHANGELOG + README transparency note** (10 phút)
2. **`test.yml` workflow** (30 phút) — verify lần đầu push CI hoạt động
3. **`release.yml` workflow** + manual setup guide trong CHANGELOG (30 phút)
4. **Tag historical versions** (5 phút) — kích hoạt workflow lần đầu, verify upload

## 6. Risks & Mitigation

| Risk | Severity | Mitigation |
|---|---|---|
| Tests fail trên Linux/macOS vì path-related issues | Medium | Đã dùng `Path.home()` + `tmp_path` portable, nên should be OK; CI sẽ verify |
| Trusted publisher setup chưa xong khi push tags | High | Order of operations: setup TRƯỚC, push tags SAU. Rõ ràng trong guide |
| PyPI account 2FA/email verification gây delay | Low | User chủ động trên pypi.org, không trong scope automation |
| `--skip-existing` nuốt lỗi thực sự | Low | Twine warn về existing, nhưng error code 0. Acceptable cho idempotency |
| `pypa/gh-action-pypi-publish` action có thay đổi behavior | Low | Pin version (e.g., `@v1`) trong workflow |

## 7. Acceptance Criteria

- [ ] `CHANGELOG.md` cover 4 versions với date + changes
- [ ] README có section ngắn explain `.pth` mechanism
- [ ] CI workflow run pass trên 3 OS × 4 Python (12 jobs)
- [ ] Release workflow uploaded cleanly khi push tag
- [ ] PyPI page open-image hiện rõ trusted publisher trong Manage settings
- [ ] `~/.pypirc` xóa được mà không break release flow
- [ ] Git tags v0.3.0/0.3.1/0.3.2 visible trên GitHub Releases
- [ ] Old token revoked

## 8. Out of Scope

- Coverage badge (Codecov) — Tier 3, skip
- Mypy / type-check CI — Tier 3, skip
- Bootstrap module test — defensive but not critical now
- Tmp-venv smoke test — manual verify đã làm, đủ confidence
- Discord/Slack notifications on release — over-engineering
- Pre-release / RC version flow — không cần
- Codeowners file / CONTRIBUTING.md — project nhỏ, README đủ
- Manual approval gate (release Environment) — single-person project, không cần

## 9. Unresolved Questions

Không có.

## 10. Next Steps

→ Trigger `/ck:plan` với report này làm context, plan dir `plans/260426-1144-release-flow-and-security-hardening/`, 4 phases như outline.
