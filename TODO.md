# TODO

## Post-1.0 hardening arc

**Done (committed, tree green — 308 Python + 43 frontend tests; Phase 15 verified in-app):**
- F1 — Raw response tab is a pure hexdump.
- F2 — Forget external workspace (core + route + switcher action) and e2e `DRUMMER_HOME` isolation.
- Phase 15 — critical save data-loss/crash fix, visible Save button, new/delete requests in the tree.
  Verified end-to-end in the running app: a url-only Save preserves auth + post-script (no data
  loss), Save/dirty-dot toggles correctly, saving no longer blanks the UI, and + New / delete work.

**Next (planned, not started):**
- Phase 16 — Environment & variable editor (the "how do I set `{{base_url}}`" gap).
- Phase 17 — Sent-request inspector (resolved URL/params/headers + unresolved-variable warnings).

See `ROADMAP.md` (Post-1.0 Hardening Arc), the spec
`docs/superpowers/specs/2026-05-29-post-1.0-hardening-arc-design.md`, and the Phase 15 plan
`docs/superpowers/plans/2026-05-29-fixes-and-phase-15-request-editing.md`.

**Deferred:** request file rename + move/folders in the tree (shared "move file" primitive — a later phase).

## Known gap to address in a future cleanup
`make check` runs Biome + tsc + the Python test suite, but NOT the frontend vitest suite — so broken
frontend tests (e.g. a missing hook in a component's `vi.mock`) pass the pre-commit gate. (This bit us
once during the arc, in AppBar.test.tsx.) Worth wiring `npm run test` (vitest run) into `make check` /
the pre-commit hook.
