# Phase 17 — Sent-Request Inspector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface what was actually sent (final URL, params, headers, body — after pre-script mutations + OAuth + cookies) in a new "Sent" response tab, plus a persistent unresolved-variable warning banner.

**Architecture:** The engine already computes the truly-sent request and the unresolved-variable warnings; it just doesn't return/stream them. Add a `SentRequest` to the engine's `RequestResult`, stream it (plus warnings + the variable set) on a new SSE `request` event, capture it in `responseStore`, and render a `SentViewer` tab + an `UnresolvedWarningBanner`. Additive within existing layers — no ADR.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pytest + httpx; React 19, TypeScript, Vite, Zustand, Vitest + Testing Library, Biome.

**Critical process notes:**
- `make check` does NOT run the frontend vitest suite. For every frontend task run `cd frontend && npx vitest run` AND `cd frontend && npx tsc -b` before committing.
- In Vitest, never destructure `vi.mocked(fn).mock.calls[0]` (fails `tsc -b`); use `toHaveBeenCalledWith` or `mock.calls[0]?.[i]`.
- No suppression comments (`# type: ignore`, `# noqa`, `biome-ignore`, `@ts-ignore`), no `any`, no non-null assertions. Fix at the root.
- End commit messages with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- History capture is intentionally OUT of scope (tagged as follow-up in the spec and TODO.md). Do not change `ResponseHistoryRecord` or the history persistence in `send.py`.

---

## File Structure

**Backend**
- Modify `drummer/core/engine.py` — `SentRequest` model + `sent`/`variables` on `RequestResult` (Task 1).
- Modify `tests/unit/test_engine.py` — engine tests (Task 1).
- Modify `drummer/api/routes/send.py` — emit the `request` SSE event (Task 2).
- Modify `tests/integration/test_send_route.py` — SSE event test (Task 2).

**Frontend**
- Modify `frontend/src/types.ts` — `SentRequest` interface (Task 3); add `"sent"` to `ResponseTab` (Task 7).
- Modify `frontend/src/store/responseStore.ts` — sentRequest/warnings/variablesUsed + setter (Task 3).
- Create `frontend/src/store/responseStore.test.ts` — store test (Task 3).
- Modify `frontend/src/api/sse.ts` — handle the `request` event (Task 4).
- Create `frontend/src/api/sse.test.ts` — consumeSSE test (Task 4).
- Create `frontend/src/components/response/SentViewer.tsx` + `.test.tsx` (Task 5).
- Create `frontend/src/components/response/UnresolvedWarningBanner.tsx` + `.test.tsx` (Task 6).
- Modify `frontend/src/components/layout/RequestResponseWorkbench.tsx` — Sent tab + banner (Task 7).
- Modify `ROADMAP.md`, `TODO.md` — close-out (Task 8).

Green-commit ordering: backend 1→2 (independent); frontend 3 (types+store) → 4 (sse) → 5 (SentViewer) → 6 (banner) → 7 (workbench wiring) → 8 (gate/docs).

---

## Task 1: Engine exposes the truly-sent request

**Files:**
- Modify: `drummer/core/engine.py`
- Test: `tests/unit/test_engine.py`

**Context:** `RequestResult` currently has response fields + `warnings`. `send()` computes `send_method/send_url/send_headers/send_params/send_body` (the truly-sent values, after pre-script mutations and the OAuth `Authorization` injection) and, for GraphQL, a JSON envelope `graphql_body`. There is an early return when a pre-script errors (`status_code=0`). `tests/unit/test_engine.py` uses `_MockTransport` (which records `last_request`), `CookieJar()`, and `async def` tests — mirror that file's existing async test decoration and helpers.

