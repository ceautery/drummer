# ADR 002: YAML frontmatter + Markdown body for request files

**Date:** 2026-05-25
**Status:** Accepted

## Context

Request definitions need to be stored in a human-readable, git-diffable format. HTTP requests
have structured metadata (method, URL, headers, auth, scripts, params) alongside free-form
documentation. Three formats were evaluated:

- **JSON**: machine-friendly, terrible for humans to read or diff
- **Pure YAML**: clean, simple to parse, good tooling, no documentation story
- **YAML frontmatter + Markdown body**: structured metadata in the YAML block, free-form
  documentation, notes, and example responses in the Markdown body

## Decision

Use **YAML frontmatter + Markdown body**. One `.md` file per request. The YAML block holds all
structured request metadata; the Markdown body is documentation for that request.

Parsed using `python-frontmatter`. Schema validated using Pydantic v2.

## Consequences

- Request files are readable and writable by hand without tooling
- Git diffs are meaningful: changing a header shows up as a one-line diff
- The Markdown body doubles as living documentation for each request
- We maintain a custom schema (validated by Pydantic) — adding new fields requires updating
  `drummer/core/storage/formats.py` and the Pydantic model
- Tooling that expects pure YAML or pure JSON will not work with request files without a converter
