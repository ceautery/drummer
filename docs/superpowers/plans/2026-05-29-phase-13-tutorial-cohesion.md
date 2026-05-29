# Phase 13 — Tutorial Cohesion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the tutorial cohesive with the app — one persistent AppBar with Workspace/Tutorial tabs, and the tutorial driving the real request/response panes instead of its bespoke card.

**Architecture:** Extract the request + response panels from `WorkspaceView` into a shared `RequestResponseWorkbench` that reads the singleton zustand stores. `TutorialView` seeds those stores per step (snapshotting/restoring them so nothing bleeds into the workspace) and renders the workbench beside a coach rail. Tutorial step content moves behind a new `GET /api/tutorial/steps` endpoint (single source of truth); the existing `POST /api/tutorial/steps/{i}/send` SSE endpoint is reused and rendered through `responseStore`.

**Tech Stack:** FastAPI + Pydantic (backend), React + TypeScript + Zustand + React Query + Vite (frontend), pytest + vitest/testing-library (tests). Gate: `make check`.

**Spec:** `docs/superpowers/specs/2026-05-29-phase-13-tutorial-cohesion-design.md`

---

## File Structure

**Backend**
- Modify `drummer/api/routes/tutorial.py` — add `GET /api/tutorial/steps` returning `list[TutorialStep]`.
- Modify `tests/integration/test_tutorial_route.py` — test the new endpoint.

**Frontend**
- Modify `frontend/src/store/responseStore.ts` — export the `ResponseState` interface.
- Modify `frontend/src/api/useSend.ts` — export `parseSSE`; extract a shared `consumeSSE` helper.
- Modify `frontend/src/types.ts` — add `TutorialStep`.
- Create `frontend/src/api/tutorial.ts` — `useTutorialSteps`, `useTutorialSend`, `stepToRequestDetail`.
- Create `frontend/src/components/layout/RequestResponseWorkbench.tsx` — extracted panels.
- Modify `frontend/src/views/WorkspaceView.tsx` — use the workbench.
- Modify `frontend/src/components/layout/AppBar.tsx` — Workspace/Tutorial tabs.
- Create `frontend/src/components/layout/AppBar.test.tsx` — tab + single-toggle test.
- Modify `frontend/src/views/TutorialView.tsx` — slim to coach rail + workbench.
- Modify `frontend/src/views/TutorialView.test.tsx` — new structure.
- Modify `frontend/src/App.tsx` — persistent AppBar + conditional body.

**Docs**
- Modify `ROADMAP.md`, `CLAUDE.md`.

---

## Task 1: Backend `GET /api/tutorial/steps`

**Files:**
- Modify: `drummer/api/routes/tutorial.py`
- Test: `tests/integration/test_tutorial_route.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/integration/test_tutorial_route.py`:

```python
@pytest.mark.asyncio
async def test_list_steps_returns_all_steps(tmp_path: Path) -> None:
    app = _make_tutorial_app(tmp_path)
    await init_db(_db_url(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/tutorial/steps")
    assert response.status_code == HTTPStatus.OK
    steps = response.json()
    assert len(steps) == 7
    assert steps[0]["title"] == "Welcome to Drummer"
    assert steps[0]["method"] is None
    assert steps[1]["method"] == "GET"
    assert steps[3]["params"] == {"q": "sunflowers"}
    assert "X-Tutorial-Id" in steps[5]["pre_script"]
    assert steps[4]["variable_overrides"] == {"base_url": "http://localhost:8000"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/pytest tests/integration/test_tutorial_route.py::test_list_steps_returns_all_steps -v`
Expected: FAIL — 404 Not Found (route does not exist yet).

- [ ] **Step 3: Add the endpoint**

In `drummer/api/routes/tutorial.py`, add this handler immediately after the `STEPS` list definition (before `_step_to_request_file`):

```python
@router.get("/steps")
def list_tutorial_steps() -> list[TutorialStep]:
    return STEPS
```

