# TODO

## Current sprint: Post-1.0 hardening arc

**Done (committed, tree green — 308 Python + 43 frontend tests):**
- F1 — Raw response tab is a pure hexdump.
- F2 — Forget external workspace (core + route + switcher action) and e2e `DRUMMER_HOME` isolation.
- Phase 15 — critical save data-loss/crash fix, visible Save button, new/delete requests in the tree.

**Remaining for Phase 15 (Task 15.9):**
- [ ] Manual app verification of the save UX end-to-end: `make dev`, then confirm
      (1) editing a request enables Save + shows the dirty dot; (2) Save and cmd-s
      both clear the dot without blanking the UI; (3) adding a bearer token + post-script,
      saving, and reloading preserves them (no data loss); (4) "+ New" creates and selects
      a request; (5) the tree ✕ deletes and clears the pane if it was selected.
- [ ] After manual verification passes, final `make check` + commit closing Phase 15.

**Next (planned, not started):**
- Phase 16 — Environment & variable editor.
- Phase 17 — Sent-request inspector.

See `ROADMAP.md` (Post-1.0 Hardening Arc) and
`docs/superpowers/plans/2026-05-29-fixes-and-phase-15-request-editing.md`.

## Known gap surfaced during this work
`make check` runs Biome + tsc + the Python test suite, but NOT the frontend vitest
suite — so broken frontend tests (e.g. a missing hook in a component's `vi.mock`) pass
the pre-commit gate. Worth wiring `npm run test` (vitest run) into `make check` / the
pre-commit hook in a future cleanup.
