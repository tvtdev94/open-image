---
title: Production Release Flow + Security Hardening
slug: release-flow-and-security-hardening
date: 2026-04-26 11:44
status: pending
mode: fast
blockedBy: []
blocks: []
---

# Production Release Flow + Security Hardening (B + D)

CHANGELOG + git tags + GitHub Actions CI + PyPI trusted publishing OIDC. Loại bỏ PyPI token vĩnh viễn (đã leak qua chat history).

## Context

- **Brainstorm report:** `plans/reports/brainstorm-260426-1144-release-flow-and-security-hardening.md`
- **Stack:** GitHub Actions, PyPI trusted publishing (OIDC), Keep a Changelog format
- **Scope:** 2 NEW workflows, 1 NEW changelog, 1 README edit; manual setup guide cho pypi.org

## Phases

| # | Phase | Status | File |
|---|---|---|---|
| 1 | CHANGELOG.md + README .pth transparency | pending | [phase-01-changelog-and-readme.md](phase-01-changelog-and-readme.md) |
| 2 | GitHub Actions test CI (matrix 3 OS × 4 Python) | pending | [phase-02-test-workflow.md](phase-02-test-workflow.md) |
| 3 | GitHub Actions release workflow (PyPI trusted publishing) | pending | [phase-03-release-workflow.md](phase-03-release-workflow.md) |
| 4 | Manual setup guide + backfill historical tags | pending | [phase-04-setup-and-tags.md](phase-04-setup-and-tags.md) |

## Key Design (chốt từ brainstorm)

- **Trusted publishing OIDC** thay vì token in secrets — zero credential exposure
- **`--skip-existing`** trong workflow → idempotent khi push retroactive tags
- **Order of operations**: setup trusted publisher TRƯỚC, push tags SAU
- User dùng `gh` CLI cho commit + tag + release ops
- CHANGELOG follow Keep a Changelog standard

## Dependencies

- GitHub Actions (free for public repos)
- PyPI trusted publishing (configured by user on pypi.org)
- `pypa/gh-action-pypi-publish@release/v1` (pinned version)
- `actions/checkout@v4` + `actions/setup-python@v5` (pinned major versions)

## Acceptance Criteria (overview)

- CI workflow pass trên 3 OS × 4 Python (12 jobs)
- Release workflow upload thành công khi push tag (verify v0.3.2 publish lại với --skip-existing)
- PyPI Manage settings hiện trusted publisher tvtdev94/open-image
- `~/.pypirc` xóa được, không break flow
- Git tags v0.3.0/v0.3.1/v0.3.2 visible trên GitHub Releases page
- Old PyPI token revoked