(`TutorialStep` is already a Pydantic model, so the response is fully typed — no untyped dicts.)

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/bin/pytest tests/integration/test_tutorial_route.py -v`
Expected: PASS (all tutorial route tests, including the new one).

- [ ] **Step 5: Commit**

```bash
git add drummer/api/routes/tutorial.py tests/integration/test_tutorial_route.py
git commit -m "feat(api): GET /api/tutorial/steps lists tutorial steps

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Shared SSE plumbing + tutorial API client

**Files:**
- Modify: `frontend/src/store/responseStore.ts`
- Modify: `frontend/src/api/useSend.ts`
- Modify: `frontend/src/types.ts`
- Create: `frontend/src/api/tutorial.ts`

No new standalone test: this matches the codebase pattern where thin API hooks (`useSettings`, `useWorkspaces`) are not unit-tested in isolation but mocked in component tests; the SSE event mapping is covered by the backend integration tests in Task 1 and the existing send-route tests. Verification is `npm run check` (tsc) plus the full vitest suite staying green.

- [ ] **Step 1: Export `ResponseState`**

In `frontend/src/store/responseStore.ts`, change the interface declaration line:

```ts
export interface ResponseState {
```

(It is currently `interface ResponseState {` — just add `export`.)

- [ ] **Step 2: Export `parseSSE` and extract a shared consumer in `useSend.ts`**

In `frontend/src/api/useSend.ts`:

1. Change `async function* parseSSE(` to `export async function* parseSSE(`.
2. Add this helper above `export function useSend()`, importing the `ResponseState` type at the top (`import type { ResponseState } from "../store/responseStore";`):

```ts
export async function consumeSSE(
  res: Response,
  response: ResponseState,
  onDone?: () => void,
): Promise<void> {
  for await (const { event, data } of parseSSE(res)) {
    const payload = JSON.parse(data) as unknown;
    if (event === "status") {
      const p = payload as { status_code: number; url: string };
      response.setStatus(p.status_code, p.url);
    } else if (event === "headers") {
      response.setHeaders(payload as [string, string][]);
    } else if (event === "body") {
      const p = payload as { body: string; encoding: string; elapsed_ms: number };
      response.setBody(p.body, p.encoding, p.elapsed_ms);
    } else if (event === "done") {
      const p = payload as {
        history_id: string | null;
        script_logs: string[];
        script_error: string | null;
        script_suggestion: string | null;
      };
      response.setDone(
        p.history_id,
        p.script_logs ?? [],
        p.script_error ?? null,
        p.script_suggestion ?? null,
      );
      onDone?.();
    } else if (event === "error") {
      const p = payload as { message: string };
      response.setError(p.message);
    }
  }
}
```

3. Replace the inline `for await (...) { ... }` block inside `useSend`'s `send` (the SSE loop, currently lines ~60–94) with:

```ts
        await consumeSSE(res, response, () => {
          void queryClient.invalidateQueries({
            queryKey: ["history", requestPath],
          });
        });
```

The surrounding `response.reset()`, `response.setStreaming("streaming")`, `fetch(...)`, the `try/catch` AbortError handling, and `cancel` are unchanged.

- [ ] **Step 3: Add the `TutorialStep` type**

In `frontend/src/types.ts`, append:

```ts
export interface TutorialStep {
  title: string;
  instructions: string;
  method: HttpMethod | null;
  url: string;
  params: Record<string, string>;
  headers: Record<string, string>;
  body: string;
  pre_script: string;
  post_script: string;
  variable_overrides: Record<string, string>;
}
```

- [ ] **Step 4: Create `frontend/src/api/tutorial.ts`**

