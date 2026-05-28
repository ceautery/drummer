# Phase 8 Design: GraphQL

**Date:** 2026-05-28  
**Status:** Approved

## Overview

Phase 8 adds full GraphQL support to Drummer:

1. **Data model** — `GraphQLConfig` wired into the save/load pipeline and send engine
2. **Introspection endpoint** — `POST /api/graphql/introspect` proxies introspection queries server-side to avoid CORS
3. **GraphQL BodyTab mode** — three sub-tabs (Query / Variables / Schema) with schema-aware autocomplete via `cm6-graphql`

---

## Data Model & File Format

### Python (`drummer/core/storage/formats.py`)

`GraphQLConfig` already exists but has the wrong type for `variables`. Change:

```python
class GraphQLConfig(BaseModel):
    query: str = ""
    variables: dict[str, Any] = Field(default_factory=dict)
```

`variables` changes from `dict[str, str]` to `dict[str, Any]` to support booleans, numbers, nested objects, and arrays.

`RequestFrontmatter.graphql: GraphQLConfig | None = None` — unchanged.

### YAML frontmatter format

```yaml
---
name: Get departments
method: POST
url: https://api.example.com/graphql
graphql:
  query: |
    query GetDepts($limit: Int) {
      departments(limit: $limit) { id displayName }
    }
  variables:
    limit: 10
    active: true
---
```

The `body` field is ignored when `graphql` is set. Any YAML-native value (bool, int, string, list, dict) is valid in `variables`.

### TypeScript (`frontend/src/types.ts`)

Add:

```typescript
export interface GraphQLConfig {
  query: string;
  variables: Record<string, unknown>;
}
```

Add to `RequestFrontmatter`:

```typescript
graphql?: GraphQLConfig;
```

---

## Backend

### Send pipeline (`drummer/core/engine.py`)

When `resolved.graphql` is not `None`:

1. Variable substitution (`{{...}}`) runs on `resolved.graphql.query` (same `substitute()` call used elsewhere).
2. Body synthesized as `json.dumps({"query": query, "variables": resolved.graphql.variables})`.
3. `Content-Type: application/json` injected into headers if not already present.
4. `resolved.body` is ignored.
5. Method is not forced — callers set it (POST is conventional; the UI defaults to POST when GraphQL mode is first activated).

`ResolvedRequest` gains a `graphql: GraphQLConfig | None = None` field, populated by `resolve()` from `request_file.frontmatter.graphql`.

### Introspection endpoint

New file: `drummer/api/routes/graphql_routes.py`, mounted at `/api/graphql` in `app.py`.

```
POST /api/graphql/introspect
```

Request body (Pydantic model):

```python
class IntrospectRequest(BaseModel):
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
```

Handler runs the standard GraphQL introspection query via httpx (using `app.state.transport` for test injection), then returns the raw JSON response from the server. HTTP errors from the upstream server are forwarded as-is with a 502.

The standard introspection query string is a module-level constant in `graphql_routes.py`.

**No new Python dependencies.** Introspection is just JSON parsing and an httpx POST.

---

## Frontend

### New components

**`frontend/src/components/request/GraphQLTab.tsx`**

Top-level GraphQL editor. Owns schema state (`schema: BuildClientSchema | null`). Three sub-tabs rendered as pill buttons inside the component:

| Sub-tab | Content |
|---------|---------|
| Query | CodeMirror editor with `cm6-graphql` extension. Reads/writes `frontmatter.graphql.query` via `patch()`. Autocomplete active when schema is loaded. |
| Variables | CodeMirror editor in JSON mode. Reads/writes `frontmatter.graphql.variables` (round-trips through `JSON.parse` / `JSON.stringify`). Starts as `{}`. |
| Schema | Type explorer tree (see below). Contains **Fetch Schema** button. |

**`frontend/src/components/request/SchemaExplorer.tsx`**

Receives `schema: BuildClientSchema | null` and `onFetch: () => void` as props.

- Before fetch: centered "No schema loaded" message + "Fetch Schema" button.
- After fetch: scrollable list of types grouped as Root Types then Object Types then other. Each type row shows name + kind badge; clicking expands to show fields with their return types. Input types, scalars, and built-in types (prefixed `__`) are collapsed by default.
- Fetch Schema button always visible in the header, shows a spinner while fetching.

Fetching: `GraphQLTab` calls `POST /api/graphql/introspect` with the current request URL and headers, receives the introspection JSON, and calls `buildClientSchema(data)` from the `graphql` package to produce a `BuildClientSchema` instance. Passes this to `SchemaExplorer` and to the `cm6-graphql` editor extension.

### Modified components

**`frontend/src/components/request/BodyTab.tsx`**

- Remove `disabled` and `cursor-not-allowed` from the graphql button.
- Remove the `title` tooltip placeholder text.
- When `mode === "graphql"`, render `<GraphQLTab />` instead of the CodeMirror editor.
- On load: if `current?.frontmatter.graphql` is set, initialize `mode` to `"graphql"` (derive from store, not hardcoded `"raw"`).
- When switching to GraphQL mode for the first time on a request that has no `graphql` frontmatter, `patch({ graphql: { query: "", variables: {} }, method: "POST" })`.

**`frontend/src/store/requestStore.ts`**

`patch()` already accepts `Partial<RequestFrontmatter>` — adding `graphql` to `RequestFrontmatter` is sufficient. No store changes needed.

### New JS dependencies

| Package | Purpose |
|---------|---------|
| `graphql` | Reference implementation: `buildClientSchema`, introspection types |
| `cm6-graphql` | CodeMirror 6 extension: syntax highlighting, autocomplete, validation |

---

## Navigation / Mounting

`drummer/api/app.py`: add `from drummer.api.routes import graphql_routes` and `app.include_router(graphql_routes.router)`.

---

## Testing

### Unit tests (`tests/unit/test_graphql_engine.py`)

- `resolve()` on a request with `graphql` set populates `resolved.graphql`
- Engine synthesizes body `{"query": ..., "variables": {...}}` when `graphql` is set
- Engine injects `Content-Type: application/json` header when `graphql` is set and no content-type present
- Engine does not override an existing `Content-Type` header
- `body` field ignored when `graphql` is set
- Variable substitution runs on `graphql.query` string (e.g. `{{endpoint}}` in query is substituted)

### Unit tests (`tests/unit/test_graphql_introspect.py`)

- `IntrospectRequest` model rejects missing `url`
- `IntrospectRequest` model accepts optional `headers`

### Integration tests (`tests/integration/test_graphql_introspect.py`)

Uses a mock httpx transport that returns a pre-baked introspection JSON blob (stored as a fixture constant).

- `POST /api/graphql/introspect` with valid body → 200, returns introspection JSON
- `POST /api/graphql/introspect` with upstream 400 → 502

### Integration tests (`tests/integration/test_graphql_send.py`)

Uses ASGITransport pointing at the app itself (same self-referential pattern as tutorial tests).

- Sending a request with `graphql` set uses POST and JSON body
- Variables are included in the synthesized body
- `Content-Type: application/json` present in outgoing request

### Frontend

No new Vitest tests. Send behavior covered by backend integration tests.

---

## Out of Scope for Phase 8

- Mutation / subscription support (queries only in the UI — but the send pipeline handles any operation type)
- Persisting introspected schema to disk
- GraphQL request history differentiation (stored same as REST in history DB)
- Form-data body mode (still shows "coming soon" placeholder)
- Authentication flows for introspection (headers field in the introspect request covers Bearer/API key manually)
