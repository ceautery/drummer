# Phase 10 — Distribution Design Spec

**Date:** 2026-05-28
**Status:** Approved

---

## Overview

Phase 10 completes the Drummer v1 build by adding distribution infrastructure and fixing two deferred items from Phase 9. The goal is infrastructure-complete: all distribution machinery works end-to-end locally, but nothing is pushed to a public release. When the project is ready for general use, the delta is: tag a release, upload the wheel, and copy the formula into a tap repo.

---

## Scope

1. **Phase 9 deferred items** — expired cookie row cleanup + OAuth credential variable substitution
2. **Docs site** — MkDocs Material, six pages, deployed to GitHub Pages
3. **Homebrew formula** — `formula/drummer.rb` in-repo, ready to copy into a tap
4. **`make dist`** — builds wheel, patches formula SHA256, prints release checklist

---

## Phase 9 Deferred Items

### Expired cookie row cleanup

`CookiePersistenceProtocol` gains a `delete(hostname, name)` method alongside the existing `save()`. In `cookies.py`, when the engine processes a `Set-Cookie` with `max-age=0` or an `expires` timestamp in the past, it calls `delete()` instead of `save()`. The SQLite implementation executes `DELETE FROM cookie_store WHERE hostname = ? AND name = ?`.

A one-time `PRAGMA incremental_vacuum` runs on app startup when the SQLite connection is first initialized, to reclaim space from rows written before this fix was in place.

Tests:
- Expired cookie triggers `delete()`, not `save()`
- Unexpired cookie still saves normally
- `delete()` on a non-existent row is a no-op

### OAuth credential variable substitution

`variables.py` already applies `resolve(text, env)` to URL, headers, bearer, and basic auth fields. The fix extends `resolve()` to the four OAuth fields in `AuthConfig`: `token_url`, `client_id`, `client_secret`, and `scope`. No new API surface — the same substitution path, applied earlier in the send pipeline before the token exchange fires.

Tests:
- `{{client_id}}` and `{{client_secret}}` resolve from the active environment
- `{{scope}}` resolves correctly
- Unresolved variables surface as warnings (existing behavior)

---

## Docs Site

### Tooling

- `mkdocs-material` added to `[project.optional-dependencies] dev` in `pyproject.toml`
- `mkdocs.yml` at the repo root
- Content lives in `docs/site/` (separate from `docs/decisions/` ADRs and `docs/superpowers/` internal specs)
- `site/` is git-ignored (build output)

### Navigation

| Page | Source |
|---|---|
| Home | New — user-facing intro, install one-liner, first-run instructions |
| Getting Started | New — `drummer serve`, open a project, send a request |
| CLI Reference | New — all CLI commands with flags and examples (drawn from `drummer --help`) |
| Scripting API | New — `dm.*` API surface, timeout behavior, `console.log` capture |
| MCP Tools | New — tool list, example Claude workflow |
| Attribution | `drummer/mock/DATA_ATTRIBUTION.md` (already exists) |

### Makefile targets

```makefile
docs:
    mkdocs build

docs-serve:
    mkdocs serve
```

`make docs` builds to `site/`. `make docs-serve` launches a local preview at `http://localhost:8000`.

### GitHub Actions deployment

`.github/workflows/docs.yml` — triggers on push to `main` when `docs/site/**` or `mkdocs.yml` changes. Uses the official MkDocs Material deploy action to build and push to the `gh-pages` branch. No secrets required for a public repo.

---

## Homebrew Formula

### Location

`formula/drummer.rb` — checked into the Drummer repo. When ready to publish a tap, copy to `Formula/drummer.rb` in a `homebrew-drummer` repo.

### Formula structure

```ruby
class Drummer < Formula
  include Language::Python::Virtualenv

  desc "Local, standalone REST client — free alternative to Postman/Insomnia/Bruno"
  homepage "https://github.com/ceautery/drummer"

  # TODO: update url and sha256 when a GitHub release exists
  url "https://github.com/ceautery/drummer/releases/download/v0.1.0/drummer-0.1.0-py3-none-any.whl"
  sha256 "PLACEHOLDER"  # updated by `make dist`

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"drummer", "--version"
  end
end
```

`make dist` updates the `sha256` line. The `url` line remains a placeholder until a real GitHub release is tagged.

---

## `make dist`

### Behavior

1. `hatch build` — produces `dist/drummer-<version>-py3-none-any.whl`
2. `scripts/dist.py` — computes SHA256 of the wheel, patches `formula/drummer.rb` in-place
3. Prints: wheel path, SHA256, and a release checklist

### Release checklist (printed, not automated)

```
Release checklist:
  [ ] Tag a release: git tag v0.1.0 && git push origin v0.1.0
  [ ] Upload dist/*.whl as a GitHub release asset
  [ ] Update formula url to the release asset URL
  [ ] Copy formula/drummer.rb → homebrew-drummer/Formula/drummer.rb
  [ ] Push tap repo
```

### What it does not do

- Does not push to GitHub
- Does not commit the formula change (review the diff first)
- Does not touch any tap repo

### Dependencies

`hatch` added to `[dev]` optional dependencies. It is already declared as the build backend in `pyproject.toml`; this makes it explicitly installable via `pip install -e ".[dev]"`.

### Implementation

`scripts/dist.py` — a small standalone Python script (no new package imports beyond `hashlib`, `pathlib`, `re`, `subprocess`). The Makefile target:

```makefile
dist: build-frontend
    hatch build
    $(PYTHON) scripts/dist.py
```

`dist` depends on `build-frontend` so the wheel always contains the latest compiled React assets.

---

## Testing

No new test layers. All new behavior covered by existing unit and integration test suites:
- Cookie cleanup: unit tests in `tests/unit/test_cookies.py`
- OAuth substitution: unit tests in `tests/unit/test_variables.py`
- `make dist` script: not tested (it's a release utility; correctness verified manually)

All existing 244 tests must continue to pass. `make check` is the gate.

---

## File changes summary

| Path | Change |
|---|---|
| `drummer/core/cookies.py` | Add `delete()` to protocol + impl; call on expired cookies |
| `drummer/core/variables.py` | Extend `resolve()` to OAuth fields in `AuthConfig` |
| `pyproject.toml` | Add `mkdocs-material`, `hatch` to dev deps |
| `mkdocs.yml` | New — MkDocs site config |
| `docs/site/*.md` | New — six documentation pages |
| `.github/workflows/docs.yml` | New — GitHub Pages deployment workflow |
| `formula/drummer.rb` | New — Homebrew formula (placeholder SHA) |
| `scripts/dist.py` | New — wheel build + formula SHA patch script |
| `Makefile` | Add `docs`, `docs-serve`, `dist` targets |
| `.gitignore` | Add `site/` |
