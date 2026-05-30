# Phase 17 — Sent-Request Inspector — Design

**Date:** 2026-05-30
**Status:** Approved (brainstorming)
**Arc:** Post-1.0 hardening (`docs/superpowers/specs/2026-05-29-post-1.0-hardening-arc-design.md`) — final planned phase.

## Context

When a request is sent, the user currently sees only the *response* (status, time, size,
body, headers, raw, script output, history). There is no view of **what was actually
sent** — the final URL after `{{variable}}` substitution, the query params, the headers
(including the computed auth header), or the body. And **unresolved-variable warnings**
(a stray `{{typo}}` left in the URL or a header) are computed on every send but never
shown to the user.

The engine already computes all of this; Phase 17 is almost entirely about **surfacing**
it.

### What already exists
- `drummer/core/engine.py` `send()` computes the truly-sent request internally as locals
  `send_method` / `send_url` / `send_headers` / `send_params` / `send_body` — these reflect
  variable substitution **and** pre-script mutations, OAuth token injection, and cookie
  headers. They are **not** returned.
- `RequestResult.warnings` holds the unresolved-variable names (from
  `drummer/core/variables.resolve`). It is written to the history DB but **never streamed
  to the frontend**.
- The SSE stream (`drummer/api/routes/send.py`) emits `status`, `headers`, `body`, `done`,
  `error` events — nothing about the sent request or warnings.
- Response tabs (`RequestResponseWorkbench.tsx`): Body / Headers / Raw / Script Output /
  History. `responseStore` holds response data only.

## Decisions (from brainstorming)
- **Show the truly-sent wire request** (after pre-script mutations + OAuth + cookies), not
  just the resolved request — so the inspector never misrepresents what happened.
- **New "Sent" response tab** + a **persistent unresolved-variable banner** rendered above
  the response tabs (so a stray `{{typo}}` can't be missed regardless of the active tab).
- **`Authorization` header value is masked** in the Sent tab display (shown as
  `Bearer ••••••` / `••••••`). Masking is **display-only** on the frontend; the engine
  returns real values. Everything else (params, body, other headers) shows as-sent. No
  reveal toggle.
- Also surface the **variable set actually used** (read-only) as a small section in the
  Sent tab.
- **History is left unchanged in this phase** (see Follow-up work).

## Architecture

Additive within existing layers (`core` → `api` → `frontend`); no layer-boundary change,
no ADR. `make check` green per commit; run `npm run test` (vitest) explicitly before any
frontend commit (since `make check` does not run the frontend suite).

### Backend

`drummer/core/engine.py`
- Add a model:
  ```python
  class SentRequest(BaseModel):
      method: str
      url: str
      params: dict[str, str] = Field(default_factory=dict)
      headers: dict[str, str] = Field(default_factory=dict)
      body: str = ""
  ```
- Add `sent: SentRequest | None = None` and `variables: dict[str, str] = Field(default_factory=dict)`
  to `RequestResult`.
- Populate `sent` from the final `send_*` values at the httpx call site (so it reflects
  pre-script mutations, the injected OAuth `Authorization`, etc.), and `variables` from the
  in-scope `variables` dict (post-pre-script). On the early pre-script-error return path,
  `sent` stays `None` but `warnings` (and `variables`) are still returned.
  - Note: for GraphQL requests the body actually sent is the JSON envelope
    (`{"query":..., "variables":...}`); `sent.body` should reflect what is put on the wire
    (the encoded GraphQL JSON), matching `send`'s existing behavior.

`drummer/api/routes/send.py`
- Emit a new SSE event **`request`** with data `{ sent, warnings, variables }`:
  - On the normal path: after the `body` event, before persisting history / `done`.
  - On the early script-error path (`status_code == 0`): emit `request` with `sent: null`
    plus `warnings`/`variables` before the early `done`, so the banner works even when no
    response arrives.
- History persistence is unchanged.

### Frontend

`frontend/src/types.ts`
- Add `SentRequest` interface (`method, url, params, headers, body`).

`frontend/src/api/sse.ts` / `frontend/src/api/useSend.ts`
- Handle the new `request` SSE event → call a new responseStore setter.

`frontend/src/store/responseStore.ts`
- Add `sentRequest: SentRequest | null`, `warnings: string[]`, `variablesUsed: Record<string,string>`,
  and a `setRequestInfo(sent, warnings, variables)` action. `reset` clears them.

`frontend/src/components/response/SentViewer.tsx` (new)
- Renders the sent request: method + URL, a params table, a headers table (with the
  `Authorization` value masked), the body (or "(none)"), and a small read-only
  "Variables used" key/value list. When `sentRequest` is `null`, shows
  "No request was sent — a pre-request script failed before sending."

`frontend/src/components/response/UnresolvedWarningBanner.tsx` (new)
- A small banner ("⚠ Unresolved variables: {{x}}, {{y}}") shown only when `warnings` is
  non-empty. Rendered above the response tab bar in the workbench.

`frontend/src/components/layout/RequestResponseWorkbench.tsx`
- Add `"sent"` to `ResponseTab` and to the response tabs list (label "Sent"); render
  `SentViewer` for that tab; render `UnresolvedWarningBanner` above the response tab bar.

### Data flow
send → engine computes `sent` + `warnings` + `variables` → route streams the `request`
SSE event → `useSend`/`sse` handler → `responseStore.setRequestInfo` → workbench renders
the Sent tab and the warning banner.

## Error handling
- `sent: null` → Sent tab shows the "no request sent" message; banner still shows if
  warnings exist.
- Empty `warnings` → no banner (zero cost on the happy path).
- Masking is display-only; never sent over the wire differently.

## Testing
- **Engine unit test:** `send()` populates `result.sent` with the truly-sent
  url/method/params/headers/body — including a pre-script URL mutation reflected in
  `sent.url` and an injected `Authorization` header present in `sent.headers`; `warnings`
  and `variables` carried through.
- **Route integration test:** the SSE stream includes a `request` event whose data has
  `sent` (with url/params/headers) and `warnings` (reuse the `parse_sse` helper +
  `client_with_mock`); assert a request whose URL has an unresolved `{{var}}` yields a
  non-empty `warnings`.
- **Frontend:** `responseStore` (setRequestInfo populates; reset clears); `SentViewer`
  (renders method/url/params/headers/body, masks `Authorization`, shows the null-sent
  message); `UnresolvedWarningBanner` (renders iff warnings non-empty).

## Out of scope (YAGNI)
- Secret-reveal toggle for the masked header.
- Editing or replaying the sent request.

## Follow-up work (tagged, NOT in Phase 17)
**History capture accuracy.** The history DB record (`ResponseHistoryRecord`) stores the
*resolved* (pre-mutation) headers/body, **omits query params entirely**, and stores the
response URL rather than the substituted request URL. A follow-up should:
- Add a `request_params` column to `ResponseHistoryRecord` (a schema change — needs a
  migration/`init_db` handling).
- Persist the **truly-sent** request (`result.sent`) into the history record
  (method/url/headers/params/body), and surface params in the `HistoryDrawer`.
This is deliberately deferred because it requires a DB schema change; the live Sent tab
fully answers "what was sent" for the current request. Tracked in `TODO.md`.