```ts
import { useQuery } from "@tanstack/react-query";
import { useCallback, useRef } from "react";
import { useResponseStore } from "../store/responseStore";
import type { RequestDetail, TutorialStep } from "../types";
import { apiFetch } from "./client";
import { consumeSSE } from "./useSend";

export function useTutorialSteps() {
  return useQuery<TutorialStep[]>({
    queryKey: ["tutorial-steps"],
    queryFn: () => apiFetch<TutorialStep[]>("/api/tutorial/steps"),
    staleTime: Number.POSITIVE_INFINITY,
  });
}

export function useTutorialSend() {
  const abortRef = useRef<AbortController | null>(null);
  const response = useResponseStore();

  const send = useCallback(
    async (stepIndex: number) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      response.reset();
      response.setStreaming("streaming");

      try {
        const res = await fetch(`/api/tutorial/steps/${stepIndex}/send`, {
          method: "POST",
          signal: controller.signal,
        });
        await consumeSSE(res, response);
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          response.setError(String(err));
          response.setStreaming("error");
        }
      }
    },
    [response],
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    response.setStreaming("idle");
  }, [response]);

  return { send, cancel };
}

// Builds a display-only RequestDetail so the real request panes can render a
// tutorial step. The actual send goes through /api/tutorial/steps/{i}/send,
// which rebuilds the request from the backend STEPS, so these defaults are
// purely cosmetic.
export function stepToRequestDetail(step: TutorialStep): RequestDetail {
  return {
    path: "<tutorial>",
    body: step.body,
    frontmatter: {
      name: step.title,
      method: step.method ?? "GET",
      url: step.url,
      headers: step.headers,
      params: step.params,
      encoding: "utf-8",
      cookies: { mode: "session", cookies: {} },
      auth: {
        type: "none",
        token: "",
        username: "",
        password: "",
        key: "",
        value: "",
        token_url: "",
        client_id: "",
        client_secret: "",
        scope: "",
      },
      pre_script: step.pre_script,
      post_script: step.post_script,
      script_timeout_ms: null,
      tags: [],
      skip: false,
    },
  };
}
```

- [ ] **Step 5: Verify type-check and existing tests pass**

Run: `cd frontend && npm run check && npm run test -- --run`
Expected: tsc/biome clean; all existing vitest tests still pass (the `useSend` refactor is behavior-preserving).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/store/responseStore.ts frontend/src/api/useSend.ts frontend/src/types.ts frontend/src/api/tutorial.ts
git commit -m "feat(frontend): tutorial API client + shared SSE consumer

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Extract `RequestResponseWorkbench`

**Files:**
- Create: `frontend/src/components/layout/RequestResponseWorkbench.tsx`
- Modify: `frontend/src/views/WorkspaceView.tsx`

This is a behavior-preserving refactor. No `WorkspaceView` unit test exists; the guard is `npm run check` + the full vitest suite staying green, and the workbench is exercised by the Task 5 TutorialView test.

- [ ] **Step 1: Create the workbench component**

Create `frontend/src/components/layout/RequestResponseWorkbench.tsx` with the request + response panels lifted from `WorkspaceView` (it reads the stores directly; only `onSend`/`onCancel` are props):

