# Phase 14 — Wikidata GraphQL

**Status:** Approved design — ready for implementation plan
**Date:** 2026-05-29
**Author:** brainstormed with Claude

## Context

Drummer's tutorial teaches its REST features against a built-in mock of the Metropolitan
Museum of Art collection (`/mock/met`, sourced from real Met Open Access data). Phase 8 built
Drummer's GraphQL support — a send pipeline that synthesizes a `{query, variables}` body when a
request carries a `graphql` config, an introspection proxy (`POST /api/graphql/introspect`), a
`GraphQLTab` with Query/Variables/Schema sub-tabs, cm6-graphql autocomplete, and a
`SchemaExplorer`. Phase 13 unified the tutorial onto the real request/response panes, with the
backend `STEPS` as the single source of truth (`GET /api/tutorial/steps`).

This final phase adds a built-in **mock GraphQL server** backed by **real Wikidata data**, plus
a **3-step GraphQL arc** appended to the tutorial, so the tutorial demonstrates Drummer's GraphQL
features end to end against a local, no-internet endpoint — mirroring how the Met mock backs the
REST steps.

## Goals

- A mock GraphQL endpoint inside Drummer (`POST /mock/wikidata/graphql`) with a real executable
  schema and real introspection.
- A dataset built from **actual Wikidata data** (real Q-ids, labels, descriptions, claim values)
  with **real Wikidata field semantics** (property labels camelCased, canonical P-id documented).
- Three GraphQL tutorial steps that drive the real Phase 8 GraphQL request pane.
- Attribution for Wikidata alongside the existing Met attribution.

## Non-goals

- Changes to the GraphQL send pipeline, introspection proxy, or GraphQL UI — all reused as-is.
- A faithful, complete Wikidata schema. We model a small, curated relational slice sufficient
  for the tutorial, not the full property space.
