# Phase 2 — GitHub Actions Test CI

## Context Links
- **Brainstorm:** `plans/reports/brainstorm-260426-1144-release-flow-and-security-hardening.md` § 4
- **File:** `.github/workflows/test.yml` (NEW)

## Overview
- **Priority:** High (production gate cho phase 3)
- **Status:** pending
- **Description:** CI matrix run pytest trên Linux/macOS/Windows × Python 3.10/3.11/3.12/3.13 (12 jobs). Catch cross-platform regressions, đặc biệt `.pth` trên *nix.

## Requirements

### Functional
- Trigger trên `push` to `main` + `pull_request`
- Matrix: `os: [ubuntu-latest, macos-latest, windows-latest]` × `python-version: ['3.10', '3.11', '3.12', '3.13']`
- Steps:
  1. `actions/checkout@v4`
  2. `actions/setup-python@v5` với matrix python-version
  3. `pip install -e ".[dev]"`
  4. `pytest -v`
- `fail-fast: false` để xem hết failures across matrix

### Non-functional
- Pin action versions (major)
- Total runtime <5 phút per job

## Implementation Steps

### Step 1: Create `.github/workflows/test.yml`

```yaml
name: Test

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    name: ${{ matrix.os }} / py${{ matrix.python-version }}
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.10', '3.11', '3.12', '3.13']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
      - name: Install package + dev deps
        run: pip install -e ".[dev]"
      - name: Run tests
        run: pytest -v
```

### Step 2: Commit + push, verify first CI run

```bash
gh repo set-default tvtdev94/open-image
git add .github/workflows/test.yml
git commit -m "ci: add test matrix workflow (3 OS × 4 Python)"
git push origin main
gh run watch    # watch first run live
```

Nếu fail trên Linux/macOS, debug ngay (likely path-related test).

## Todo List
- [ ] Create `.github/workflows/test.yml`
- [ ] Commit với message `ci: add test matrix workflow`
- [ ] Push to main
- [ ] `gh run list --workflow=test.yml` để check status
- [ ] Nếu fail: identify failing job, fix root cause (likely `Path.home()` or import path issue), re-push
- [ ] Verify all 12 jobs xanh

## Success Criteria
- Workflow file valid YAML (no syntax errors)
- All 12 matrix jobs pass on first push
- Total run time <5 phút cho slowest job
- Workflow visible tại github.com/tvtdev94/open-image/actions

## Risk Assessment
- **Risk:** Tests fail trên *nix vì Windows-specific assumption. **Mitigation:** existing tests dùng `Path.home()` + `tmp_path` portable; check cẩn thận sau push đầu.
- **Risk:** `pip install -e .` triggers `.pth` install side effect on CI runner (touches `~/.claude` of GitHub Actions VM). **Mitigation:** GitHub Actions VMs don't have `~/.claude`, nên `maybe_install_skill_silently()` skip silent. ✓
- **Risk:** Python 3.13 chưa stable trên hành tinh — có thể action setup-python không có. **Mitigation:** 3.13 đã GA tháng 10/2024, action support tốt.

## Next Steps
→ Phase 3 (release workflow)
