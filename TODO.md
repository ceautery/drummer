# TODO

## Post-1.0 hardening arc

**Done (committed, tree green — Python + frontend tests passing):**
- F1 — Raw response tab is a pure hexdump.
- F2 — Forget external workspace (core + route + switcher action) and e2e `DRUMMER_HOME` isolation.
- Phase 15 — critical save data-loss/crash fix, visible Save button, new/delete requests in the tree. Verified in-app.
- Phase 16 — environment & variable editor: backend create/delete routes, a `Dialog` UI primitive,
  the `EnvironmentManager` modal (edit variables, create, delete) launched from a sidebar gear button.
  Verified in-app: gear opens the modal; editing a variable + Save persists; create and delete both work.

**Next (planned, not started):**
- Phase 17 — Sent-request inspector: surface the resolved request (final URL, substituted
  params/headers, the variable set used) and unresolved-variable warnings on the response side.

See `ROADMAP.md` (Post-1.0 Hardening Arc), the spec
`docs/superpowers/specs/2026-05-30-phase-16-environment-editor-design.md`, and the plan
`docs/superpowers/plans/2026-05-30-phase-16-environment-editor.md`.

**Deferred:** request file rename + environment rename + move/folders in the tree (shared "move file" primitive — a later phase).

## Known gaps to address in a future cleanup
- `make check` runs Biome + tsc + the Python test suite, but NOT the frontend vitest suite — so broken
  frontend tests pass the pre-commit gate. Worth wiring `npm run test` (vitest run) into `make check`.
- The EnvironmentManager "discard unsaved changes on env switch" guard is not unit-tested (it requires
  driving the Base UI Select dropdown headlessly); it was checked via the in-app verification instead.
