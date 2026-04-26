# Phase 3 — GitHub Actions Release Workflow (PyPI Trusted Publishing)

## Context Links
- **Brainstorm:** `plans/reports/brainstorm-260426-1144-release-flow-and-security-hardening.md` § 4 + § 7
- **File:** `.github/workflows/release.yml` (NEW)

## Overview
- **Priority:** High (security-critical: removes token risk)
- **Status:** pending
- **Description:** Auto-publish to PyPI khi push tag `v*.*.*`. Zero token — uses OIDC trusted publishing. `--skip-existing` để safe khi backfill old tags.

## Requirements

### Functional
- Trigger: `push` tag matching `v*.*.*`
- Steps:
  1. `actions/checkout@v4`
  2. `actions/setup-python@v5` với Python 3.12 (build env)
  3. `pip install build`
  4. `python -m build`
  5. `pypa/gh-action-pypi-publish@release/v1` với `skip-existing: true`
- `permissions: id-token: write` để OIDC hoạt động
- No PyPI token in secrets

### Non-functional
- Pin all action versions
- Workflow visible cho audit

## Implementation Steps

### Step 1: Tạo `.github/workflows/release.yml`

```yaml
name: Release

on:
  push:
    tags: ['v*.*.*']

jobs:
  publish:
    name: Build + publish to PyPI
    runs-on: ubuntu-latest
    permissions:
      id-token: write    # required for OIDC trusted publishing
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install build
        run: pip install build
      - name: Build sdist + wheel
        run: python -m build
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          skip-existing: true
```

### Step 2: Commit + push

```bash
git add .github/workflows/release.yml
git commit -m "ci: add PyPI trusted publishing workflow on tag"
git push origin main
```

### Step 3: Document manual setup steps trong CHANGELOG note hoặc README

User cần thao tác trên pypi.org TRƯỚC KHI push tag đầu tiên:

1. **Revoke token cũ** (đã leak qua chat):
   - https://pypi.org/manage/account/token/
   - Find token "open-image" hoặc whatever name → "Remove token"

2. **Setup trusted publisher**:
   - https://pypi.org/manage/project/open-image/settings/publishing/
   - "Add a new publisher" → "GitHub":
     - Owner: `tvtdev94`
     - Repository name: `open-image`
     - Workflow filename: `release.yml`
     - Environment name: (để trống)
   - Submit

3. **Verify** trusted publisher xuất hiện trong list, không còn pending tokens

4. **Cleanup local**:
   ```bash
   rm ~/.pypirc
   ```

5. **Verify từ Phase 4**: Push 1 tag (e.g. v0.3.2) → workflow chạy → check Actions tab → upload thành công (skip-existing nuốt "version already exists" warning)

## Todo List
- [ ] Create `.github/workflows/release.yml`
- [ ] Commit với message `ci: add PyPI trusted publishing workflow on tag`
- [ ] Push to main
- [ ] **PAUSE** — user thao tác manual trên pypi.org (revoke + setup trusted publisher)
- [ ] User confirm "đã setup xong" → resume Phase 4
- [ ] Add manual setup guide vào CHANGELOG.md hoặc README

## Success Criteria
- Workflow file valid YAML
- Trusted publisher visible tại pypi.org/manage/project/open-image/settings/publishing/
- Old token đã revoke
- `~/.pypirc` đã xóa
- (Sẽ verify trong Phase 4 khi push tag thực)

## Risk Assessment
- **Risk:** User thao tác sai trên pypi.org → trusted publisher không match repo/workflow → workflow fail. **Mitigation:** Detailed step-by-step + verify output.
- **Risk:** Push tag trước khi setup trusted publisher → workflow fail. **Mitigation:** Order of operations rõ ràng. Phase 4 chỉ chạy sau khi user confirm setup xong.
- **Risk:** `pypa/gh-action-pypi-publish` action có breaking change. **Mitigation:** Pin `@release/v1` (stable major).
- **Risk:** OIDC token expire mid-build (rất hiếm). **Mitigation:** Action handles token refresh.

## Security Considerations
- Workflow `permissions: id-token: write` chỉ apply cho job này
- No secrets used
- All actions pinned to major version (`@v4`, `@v5`, `@release/v1`) → audit-able

## Next Steps
→ Phase 4 (backfill tags + verify)