```tsx
import { AuthTab } from "../request/AuthTab";
import { BodyTab } from "../request/BodyTab";
import { CookiesTab } from "../request/CookiesTab";
import { HeadersTab } from "../request/HeadersTab";
import { ParamsTab } from "../request/ParamsTab";
import { ScriptTab } from "../request/ScriptTab";
import { UrlBar } from "../request/UrlBar";
import { BodyViewer } from "../response/BodyViewer";
import { HeadersViewer } from "../response/HeadersViewer";
import { HistoryDrawer } from "../response/HistoryDrawer";
import { RawViewer } from "../response/RawViewer";
import { ResponseMeta } from "../response/ResponseMeta";
import { ScriptOutput } from "../response/ScriptOutput";
import { useRequestStore } from "../../store/requestStore";
import { useResponseStore } from "../../store/responseStore";
import { useSessionStore } from "../../store/sessionStore";
import type { HttpMethod, RequestTab, ResponseTab } from "../../types";
import { TwoPanel } from "./PanelGroup";

const REQUEST_TABS: { id: RequestTab; label: string }[] = [
  { id: "params", label: "Params" },
  { id: "headers", label: "Headers" },
  { id: "body", label: "Body" },
  { id: "auth", label: "Auth" },
  { id: "scripts", label: "Scripts" },
  { id: "cookies", label: "Cookies" },
];

const RESPONSE_TABS: { id: ResponseTab; label: string }[] = [
  { id: "body", label: "Body" },
  { id: "headers", label: "Headers" },
  { id: "raw", label: "Raw" },
  { id: "script-output", label: "Script Output" },
  { id: "history", label: "History" },
];

interface RequestResponseWorkbenchProps {
  onSend: () => void;
  onCancel: () => void;
}

export function RequestResponseWorkbench({
  onSend,
  onCancel,
}: RequestResponseWorkbenchProps) {
  const saved = useRequestStore((s) => s.saved);
  const draft = useRequestStore((s) => s.draft);
  const patchRequest = useRequestStore((s) => s.patch);
  const requestTab = useRequestStore((s) => s.activeTab);
  const setRequestTab = useRequestStore((s) => s.setTab);

  const streaming = useResponseStore((s) => s.streaming);
  const statusCode = useResponseStore((s) => s.statusCode);
  const elapsedMs = useResponseStore((s) => s.elapsedMs);
  const body = useResponseStore((s) => s.body);
  const responseHeaders = useResponseStore((s) => s.responseHeaders);
  const responseTab = useResponseStore((s) => s.activeTab);
  const setResponseTab = useResponseStore((s) => s.setTab);

  const { variables } = useSessionStore();

  const current = draft ?? saved;
  const contentType =
    responseHeaders.find(([k]) => k.toLowerCase() === "content-type")?.[1] ??
    "";

  const requestPanel = (
    <div className="flex h-full flex-col">
      <UrlBar
        method={current?.frontmatter.method ?? "GET"}
        url={current?.frontmatter.url ?? ""}
        onMethodChange={(m: HttpMethod) => patchRequest({ method: m })}
        onUrlChange={(url) => patchRequest({ url })}
        onSend={onSend}
        onCancel={onCancel}
        isStreaming={streaming === "streaming"}
        variables={variables}
      />
      <div className="flex gap-0 border-b px-2">
        {REQUEST_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setRequestTab(tab.id)}
            className={`px-3 py-1.5 text-xs border-b-2 ${
              requestTab === tab.id
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto">
        {requestTab === "params" && <ParamsTab />}
        {requestTab === "headers" && <HeadersTab />}
        {requestTab === "body" && <BodyTab />}
        {requestTab === "auth" && <AuthTab />}
        {requestTab === "scripts" && <ScriptTab />}
        {requestTab === "cookies" && <CookiesTab />}
      </div>
    </div>
  );

  const responsePanel = (
    <div className="flex h-full flex-col">
      <ResponseMeta
        statusCode={statusCode}
        elapsedMs={elapsedMs}
        bodyLength={body?.length ?? null}
        streaming={streaming}
      />
      <div className="flex gap-0 border-b px-2">
        {RESPONSE_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setResponseTab(tab.id)}
            className={`px-3 py-1.5 text-xs border-b-2 ${
              responseTab === tab.id
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto">
        {responseTab === "body" && (
          <BodyViewer body={body} contentType={contentType} />
        )}
        {responseTab === "headers" && (
          <HeadersViewer headers={responseHeaders} />
        )}
        {responseTab === "raw" && <RawViewer body={body} />}
        {responseTab === "script-output" && <ScriptOutput />}
        {responseTab === "history" && <HistoryDrawer />}
      </div>
    </div>
  );

  return (
    <TwoPanel
      left={requestPanel}
      right={responsePanel}
      direction="vertical"
      defaultSizes={[50, 50]}
    />
  );
}
```

- [ ] **Step 2: Refactor `WorkspaceView` to use the workbench**

In `frontend/src/views/WorkspaceView.tsx`:

1. Remove the now-unused imports for the request/response tab components and `TwoPanel`'s vertical usage that moved into the workbench: delete imports of `AuthTab`, `BodyTab`, `CookiesTab`, `HeadersTab`, `ParamsTab`, `ScriptTab`, `UrlBar`, `BodyViewer`, `HeadersViewer`, `HistoryDrawer`, `RawViewer`, `ResponseMeta`, `ScriptOutput`. Keep `Sidebar` and `TwoPanel` (still used for the sidebar/main split). Add `import { RequestResponseWorkbench } from "../components/layout/RequestResponseWorkbench";`.
2. Remove the now-unused store selectors that only fed the panels: `streaming`, `statusCode`, `elapsedMs`, `body`, `responseHeaders`, `responseTab`, `setResponseTab`, `requestTab`, `setRequestTab`, `patchRequest`, and `variables`/`useSessionStore`. Keep everything used by data loading + save + send: `project`, `setRequests`, `selectedPath`, `draft`, `saved`, `loadRequest`, `selectRequest`, `discardRequest`, `markSaved`, `isDirty`, the queries, `saveRequest`, and `send`/`cancel`.
3. Delete the `REQUEST_TABS`, `RESPONSE_TABS`, `contentType`, `current`, `requestPanel`, `responsePanel`, and `mainArea` definitions.
4. Replace the final return's `mainArea` with the workbench:

```tsx
  const mainArea = (
    <RequestResponseWorkbench onSend={handleSend} onCancel={cancel} />
  );

  return (
    <div className="flex h-full">
      <TwoPanel
        left={sidebar}
        right={mainArea}
        direction="horizontal"
        defaultSizes={[20, 80]}
      />
    </div>
  );
```

`handleSend`, `handleSave`, the Cmd+S effect, `sidebar`, and the data-loading effects remain in `WorkspaceView`.

- [ ] **Step 3: Verify type-check and tests pass**

Run: `cd frontend && npm run check && npm run test -- --run`
Expected: tsc/biome clean (no unused imports/vars — fix any flagged); all vitest tests pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/layout/RequestResponseWorkbench.tsx frontend/src/views/WorkspaceView.tsx
git commit -m "refactor(frontend): extract RequestResponseWorkbench from WorkspaceView

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: AppBar Workspace/Tutorial tabs

**Files:**
- Modify: `frontend/src/components/layout/AppBar.tsx`
- Create: `frontend/src/components/layout/AppBar.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/layout/AppBar.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useThemeStore } from "../../store/themeStore";
import { useViewStore } from "../../store/viewStore";
import { AppBar } from "./AppBar";

vi.mock("../../api/settings", () => ({
  useSetTheme: () => ({ mutate: vi.fn() }),
}));

vi.mock("../../api/workspaces", () => ({
  useWorkspaces: () => ({
    data: {
      active: "scratch",
      workspaces: [
        { id: "scratch", name: "Scratch", kind: "central", path: "/s", is_scratch: true },
      ],
    },
  }),
  useSwitchWorkspace: () => ({ mutate: vi.fn() }),
  useCreateWorkspace: () => ({ mutate: vi.fn() }),
  useRegisterWorkspace: () => ({ mutate: vi.fn() }),
}));

describe("AppBar", () => {
  beforeEach(() => {
    useViewStore.setState({ view: "workspace" });
    useThemeStore.setState({ theme: "system", systemDark: false });
  });

  it("renders Workspace and Tutorial tabs", () => {
    render(<AppBar />);
    expect(screen.getByRole("button", { name: "Workspace" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tutorial" })).toBeInTheDocument();
  });

  it("clicking Tutorial switches the view", async () => {
    render(<AppBar />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Tutorial" }));
    expect(useViewStore.getState().view).toBe("tutorial");
  });

  it("has exactly one theme toggle", () => {
    render(<AppBar />);
    expect(screen.getAllByLabelText(/theme/i)).toHaveLength(1);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- --run AppBar`
Expected: FAIL — the tabs don't exist yet (current AppBar has only a right-side "Tutorial" button, no "Workspace" button).

- [ ] **Step 3: Rewrite `AppBar.tsx`**

```tsx
import { useViewStore } from "../../store/viewStore";
import { ThemeToggle } from "./ThemeToggle";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";

const TABS = [
  { id: "workspace", label: "Workspace" },
  { id: "tutorial", label: "Tutorial" },
] as const;

export function AppBar() {
  const view = useViewStore((s) => s.view);
  const setView = useViewStore((s) => s.setView);
  return (
    <nav className="flex shrink-0 items-center gap-4 border-b bg-card px-4 py-2">
      <span className="text-sm font-semibold">🥁 Drummer</span>
      <div className="flex gap-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setView(tab.id)}
            className={`rounded px-3 py-1 text-xs ${
              view === tab.id
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <WorkspaceSwitcher />
      <div className="ml-auto flex items-center gap-2">
        <ThemeToggle />
      </div>
    </nav>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- --run AppBar`
Expected: PASS (all three AppBar tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/layout/AppBar.tsx frontend/src/components/layout/AppBar.test.tsx
git commit -m "feat(frontend): Workspace/Tutorial tabs in the persistent AppBar

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Rewrite `TutorialView` to use the real panes

**Files:**
- Modify: `frontend/src/views/TutorialView.tsx`
- Modify: `frontend/src/views/TutorialView.test.tsx`

- [ ] **Step 1: Replace the test with the new structure**

Replace the entire contents of `frontend/src/views/TutorialView.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { TutorialStep } from "../types";
import { TutorialView } from "./TutorialView";

const STEPS: TutorialStep[] = [
  {
    title: "Welcome to Drummer",
    instructions: "Welcome to the tutorial.",
    method: null,
    url: "",
    params: {},
    headers: {},
    body: "",
    pre_script: "",
    post_script: "",
    variable_overrides: {},
  },
  {
    title: "Your first GET request",
    instructions: "The simplest request is a GET.",
    method: "GET",
    url: "http://localhost:8000/mock/met/departments",
    params: {},
    headers: {},
    body: "",
    pre_script: "",
    post_script: "",
    variable_overrides: {},
  },
];

vi.mock("../api/tutorial", async (importActual) => {
  const actual = await importActual<typeof import("../api/tutorial")>();
  return {
    ...actual,
    useTutorialSteps: () => ({ data: STEPS }),
    useTutorialSend: () => ({ send: vi.fn(), cancel: vi.fn() }),
  };
});

function renderTutorial() {
  const qc = new QueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <TutorialView />
    </QueryClientProvider>,
  );
}

describe("TutorialView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("lists step titles in the coach rail", () => {
    renderTutorial();
    expect(screen.getByText("Welcome to Drummer")).toBeInTheDocument();
    expect(screen.getByText("Your first GET request")).toBeInTheDocument();
  });

  it("has no theme toggle (it lives in the AppBar now)", () => {
    renderTutorial();
    expect(screen.queryByLabelText(/theme/i)).not.toBeInTheDocument();
  });

  it("shows a placeholder on a no-request step", () => {
    renderTutorial();
    expect(screen.getByText(/no request/i)).toBeInTheDocument();
  });

  it("mounts the real request workbench on a request step", async () => {
    renderTutorial();
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: /Your first GET request/ }));
    // Real request/response tab bars from RequestResponseWorkbench:
    expect(screen.getByRole("button", { name: "Params" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Script Output" })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- --run TutorialView`
Expected: FAIL — the current `TutorialView` still renders its own theme toggle and bespoke card, and imports no `useTutorialSteps`.

- [ ] **Step 3: Rewrite `TutorialView.tsx`**

Replace the entire contents of `frontend/src/views/TutorialView.tsx`:

```tsx
import { useEffect, useRef, useState } from "react";
import { RequestResponseWorkbench } from "../components/layout/RequestResponseWorkbench";
import {
  stepToRequestDetail,
  useTutorialSend,
  useTutorialSteps,
} from "../api/tutorial";
import { useRequestStore } from "../store/requestStore";
import { useResponseStore } from "../store/responseStore";
import { useSessionStore } from "../store/sessionStore";

export function TutorialView() {
  const { data: steps = [] } = useTutorialSteps();
  const { send, cancel } = useTutorialSend();
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());

  // Snapshot the shared stores on mount; restore on unmount so the tutorial
  // never disturbs the workspace's in-progress request/response/session.
  const snapshotRef = useRef<{
    request: ReturnType<typeof useRequestStore.getState>;
    response: ReturnType<typeof useResponseStore.getState>;
    session: ReturnType<typeof useSessionStore.getState>;
  } | null>(null);
  useEffect(() => {
    snapshotRef.current = {
      request: { ...useRequestStore.getState() },
      response: { ...useResponseStore.getState() },
      session: { ...useSessionStore.getState() },
    };
    return () => {
      const snap = snapshotRef.current;
      if (!snap) return;
      useRequestStore.setState(snap.request);
      useResponseStore.setState(snap.response);
      useSessionStore.setState(snap.session);
    };
  }, []);

  const step = steps[currentStep];

  // Seed the shared stores from the current step.
  useEffect(() => {
    if (!step) return;
    if (step.method) {
      useRequestStore.getState().load(stepToRequestDetail(step));
    }
    useResponseStore.getState().reset();
    useSessionStore.getState().setVariables(step.variable_overrides ?? {});
  }, [step]);

  if (!step) return null;

  const goToStep = (i: number) => setCurrentStep(i);
  const handleNext = () => {
    setCompletedSteps((prev) => new Set(prev).add(currentStep));
    setCurrentStep((prev) => Math.min(prev + 1, steps.length - 1));
  };
  const handleBack = () => setCurrentStep((prev) => Math.max(prev - 1, 0));

  return (
    <div className="flex h-full overflow-hidden">
      {/* Coach rail */}
      <div className="flex w-72 shrink-0 flex-col border-r bg-card p-4">
        <div className="mb-4">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Progress
          </div>
          <div className="flex flex-col gap-1">
            {steps.map((s, i) => (
              <button
                key={s.title}
                type="button"
                onClick={() => goToStep(i)}
                className={`flex items-center gap-2 rounded px-2 py-1.5 text-left text-xs ${
                  i === currentStep
                    ? "border border-primary bg-primary/10 text-primary"
                    : completedSteps.has(i)
                      ? "bg-green-500/10 text-green-700 dark:text-green-400"
                      : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <span className="w-4 shrink-0 text-center">
                  {completedSteps.has(i)
                    ? "✓"
                    : i === currentStep
                      ? "▶"
                      : "○"}
                </span>
                {s.title}
              </button>
            ))}
          </div>
        </div>

        <div className="mb-4 min-h-0 flex-1 overflow-y-auto">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Instructions
          </div>
          <div className="whitespace-pre-wrap text-xs leading-relaxed text-foreground">
            {step.instructions}
          </div>
        </div>

        <div className="flex gap-2 border-t pt-3">
          <button
            type="button"
            onClick={handleBack}
            disabled={currentStep === 0}
            className="rounded bg-muted px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground disabled:opacity-30"
          >
            ← Back
          </button>
          <button
            type="button"
            onClick={handleNext}
            disabled={currentStep === steps.length - 1}
            className="flex-1 rounded bg-primary px-3 py-1.5 text-xs text-primary-foreground hover:bg-primary/90 disabled:opacity-30"
          >
            Next →
          </button>
        </div>
      </div>

      {/* Real request/response panes */}
      <div className="min-h-0 flex-1">
        {step.method ? (
          <RequestResponseWorkbench
            onSend={() => void send(currentStep)}
            onCancel={cancel}
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-muted-foreground">
              This step has no request — read the instructions and click Next.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- --run TutorialView`
Expected: PASS (all four TutorialView tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/TutorialView.tsx frontend/src/views/TutorialView.test.tsx
git commit -m "feat(frontend): tutorial drives the real request/response panes

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Unify the shell in `App.tsx`

**Files:**
- Modify: `frontend/src/App.tsx`

No `App` unit test exists; guarded by `npm run check` + full vitest.

- [ ] **Step 1: Update `App.tsx`**

Replace the render logic so the `AppBar` is always present and the body is conditional. Replace lines 37–54 (the `if (view === "tutorial") return <TutorialView />;` through the final `return`):

```tsx
  return (
    <div className="flex h-screen flex-col">
      <AppBar />
      <div className="min-h-0 flex-1">
        {view === "tutorial" ? (
          <TutorialView />
        ) : isLoading ? (
          <div className="flex h-full items-center justify-center bg-background text-sm text-muted-foreground">
            Loading…
          </div>
        ) : (
          <WorkspaceView />
        )}
      </div>
    </div>
  );
```

The `settingsLoading` early-return guard above it is unchanged.

- [ ] **Step 2: Verify the full frontend gate**

Run: `cd frontend && npm run check && npm run test -- --run`
Expected: tsc/biome clean; entire vitest suite passes.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "refactor(frontend): persistent AppBar across workspace and tutorial views

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Docs — ROADMAP + CLAUDE.md

**Files:**
- Modify: `ROADMAP.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update `ROADMAP.md`**

Set Phase 12 to Done and reword + complete Phase 13:

```markdown
| 12 — Theming | Dark / light / system-auto toggle across the app and tutorial | ✅ Done |
| 13 — Tutorial cohesion | Tutorial drives the real request/response panes; unified Workspace/Tutorial tabs in the AppBar | ✅ Done |
```

- [ ] **Step 2: Update `CLAUDE.md`**

Change the current-phase line near the bottom:

```markdown
Current phase: **13 — Tutorial cohesion**
```

- [ ] **Step 3: Commit**

```bash
git add ROADMAP.md CLAUDE.md
git commit -m "docs: mark Phase 13 tutorial cohesion done

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: Final gate + milestone push

- [ ] **Step 1: Run the full check**

Run: `make check`
Expected: ruff + pyright + biome + tsc + pytest (286+ backend) all pass.

- [ ] **Step 2: Run the full frontend test suite**

Run: `cd frontend && npm run test -- --run`
Expected: all vitest suites pass (including new AppBar + rewritten TutorialView tests).

- [ ] **Step 3: Manual smoke check (optional but recommended)**

Run the app, click the **Tutorial** tab in the AppBar, step through: the real URL bar/tabs render each step, **Send** streams a response into the real response pane, the theme toggle is only in the AppBar, and switching back to **Workspace** restores any in-progress request.

- [ ] **Step 4: Push to main**

```bash
git push origin main
```

---

## Self-Review

**Spec coverage:**
- Persistent AppBar + Workspace/Tutorial tabs → Tasks 4, 6. ✔
- Tutorial drives real request/response panes → Tasks 3, 5. ✔
- Remove duplicate ThemeToggle from TutorialView → Task 5 (and test asserts its absence). ✔
- Single source of truth `GET /api/tutorial/steps` + delete frontend STEPS → Tasks 1, 2, 5. ✔
- Reuse `/api/tutorial/steps/{i}/send` rendered via responseStore → Task 2 (`useTutorialSend`). ✔
- Snapshot/restore store isolation → Task 5. ✔
- Seed request/response/session per step incl. variable_overrides → Task 5. ✔
- No-request step placeholder → Task 5. ✔
- App.tsx gating (tutorial doesn't block on project load) → Task 6. ✔
- Tests (backend endpoint, AppBar, TutorialView) + green gate → Tasks 1, 4, 5, 8. ✔
- Docs reword (drop "project pane steps") + current phase → Task 7. ✔

**Placeholder scan:** No TBD/TODO; every code step shows complete code.

**Type consistency:** `TutorialStep` (Task 2) matches the backend `TutorialStep` fields (Task 1) and the test fixtures (Tasks 1, 5). `consumeSSE(res, response, onDone?)` signature is consistent between definition (Task 2) and both call sites (`useSend` Task 2, `useTutorialSend` Task 2). `stepToRequestDetail` returns a full `RequestDetail`/`RequestFrontmatter` matching `types.ts`. `RequestResponseWorkbench` props (`onSend`, `onCancel`) are consistent between definition (Task 3) and call sites (Tasks 3, 5).