- GraphQL mutations/subscriptions — query-only.
- Port-independence of tutorial requests. Like the existing Met steps, the GraphQL steps target
  `http://localhost:8000` (Drummer's default port); this pre-existing assumption is unchanged.

## Key decisions

| Decision | Choice |
|---|---|
| Mock execution | **Real executable schema via `graphql-core`** (pure-Python reference implementation) — real query execution AND introspection, so the Phase 8 schema explorer / autocomplete / query editing all work against the mock |
| Schema shape | **Relational mini-schema** — one `Entity` type with scalar fields + typed relation fields resolving to other entities |
| Field naming | **camelCase of the real Wikidata property label, with the canonical P-id documented** in the field description (not raw `P31`-style names) |
| Data | **Real Wikidata data**, fetched from the Wikidata API at implementation time; no invented values |
| Tutorial scope | **3-step GraphQL arc** appended to the existing 7 REST steps |
| New dependency | **`graphql-core`** added to the backend (the one ADR-worthy addition) |

## Architecture

```
drummer/api/mock/wikidata_snapshot.json   ← ~15 interlinked entities, real Wikidata data
drummer/api/mock/wikidata.py              ← graphql-core schema + resolvers + execute(query, variables)
drummer/api/routes/mock.py                ← + POST /mock/wikidata/graphql (thin; calls execute)
drummer/api/routes/tutorial.py            ← TutorialStep gains `graphql`; 3 GraphQL steps appended
drummer/cli.py                            ← _ATTRIBUTION gains a Wikidata block
frontend/src/types.ts                     ← TutorialStep.graphql
frontend/src/api/tutorial.ts              ← stepToRequestDetail passes graphql through
pyproject.toml                            ← add graphql-core dependency
```

The GraphQL tutorial steps flow through the **existing** send pipeline unchanged: `resolve()`
already substitutes `graphql.query`, and `engine.send()` already synthesizes the
`{query, variables}` JSON body when `frontmatter.graphql` is set. The only backend change to the
tutorial is that `TutorialStep` must carry a `graphql` config and `_step_to_request_file` must
pass it through.

## Schema

A single `Entity` type keeps the schema tutorial-friendly (no interfaces/unions). Relation fields
are a superset — populated where they apply on a given entity, `null`/empty otherwise. The SDL
carries the canonical P-id in each field's description.

```graphql
type Query {
  entity(id: ID!): Entity
  search(term: String!): [Entity!]!
}

type Entity {
  id: ID!                  # the real Q-id, e.g. "Q42"
  label: String!           # real English rdfs:label
  description: String      # real English schema:description
  instanceOf: [Entity!]!   # P31
  author: Entity           # P50
  placeOfBirth: Entity     # P19
  country: Entity          # P17
  publicationDate: String  # P577 (real date value, e.g. "1979-10-12")
  notableWork: [Entity!]   # P800
}
```

`search` matches a case-insensitive substring against `label` and `description`.

## Dataset

`drummer/api/mock/wikidata_snapshot.json` — ~15 curated, interlinked, recognizable entities,
built from **real Wikidata data**. At implementation time, each chosen entity is fetched from the
Wikidata API (`https://www.wikidata.org/wiki/Special:EntityData/<Qid>.json`); the build extracts
the real English label, real English description, and the real claim values for the modeled
properties (P31, P50, P19, P17, P577, P800).

- Entities form connected chains so nested queries resolve end to end. Example chain:
  `Q3107329` (The Hitchhiker's Guide to the Galaxy) `author`→ `Q42` (Douglas Adams)
  `placeOfBirth`→ `Q350` (Cambridge) `country`→ `Q145` (United Kingdom).
- Stored flat: relations are id references; resolvers dereference them against the index.
- **Every Q-id referenced by a modeled relation must itself be present in the snapshot** (no
  dangling references) — enforced by a test.
- The curated set spans a few authors, their notable works, and the relevant places, chosen so
  steps 1–3 have meaningful data.

## Mock execution module + route

`drummer/api/mock/wikidata.py` (no FastAPI imports — keeps mock data/logic out of handlers,
mirroring how `mock.py` holds the Met helpers):

- Loads `wikidata_snapshot.json` into an `{Qid: entity}` index at import time.
- Builds the executable schema via `graphql.build_schema(SDL)` and attaches resolvers:
  - `Query.entity(id)` — index lookup, returns `None` when absent.
  - `Query.search(term)` — case-insensitive substring match on label/description.
  - Relation-field resolvers (`instanceOf`, `author`, `placeOfBirth`, `country`, `notableWork`)
    that dereference stored id refs → entity dicts. Scalar fields use the default resolver.
- `execute(query: str, variables: dict[str, Any] | None) -> dict` runs `graphql_sync(...)` and
  returns `{"data": ...}`, adding `"errors"` only when the result has errors.

`drummer/api/routes/mock.py` gains:

- `POST /mock/wikidata/graphql` — Pydantic body `GraphQLQuery { query: str; variables: dict[str, Any] = {} }`,
  returns `JSONResponse(execute(body.query, body.variables))`. No logic in the handler.
- Introspection queries are handled automatically by graphql-core, so the existing
  `/api/graphql/introspect` proxy and `SchemaExplorer` work against this endpoint with no
  special-casing.

## Tutorial steps

`drummer/api/routes/tutorial.py`:

- `TutorialStep` gains `graphql: GraphQLConfig | None = None` (import `GraphQLConfig` from
  `drummer.core.storage.formats`).
- `_step_to_request_file` passes `graphql=step.graphql` into the `RequestFrontmatter`.
- Three steps appended to `STEPS`, each `method="POST"`,
  `url="http://localhost:8000/mock/wikidata/graphql"`, with a `GraphQLConfig`:

  1. **Your first GraphQL query** — `{ entity(id: "Q42") { label description instanceOf { label } } }`.
     Teaches the single endpoint and selection sets.
  2. **Nested selection and variables** —
     `query($id: ID!) { entity(id: $id) { label author { label placeOfBirth { label country { label } } } } }`,
     variables `{"id": "Q3107329"}`. Teaches following relations and GraphQL operation variables
     (distinct from environment variables).
  3. **Explore the schema** — a simple query; instructions point to the GraphQLTab **Schema**
     sub-tab to browse types via introspection.

`GET /api/tutorial/steps` then returns 10 steps; the GraphQL steps carry a `graphql` config.

## Frontend

- `frontend/src/types.ts`: add `graphql?: GraphQLConfig | null` to the `TutorialStep` interface
  (`GraphQLConfig` already exists from Phase 8).
- `frontend/src/api/tutorial.ts`: `stepToRequestDetail` sets `graphql: step.graphql ?? undefined`
  on the synthetic `frontmatter`. Because the Body tab's mode-sync keys on `hasGraphql` (presence
  of `frontmatter.graphql`), a GraphQL step automatically renders the real `GraphQLTab` in the
  tutorial's request pane — no tutorial-specific UI.
- No other frontend changes: the real Send streams through `responseStore`; the Schema sub-tab
  introspects the mock endpoint via the existing proxy.

## Attribution

Extend `_ATTRIBUTION` in `drummer/cli.py` to add a Wikidata block: the dataset is a snapshot of
Wikidata content, licensed CC0, source `https://www.wikidata.org`. Printed by `drummer --attribution`.

## Testing

**Backend (pytest)**
- `wikidata.py`: `entity(id)` returns the real scalar fields; a nested relation resolves
  end to end (book → author → placeOfBirth → country); `search(term)` matches expected ids;
  unknown id → `null`; a malformed query surfaces `errors`; an introspection query returns a
  populated `__schema`.
- Snapshot integrity: every relation id referenced by any entity exists in the snapshot.
- Route: `POST /mock/wikidata/graphql` returns the expected data for a known query.
- Tutorial route: the 3 new steps send and return GraphQL data; `GET /api/tutorial/steps`
  returns 10 steps and the GraphQL steps carry a `graphql` config.
- CLI: `--attribution` output includes the Wikidata block.

**Frontend (vitest)**
- `stepToRequestDetail`: a step with a `graphql` config produces a `RequestDetail` whose
  `frontmatter.graphql` is set (driving GraphQL mode).

**Gate:** `make check` (ruff + pyright + biome + tsc + pytest) stays green. No suppression
comments. `graphql-core` added to `pyproject.toml` and the lockfile.

## Docs / roadmap updates

- `ROADMAP.md` Phase 14 → ✅ Done (completing the 14-phase arc).
- `CLAUDE.md` current phase → 14.
- README / attribution mention the Wikidata dataset.

## Open considerations (resolve during planning, not blocking)

- Exact entity set: pick the ~15 Q-ids during planning so the three tutorial queries have
  meaningful, connected data; verify each against the live Wikidata API when building the snapshot.
- `graphql-core` version pin.
