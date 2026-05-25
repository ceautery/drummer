# ADR 001: QuickJS for scripting engine

**Date:** 2026-05-25
**Status:** Accepted

## Context

Drummer needs a scripting engine for pre- and post-request scripts. Users need to inspect and
mutate request/response data, extract values into environment variables, and log output for
debugging. The scripting language must be familiar to API developers, safely sandboxable, and
embeddable in a Python process.

Candidates evaluated:
- **Lua** (`lupa`): battle-tested, small runtime, but unfamiliar to most API developers
- **Python subprocess**: familiar, but sandboxing safely is genuinely hard and per-script startup
  latency is noticeable
- **JavaScript via QuickJS** (`quickjs`): JS is the Postman mental model, the runtime is
  tiny (~210kB), sandboxing is solid, and startup is fast

## Decision

Use **QuickJS via the `quickjs` PyPI package**. Scripts run in an isolated QuickJS context per
request. The `dm` object is the only API surface exposed to scripts.

## Consequences

- Users write pre/post scripts in JavaScript — consistent with Postman muscle memory
- The sandbox boundary is well-defined: scripts cannot import modules or access the filesystem
- `quickjs` must be available as a binary wheel for the target platforms (macOS, Linux)
- New `dm.*` API methods require changes to the QuickJS context setup in `drummer/core/scripting.py`
