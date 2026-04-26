# Phase 4 — Manual Setup + Backfill Historical Tags

## Context Links
- **Brainstorm:** `plans/reports/brainstorm-260426-1144-release-flow-and-security-hardening.md` § 4 + § 7
- **No new files** — orchestration phase using `gh` CLI

## Overview
- **Priority:** High (final validation)
- **Status:** pending — **blocked by user manual setup**
- **Description:** Sau khi user complete trusted publisher setup trên pypi.org, push retroactive tags v0.3.0/v0.3.1/v0.3.2 để kích hoạt release workflow lần đầu, verify upload thành công.

## Requirements

### Functional
- Tag 3 historical commits với `v0.3.0`, `v0.3.1`, `v0.3.2`
- Push tags → trigger release workflow 3 lần
- Each run: `--skip-existing` nuốt "version exists" → success exit 0
- Verify GitHub Releases page hiện 3 releases
- Verify pypi.org không có duplicate (vẫn 1 entry per version)

### Non-functional
- Idempotent — chạy lại không gây hại
- Use `gh release create` để có release notes

## Pre-conditions

⚠️ **MUST be completed by user trước Phase 4:**
1. PyPI old token revoked
2. Trusted publisher configured cho `tvtdev94/open-image` workflow `release.yml`
3. User confirm "setup xong"

## Implementation Steps

### Step 1: Identify commits cho từng version

```bash
git log --oneline | head -20
```

Map versions → commits (theo session history):
- `v0.3.0` → commit `7f35133` (feat: v0.3.0 — model registry + Claude Code skill auto-install)
- `v0.3.1` → commit `3fb16c3` (feat(v0.3.1): auto-update skill on upgrade...)
- `v0.3.2` → commit `9e777b0` (feat(v0.3.2): true post-install skill via .pth...)

### Step 2: Tag historical commits + push

Option A — `git tag` đơn giản:
```bash
git tag v0.3.0 7f35133
git tag v0.3.1 3fb16c3
git tag v0.3.2 9e777b0
git push origin --tags
```

Option B — `gh release create` (có release notes ngay):
```bash
gh release create v0.3.0 7f35133 \
  --title "v0.3.0 — Model Registry + Claude Code Skill" \
  --notes "$(awk '/## \[0.3.0\]/,/## \[0.2.0\]/' CHANGELOG.md | sed '$d')"

gh release create v0.3.1 3fb16c3 \
  --title "v0.3.1 — Skill Auto-Update on Upgrade" \
  --notes "$(awk '/## \[0.3.1\]/,/## \[0.3.0\]/' CHANGELOG.md | sed '$d')"

gh release create v0.3.2 9e777b0 \
  --title "v0.3.2 — Zero-Step Skill Install via .pth" \
  --notes "$(awk '/## \[0.3.2\]/,/## \[0.3.1\]/' CHANGELOG.md | sed '$d')"
```

**Recommend Option B** — cleaner UX trên GitHub Releases page.

### Step 3: Watch release workflow runs

```bash
gh run list --workflow=release.yml --limit=5
gh run watch <run-id>
```

Verify:
- 3 runs trigger
- Each completes với `--skip-existing` (warning về existing version, exit 0)
- No actual upload duplicate trên PyPI

### Step 4: Verify outputs

```bash
# GitHub Releases
gh release list

# PyPI (nên unchanged — 0.3.0/0.3.1/0.3.2 đã tồn tại)
pip index versions open-image
```

### Step 5: Cleanup

```bash
rm ~/.pypirc       # token-based auth không còn cần
```

## Todo List
- [ ] **WAIT FOR USER**: confirm trusted publisher setup xong + token revoked
- [ ] Identify exact commit SHAs cho v0.3.0/0.3.1/0.3.2
- [ ] `gh release create` cho 3 versions với CHANGELOG-extracted notes
- [ ] Watch 3 workflow runs via `gh run watch`
- [ ] Verify GitHub Releases page hiện 3 entries
- [ ] Verify PyPI versions list không bị duplicate
- [ ] Remove `~/.pypirc`
- [ ] Final journal entry

## Success Criteria
- 3 GitHub Releases visible (v0.3.0, v0.3.1, v0.3.2) với release notes
- 3 release workflow runs all green (with skip-existing warnings, exit 0)
- PyPI page open-image không có duplicate version uploads
- `~/.pypirc` removed, future releases pure OIDC
- Old PyPI token confirmed revoked (404 khi try login với it)

## Risk Assessment
- **Risk:** User setup chưa xong, tag push trigger workflow → fail OIDC. **Mitigation:** Block phase 4 until user confirms (explicit gate trong Todo).
- **Risk:** `awk` extract release notes sai vì CHANGELOG format khác. **Mitigation:** Có thể pass `--notes-from-tag` hoặc `--generate-notes` thay thế.
- **Risk:** Push 3 tags simultaneously gây race condition trên Actions runner. **Mitigation:** Push tuần tự nếu cần (`gh release create` 1 lần 1 release).
- **Risk:** Ai đó push tag `v0.3.3` ngẫu nhiên → trigger workflow nhưng version chưa publish PyPI → fail. **Mitigation:** Future tags chỉ push sau khi version trong pyproject.toml match. Document trong CHANGELOG.

## Security Considerations
- After Phase 4 complete: project có ZERO long-lived credentials
- Future releases: chỉ cần `gh release create vX.Y.Z` → workflow auto-publish
- OIDC tokens transient (per-job), expire ~5-10 phút → minimal blast radius

## Next Steps
→ Plan complete. Final journal + commit-and-done.