- [ ] **Step 1: Write failing tests.** Append to `tests/unit/test_engine.py` (mirror the file's existing async-test style and `_MockTransport`/`CookieJar` usage). Two tests:

```python
async def test_send_result_includes_sent_request() -> None:
    transport = _MockTransport(status_code=_HTTP_OK, content=b"ok")
    resolved = ResolvedRequest(
        name="t",
        method="GET",
        url="https://api.example.com/v1",
        params={"q": "x"},
        headers={"Accept": "application/json", "Authorization": "Bearer tok"},
        warnings=["missing_var"],
        variables={"base_url": "https://api.example.com"},
    )
    result = await send(resolved, CookieJar(), transport=transport)
    assert result.sent is not None
    assert result.sent.method == "GET"
    assert result.sent.url == "https://api.example.com/v1"
    assert result.sent.params == {"q": "x"}
    # The auth header that resolve() injected is visible in the sent request.
    assert result.sent.headers.get("Authorization") == "Bearer tok"
    assert result.warnings == ["missing_var"]
    assert result.variables == {"base_url": "https://api.example.com"}


async def test_send_sent_reflects_pre_script_url_mutation() -> None:
    # Mirror an existing pre-script test in this file for the exact dm API used to mutate
    # the request URL (grep this file for `pre_script=` to copy the working dm API call).
    transport = _MockTransport(status_code=_HTTP_OK, content=b"ok")
    resolved = ResolvedRequest(
        name="t",
        method="GET",
        url="https://api.example.com/v1",
        pre_script=_PRE_SCRIPT_THAT_SETS_URL_TO_V2,  # define using the real dm API
    )
    result = await send(resolved, CookieJar(), transport=transport)
    assert result.sent is not None
    assert result.sent.url == "https://api.example.com/v2"
```

For the second test: look at an existing `pre_script=` test in `test_engine.py` and reuse the exact dm API that mutates `request.url` (e.g. whatever sets `request_mutations["url"]`). Replace `_PRE_SCRIPT_THAT_SETS_URL_TO_V2` with that real script string. If the dm API cannot set the URL, instead mutate a header and assert `result.sent.headers` reflects it — the point is that `sent` is the post-mutation request.

- [ ] **Step 2: Run — expect FAIL** (`result.sent` doesn't exist / AttributeError or model lacks field): `venv/bin/pytest tests/unit/test_engine.py -k "sent" -v`

- [ ] **Step 3: Implement.** In `drummer/core/engine.py`:

(a) Add the model after the imports, before `ResolvedRequest`:

```python
class SentRequest(BaseModel):
    method: str
    url: str
    params: dict[str, str] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    body: str = ""
```

(b) Add two fields to `RequestResult`:

```python
    sent: "SentRequest | None" = None
    variables: dict[str, str] = Field(default_factory=dict)
```

(c) In the early pre-script-error `return RequestResult(...)` (the one with `status_code=0`), add `sent=None` and `variables=variables` to the constructor args.

(d) In `send()`, compute the wire body next to where `content` is built. Replace the existing graphql/else block that sets `content` so it also records a human-readable `sent_body`:

```python
    if resolved.graphql is not None:
        graphql_body = json.dumps(
            {"query": resolved.graphql.query, "variables": resolved.graphql.variables}
        )
        content = encode_body(graphql_body, resolved.encoding)
        if not any(k.lower() == "content-type" for k in send_headers):
            send_headers["Content-Type"] = "application/json"
        sent_body = graphql_body
    else:
        content = encode_body(send_body, resolved.encoding) if send_body else None
        sent_body = send_body
```

(e) In the final `return RequestResult(...)`, add:

```python
        sent=SentRequest(
            method=send_method,
            url=send_url,
            params=send_params,
            headers=send_headers,
            body=sent_body,
        ),
        variables=variables,
```

- [ ] **Step 4: Run — expect PASS:** `venv/bin/pytest tests/unit/test_engine.py -v`

- [ ] **Step 5: Lint + commit.** `venv/bin/ruff check drummer tests && venv/bin/ruff format --check . && venv/bin/pyright drummer`

```bash
git add drummer/core/engine.py tests/unit/test_engine.py
git commit -m "feat(core): engine returns the truly-sent request + variables on RequestResult (17)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Send route streams the `request` SSE event

**Files:**
- Modify: `drummer/api/routes/send.py`
- Test: `tests/integration/test_send_route.py`

**Context:** `generate()` yields `status`, `headers`, `body`, then persists history, then `done`. There's an early `done` on the script-error path (`result.script_error and result.status_code == 0`). `result.sent`, `result.warnings`, `result.variables` now exist (Task 1). The integration `conftest` provides `parse_sse(text)` and a `client_with_mock` fixture; `tests/integration/test_send_route.py` already shows how to POST `/api/send` and consume the SSE body — mirror that pattern.

- [ ] **Step 1: Write the failing test.** Append to `tests/integration/test_send_route.py` (mirror the existing SSE-consumption + request-creation pattern in that file; `parse_sse` is importable from the integration conftest as the other tests import it):

```python
async def test_send_emits_request_event_with_sent_and_warnings(client_with_mock: AsyncClient) -> None:
    await client_with_mock.post(
        "/api/requests",
        json={"path": "u.md", "name": "U", "method": "GET", "url": "https://api.test/{{missing}}"},
    )
    # Send and collect the full SSE body, then parse events (match how the other
    # tests in this file read the stream).
    resp = await client_with_mock.post("/api/send", json={"path": "u.md"})
    events = parse_sse(resp.text)
    request_events = [e for e in events if e["event"] == "request"]
    assert len(request_events) == 1
    data = request_events[0]["data"]
    assert data["sent"] is not None
    assert "{{missing}}" in data["sent"]["url"]
    assert "missing" in data["warnings"]
```

If `parse_sse` is not already imported in this file, import it the same way the existing tests do (from the integration conftest module).

- [ ] **Step 2: Run — expect FAIL** (no `request` event): `venv/bin/pytest tests/integration/test_send_route.py -k request_event -v`

- [ ] **Step 3: Implement.** In `drummer/api/routes/send.py`, inside `generate()`:

(a) On the **normal path**, add a `request` event immediately after the `body` yield (before `record_id = str(uuid4())`):

```python
            yield {
                "event": "request",
                "data": json.dumps(
                    {
                        "sent": result.sent.model_dump() if result.sent else None,
                        "warnings": result.warnings,
                        "variables": result.variables,
                    }
                ),
            }
```

(b) On the **early script-error path**, add the same `request` event (with `sent` likely null) immediately before that early `done` yield:

```python
            yield {
                "event": "request",
                "data": json.dumps(
                    {
                        "sent": result.sent.model_dump() if result.sent else None,
                        "warnings": result.warnings,
                        "variables": result.variables,
                    }
                ),
            }
```

- [ ] **Step 4: Run — expect PASS:** `venv/bin/pytest tests/integration/test_send_route.py -v`

- [ ] **Step 5: Lint + commit.** `venv/bin/ruff check drummer tests && venv/bin/ruff format --check . && venv/bin/pyright drummer`

```bash
git add drummer/api/routes/send.py tests/integration/test_send_route.py
git commit -m "feat(api): stream a 'request' SSE event with the sent request + warnings (17)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: `SentRequest` type + responseStore state

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/store/responseStore.ts`
- Test: `frontend/src/store/responseStore.test.ts` (create)

- [ ] **Step 1: Write the failing test.** Create `frontend/src/store/responseStore.test.ts`:

```ts
import { beforeEach, describe, expect, it } from "vitest";
import { useResponseStore } from "./responseStore";

describe("responseStore.setRequestInfo", () => {
  beforeEach(() => {
    useResponseStore.getState().reset();
  });

  it("stores the sent request, warnings, and variables", () => {
    useResponseStore.getState().setRequestInfo(
      {
        method: "GET",
        url: "https://x/{{missing}}",
        params: { q: "1" },
        headers: { Accept: "application/json" },
        body: "",
      },
      ["missing"],
      { base_url: "https://x" },
    );
    const s = useResponseStore.getState();
    expect(s.sentRequest?.url).toBe("https://x/{{missing}}");
    expect(s.warnings).toEqual(["missing"]);
    expect(s.variablesUsed).toEqual({ base_url: "https://x" });
  });

  it("reset clears the request info", () => {
    useResponseStore.getState().setRequestInfo(
      { method: "GET", url: "https://x", params: {}, headers: {}, body: "" },
      ["w"],
      { a: "b" },
    );
    useResponseStore.getState().reset();
    const s = useResponseStore.getState();
    expect(s.sentRequest).toBeNull();
    expect(s.warnings).toEqual([]);
    expect(s.variablesUsed).toEqual({});
  });
});
```

- [ ] **Step 2: Run — expect FAIL** (`setRequestInfo` not a function): `cd frontend && npx vitest run src/store/responseStore.test.ts`

- [ ] **Step 3: Implement.**

In `frontend/src/types.ts`, add (near the other request types):

```ts
export interface SentRequest {
  method: string;
  url: string;
  params: Record<string, string>;
  headers: Record<string, string>;
  body: string;
}
```

In `frontend/src/store/responseStore.ts`:
- Add `import type { ResponseTab, SentRequest, StreamingState } from "../types";` (extend the existing type import to include `SentRequest`).
- Add to the `ResponseState` interface:

```ts
  sentRequest: SentRequest | null;
  warnings: string[];
  variablesUsed: Record<string, string>;
  setRequestInfo: (
    sent: SentRequest | null,
    warnings: string[],
    variables: Record<string, string>,
  ) => void;
```

- Add to `initialState`:

```ts
  sentRequest: null as SentRequest | null,
  warnings: [] as string[],
  variablesUsed: {} as Record<string, string>,
```

- Add the action in the store body:

```ts
  setRequestInfo: (sentRequest, warnings, variablesUsed) =>
    set({ sentRequest, warnings, variablesUsed }),
```

(`reset` already spreads `initialState`, so the new fields are cleared on reset.)

- [ ] **Step 4: Run — expect PASS:** `cd frontend && npx vitest run src/store/responseStore.test.ts`

- [ ] **Step 5: Verify + commit.** `cd frontend && npx tsc -b` (clean) and `cd frontend && npm run check` (clean).

```bash
git add frontend/src/types.ts frontend/src/store/responseStore.ts frontend/src/store/responseStore.test.ts
git commit -m "feat(frontend): responseStore holds the sent request + warnings (17)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Handle the `request` SSE event in `consumeSSE`

**Files:**
- Modify: `frontend/src/api/sse.ts`
- Test: `frontend/src/api/sse.test.ts` (create)

**Context:** `consumeSSE(res, response, onDone)` iterates `parseSSE(res)` and dispatches per event onto the `response` (a `ResponseState`). Add a `request` branch. `parseSSE` reads `res.body?.getReader()`, so a real `new Response(sseText)` works as input in the test environment.

- [ ] **Step 1: Write the failing test.** Create `frontend/src/api/sse.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";
import type { ResponseState } from "../store/responseStore";
import { consumeSSE } from "./sse";

function sseResponse(blocks: string[]): Response {
  return new Response(blocks.join("\n\n") + "\n\n");
}

describe("consumeSSE request event", () => {
  it("dispatches setRequestInfo with sent, warnings, variables", async () => {
    const setRequestInfo = vi.fn();
    const stub = { setRequestInfo } as unknown as ResponseState;
    const payload = {
      sent: { method: "GET", url: "https://x/{{m}}", params: {}, headers: {}, body: "" },
      warnings: ["m"],
      variables: { a: "b" },
    };
    const res = sseResponse([`event: request\ndata: ${JSON.stringify(payload)}`]);
    await consumeSSE(res, stub);
    expect(setRequestInfo).toHaveBeenCalledWith(payload.sent, ["m"], { a: "b" });
  });
});
```

- [ ] **Step 2: Run — expect FAIL** (no `request` branch → setRequestInfo not called): `cd frontend && npx vitest run src/api/sse.test.ts`

- [ ] **Step 3: Implement.** In `frontend/src/api/sse.ts`:
- Add `import type { SentRequest } from "../types";` at the top.
- Add a branch inside the `for await` loop (e.g. after the `body` branch):

```ts
    } else if (event === "request") {
      const p = payload as {
        sent: SentRequest | null;
        warnings: string[];
        variables: Record<string, string>;
      };
      response.setRequestInfo(p.sent, p.warnings ?? [], p.variables ?? {});
```

- [ ] **Step 4: Run — expect PASS:** `cd frontend && npx vitest run src/api/sse.test.ts`

(If `new Response(text).body` is not a readable stream in the env, the test will surface it; in that case adapt the test to build the `Response` with a `ReadableStream` of `TextEncoder`-encoded chunks — but do NOT change `consumeSSE`'s behavior.)

- [ ] **Step 5: Verify + commit.** `cd frontend && npx tsc -b` and `cd frontend && npm run check` clean.

```bash
git add frontend/src/api/sse.ts frontend/src/api/sse.test.ts
git commit -m "feat(frontend): consumeSSE handles the 'request' event (17)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: `SentViewer` component

**Files:**
- Create: `frontend/src/components/response/SentViewer.tsx`
- Test: `frontend/src/components/response/SentViewer.test.tsx`

**Context:** Reads `sentRequest` and `variablesUsed` from `useResponseStore`. Masks the `Authorization` header value. Shows a friendly message when `sentRequest` is null. Mirror the styling of sibling response viewers (e.g. `HeadersViewer.tsx` uses simple tables with `text-xs font-mono`).

- [ ] **Step 1: Write the failing test.** Create `frontend/src/components/response/SentViewer.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { useResponseStore } from "../../store/responseStore";
import { SentViewer } from "./SentViewer";

afterEach(() => {
  useResponseStore.getState().reset();
});

describe("SentViewer", () => {
  it("renders method, url, params and masks the Authorization header", () => {
    useResponseStore.getState().setRequestInfo(
      {
        method: "GET",
        url: "https://api.example.com/v1",
        params: { q: "search" },
        headers: { Accept: "application/json", Authorization: "Bearer secret-token" },
        body: "",
      },
      [],
      {},
    );
    render(<SentViewer />);
    expect(screen.getByText("https://api.example.com/v1")).toBeInTheDocument();
    expect(screen.getByText("search")).toBeInTheDocument();
    expect(screen.getByText("application/json")).toBeInTheDocument();
    // The real token must NOT appear; a mask stands in for it.
    expect(screen.queryByText(/secret-token/)).not.toBeInTheDocument();
  });

  it("shows a message when no request was sent", () => {
    useResponseStore.getState().setRequestInfo(null, [], {});
    render(<SentViewer />);
    expect(screen.getByText(/no request was sent/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run — expect FAIL** (module missing): `cd frontend && npx vitest run src/components/response/SentViewer.test.tsx`

- [ ] **Step 3: Implement.** Create `frontend/src/components/response/SentViewer.tsx`:

```tsx
import { useResponseStore } from "../../store/responseStore";

function maskAuth(value: string): string {
  const space = value.indexOf(" ");
  return space > 0 ? `${value.slice(0, space)} ••••••` : "••••••";
}

function Rows({ entries }: { entries: Record<string, string> }) {
  const pairs = Object.entries(entries);
  if (pairs.length === 0) {
    return <p className="text-xs text-muted-foreground">(none)</p>;
  }
  return (
    <table className="w-full text-xs font-mono">
      <tbody>
        {pairs.map(([k, v]) => (
          <tr key={k} className="border-b last:border-0">
            <td className="px-2 py-0.5 text-muted-foreground align-top w-1/3">{k}</td>
            <td className="px-2 py-0.5 text-foreground break-all">{v}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function SentViewer() {
  const sent = useResponseStore((s) => s.sentRequest);
  const variablesUsed = useResponseStore((s) => s.variablesUsed);

  if (!sent) {
    return (
      <p className="px-3 py-4 text-xs text-muted-foreground">
        No request was sent — a pre-request script failed before sending.
      </p>
    );
  }

  const displayHeaders: Record<string, string> = Object.fromEntries(
    Object.entries(sent.headers).map(([k, v]) => [
      k,
      k.toLowerCase() === "authorization" ? maskAuth(v) : v,
    ]),
  );

  return (
    <div className="flex flex-col gap-3 p-2 text-sm">
      <div className="font-mono text-xs break-all">
        <span className="font-semibold">{sent.method}</span>{" "}
        <span className="text-foreground">{sent.url}</span>
      </div>
      <section>
        <h3 className="px-2 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Params
        </h3>
        <Rows entries={sent.params} />
      </section>
      <section>
        <h3 className="px-2 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Headers
        </h3>
        <Rows entries={displayHeaders} />
      </section>
      <section>
        <h3 className="px-2 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Body
        </h3>
        {sent.body ? (
          <pre className="px-2 text-xs font-mono whitespace-pre-wrap break-all text-foreground">
            {sent.body}
          </pre>
        ) : (
          <p className="px-2 text-xs text-muted-foreground">(none)</p>
        )}
      </section>
      <section>
        <h3 className="px-2 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Variables used
        </h3>
        <Rows entries={variablesUsed} />
      </section>
    </div>
  );
}
```

- [ ] **Step 4: Run — expect PASS:** `cd frontend && npx vitest run src/components/response/SentViewer.test.tsx`

- [ ] **Step 5: Verify + commit.** `cd frontend && npx tsc -b` and `cd frontend && npm run check` clean.

```bash
git add frontend/src/components/response/SentViewer.tsx frontend/src/components/response/SentViewer.test.tsx
git commit -m "feat(frontend): SentViewer renders the sent request (auth masked) (17)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: `UnresolvedWarningBanner` component

**Files:**
- Create: `frontend/src/components/response/UnresolvedWarningBanner.tsx`
- Test: `frontend/src/components/response/UnresolvedWarningBanner.test.tsx`

- [ ] **Step 1: Write the failing test.** Create `frontend/src/components/response/UnresolvedWarningBanner.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { useResponseStore } from "../../store/responseStore";
import { UnresolvedWarningBanner } from "./UnresolvedWarningBanner";

afterEach(() => {
  useResponseStore.getState().reset();
});

describe("UnresolvedWarningBanner", () => {
  it("renders the unresolved variable names when warnings exist", () => {
    useResponseStore
      .getState()
      .setRequestInfo({ method: "GET", url: "x", params: {}, headers: {}, body: "" }, ["api_key", "host"], {});
    render(<UnresolvedWarningBanner />);
    expect(screen.getByRole("alert")).toHaveTextContent("api_key");
    expect(screen.getByRole("alert")).toHaveTextContent("host");
  });

  it("renders nothing when there are no warnings", () => {
    const { container } = render(<UnresolvedWarningBanner />);
    expect(container).toBeEmptyDOMElement();
  });
});
```

- [ ] **Step 2: Run — expect FAIL:** `cd frontend && npx vitest run src/components/response/UnresolvedWarningBanner.test.tsx`

- [ ] **Step 3: Implement.** Create `frontend/src/components/response/UnresolvedWarningBanner.tsx`:

```tsx
import { useResponseStore } from "../../store/responseStore";

export function UnresolvedWarningBanner() {
  const warnings = useResponseStore((s) => s.warnings);
  if (warnings.length === 0) return null;
  return (
    <div
      role="alert"
      className="border-b border-amber-500/40 bg-amber-500/10 px-3 py-1.5 text-xs text-amber-700 dark:text-amber-400"
    >
      ⚠ Unresolved variables:{" "}
      <span className="font-mono">
        {warnings.map((w) => `{{${w}}}`).join(", ")}
      </span>
    </div>
  );
}
```

- [ ] **Step 4: Run — expect PASS:** `cd frontend && npx vitest run src/components/response/UnresolvedWarningBanner.test.tsx`

- [ ] **Step 5: Verify + commit.** `cd frontend && npx tsc -b` and `cd frontend && npm run check` clean.

```bash
git add frontend/src/components/response/UnresolvedWarningBanner.tsx frontend/src/components/response/UnresolvedWarningBanner.test.tsx
git commit -m "feat(frontend): UnresolvedWarningBanner for stray template variables (17)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Wire the Sent tab + banner into the workbench

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/components/layout/RequestResponseWorkbench.tsx`

**Context:** `RequestResponseWorkbench` defines `RESPONSE_TABS` and renders a response panel: `<ResponseMeta .../>`, then a tab-bar `<div>`, then the tab content (`{responseTab === "body" && ...}` etc.). The `ResponseTab` union lives in `types.ts`.

- [ ] **Step 1: Add `"sent"` to the `ResponseTab` union** in `frontend/src/types.ts`:

```ts
export type ResponseTab =
  | "body"
  | "headers"
  | "raw"
  | "sent"
  | "script-output"
  | "history";
```

- [ ] **Step 2: Wire the workbench.** In `frontend/src/components/layout/RequestResponseWorkbench.tsx`:

(a) Add imports:

```tsx
import { SentViewer } from "../response/SentViewer";
import { UnresolvedWarningBanner } from "../response/UnresolvedWarningBanner";
```

(b) Add a "Sent" entry to `RESPONSE_TABS` (place it after `raw`):

```tsx
  { id: "raw", label: "Raw" },
  { id: "sent", label: "Sent" },
  { id: "script-output", label: "Script Output" },
```

(c) In the `responsePanel`, render the banner immediately after `<ResponseMeta ... />` and before the tab-bar `<div>`:

```tsx
      <ResponseMeta
        statusCode={statusCode}
        elapsedMs={elapsedMs}
        bodyLength={body?.length ?? null}
        streaming={streaming}
      />
      <UnresolvedWarningBanner />
```

(d) In the tab-content area, add the Sent branch (next to the other `responseTab === ...` branches):

```tsx
        {responseTab === "sent" && <SentViewer />}
```

- [ ] **Step 3: Run the FULL frontend suite + typecheck.**
- `cd frontend && npx vitest run` → ALL pass.
- `cd frontend && npx tsc -b` → no errors.
- `cd frontend && npm run check` → clean.

- [ ] **Step 4: Commit.**

```bash
git add frontend/src/types.ts frontend/src/components/layout/RequestResponseWorkbench.tsx
git commit -m "feat(frontend): Sent response tab + unresolved-variable banner (17)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: Full-suite gate, in-app verification, docs

**Files:**
- Modify: `ROADMAP.md`, `TODO.md`

- [ ] **Step 1: Full gate.** `make check` → green. `cd frontend && npx vitest run` → all pass (remember `make check` does NOT run vitest). Fix anything red at the root, re-run.

- [ ] **Step 2: Manual in-app verification.** `cd frontend && npm run build`, then run the server against a temp project (`DRUMMER_HOME=$(mktemp -d) venv/bin/python -m drummer.cli serve --project <tmpproj> --port 8767`) where one request's URL contains a real `{{var}}` (defined in the env) and one contains a stray `{{typo}}` (not defined). In the browser:
  1. Send the well-formed request → open the **Sent** tab → confirm the final URL has the variable substituted, params/headers/body shown, and the `Authorization` value (if any) is masked.
  2. Send the request with `{{typo}}` → confirm the **⚠ Unresolved variables** banner appears above the response tabs naming `typo`, and the Sent tab shows the unsubstituted `{{typo}}` in the URL.
  Stop the server and remove temp dirs when done.

- [ ] **Step 3: Update docs.** In `ROADMAP.md`, change the Phase 17 row status to `✅ Done (verified in-app)`. In `TODO.md`: move Phase 17 to the Done section with a one-line summary; record that the **post-1.0 hardening arc is complete**; and ensure the **history-capture follow-up** (request_params column + persist the truly-sent request into history + show params in HistoryDrawer) is listed under follow-up/known-gaps.

- [ ] **Step 4: Commit.**

```bash
git add ROADMAP.md TODO.md
git commit -m "docs: close out Phase 17 (sent-request inspector); arc complete

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

- **Spec coverage:**
  - Truly-sent request exposed by the engine → Task 1 (`SentRequest` + `sent` populated from `send_*`, GraphQL body handled). ✓
  - Warnings + variables surfaced → Task 1 (carried on `RequestResult`) + Task 2 (streamed). ✓
  - New `request` SSE event (normal + early-error path with `sent: null`) → Task 2. ✓
  - responseStore holds sentRequest/warnings/variablesUsed, cleared on reset → Task 3. ✓
  - consumeSSE handles `request` → Task 4. ✓
  - Sent tab (method/url/params/headers/body + variables used, Authorization masked, null-sent message) → Task 5. ✓
  - Persistent unresolved-variable banner (shown iff warnings) → Task 6, rendered above tabs in Task 7. ✓
  - History unchanged; follow-up tagged → respected (no history changes) + Task 8 records the follow-up. ✓
- **Placeholder scan:** The only intentional placeholder is `_PRE_SCRIPT_THAT_SETS_URL_TO_V2` in Task 1, with explicit instructions to copy the real dm API from an existing `pre_script=` test in the same file (and a concrete fallback: mutate a header instead). Everything else is complete code.
- **Type consistency:** `SentRequest` fields (`method/url/params/headers/body`) are identical across the engine model (Task 1), the SSE payload (Task 2 `model_dump()`), the TS interface (Task 3), the sse cast (Task 4), and `SentViewer` (Task 5). `setRequestInfo(sent, warnings, variables)` signature matches its store definition (Task 3), the sse call site (Task 4), and the tests. `ResponseTab` gains `"sent"` in Task 7 before it's used in `RESPONSE_TABS`/rendering.
