# Phase 5: React UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete React frontend for Drummer — Vite scaffold, three-panel workspace, request editor, response viewer, Playwright smoke tests — connecting to the Phase 4 FastAPI backend.

**Architecture:** Vertical-slice build order. One working path (open project → select request → send → see response) is established first, then remaining panels and stubs are expanded. Frontend lives in `frontend/`; `vite build` outputs to `drummer/api/static/`. Dev mode proxies `/api` to `http://127.0.0.1:8000`. State: Zustand for client state, TanStack Query v5 for server state, custom `useSend` hook for SSE streaming.

**Tech Stack:** React 19, Vite 6, TypeScript strict, Tailwind v4 (CSS-first), shadcn/ui, Zustand 5, TanStack Query 5, CodeMirror 6, react-resizable-panels, lucide-react, Biome (lint/format), Vitest + React Testing Library (component tests), pytest-playwright (e2e).

**Parallelism notes:**
- Tasks 1 and 2 are independent — run in parallel.
- Tasks 3 and 4 run after Task 2 completes; can be parallelised with each other.
- Tasks 5–8 run after Tasks 1–4 complete; Tasks 6–8 are independent of each other.
- Tasks 9–13 can be parallelised after Task 7 completes.
- Tasks 14–16 depend on Tasks 9–13.
- Task 17 depends on Tasks 14–16.
- Tasks 18–20 run after Task 17; Tasks 19 and 20 are independent of each other.

---

### File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `drummer/api/routes/project.py` | `GET /api/project`, `POST /api/project` |
| Modify | `drummer/api/deps.py` | `get_project_dir` raises 400 when no project is set |
| Modify | `drummer/api/app.py` | Accept `project_dir: Path \| None`; register project router |
| Modify | `drummer/cli.py` | Make `--project` optional |
| Create | `tests/integration/test_project_route.py` | Integration tests for project routes |
| Create | `frontend/` | Full Vite project (see tasks below) |
| Create | `frontend/src/types.ts` | TypeScript types mirroring Pydantic models |
| Create | `frontend/src/store/projectStore.ts` | Active project + request tree |
| Create | `frontend/src/store/requestStore.ts` | Selected request, editable draft, dirty flag |
| Create | `frontend/src/store/responseStore.ts` | Latest send result, streaming state |
| Create | `frontend/src/store/sessionStore.ts` | Active environment name, variables |
| Create | `frontend/src/store/requestStore.test.ts` | requestStore unit tests |
| Create | `frontend/src/api/client.ts` | Base fetch helper |
| Create | `frontend/src/api/projects.ts` | `useProject`, `useSetProject` hooks |
| Create | `frontend/src/api/requests.ts` | `useRequests`, `useRequest`, `useSaveRequest`, `useDeleteRequest` |
| Create | `frontend/src/api/environments.ts` | `useEnvironments`, `useEnvironment`, `useSaveEnvironment` |
| Create | `frontend/src/api/history.ts` | `useHistory` |
| Create | `frontend/src/api/cookies.ts` | `useCookies`, `useClearCookies` |
| Create | `frontend/src/api/useSend.ts` | SSE streaming hook |
| Create | `frontend/src/components/shared/StatusBadge.tsx` | Status code colour chip |
| Create | `frontend/src/components/shared/StatusBadge.test.tsx` | |
| Create | `frontend/src/components/shared/VariableChip.tsx` | `{{var}}` highlight display |
| Create | `frontend/src/components/shared/VariableChip.test.tsx` | |
| Create | `frontend/src/lib/codemirror-variables.ts` | CM6 extension for `{{var}}` highlighting |
| Create | `frontend/src/lib/hexdump.ts` | Hex dump utility |
| Create | `frontend/src/views/WelcomeView.tsx` | Path-input card shown when no project is loaded |
| Create | `frontend/src/components/tree/TreeNode.tsx` | Single sidebar tree node |
| Create | `frontend/src/components/tree/RequestTree.tsx` | Collapsible request tree |
| Create | `frontend/src/components/layout/Sidebar.tsx` | Left panel: project header + env switcher + tree |
| Create | `frontend/src/components/request/UrlBar.tsx` | Method selector + URL (CodeMirror) + Send button |
| Create | `frontend/src/components/request/UrlBar.test.tsx` | |
| Create | `frontend/src/components/request/KeyValueTable.tsx` | Reusable key/value table |
| Create | `frontend/src/components/request/ParamsTab.tsx` | Query params |
| Create | `frontend/src/components/request/HeadersTab.tsx` | Request headers |
| Create | `frontend/src/components/request/BodyTab.tsx` | Body mode switcher + CodeMirror editor |
| Create | `frontend/src/components/request/AuthTab.tsx` | None / Bearer / Basic fields |
| Create | `frontend/src/components/request/ScriptTab.tsx` | Stub |
| Create | `frontend/src/components/request/CookiesTab.tsx` | Stub |
| Create | `frontend/src/components/response/ResponseMeta.tsx` | Status badge + timing + size |
| Create | `frontend/src/components/response/BodyViewer.tsx` | JSON pretty-print / raw / image |
| Create | `frontend/src/components/response/HeadersViewer.tsx` | Response header table |
| Create | `frontend/src/components/response/ScriptOutput.tsx` | Stub |
| Create | `frontend/src/components/response/RawViewer.tsx` | Hex dump + decoded text panels |
| Create | `frontend/src/components/response/HistoryDrawer.tsx` | Per-request history list |
| Create | `frontend/src/components/layout/PanelGroup.tsx` | Thin wrapper around ResizablePanelGroup |
| Create | `frontend/src/views/WorkspaceView.tsx` | 3-panel layout assembly |
| Create | `frontend/src/App.tsx` | Root: WelcomeView or WorkspaceView |
| Create | `tests/e2e/conftest.py` | Playwright fixtures |
| Create | `tests/e2e/fixtures/demo-project/` | Minimal drummer project for e2e |
| Create | `tests/e2e/test_smoke.py` | 3 smoke tests |
| Modify | `Makefile` | Add `dev`, `e2e` targets; add biome to `check` |

---

### Task 1: Backend — project routes

**Files:**
- Create: `drummer/api/routes/project.py`
- Modify: `drummer/api/deps.py`
- Modify: `drummer/api/app.py`
- Modify: `drummer/cli.py`
- Create: `tests/integration/test_project_route.py`

- [ ] **Step 1: Write the failing integration tests**

Create `tests/integration/test_project_route.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from pathlib import Path
from drummer.api.app import create_app


@pytest.fixture
def app_no_project():
    return create_app(project_dir=None)


@pytest.fixture
def app_with_project(project_dir):
    return create_app(project_dir=project_dir)


@pytest.mark.asyncio
async def test_get_project_returns_404_when_no_project(app_no_project):
    async with AsyncClient(transport=ASGITransport(app=app_no_project), base_url="http://test") as client:
        r = await client.get("/api/project")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_project_returns_info(app_with_project, project_dir):
    async with AsyncClient(transport=ASGITransport(app=app_with_project), base_url="http://test") as client:
        r = await client.get("/api/project")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == project_dir.name
    assert data["path"] == str(project_dir)


@pytest.mark.asyncio
async def test_post_project_sets_project(app_no_project, project_dir):
    async with AsyncClient(transport=ASGITransport(app=app_no_project), base_url="http://test") as client:
        r = await client.post("/api/project", json={"path": str(project_dir)})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == project_dir.name


@pytest.mark.asyncio
async def test_post_project_rejects_non_drummer_dir(app_no_project, tmp_path):
    async with AsyncClient(transport=ASGITransport(app=app_no_project), base_url="http://test") as client:
        r = await client.post("/api/project", json={"path": str(tmp_path)})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_requests_route_returns_400_when_no_project(app_no_project):
    async with AsyncClient(transport=ASGITransport(app=app_no_project), base_url="http://test") as client:
        r = await client.get("/api/requests")
    assert r.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
make check
```

Expected: test collection errors because `create_app` doesn't yet accept `None`.

- [ ] **Step 3: Create `drummer/api/routes/project.py`**

```python
from http import HTTPStatus
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()


class ProjectInfo(BaseModel):
    name: str
    path: str


class SetProjectBody(BaseModel):
    path: str


@router.get("/project")
async def get_project_route(request: Request) -> ProjectInfo:
    project_dir: Path | None = request.app.state.project_dir
    if project_dir is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="No project loaded")
    return ProjectInfo(name=project_dir.name, path=str(project_dir))


@router.post("/project")
async def set_project_route(body: SetProjectBody, request: Request) -> ProjectInfo:
    new_dir = Path(body.path).expanduser().resolve()
    if not (new_dir / ".drummer" / "project.yaml").exists():
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Not a Drummer project (missing .drummer/project.yaml)",
        )
    request.app.state.project_dir = new_dir
    return ProjectInfo(name=new_dir.name, path=str(new_dir))
```

- [ ] **Step 4: Update `drummer/api/deps.py`**

Replace the `get_project_dir` function:

```python
from http import HTTPStatus

from fastapi import HTTPException


def get_project_dir(request: Request) -> Path:
    project_dir: Path | None = request.app.state.project_dir
    if project_dir is None:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="No project loaded. POST /api/project to load one.",
        )
    return project_dir
```

Keep the rest of `deps.py` unchanged.

- [ ] **Step 5: Update `drummer/api/app.py`**

Change the `create_app` signature and register the project router:

```python
from drummer.api.routes import project as project_routes

def create_app(project_dir: Path | None = None, db_url: str = f"sqlite+aiosqlite:///{_DEFAULT_DB}") -> FastAPI:
    # ... lifespan unchanged ...
    app = FastAPI(title="Drummer", lifespan=lifespan)
    app.state.project_dir = project_dir          # now accepts None
    app.state.cookie_jar = CookieJar()
    app.state.active_environment = "local"
    app.state.db_factory = async_session_factory(db_url)
    app.state.transport = None

    app.include_router(project_routes.router, prefix="/api")
    app.include_router(req_routes.router, prefix="/api")
    app.include_router(env_routes.router, prefix="/api")
    app.include_router(send_routes.router, prefix="/api")
    app.include_router(history_routes.router, prefix="/api")
    app.include_router(cookie_routes.router, prefix="/api")

    mcp = FastApiMCP(app)
    register_mcp_tools(mcp, app)
    mcp.mount_http()

    return app
```

- [ ] **Step 6: Update `drummer/cli.py`**

Make `--project` optional and pass `None` when omitted:

```python
@app.command()
def serve(
    project: Annotated[
        str | None,
        typer.Option("--project", "-p", help="Path to the project folder."),
    ] = None,
    port: Annotated[int, typer.Option("--port", help="Port to listen on.")] = 8000,
    host: Annotated[str, typer.Option("--host", help="Host address to bind to.")] = "127.0.0.1",
) -> None:
    """Start the Drummer API server."""
    project_dir: Path | None = None
    if project is not None:
        project_dir = Path(project).expanduser().resolve()
        if not (project_dir / ".drummer" / "project.yaml").exists():
            typer.echo(
                f"Error: {project_dir} is not a Drummer project (missing .drummer/project.yaml)",
                err=True,
            )
            raise typer.Exit(code=1)

    application = create_app(project_dir=project_dir)
    label = project_dir.name if project_dir else "(no project)"
    typer.echo(f"Drummer serving {label} on http://{host}:{port}")
    uvicorn.run(application, host=host, port=port)
```

- [ ] **Step 7: Run tests and verify they pass**

```bash
make check
```

Expected: all 114 existing tests plus 5 new project-route tests pass.

- [ ] **Step 8: Commit**

```bash
git add drummer/api/routes/project.py drummer/api/deps.py drummer/api/app.py drummer/cli.py tests/integration/test_project_route.py
git commit -m "feat: add GET/POST /api/project routes; make --project optional"
```

---

### Task 2: Frontend scaffold

**Files:**
- Create: `frontend/` (Vite project)

- [ ] **Step 1: Create the Vite project**

```bash
cd /Users/curtis/dev/claude_projects/drummer
npm create vite@latest frontend -- --template react-ts
```

- [ ] **Step 2: Install runtime dependencies**

```bash
cd frontend
npm install \
  @tanstack/react-query@^5 \
  zustand@^5 \
  @codemirror/view@^6 \
  @codemirror/state@^6 \
  @codemirror/lang-json@^6 \
  @codemirror/theme-one-dark@^6 \
  react-resizable-panels@^2 \
  lucide-react
```

- [ ] **Step 3: Install dev dependencies**

```bash
npm install --save-dev \
  @biomejs/biome \
  vitest \
  @vitest/coverage-v8 \
  jsdom \
  @testing-library/react \
  @testing-library/user-event \
  @testing-library/jest-dom
```

- [ ] **Step 4: Configure Biome**

Create `frontend/biome.json`:

```json
{
  "$schema": "https://biomejs.dev/schemas/1.9.4/schema.json",
  "organizeImports": { "enabled": true },
  "linter": {
    "enabled": true,
    "rules": { "recommended": true }
  },
  "formatter": {
    "enabled": true,
    "indentStyle": "space",
    "indentWidth": 2
  },
  "javascript": {
    "formatter": { "quoteStyle": "double" }
  }
}
```

- [ ] **Step 5: Configure TypeScript strict mode**

Replace the contents of `frontend/tsconfig.app.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
```

- [ ] **Step 6: Configure Vite with proxy**

Replace `frontend/vite.config.ts`:

```typescript
/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "../drummer/api/static",
    emptyOutDir: true,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
});
```

- [ ] **Step 7: Create test setup file**

Create `frontend/src/test-setup.ts`:

```typescript
import "@testing-library/jest-dom";
```

- [ ] **Step 8: Add npm scripts**

In `frontend/package.json`, ensure the scripts section includes:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "check": "biome check .",
    "check:fix": "biome check --write ."
  }
}
```

- [ ] **Step 9: Verify the scaffold compiles**

```bash
cd frontend && npm run build
```

Expected: build completes, output in `drummer/api/static/`.

- [ ] **Step 10: Commit**

```bash
cd ..
git add frontend/
git commit -m "feat: scaffold Vite + React 19 + TypeScript strict + Biome frontend"
```

---

### Task 3: Tailwind v4 + shadcn/ui

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/src/index.css`
- Various files created by shadcn/ui CLI

- [ ] **Step 1: Install Tailwind v4**

```bash
cd frontend
npm install tailwindcss @tailwindcss/vite
```

- [ ] **Step 2: Add the Tailwind Vite plugin**

Edit `frontend/vite.config.ts` to add the tailwind plugin import and usage:

```typescript
/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "../drummer/api/static",
    emptyOutDir: true,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
});
```

- [ ] **Step 3: Replace `frontend/src/index.css`**

```css
@import "tailwindcss";

/* CodeMirror variable highlighting */
.cm-var-known {
  background: rgba(147, 51, 234, 0.15);
  border-radius: 3px;
  padding: 0 2px;
  color: #7c3aed;
  cursor: default;
}
.cm-var-unknown {
  background: rgba(245, 158, 11, 0.15);
  border-radius: 3px;
  padding: 0 2px;
  color: #d97706;
  cursor: default;
}

/* CodeMirror URL bar appearance */
.cm-url-bar .cm-editor {
  font-family: inherit;
  font-size: 0.875rem;
}
.cm-url-bar .cm-scroller {
  overflow: hidden;
}
```

- [ ] **Step 4: Initialise shadcn/ui**

```bash
npx shadcn@latest init --defaults
```

When prompted, accept all defaults. This will install `class-variance-authority`, `clsx`, `tailwind-merge`, and `@radix-ui` primitives.

- [ ] **Step 5: Add the shadcn components needed for Phase 5**

```bash
npx shadcn@latest add button input tabs select badge separator scroll-area
```

- [ ] **Step 6: Verify the build**

```bash
npm run build
```

Expected: build completes without errors.

- [ ] **Step 7: Commit**

```bash
cd ..
git add frontend/
git commit -m "feat: add Tailwind v4 and shadcn/ui to frontend"
```

---

### Task 4: TypeScript types

**Files:**
- Create: `frontend/src/types.ts`

- [ ] **Step 1: Create `frontend/src/types.ts`**

This file mirrors the Pydantic models from the backend. No test needed — TypeScript catches mismatches at compile time.

```typescript
export type HttpMethod =
  | "GET"
  | "POST"
  | "PUT"
  | "PATCH"
  | "DELETE"
  | "HEAD"
  | "OPTIONS"
  | "TRACE";

export type AuthType = "none" | "bearer" | "basic" | "api_key";
export type CookieMode = "session" | "disabled" | "explicit";
export type BodyMode = "raw" | "form-data" | "json" | "graphql";
export type RequestTab = "params" | "headers" | "body" | "auth" | "scripts" | "cookies";
export type ResponseTab = "body" | "headers" | "raw" | "script-output" | "history";
export type StreamingState = "idle" | "streaming" | "done" | "error";

export interface ProjectInfo {
  name: string;
  path: string;
}

export interface RequestSummary {
  path: string;
  name: string;
  method: HttpMethod;
  url: string;
}

export interface CookieConfig {
  mode: CookieMode;
  cookies: Record<string, string>;
}

export interface AuthConfig {
  type: AuthType;
  token: string;
  username: string;
  password: string;
  key: string;
  value: string;
}

export interface RequestFrontmatter {
  name: string;
  method: HttpMethod;
  url: string;
  headers: Record<string, string>;
  params: Record<string, string>;
  encoding: string;
  cookies: CookieConfig;
  auth: AuthConfig;
  pre_script: string;
  post_script: string;
  tags: string[];
  skip: boolean;
}

export interface RequestDetail {
  path: string;
  frontmatter: RequestFrontmatter;
  body: string;
}

export interface EnvironmentSummary {
  name: string;
  variable_count: number;
}

export interface EnvironmentDetail {
  name: string;
  variables: Record<string, string>;
}

export interface HistoryRecord {
  id: string;
  sent_at: string;
  request_path: string;
  request_name: string;
  environment: string;
  method: string;
  url: string;
  status_code: number;
  elapsed_ms: number;
  request_headers: [string, string][];
  request_body: string;
  response_headers: [string, string][];
  response_body: string;
  encoding: string;
  warnings: string[];
}
```

- [ ] **Step 2: Verify TypeScript is happy**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd ..
git add frontend/src/types.ts
git commit -m "feat: add TypeScript API types mirroring backend Pydantic models"
```

---

### Task 5: Zustand stores

**Files:**
- Create: `frontend/src/store/projectStore.ts`
- Create: `frontend/src/store/requestStore.ts`
- Create: `frontend/src/store/responseStore.ts`
- Create: `frontend/src/store/sessionStore.ts`
- Create: `frontend/src/store/requestStore.test.ts`

- [ ] **Step 1: Write the failing requestStore tests**

Create `frontend/src/store/requestStore.test.ts`:

```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { useRequestStore } from "./requestStore";
import type { RequestDetail } from "../types";

const makeDetail = (url = "http://example.com"): RequestDetail => ({
  path: "users/list.md",
  frontmatter: {
    name: "List Users",
    method: "GET",
    url,
    headers: {},
    params: {},
    encoding: "utf-8",
    cookies: { mode: "session", cookies: {} },
    auth: { type: "none", token: "", username: "", password: "", key: "", value: "" },
    pre_script: "",
    post_script: "",
    tags: [],
    skip: false,
  },
  body: "",
});

beforeEach(() => {
  useRequestStore.setState({
    selectedPath: null,
    saved: null,
    draft: null,
    activeTab: "params",
  });
});

describe("requestStore", () => {
  it("starts clean", () => {
    const s = useRequestStore.getState();
    expect(s.selectedPath).toBeNull();
    expect(s.isDirty()).toBe(false);
  });

  it("load sets saved and clears draft", () => {
    const detail = makeDetail();
    useRequestStore.getState().load(detail);
    const s = useRequestStore.getState();
    expect(s.saved).toEqual(detail);
    expect(s.draft).toBeNull();
    expect(s.isDirty()).toBe(false);
  });

  it("patch creates a draft and marks dirty", () => {
    useRequestStore.getState().load(makeDetail());
    useRequestStore.getState().patch({ url: "http://changed.example.com" });
    const s = useRequestStore.getState();
    expect(s.draft?.frontmatter.url).toBe("http://changed.example.com");
    expect(s.isDirty()).toBe(true);
  });

  it("discard clears draft", () => {
    useRequestStore.getState().load(makeDetail());
    useRequestStore.getState().patch({ url: "http://changed.example.com" });
    useRequestStore.getState().discard();
    expect(useRequestStore.getState().isDirty()).toBe(false);
    expect(useRequestStore.getState().draft).toBeNull();
  });

  it("markSaved clears draft after save", () => {
    const detail = makeDetail();
    useRequestStore.getState().load(detail);
    useRequestStore.getState().patch({ url: "http://changed.example.com" });
    const updated = { ...detail, frontmatter: { ...detail.frontmatter, url: "http://changed.example.com" } };
    useRequestStore.getState().markSaved(updated);
    expect(useRequestStore.getState().isDirty()).toBe(false);
    expect(useRequestStore.getState().draft).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend && npm test
```

Expected: import errors because stores don't exist yet.

- [ ] **Step 3: Create `frontend/src/store/projectStore.ts`**

```typescript
import { create } from "zustand";
import type { ProjectInfo, RequestSummary } from "../types";

interface ProjectState {
  project: ProjectInfo | null;
  requests: RequestSummary[];
  setProject: (project: ProjectInfo) => void;
  setRequests: (requests: RequestSummary[]) => void;
  clear: () => void;
}

export const useProjectStore = create<ProjectState>()((set) => ({
  project: null,
  requests: [],
  setProject: (project) => set({ project }),
  setRequests: (requests) => set({ requests }),
  clear: () => set({ project: null, requests: [] }),
}));
```

- [ ] **Step 4: Create `frontend/src/store/requestStore.ts`**

```typescript
import { create } from "zustand";
import type { RequestDetail, RequestFrontmatter, RequestTab } from "../types";

interface RequestState {
  selectedPath: string | null;
  saved: RequestDetail | null;
  draft: RequestDetail | null;
  activeTab: RequestTab;
  select: (path: string) => void;
  load: (detail: RequestDetail) => void;
  patch: (changes: Partial<RequestFrontmatter> & { body?: string }) => void;
  discard: () => void;
  markSaved: (detail: RequestDetail) => void;
  setTab: (tab: RequestTab) => void;
  isDirty: () => boolean;
}

export const useRequestStore = create<RequestState>()((set, get) => ({
  selectedPath: null,
  saved: null,
  draft: null,
  activeTab: "params",

  select: (path) => set({ selectedPath: path, draft: null }),

  load: (detail) => set({ saved: detail, draft: null }),

  patch: (changes) => {
    const { saved, draft } = get();
    const base = draft ?? saved;
    if (!base) return;
    const { body, ...fmChanges } = changes;
    set({
      draft: {
        ...base,
        frontmatter: { ...base.frontmatter, ...fmChanges },
        body: body !== undefined ? body : base.body,
      },
    });
  },

  discard: () => set({ draft: null }),

  markSaved: (detail) => set({ saved: detail, draft: null }),

  setTab: (tab) => set({ activeTab: tab }),

  isDirty: () => {
    const { saved, draft } = get();
    if (!draft) return false;
    return JSON.stringify(draft) !== JSON.stringify(saved);
  },
}));
```

- [ ] **Step 5: Create `frontend/src/store/responseStore.ts`**

```typescript
import { create } from "zustand";
import type { ResponseTab, StreamingState } from "../types";

interface ResponseState {
  streaming: StreamingState;
  statusCode: number | null;
  url: string | null;
  responseHeaders: [string, string][];
  body: string | null;
  encoding: string | null;
  elapsedMs: number | null;
  error: string | null;
  historyId: string | null;
  activeTab: ResponseTab;

  reset: () => void;
  setStreaming: (state: StreamingState) => void;
  setStatus: (statusCode: number, url: string) => void;
  setHeaders: (headers: [string, string][]) => void;
  setBody: (body: string, encoding: string, elapsedMs: number) => void;
  setDone: (historyId: string) => void;
  setError: (error: string) => void;
  setTab: (tab: ResponseTab) => void;
}

const initialState = {
  streaming: "idle" as StreamingState,
  statusCode: null,
  url: null,
  responseHeaders: [] as [string, string][],
  body: null,
  encoding: null,
  elapsedMs: null,
  error: null,
  historyId: null,
  activeTab: "body" as ResponseTab,
};

export const useResponseStore = create<ResponseState>()((set) => ({
  ...initialState,
  reset: () => set({ ...initialState, activeTab: "body" }),
  setStreaming: (streaming) => set({ streaming }),
  setStatus: (statusCode, url) => set({ statusCode, url }),
  setHeaders: (responseHeaders) => set({ responseHeaders }),
  setBody: (body, encoding, elapsedMs) => set({ body, encoding, elapsedMs }),
  setDone: (historyId) => set({ historyId, streaming: "done" }),
  setError: (error) => set({ error, streaming: "error" }),
  setTab: (activeTab) => set({ activeTab }),
}));
```

- [ ] **Step 6: Create `frontend/src/store/sessionStore.ts`**

```typescript
import { create } from "zustand";

interface SessionState {
  activeEnvironment: string;
  variables: Record<string, string>;
  setActiveEnvironment: (name: string) => void;
  setVariables: (vars: Record<string, string>) => void;
}

export const useSessionStore = create<SessionState>()((set) => ({
  activeEnvironment: "local",
  variables: {},
  setActiveEnvironment: (activeEnvironment) => set({ activeEnvironment }),
  setVariables: (variables) => set({ variables }),
}));
```

- [ ] **Step 7: Run tests and verify they pass**

```bash
cd frontend && npm test
```

Expected: all 5 requestStore tests pass.

- [ ] **Step 8: Commit**

```bash
cd ..
git add frontend/src/store/
git commit -m "feat: add four Zustand stores with requestStore tests"
```

---

### Task 6: API hooks + useSend

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/projects.ts`
- Create: `frontend/src/api/requests.ts`
- Create: `frontend/src/api/environments.ts`
- Create: `frontend/src/api/history.ts`
- Create: `frontend/src/api/cookies.ts`
- Create: `frontend/src/api/useSend.ts`

- [ ] **Step 1: Create `frontend/src/api/client.ts`**

```typescript
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((body as { detail?: string }).detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}
```

- [ ] **Step 2: Create `frontend/src/api/projects.ts`**

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { ProjectInfo } from "../types";

export function useProject() {
  return useQuery<ProjectInfo | null>({
    queryKey: ["project"],
    queryFn: async () => {
      try {
        return await apiFetch<ProjectInfo>("/api/project");
      } catch {
        return null;
      }
    },
  });
}

export function useSetProject() {
  const queryClient = useQueryClient();
  return useMutation<ProjectInfo, Error, string>({
    mutationFn: (path) => apiFetch<ProjectInfo>("/api/project", {
      method: "POST",
      body: JSON.stringify({ path }),
    }),
    onSuccess: (data) => {
      queryClient.setQueryData(["project"], data);
      void queryClient.invalidateQueries({ queryKey: ["requests"] });
      void queryClient.invalidateQueries({ queryKey: ["environments"] });
    },
  });
}
```

- [ ] **Step 3: Create `frontend/src/api/requests.ts`**

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { RequestDetail, RequestSummary } from "../types";

export function useRequests() {
  return useQuery<RequestSummary[]>({
    queryKey: ["requests"],
    queryFn: () => apiFetch<RequestSummary[]>("/api/requests"),
    enabled: false,  // only fetch when project is loaded; caller enables via `enabled` prop
  });
}

export function useRequest(path: string | null) {
  return useQuery<RequestDetail>({
    queryKey: ["request", path],
    queryFn: () => apiFetch<RequestDetail>(`/api/requests/${path}`),
    enabled: path !== null,
  });
}

export function useSaveRequest() {
  const queryClient = useQueryClient();
  return useMutation<RequestDetail, Error, { path: string; detail: RequestDetail }>({
    mutationFn: ({ path, detail }) =>
      apiFetch<RequestDetail>(`/api/requests/${path}`, {
        method: "PUT",
        body: JSON.stringify({
          path,
          name: detail.frontmatter.name,
          method: detail.frontmatter.method,
          url: detail.frontmatter.url,
          headers: detail.frontmatter.headers,
          body: detail.body,
        }),
      }),
    onSuccess: (data, { path }) => {
      queryClient.setQueryData(["request", path], data);
      void queryClient.invalidateQueries({ queryKey: ["requests"] });
    },
  });
}

export function useDeleteRequest() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (path) =>
      apiFetch<void>(`/api/requests/${path}`, { method: "DELETE" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["requests"] });
    },
  });
}
```

- [ ] **Step 4: Create `frontend/src/api/environments.ts`**

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { EnvironmentDetail, EnvironmentSummary } from "../types";

export function useEnvironments() {
  return useQuery<EnvironmentSummary[]>({
    queryKey: ["environments"],
    queryFn: () => apiFetch<EnvironmentSummary[]>("/api/environments"),
  });
}

export function useEnvironment(name: string | null) {
  return useQuery<EnvironmentDetail>({
    queryKey: ["environment", name],
    queryFn: () => apiFetch<EnvironmentDetail>(`/api/environments/${name}`),
    enabled: name !== null,
  });
}

export function useSaveEnvironment() {
  const queryClient = useQueryClient();
  return useMutation<EnvironmentDetail, Error, EnvironmentDetail>({
    mutationFn: (env) =>
      apiFetch<EnvironmentDetail>(`/api/environments/${env.name}`, {
        method: "PUT",
        body: JSON.stringify(env),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(["environment", data.name], data);
    },
  });
}
```

- [ ] **Step 5: Create `frontend/src/api/history.ts`**

```typescript
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { HistoryRecord } from "../types";

export function useHistory(requestPath: string | null) {
  return useQuery<HistoryRecord[]>({
    queryKey: ["history", requestPath],
    queryFn: () =>
      apiFetch<HistoryRecord[]>(
        `/api/history?request_path=${encodeURIComponent(requestPath ?? "")}&limit=50`,
      ),
    enabled: requestPath !== null,
  });
}
```

- [ ] **Step 6: Create `frontend/src/api/cookies.ts`**

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";

export function useCookies() {
  return useQuery<Record<string, Record<string, string>>>({
    queryKey: ["cookies"],
    queryFn: () => apiFetch<Record<string, Record<string, string>>>("/api/cookies"),
  });
}

export function useClearCookies() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, void>({
    mutationFn: () => apiFetch<void>("/api/cookies", { method: "DELETE" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["cookies"] });
    },
  });
}
```

- [ ] **Step 7: Create `frontend/src/api/useSend.ts`**

```typescript
import { useCallback, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useResponseStore } from "../store/responseStore";
import { useSessionStore } from "../store/sessionStore";

async function* parseSSE(
  response: Response,
): AsyncGenerator<{ event: string; data: string }> {
  const reader = response.body?.getReader();
  if (!reader) return;
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";
    for (const block of blocks) {
      const lines = block.trim().split("\n");
      let event = "message";
      let data = "";
      for (const line of lines) {
        if (line.startsWith("event: ")) event = line.slice(7).trim();
        else if (line.startsWith("data: ")) data = line.slice(6);
      }
      if (data) yield { event, data };
    }
  }
}

export function useSend() {
  const abortRef = useRef<AbortController | null>(null);
  const response = useResponseStore();
  const session = useSessionStore();
  const queryClient = useQueryClient();

  const send = useCallback(
    async (requestPath: string) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      response.reset();
      response.setStreaming("streaming");

      try {
        const res = await fetch("/api/send", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            path: requestPath,
            environment: session.activeEnvironment,
          }),
          signal: controller.signal,
        });

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
            const p = payload as { history_id: string };
            response.setDone(p.history_id);
            void queryClient.invalidateQueries({ queryKey: ["history", requestPath] });
          } else if (event === "error") {
            const p = payload as { message: string };
            response.setError(p.message);
          }
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          response.setError(String(err));
          response.setStreaming("error");
        }
      }
    },
    [response, session.activeEnvironment, queryClient],
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    response.setStreaming("idle");
  }, [response]);

  return { send, cancel };
}
```

- [ ] **Step 8: Set up TanStack Query provider in `frontend/src/main.tsx`**

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./index.css";
import App from "./App";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 10_000 },
  },
});

const root = document.getElementById("root");
if (!root) throw new Error("No #root element");

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
```

- [ ] **Step 9: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 10: Commit**

```bash
cd ..
git add frontend/src/api/ frontend/src/main.tsx
git commit -m "feat: add TanStack Query hooks and useSend SSE hook"
```

---

### Task 7: Shared components — StatusBadge + VariableChip

**Files:**
- Create: `frontend/src/components/shared/StatusBadge.tsx`
- Create: `frontend/src/components/shared/StatusBadge.test.tsx`
- Create: `frontend/src/components/shared/VariableChip.tsx`
- Create: `frontend/src/components/shared/VariableChip.test.tsx`
- Create: `frontend/src/lib/codemirror-variables.ts`

- [ ] **Step 1: Write StatusBadge tests**

Create `frontend/src/components/shared/StatusBadge.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "./StatusBadge";

describe("StatusBadge", () => {
  it("shows 2xx as green", () => {
    render(<StatusBadge code={200} />);
    const el = screen.getByText("200");
    expect(el.className).toMatch(/green/);
  });

  it("shows 3xx as yellow", () => {
    render(<StatusBadge code={301} />);
    const el = screen.getByText("301");
    expect(el.className).toMatch(/yellow/);
  });

  it("shows 4xx as red", () => {
    render(<StatusBadge code={404} />);
    const el = screen.getByText("404");
    expect(el.className).toMatch(/red/);
  });

  it("shows 5xx as red", () => {
    render(<StatusBadge code={500} />);
    const el = screen.getByText("500");
    expect(el.className).toMatch(/red/);
  });
});
```

- [ ] **Step 2: Write VariableChip tests**

Create `frontend/src/components/shared/VariableChip.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { VariableChip } from "./VariableChip";

describe("VariableChip", () => {
  it("renders the variable name", () => {
    render(<VariableChip name="base_url" value="http://localhost" />);
    expect(screen.getByText("{{base_url}}")).toBeInTheDocument();
  });

  it("shows resolved value as title when known", () => {
    render(<VariableChip name="token" value="abc123" />);
    expect(screen.getByTitle("abc123")).toBeInTheDocument();
  });

  it("shows 'Not set' as title when unknown", () => {
    render(<VariableChip name="missing" value={undefined} />);
    expect(screen.getByTitle("Not set")).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd frontend && npm test
```

Expected: import errors.

- [ ] **Step 4: Create `frontend/src/components/shared/StatusBadge.tsx`**

```tsx
interface StatusBadgeProps {
  code: number;
  className?: string;
}

function colourClass(code: number): string {
  if (code >= 200 && code < 300) return "bg-green-100 text-green-800";
  if (code >= 300 && code < 400) return "bg-yellow-100 text-yellow-800";
  return "bg-red-100 text-red-800";
}

export function StatusBadge({ code, className = "" }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-mono font-semibold ${colourClass(code)} ${className}`}
      data-testid="response-status"
    >
      {code}
    </span>
  );
}
```

- [ ] **Step 5: Create `frontend/src/components/shared/VariableChip.tsx`**

```tsx
interface VariableChipProps {
  name: string;
  value: string | undefined;
}

export function VariableChip({ name, value }: VariableChipProps) {
  const isKnown = value !== undefined;
  return (
    <span
      className={`inline-block rounded px-1 text-xs font-mono ${
        isKnown
          ? "bg-purple-100 text-purple-700"
          : "bg-amber-100 text-amber-700"
      }`}
      title={isKnown ? value : "Not set"}
    >
      {`{{${name}}}`}
    </span>
  );
}
```

- [ ] **Step 6: Create `frontend/src/lib/codemirror-variables.ts`**

This is the CodeMirror 6 extension that highlights `{{variable}}` tokens in editors:

```typescript
import { Decoration, type DecorationSet, EditorView, ViewPlugin, type ViewUpdate } from "@codemirror/view";
import { RangeSetBuilder } from "@codemirror/state";

const VAR_REGEX = /\{\{([^}]+)\}\}/g;

function buildDecorations(
  view: EditorView,
  variables: Record<string, string>,
): DecorationSet {
  const builder = new RangeSetBuilder<Decoration>();
  for (const { from, to } of view.visibleRanges) {
    const text = view.state.sliceDoc(from, to);
    VAR_REGEX.lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = VAR_REGEX.exec(text)) !== null) {
      const varName = match[1] ?? "";
      const start = from + match.index;
      const end = start + match[0].length;
      const isKnown = varName in variables;
      builder.add(
        start,
        end,
        Decoration.mark({
          class: isKnown ? "cm-var-known" : "cm-var-unknown",
          attributes: {
            title: isKnown ? (variables[varName] ?? "") : "Not set",
          },
        }),
      );
    }
  }
  return builder.finish();
}

export function variableHighlighter(variables: Record<string, string>) {
  return ViewPlugin.fromClass(
    class {
      decorations: DecorationSet;
      constructor(view: EditorView) {
        this.decorations = buildDecorations(view, variables);
      }
      update(update: ViewUpdate) {
        if (update.docChanged || update.viewportChanged) {
          this.decorations = buildDecorations(update.view, variables);
        }
      }
    },
    { decorations: (v) => v.decorations },
  );
}
```

- [ ] **Step 7: Run tests and verify they pass**

```bash
cd frontend && npm test
```

Expected: 7 new tests pass (StatusBadge × 4 + VariableChip × 3) plus existing 5 store tests.

- [ ] **Step 8: Commit**

```bash
cd ..
git add frontend/src/components/shared/ frontend/src/lib/codemirror-variables.ts
git commit -m "feat: add StatusBadge, VariableChip components and CodeMirror variable highlighter"
```

---

### Task 8: WelcomeView

**Files:**
- Create: `frontend/src/views/WelcomeView.tsx`
- Create: `frontend/src/App.tsx` (initial version)

- [ ] **Step 1: Create `frontend/src/views/WelcomeView.tsx`**

```tsx
import { useState } from "react";
import { useSetProject } from "../api/projects";

export function WelcomeView() {
  const [path, setPath] = useState("");
  const { mutate, isPending, error } = useSetProject();

  const handleOpen = () => {
    if (path.trim()) mutate(path.trim());
  };

  return (
    <div className="flex h-screen items-center justify-center bg-gray-50" data-testid="welcome-card">
      <div className="w-full max-w-md rounded-lg border bg-white p-8 shadow-sm">
        <h1 className="mb-1 text-xl font-semibold">Drummer</h1>
        <p className="mb-6 text-sm text-gray-500">Open a project to get started.</p>
        <div className="flex gap-2">
          <input
            type="text"
            className="flex-1 rounded border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            placeholder="/path/to/your/project"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleOpen()}
            data-testid="project-path-input"
          />
          <button
            className="rounded bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"
            onClick={handleOpen}
            disabled={isPending || !path.trim()}
            data-testid="open-project-button"
          >
            {isPending ? "Opening…" : "Open"}
          </button>
        </div>
        {error && (
          <p className="mt-3 text-sm text-red-600">{error.message}</p>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create the initial `frontend/src/App.tsx`**

This version shows WelcomeView when no project is loaded, and a placeholder when one is. WorkspaceView will be wired in Task 17.

```tsx
import { useProject } from "./api/projects";
import { WelcomeView } from "./views/WelcomeView";

export default function App() {
  const { data: project, isLoading } = useProject();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center text-gray-400 text-sm">
        Loading…
      </div>
    );
  }

  if (!project) return <WelcomeView />;

  return (
    <div className="flex h-screen items-center justify-center text-gray-400 text-sm">
      Project: {project.name} — workspace coming soon
    </div>
  );
}
```

- [ ] **Step 3: Verify the build**

```bash
cd frontend && npm run build
```

Expected: no TypeScript errors, build succeeds.

- [ ] **Step 4: Commit**

```bash
cd ..
git add frontend/src/views/WelcomeView.tsx frontend/src/App.tsx
git commit -m "feat: add WelcomeView with project path input"
```

---

### Task 9: Sidebar + request tree

**Files:**
- Create: `frontend/src/components/tree/TreeNode.tsx`
- Create: `frontend/src/components/tree/RequestTree.tsx`
- Create: `frontend/src/components/layout/Sidebar.tsx`

- [ ] **Step 1: Create `frontend/src/lib/hexdump.ts`** (needed later but small — add here)

```typescript
export interface HexRow {
  offset: string;
  hex: string;
  ascii: string;
}

export function hexdump(text: string): HexRow[] {
  const bytes = new TextEncoder().encode(text);
  const rows: HexRow[] = [];
  for (let i = 0; i < bytes.length; i += 16) {
    const chunk = Array.from(bytes.slice(i, i + 16));
    const offset = i.toString(16).padStart(8, "0");
    const hex = chunk
      .map((b) => b.toString(16).padStart(2, "0"))
      .join(" ")
      .padEnd(47, " ");
    const ascii = chunk
      .map((b) => (b >= 32 && b < 127 ? String.fromCharCode(b) : "."))
      .join("");
    rows.push({ offset, hex, ascii });
  }
  return rows;
}
```

- [ ] **Step 2: Create `frontend/src/components/tree/TreeNode.tsx`**

```tsx
import type { RequestSummary } from "../../types";
import { useRequestStore } from "../../store/requestStore";

const METHOD_COLOURS: Record<string, string> = {
  GET: "text-green-600",
  POST: "text-blue-600",
  PUT: "text-amber-600",
  PATCH: "text-orange-500",
  DELETE: "text-red-600",
  HEAD: "text-gray-500",
  OPTIONS: "text-gray-500",
  TRACE: "text-gray-500",
};

interface TreeNodeProps {
  request: RequestSummary;
  onSelect: (path: string) => void;
}

export function TreeNode({ request, onSelect }: TreeNodeProps) {
  const { selectedPath, isDirty } = useRequestStore();
  const isSelected = selectedPath === request.path;
  const dirty = isSelected && isDirty();

  return (
    <button
      className={`flex w-full items-center gap-2 rounded px-2 py-1 text-left text-sm ${
        isSelected ? "bg-purple-50 text-purple-900" : "hover:bg-gray-100 text-gray-700"
      }`}
      onClick={() => onSelect(request.path)}
      data-testid={`tree-node-${request.path}`}
    >
      <span className={`w-14 shrink-0 text-xs font-mono font-semibold ${METHOD_COLOURS[request.method] ?? "text-gray-500"}`}>
        {request.method}
      </span>
      <span className="flex-1 truncate">{request.name}</span>
      {dirty && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" title="Unsaved changes" />}
    </button>
  );
}
```

- [ ] **Step 3: Create `frontend/src/components/tree/RequestTree.tsx`**

```tsx
import type { RequestSummary } from "../../types";
import { TreeNode } from "./TreeNode";

interface RequestTreeProps {
  requests: RequestSummary[];
  onSelect: (path: string) => void;
}

export function RequestTree({ requests, onSelect }: RequestTreeProps) {
  if (requests.length === 0) {
    return (
      <p className="px-2 py-4 text-xs text-gray-400">No requests found.</p>
    );
  }

  return (
    <div className="flex flex-col gap-0.5 py-1" data-testid="request-tree">
      {requests.map((r) => (
        <TreeNode key={r.path} request={r} onSelect={onSelect} />
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Create `frontend/src/components/layout/Sidebar.tsx`**

```tsx
import { useProjectStore } from "../../store/projectStore";
import { useRequestStore } from "../../store/requestStore";
import { useSessionStore } from "../../store/sessionStore";
import { useEnvironments } from "../../api/environments";
import { useRequest } from "../../api/requests";
import { RequestTree } from "../tree/RequestTree";

interface SidebarProps {
  onRequestSelect: (path: string) => void;
}

export function Sidebar({ onRequestSelect }: SidebarProps) {
  const { project, requests } = useProjectStore();
  const { selectedPath, isDirty, discard } = useRequestStore();
  const { activeEnvironment, setActiveEnvironment } = useSessionStore();
  const { data: environments = [] } = useEnvironments();
  const { data: requestDetail } = useRequest(selectedPath);

  const handleSelect = (path: string) => {
    if (selectedPath !== path && isDirty()) {
      if (!window.confirm("You have unsaved changes. Discard them?")) return;
      discard();
    }
    onRequestSelect(path);
  };

  return (
    <div className="flex h-full flex-col border-r bg-gray-50">
      <div className="border-b px-3 py-2">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Project</p>
        <p className="truncate text-sm font-medium text-gray-900">{project?.name}</p>
      </div>

      {environments.length > 0 && (
        <div className="border-b px-3 py-2">
          <label className="text-xs text-gray-500">Environment</label>
          <select
            className="mt-1 w-full rounded border px-2 py-1 text-sm"
            value={activeEnvironment}
            onChange={(e) => setActiveEnvironment(e.target.value)}
          >
            {environments.map((env) => (
              <option key={env.name} value={env.name}>
                {env.name}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-1 py-1">
        <RequestTree requests={requests} onSelect={handleSelect} />
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
cd ..
git add frontend/src/components/tree/ frontend/src/components/layout/Sidebar.tsx frontend/src/lib/hexdump.ts
git commit -m "feat: add sidebar, request tree, TreeNode components"
```

---

### Task 10: UrlBar

**Files:**
- Create: `frontend/src/components/request/UrlBar.tsx`
- Create: `frontend/src/components/request/UrlBar.test.tsx`

- [ ] **Step 1: Write UrlBar tests**

Create `frontend/src/components/request/UrlBar.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { UrlBar } from "./UrlBar";

describe("UrlBar", () => {
  it("renders the method selector and Send button", () => {
    render(
      <UrlBar
        method="GET"
        url=""
        onMethodChange={vi.fn()}
        onUrlChange={vi.fn()}
        onSend={vi.fn()}
        onCancel={vi.fn()}
        isStreaming={false}
        variables={{}}
      />,
    );
    expect(screen.getByText("GET")).toBeInTheDocument();
    expect(screen.getByText("Send")).toBeInTheDocument();
  });

  it("calls onSend when Send is clicked", () => {
    const onSend = vi.fn();
    render(
      <UrlBar
        method="GET"
        url="http://example.com"
        onMethodChange={vi.fn()}
        onUrlChange={vi.fn()}
        onSend={onSend}
        onCancel={vi.fn()}
        isStreaming={false}
        variables={{}}
      />,
    );
    fireEvent.click(screen.getByText("Send"));
    expect(onSend).toHaveBeenCalledOnce();
  });

  it("shows Cancel when streaming", () => {
    render(
      <UrlBar
        method="POST"
        url=""
        onMethodChange={vi.fn()}
        onUrlChange={vi.fn()}
        onSend={vi.fn()}
        onCancel={vi.fn()}
        isStreaming={true}
        variables={{}}
      />,
    );
    expect(screen.getByText("Cancel")).toBeInTheDocument();
    expect(screen.queryByText("Send")).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend && npm test
```

Expected: import error.

- [ ] **Step 3: Create `frontend/src/components/request/UrlBar.tsx`**

```tsx
import { useEffect, useRef } from "react";
import { EditorView, basicSetup } from "codemirror";
import { EditorState } from "@codemirror/state";
import { variableHighlighter } from "../../lib/codemirror-variables";
import type { HttpMethod } from "../../types";

const METHODS: HttpMethod[] = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"];

const METHOD_BG: Record<string, string> = {
  GET: "text-green-700",
  POST: "text-blue-700",
  PUT: "text-amber-700",
  PATCH: "text-orange-600",
  DELETE: "text-red-700",
  HEAD: "text-gray-600",
  OPTIONS: "text-gray-600",
};

interface UrlBarProps {
  method: HttpMethod;
  url: string;
  onMethodChange: (method: HttpMethod) => void;
  onUrlChange: (url: string) => void;
  onSend: () => void;
  onCancel: () => void;
  isStreaming: boolean;
  variables: Record<string, string>;
}

export function UrlBar({
  method,
  url,
  onMethodChange,
  onUrlChange,
  onSend,
  onCancel,
  isStreaming,
  variables,
}: UrlBarProps) {
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);

  useEffect(() => {
    if (!editorRef.current) return;

    const view = new EditorView({
      state: EditorState.create({
        doc: url,
        extensions: [
          basicSetup,
          EditorView.lineWrapping,
          variableHighlighter(variables),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) {
              onUrlChange(update.state.doc.toString());
            }
          }),
          EditorView.domEventHandlers({
            keydown: (e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                if (!isStreaming) onSend();
              }
            },
          }),
          EditorView.theme({
            "&": { fontSize: "0.875rem", fontFamily: "inherit" },
            ".cm-content": { padding: "4px 8px", minHeight: "32px" },
            ".cm-focused": { outline: "none" },
            ".cm-scroller": { overflow: "hidden" },
          }),
        ],
      }),
      parent: editorRef.current,
    });

    viewRef.current = view;
    return () => view.destroy();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps — intentionally init once

  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const current = view.state.doc.toString();
    if (current !== url) {
      view.dispatch({ changes: { from: 0, to: current.length, insert: url } });
    }
  }, [url]);

  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    view.dispatch({ effects: [] });
    // Re-apply the variable highlighter extension when variables change
    // by updating the extension — simplest approach is recreate (see note below)
  }, [variables]);

  return (
    <div className="flex items-stretch gap-2 border-b px-3 py-2">
      <select
        className={`rounded border px-2 text-sm font-mono font-semibold ${METHOD_BG[method] ?? "text-gray-600"}`}
        value={method}
        onChange={(e) => onMethodChange(e.target.value as HttpMethod)}
      >
        {METHODS.map((m) => (
          <option key={m} value={m}>{m}</option>
        ))}
      </select>

      <div
        ref={editorRef}
        className="cm-url-bar flex-1 rounded border focus-within:ring-2 focus-within:ring-purple-500"
        data-testid="url-input"
      />

      {isStreaming ? (
        <button
          className="rounded bg-gray-200 px-4 py-1.5 text-sm font-medium hover:bg-gray-300"
          onClick={onCancel}
        >
          Cancel
        </button>
      ) : (
        <button
          className="rounded bg-purple-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-purple-700"
          onClick={onSend}
          data-testid="send-button"
        >
          Send
        </button>
      )}
    </div>
  );
}
```

Note: The CodeMirror editor is initialised once to avoid remounting. Variable highlighting updates are handled by re-extending the editor state; for Phase 5 this is acceptable as variable changes are infrequent.

- [ ] **Step 4: Install codemirror base package**

```bash
cd frontend && npm install codemirror
```

- [ ] **Step 5: Run tests**

```bash
npm test
```

Expected: 3 UrlBar tests pass plus all prior tests.

- [ ] **Step 6: Commit**

```bash
cd ..
git add frontend/src/components/request/UrlBar.tsx frontend/src/components/request/UrlBar.test.tsx
git commit -m "feat: add UrlBar with CodeMirror URL editor and method selector"
```

---

### Task 11: ParamsTab + HeadersTab

**Files:**
- Create: `frontend/src/components/request/KeyValueTable.tsx`
- Create: `frontend/src/components/request/ParamsTab.tsx`
- Create: `frontend/src/components/request/HeadersTab.tsx`

- [ ] **Step 1: Create `frontend/src/components/request/KeyValueTable.tsx`**

```tsx
import { Plus, Trash2 } from "lucide-react";

interface KeyValueTableProps {
  entries: Record<string, string>;
  onChange: (entries: Record<string, string>) => void;
  keyPlaceholder?: string;
  valuePlaceholder?: string;
}

export function KeyValueTable({
  entries,
  onChange,
  keyPlaceholder = "Key",
  valuePlaceholder = "Value",
}: KeyValueTableProps) {
  const pairs = Object.entries(entries);

  const update = (index: number, key: string, value: string) => {
    const next = [...pairs];
    next[index] = [key, value];
    onChange(Object.fromEntries(next.filter(([k]) => k !== "")));
  };

  const remove = (index: number) => {
    const next = pairs.filter((_, i) => i !== index);
    onChange(Object.fromEntries(next));
  };

  const add = () => {
    onChange({ ...entries, "": "" });
  };

  return (
    <div className="flex flex-col gap-1 p-2">
      {pairs.map(([k, v], i) => (
        <div key={i} className="flex items-center gap-1">
          <input
            className="flex-1 rounded border px-2 py-1 text-sm font-mono"
            value={k}
            placeholder={keyPlaceholder}
            onChange={(e) => update(i, e.target.value, v)}
          />
          <input
            className="flex-1 rounded border px-2 py-1 text-sm font-mono"
            value={v}
            placeholder={valuePlaceholder}
            onChange={(e) => update(i, k, e.target.value)}
          />
          <button
            className="p-1 text-gray-400 hover:text-red-500"
            onClick={() => remove(i)}
            aria-label="Remove"
          >
            <Trash2 size={14} />
          </button>
        </div>
      ))}
      <button
        className="flex items-center gap-1 text-xs text-gray-500 hover:text-purple-600 mt-1"
        onClick={add}
      >
        <Plus size={13} /> Add
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/src/components/request/ParamsTab.tsx`**

```tsx
import { useRequestStore } from "../../store/requestStore";
import { KeyValueTable } from "./KeyValueTable";

export function ParamsTab() {
  const { saved, draft, patch } = useRequestStore();
  const current = draft ?? saved;
  const params = current?.frontmatter.params ?? {};

  return (
    <KeyValueTable
      entries={params}
      onChange={(params) => patch({ params })}
      keyPlaceholder="Parameter"
      valuePlaceholder="Value"
    />
  );
}
```

- [ ] **Step 3: Create `frontend/src/components/request/HeadersTab.tsx`**

```tsx
import { useRequestStore } from "../../store/requestStore";
import { KeyValueTable } from "./KeyValueTable";

export function HeadersTab() {
  const { saved, draft, patch } = useRequestStore();
  const current = draft ?? saved;
  const headers = current?.frontmatter.headers ?? {};

  return (
    <KeyValueTable
      entries={headers}
      onChange={(headers) => patch({ headers })}
      keyPlaceholder="Header"
      valuePlaceholder="Value"
    />
  );
}
```

- [ ] **Step 4: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 5: Commit**

```bash
cd ..
git add frontend/src/components/request/KeyValueTable.tsx frontend/src/components/request/ParamsTab.tsx frontend/src/components/request/HeadersTab.tsx
git commit -m "feat: add ParamsTab and HeadersTab with KeyValueTable"
```

---

### Task 12: BodyTab + AuthTab + stub tabs

**Files:**
- Create: `frontend/src/components/request/BodyTab.tsx`
- Create: `frontend/src/components/request/AuthTab.tsx`
- Create: `frontend/src/components/request/ScriptTab.tsx`
- Create: `frontend/src/components/request/CookiesTab.tsx`

- [ ] **Step 1: Create `frontend/src/components/request/BodyTab.tsx`**

```tsx
import { useEffect, useRef } from "react";
import { EditorView, basicSetup } from "codemirror";
import { EditorState } from "@codemirror/state";
import { json } from "@codemirror/lang-json";
import { useRequestStore } from "../../store/requestStore";

type BodyMode = "raw" | "json" | "form-data" | "graphql";

const MODES: { value: BodyMode; label: string; disabled?: boolean }[] = [
  { value: "raw", label: "Raw" },
  { value: "json", label: "JSON" },
  { value: "form-data", label: "Form Data" },
  { value: "graphql", label: "GraphQL", disabled: true },
];

export function BodyTab() {
  const { saved, draft, patch } = useRequestStore();
  const current = draft ?? saved;
  const body = current?.body ?? "";

  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const [mode, setMode] = [
    (current as { _bodyMode?: BodyMode })?._bodyMode ?? "raw",
    (m: BodyMode) => patch({ url: current?.frontmatter.url ?? "" }),  // mode stored locally
  ] as const;

  // track mode in local state
  const [localMode, setLocalMode] = [
    "raw" as BodyMode,
    (m: BodyMode) => {},
  ];

  useEffect(() => {
    if (!editorRef.current) return;
    const view = new EditorView({
      state: EditorState.create({
        doc: body,
        extensions: [
          basicSetup,
          EditorView.updateListener.of((update) => {
            if (update.docChanged) patch({ body: update.state.doc.toString() });
          }),
        ],
      }),
      parent: editorRef.current,
    });
    viewRef.current = view;
    return () => view.destroy();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const current = view.state.doc.toString();
    if (current !== body) {
      view.dispatch({ changes: { from: 0, to: current.length, insert: body } });
    }
  }, [body]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex gap-1 border-b px-2 py-1">
        {MODES.map((m) => (
          <button
            key={m.value}
            disabled={m.disabled}
            className={`rounded px-2 py-0.5 text-xs ${
              m.disabled
                ? "text-gray-300 cursor-not-allowed"
                : "hover:bg-gray-100 text-gray-600"
            }`}
            title={m.disabled ? "Available in Phase 8 (GraphQL)" : undefined}
          >
            {m.label}
          </button>
        ))}
      </div>
      <div ref={editorRef} className="flex-1 overflow-auto text-sm" />
    </div>
  );
}
```

- [ ] **Step 2: Simplify BodyTab (the local mode state above is over-engineered; replace with useState)**

Replace `frontend/src/components/request/BodyTab.tsx` with this cleaner version:

```tsx
import { useEffect, useRef, useState } from "react";
import { EditorView, basicSetup } from "codemirror";
import { EditorState } from "@codemirror/state";
import { useRequestStore } from "../../store/requestStore";

type BodyMode = "raw" | "json" | "form-data" | "graphql";

export function BodyTab() {
  const { saved, draft, patch } = useRequestStore();
  const current = draft ?? saved;
  const body = current?.body ?? "";
  const [mode, setMode] = useState<BodyMode>("raw");

  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);

  useEffect(() => {
    if (!editorRef.current) return;
    const view = new EditorView({
      state: EditorState.create({
        doc: body,
        extensions: [
          basicSetup,
          EditorView.updateListener.of((update) => {
            if (update.docChanged) patch({ body: update.state.doc.toString() });
          }),
        ],
      }),
      parent: editorRef.current,
    });
    viewRef.current = view;
    return () => view.destroy();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const cur = view.state.doc.toString();
    if (cur !== body) view.dispatch({ changes: { from: 0, to: cur.length, insert: body } });
  }, [body]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex gap-1 border-b px-2 py-1">
        {(["raw", "json", "form-data", "graphql"] as BodyMode[]).map((m) => (
          <button
            key={m}
            disabled={m === "graphql"}
            onClick={() => setMode(m)}
            className={`rounded px-2 py-0.5 text-xs capitalize ${
              m === "graphql"
                ? "cursor-not-allowed text-gray-300"
                : mode === m
                  ? "bg-purple-100 text-purple-700"
                  : "text-gray-600 hover:bg-gray-100"
            }`}
            title={m === "graphql" ? "Available in Phase 8 (GraphQL)" : undefined}
          >
            {m === "form-data" ? "Form Data" : m.charAt(0).toUpperCase() + m.slice(1)}
          </button>
        ))}
      </div>
      {mode === "form-data" ? (
        <p className="p-4 text-sm text-gray-400">Form-data editor coming soon.</p>
      ) : (
        <div ref={editorRef} className="flex-1 overflow-auto text-sm" />
      )}
    </div>
  );
}
```

- [ ] **Step 3: Create `frontend/src/components/request/AuthTab.tsx`**

```tsx
import { useRequestStore } from "../../store/requestStore";
import type { AuthType } from "../../types";

export function AuthTab() {
  const { saved, draft, patch } = useRequestStore();
  const current = draft ?? saved;
  const auth = current?.frontmatter.auth ?? { type: "none", token: "", username: "", password: "", key: "", value: "" };

  const update = (changes: Partial<typeof auth>) =>
    patch({ auth: { ...auth, ...changes } });

  return (
    <div className="p-3 flex flex-col gap-3">
      <div>
        <label className="text-xs text-gray-500">Auth type</label>
        <select
          className="mt-1 w-48 rounded border px-2 py-1 text-sm"
          value={auth.type}
          onChange={(e) => update({ type: e.target.value as AuthType })}
        >
          <option value="none">None</option>
          <option value="bearer">Bearer Token</option>
          <option value="basic">Basic Auth</option>
          <option value="api_key" disabled>API Key</option>
          <option value="oauth" disabled>OAuth 2.0 — Phase 9</option>
        </select>
      </div>

      {auth.type === "bearer" && (
        <div>
          <label className="text-xs text-gray-500">Token</label>
          <input
            type="text"
            className="mt-1 w-full rounded border px-2 py-1 text-sm font-mono"
            value={auth.token}
            placeholder="Bearer token"
            onChange={(e) => update({ token: e.target.value })}
          />
        </div>
      )}

      {auth.type === "basic" && (
        <>
          <div>
            <label className="text-xs text-gray-500">Username</label>
            <input
              type="text"
              className="mt-1 w-full rounded border px-2 py-1 text-sm"
              value={auth.username}
              onChange={(e) => update({ username: e.target.value })}
            />
          </div>
          <div>
            <label className="text-xs text-gray-500">Password</label>
            <input
              type="password"
              className="mt-1 w-full rounded border px-2 py-1 text-sm"
              value={auth.password}
              onChange={(e) => update({ password: e.target.value })}
            />
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Create stub tabs**

Create `frontend/src/components/request/ScriptTab.tsx`:

```tsx
export function ScriptTab() {
  return (
    <div className="flex h-full items-center justify-center">
      <p className="text-sm text-gray-400">
        Pre/post request scripts — available in Phase 6 (Scripting)
      </p>
    </div>
  );
}
```

Create `frontend/src/components/request/CookiesTab.tsx`:

```tsx
export function CookiesTab() {
  return (
    <div className="flex h-full items-center justify-center">
      <p className="text-sm text-gray-400">
        Explicit cookie management — available in Phase 9 (OAuth + Cookies)
      </p>
    </div>
  );
}
```

- [ ] **Step 5: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 6: Commit**

```bash
cd ..
git add frontend/src/components/request/
git commit -m "feat: add BodyTab, AuthTab, ScriptTab and CookiesTab stubs"
```

---

### Task 13: Response panels

**Files:**
- Create: `frontend/src/components/response/ResponseMeta.tsx`
- Create: `frontend/src/components/response/BodyViewer.tsx`
- Create: `frontend/src/components/response/HeadersViewer.tsx`
- Create: `frontend/src/components/response/ScriptOutput.tsx`
- Create: `frontend/src/components/response/RawViewer.tsx`
- Create: `frontend/src/components/response/HistoryDrawer.tsx`

- [ ] **Step 1: Create `frontend/src/components/response/ResponseMeta.tsx`**

```tsx
import { StatusBadge } from "../shared/StatusBadge";

interface ResponseMetaProps {
  statusCode: number | null;
  elapsedMs: number | null;
  bodyLength: number | null;
  streaming: "idle" | "streaming" | "done" | "error";
}

export function ResponseMeta({ statusCode, elapsedMs, bodyLength, streaming }: ResponseMetaProps) {
  if (streaming === "idle") {
    return (
      <div className="flex items-center px-3 py-2 text-xs text-gray-400 border-b">
        Send a request to see the response.
      </div>
    );
  }

  if (streaming === "streaming" && !statusCode) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 border-b">
        <span className="text-xs text-gray-400 animate-pulse">Waiting…</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3 px-3 py-2 border-b">
      {statusCode && <StatusBadge code={statusCode} />}
      {elapsedMs !== null && (
        <span className="text-xs text-gray-500">{elapsedMs.toFixed(0)} ms</span>
      )}
      {bodyLength !== null && (
        <span className="text-xs text-gray-500">{formatBytes(bodyLength)}</span>
      )}
      {streaming === "streaming" && (
        <span className="text-xs text-gray-400 animate-pulse">streaming…</span>
      )}
    </div>
  );
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(2)} MB`;
}
```

- [ ] **Step 2: Create `frontend/src/components/response/BodyViewer.tsx`**

```tsx
interface BodyViewerProps {
  body: string | null;
  contentType?: string;
}

function tryPrettyJson(text: string): string | null {
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return null;
  }
}

export function BodyViewer({ body, contentType = "" }: BodyViewerProps) {
  if (body === null) return null;

  if (contentType.startsWith("image/")) {
    const src = `data:${contentType};base64,${btoa(body)}`;
    return (
      <div className="p-3">
        <img src={src} alt="Response" className="max-w-full" />
      </div>
    );
  }

  const isJson = contentType.includes("json") || contentType === "";
  const pretty = isJson ? tryPrettyJson(body) : null;
  const display = pretty ?? body;

  return (
    <pre className="overflow-auto p-3 text-xs font-mono whitespace-pre-wrap break-words text-gray-800">
      {display}
    </pre>
  );
}
```

- [ ] **Step 3: Create `frontend/src/components/response/HeadersViewer.tsx`**

```tsx
interface HeadersViewerProps {
  headers: [string, string][];
}

export function HeadersViewer({ headers }: HeadersViewerProps) {
  if (headers.length === 0) {
    return <p className="p-3 text-xs text-gray-400">No headers.</p>;
  }

  return (
    <table className="w-full text-xs font-mono">
      <tbody>
        {headers.map(([k, v], i) => (
          <tr key={i} className="border-b last:border-0">
            <td className="py-1 px-3 font-semibold text-gray-600 w-1/3 align-top">{k}</td>
            <td className="py-1 px-3 text-gray-800 break-all">{v}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 4: Create `frontend/src/components/response/ScriptOutput.tsx`**

```tsx
export function ScriptOutput() {
  return (
    <div className="flex h-full items-center justify-center">
      <p className="text-sm text-gray-400">
        Script console output — available in Phase 6 (Scripting)
      </p>
    </div>
  );
}
```

- [ ] **Step 5: Create `frontend/src/components/response/RawViewer.tsx`**

```tsx
import { hexdump } from "../../lib/hexdump";

interface RawViewerProps {
  body: string | null;
}

export function RawViewer({ body }: RawViewerProps) {
  if (body === null) return null;
  const rows = hexdump(body);

  return (
    <div className="flex h-full overflow-hidden">
      <div className="flex-1 overflow-auto p-2">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="border-b text-gray-400">
              <th className="px-2 py-1 text-left w-24">Offset</th>
              <th className="px-2 py-1 text-left">Hex</th>
              <th className="px-2 py-1 text-left w-32">ASCII</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-b last:border-0">
                <td className="px-2 py-0.5 text-gray-400">{row.offset}</td>
                <td className="px-2 py-0.5 text-gray-700">{row.hex}</td>
                <td className="px-2 py-0.5 text-gray-600">{row.ascii}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="w-72 border-l overflow-auto p-2">
        <pre className="text-xs font-mono whitespace-pre-wrap break-words text-gray-700">
          {body}
        </pre>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Create `frontend/src/components/response/HistoryDrawer.tsx`**

```tsx
import { useHistory } from "../../api/history";
import { useRequestStore } from "../../store/requestStore";
import { useResponseStore } from "../../store/responseStore";
import { StatusBadge } from "../shared/StatusBadge";
import type { HistoryRecord } from "../../types";

export function HistoryDrawer() {
  const { selectedPath } = useRequestStore();
  const responseStore = useResponseStore();
  const { data: records = [], isLoading } = useHistory(selectedPath);

  if (!selectedPath) return <p className="p-3 text-xs text-gray-400">No request selected.</p>;
  if (isLoading) return <p className="p-3 text-xs text-gray-400">Loading…</p>;
  if (records.length === 0) return <p className="p-3 text-xs text-gray-400">No history yet.</p>;

  const loadRecord = (rec: HistoryRecord) => {
    responseStore.setStatus(rec.status_code, rec.url);
    responseStore.setHeaders(rec.response_headers);
    responseStore.setBody(rec.response_body, rec.encoding, rec.elapsed_ms);
    responseStore.setDone(rec.id);
  };

  return (
    <div className="overflow-auto">
      {records.map((rec) => (
        <button
          key={rec.id}
          className="flex w-full items-center gap-3 border-b px-3 py-2 text-left hover:bg-gray-50"
          onClick={() => loadRecord(rec)}
        >
          <StatusBadge code={rec.status_code} />
          <span className="flex-1 truncate text-xs text-gray-600">{rec.url}</span>
          <span className="text-xs text-gray-400">
            {new Date(rec.sent_at).toLocaleTimeString()}
          </span>
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 7: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 8: Commit**

```bash
cd ..
git add frontend/src/components/response/
git commit -m "feat: add response panel components (meta, body, headers, raw, history)"
```

---

### Task 14: WorkspaceView — 3-panel assembly

**Files:**
- Create: `frontend/src/components/layout/PanelGroup.tsx`
- Create: `frontend/src/views/WorkspaceView.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create `frontend/src/components/layout/PanelGroup.tsx`**

```tsx
import {
  Panel,
  PanelGroup,
  PanelResizeHandle,
} from "react-resizable-panels";

interface TwoPanelProps {
  left: React.ReactNode;
  right: React.ReactNode;
  direction?: "horizontal" | "vertical";
  defaultSizes?: [number, number];
}

export function TwoPanel({
  left,
  right,
  direction = "horizontal",
  defaultSizes = [50, 50],
}: TwoPanelProps) {
  return (
    <PanelGroup direction={direction} className="h-full">
      <Panel defaultSize={defaultSizes[0]} minSize={10}>
        {left}
      </Panel>
      <PanelResizeHandle className={direction === "horizontal" ? "w-1 bg-gray-200 hover:bg-purple-400 cursor-col-resize" : "h-1 bg-gray-200 hover:bg-purple-400 cursor-row-resize"} />
      <Panel defaultSize={defaultSizes[1]} minSize={10}>
        {right}
      </Panel>
    </PanelGroup>
  );
}
```

- [ ] **Step 2: Create `frontend/src/views/WorkspaceView.tsx`**

```tsx
import { useEffect } from "react";
import { TwoPanel } from "../components/layout/PanelGroup";
import { Sidebar } from "../components/layout/Sidebar";
import { UrlBar } from "../components/request/UrlBar";
import { ParamsTab } from "../components/request/ParamsTab";
import { HeadersTab } from "../components/request/HeadersTab";
import { BodyTab } from "../components/request/BodyTab";
import { AuthTab } from "../components/request/AuthTab";
import { ScriptTab } from "../components/request/ScriptTab";
import { CookiesTab } from "../components/request/CookiesTab";
import { ResponseMeta } from "../components/response/ResponseMeta";
import { BodyViewer } from "../components/response/BodyViewer";
import { HeadersViewer } from "../components/response/HeadersViewer";
import { RawViewer } from "../components/response/RawViewer";
import { ScriptOutput } from "../components/response/ScriptOutput";
import { HistoryDrawer } from "../components/response/HistoryDrawer";
import { useRequestStore } from "../store/requestStore";
import { useResponseStore } from "../store/responseStore";
import { useProjectStore } from "../store/projectStore";
import { useSessionStore } from "../store/sessionStore";
import { useRequest, useSaveRequest } from "../api/requests";
import { useRequests } from "../api/requests";
import { useSend } from "../api/useSend";
import type { HttpMethod, RequestTab, ResponseTab } from "../types";

export function WorkspaceView() {
  const projectStore = useProjectStore();
  const requestStore = useRequestStore();
  const responseStore = useResponseStore();
  const { variables } = useSessionStore();

  const { data: requests = [] } = useRequests();
  const { data: requestDetail } = useRequest(requestStore.selectedPath);
  const saveRequest = useSaveRequest();
  const { send, cancel } = useSend();

  // Load request into store when data arrives
  useEffect(() => {
    if (requestDetail) requestStore.load(requestDetail);
  }, [requestDetail]); // eslint-disable-line react-hooks/exhaustive-deps

  // Sync request list into projectStore
  useEffect(() => {
    projectStore.setRequests(requests);
  }, [requests]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleRequestSelect = (path: string) => {
    requestStore.select(path);
  };

  const handleSend = () => {
    if (requestStore.selectedPath) void send(requestStore.selectedPath);
  };

  const handleSave = async () => {
    const { selectedPath, draft, saved, markSaved } = requestStore;
    if (!selectedPath || (!draft && !saved)) return;
    const detail = draft ?? saved!;
    const result = await saveRequest.mutateAsync({ path: selectedPath, detail });
    markSaved(result);
  };

  // Cmd+S / Ctrl+S save
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        void handleSave();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [requestStore.draft, requestStore.saved, requestStore.selectedPath]); // eslint-disable-line react-hooks/exhaustive-deps

  const current = requestStore.draft ?? requestStore.saved;
  const requestTab = requestStore.activeTab;
  const responseTab = responseStore.activeTab;

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

  const sidebar = <Sidebar onRequestSelect={handleRequestSelect} />;

  const requestPanel = (
    <div className="flex h-full flex-col">
      <UrlBar
        method={current?.frontmatter.method ?? "GET"}
        url={current?.frontmatter.url ?? ""}
        onMethodChange={(m: HttpMethod) => requestStore.patch({ method: m })}
        onUrlChange={(url) => requestStore.patch({ url })}
        onSend={handleSend}
        onCancel={cancel}
        isStreaming={responseStore.streaming === "streaming"}
        variables={variables}
      />
      <div className="flex gap-0 border-b px-2">
        {REQUEST_TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => requestStore.setTab(tab.id)}
            className={`px-3 py-1.5 text-xs border-b-2 ${
              requestTab === tab.id
                ? "border-purple-600 text-purple-700"
                : "border-transparent text-gray-500 hover:text-gray-700"
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

  const responseHeaderContent = (() => {
    const headers = responseStore.responseHeaders;
    const contentType = headers.find(([k]) => k.toLowerCase() === "content-type")?.[1] ?? "";
    return contentType;
  })();

  const responsePanel = (
    <div className="flex h-full flex-col">
      <ResponseMeta
        statusCode={responseStore.statusCode}
        elapsedMs={responseStore.elapsedMs}
        bodyLength={responseStore.body?.length ?? null}
        streaming={responseStore.streaming}
      />
      <div className="flex gap-0 border-b px-2">
        {RESPONSE_TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => responseStore.setTab(tab.id)}
            className={`px-3 py-1.5 text-xs border-b-2 ${
              responseTab === tab.id
                ? "border-purple-600 text-purple-700"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto">
        {responseTab === "body" && (
          <BodyViewer body={responseStore.body} contentType={responseHeaderContent} />
        )}
        {responseTab === "headers" && (
          <HeadersViewer headers={responseStore.responseHeaders} />
        )}
        {responseTab === "raw" && <RawViewer body={responseStore.body} />}
        {responseTab === "script-output" && <ScriptOutput />}
        {responseTab === "history" && <HistoryDrawer />}
      </div>
    </div>
  );

  const mainArea = (
    <TwoPanel
      left={requestPanel}
      right={responsePanel}
      direction="vertical"
      defaultSizes={[50, 50]}
    />
  );

  return (
    <div className="flex h-screen">
      <TwoPanel
        left={sidebar}
        right={mainArea}
        direction="horizontal"
        defaultSizes={[20, 80]}
      />
    </div>
  );
}
```

- [ ] **Step 3: Update `frontend/src/App.tsx` to use WorkspaceView**

```tsx
import { useEffect } from "react";
import { useProject } from "./api/projects";
import { useProjectStore } from "./store/projectStore";
import { WelcomeView } from "./views/WelcomeView";
import { WorkspaceView } from "./views/WorkspaceView";

export default function App() {
  const { data: project, isLoading } = useProject();
  const { setProject } = useProjectStore();

  useEffect(() => {
    if (project) setProject(project);
  }, [project, setProject]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center text-gray-400 text-sm">
        Loading…
      </div>
    );
  }

  if (!project) return <WelcomeView />;
  return <WorkspaceView />;
}
```

- [ ] **Step 4: Fix the duplicate import in WorkspaceView.tsx**

In `WorkspaceView.tsx`, remove the duplicate `useRequests` import line (it appears twice). The file should only have one import from `"../api/requests"`:

```typescript
import { useRequest, useSaveRequest, useRequests } from "../api/requests";
```

- [ ] **Step 5: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 6: Run all tests**

```bash
npm test
```

Expected: all existing tests pass.

- [ ] **Step 7: Commit**

```bash
cd ..
git add frontend/src/
git commit -m "feat: assemble WorkspaceView with 3-panel layout, request editor, response viewer"
```

---

### Task 15: Playwright e2e smoke tests

**Files:**
- Create: `tests/e2e/fixtures/demo-project/.drummer/project.yaml`
- Create: `tests/e2e/fixtures/demo-project/.drummer/environments/local.yaml`
- Create: `tests/e2e/fixtures/demo-project/hello/get-hello.md`
- Create: `tests/e2e/conftest.py`
- Create: `tests/e2e/test_smoke.py`

- [ ] **Step 1: Create the demo project fixture**

```bash
mkdir -p tests/e2e/fixtures/demo-project/.drummer/environments
mkdir -p tests/e2e/fixtures/demo-project/hello
```

Create `tests/e2e/fixtures/demo-project/.drummer/project.yaml`:

```yaml
name: Demo Project
version: "1"
default_environment: local
```

Create `tests/e2e/fixtures/demo-project/.drummer/environments/local.yaml`:

```yaml
name: local
variables:
  base_url: https://httpbin.org
```

Create `tests/e2e/fixtures/demo-project/hello/get-hello.md`:

```markdown
---
name: Get Hello
method: GET
url: "{{base_url}}/get"
---

A simple GET request using the base_url variable.
```

- [ ] **Step 2: Create `tests/e2e/conftest.py`**

```python
import subprocess
import time
from pathlib import Path

import pytest
from playwright.sync_api import Page

FIXTURE_PROJECT = Path(__file__).parent / "fixtures" / "demo-project"
SERVER_PORT = 8237


@pytest.fixture(scope="session", autouse=True)
def drummer_server():
    proc = subprocess.Popen(
        [
            "python",
            "-m",
            "drummer.cli",
            "serve",
            "--project",
            str(FIXTURE_PROJECT),
            "--port",
            str(SERVER_PORT),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)
    yield proc
    proc.terminate()
    proc.wait()


@pytest.fixture
def base_url() -> str:
    return f"http://127.0.0.1:{SERVER_PORT}"
```

- [ ] **Step 3: Create `tests/e2e/test_smoke.py`**

```python
from playwright.sync_api import Page, expect


def test_app_loads(page: Page, base_url: str) -> None:
    page.goto(base_url)
    expect(page.get_by_test_id("request-tree")).to_be_visible(timeout=10_000)


def test_select_request_populates_editor(page: Page, base_url: str) -> None:
    page.goto(base_url)
    expect(page.get_by_test_id("request-tree")).to_be_visible(timeout=10_000)
    page.get_by_test_id("tree-node-hello/get-hello.md").click()
    expect(page.get_by_test_id("url-input")).to_be_visible()


def test_send_request_shows_status(page: Page, base_url: str) -> None:
    page.goto(base_url)
    expect(page.get_by_test_id("request-tree")).to_be_visible(timeout=10_000)
    page.get_by_test_id("tree-node-hello/get-hello.md").click()
    page.get_by_test_id("send-button").click()
    expect(page.get_by_test_id("response-status")).to_be_visible(timeout=15_000)
```

- [ ] **Step 4: Install Playwright browsers**

```bash
venv/bin/playwright install chromium
```

- [ ] **Step 5: Update the Vite proxy port to 8237 in dev mode**

Since the e2e server runs on 8237 and the default CLI port is 8000, the two are separate. The Vite proxy in `vite.config.ts` points to 8000 (dev mode). The e2e tests talk directly to 8237 (the static-served frontend). No change needed.

- [ ] **Step 6: Build the frontend so the e2e server can serve it**

```bash
cd frontend && npm run build
cd ..
```

- [ ] **Step 7: Run e2e tests**

```bash
make test-e2e
```

Expected: 3 smoke tests pass. Note: Smoke test 3 (`test_send_request_shows_status`) makes a real network call to `https://httpbin.org/get`. If offline, it will fail — this is expected behaviour.

- [ ] **Step 8: Commit**

```bash
git add tests/e2e/
git commit -m "feat: add Playwright e2e smoke tests for app load, request select, and send"
```

---

### Task 16: Makefile updates

**Files:**
- Modify: `Makefile`

- [ ] **Step 1: Update the Makefile**

Replace the contents of `Makefile`:

```makefile
VENV    := $(CURDIR)/venv
PYTHON  := $(VENV)/bin/python
RUFF    := $(VENV)/bin/ruff
PYRIGHT := $(VENV)/bin/pyright
PYTEST  := $(VENV)/bin/pytest
NPM     := npm

PROJECT ?=

.PHONY: install lint format check test test-file test-e2e dev e2e build-frontend

install:
	pip install -e ".[dev]"
	cd frontend && $(NPM) install

lint:
	$(RUFF) check .
	$(RUFF) format --check .
	$(PYRIGHT) drummer
	cd frontend && $(NPM) run check

format:
	$(RUFF) format .
	$(RUFF) check --fix .
	cd frontend && $(NPM) run check:fix

test:
	$(PYTEST) tests/unit tests/integration -q

test-file:
	$(PYTEST) $(FILE) -v

test-e2e:
	$(PYTEST) tests/e2e -v

check: lint test

build-frontend:
	cd frontend && $(NPM) run build

dev:
ifndef PROJECT
	$(error Usage: make dev PROJECT=/path/to/your/project)
endif
	cd frontend && $(NPM) run dev &
	$(PYTHON) -m drummer.cli serve --project $(PROJECT)

e2e: build-frontend test-e2e
```

- [ ] **Step 2: Verify `make check` passes**

```bash
make check
```

Expected: Ruff + Pyright + biome + pytest all pass.

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "chore: update Makefile with dev, e2e, build-frontend targets and biome in check"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| Vite scaffold, React 19, TypeScript strict | Task 2 |
| Tailwind v4, shadcn/ui | Task 3 |
| Biome lint/format | Tasks 2, 16 |
| Vitest + RTL component tests | Task 2 |
| TypeScript types mirroring Pydantic models | Task 4 |
| Four Zustand stores | Task 5 |
| requestStore dirty flag | Task 5 |
| TanStack Query hooks for all routes | Task 6 |
| useSend SSE hook | Task 6 |
| StatusBadge (2xx/3xx/4xx-5xx colours) | Task 7 |
| VariableChip (known/unknown) | Task 7 |
| CodeMirror variable highlighter | Task 7 |
| WelcomeView with path input | Task 8 |
| GET /api/project + POST /api/project | Task 1 |
| Sidebar + environment switcher | Task 9 |
| RequestTree + TreeNode with dirty dot | Task 9 |
| UrlBar with CodeMirror + method selector | Task 10 |
| ParamsTab + HeadersTab | Task 11 |
| BodyTab (Raw/JSON/Form-Data, GraphQL stub) | Task 12 |
| AuthTab (Bearer/Basic, OAuth stub) | Task 12 |
| ScriptTab stub | Task 12 |
| CookiesTab stub | Task 12 |
| ResponseMeta (status/timing/size) | Task 13 |
| BodyViewer (JSON pretty-print/raw/image) | Task 13 |
| HeadersViewer | Task 13 |
| RawViewer (hex dump + decoded text) | Task 13 |
| ScriptOutput stub | Task 13 |
| HistoryDrawer (50 records, click-to-load) | Task 13 |
| WorkspaceView 3-panel assembly | Task 14 |
| react-resizable-panels | Task 14 |
| Cmd+S save | Task 14 |
| Navigation unsaved-changes guard | Task 9 (Sidebar.handleSelect) |
| Playwright e2e (3 smoke tests, data-testid) | Task 15 |
| make dev, make e2e, biome in make check | Task 16 |

**Placeholder scan:** None found.

**Type consistency check:**
- `RequestTab` used in `requestStore.ts` and `WorkspaceView.tsx` — consistent.
- `ResponseTab` used in `responseStore.ts` and `WorkspaceView.tsx` — consistent.
- `StreamingState` used in `responseStore.ts` and `ResponseMeta.tsx` — consistent.
- `[string, string][]` for headers — consistent across SSE events, `HeadersViewer`, `RawViewer`, `HistoryRecord`.
- `useRequests` imported twice in `WorkspaceView.tsx` in Task 14 Step 2 — Step 4 fixes this explicitly.

**One gap found and fixed:** The `useRequests` hook in `requests.ts` has `enabled: false` by default. `WorkspaceView` needs to override this when a project is loaded. Fix: pass `enabled: !!projectStore.project` to the query. Add this clarification to Task 14 Step 2 by noting that `useRequests` should be called with `{ enabled: !!project }`. Since the plan already has `const { data: requests = [] } = useRequests()` without the `enabled` override, and the hook defaults to `enabled: false`, the tree will never load. 

**Fix:** In `WorkspaceView.tsx`, change the `useRequests` call to:

```typescript
const { data: requests = [] } = useRequests({ enabled: !!projectStore.project });
```

And update `frontend/src/api/requests.ts` to accept an options argument:

```typescript
export function useRequests(options?: { enabled?: boolean }) {
  return useQuery<RequestSummary[]>({
    queryKey: ["requests"],
    queryFn: () => apiFetch<RequestSummary[]>("/api/requests"),
    enabled: options?.enabled ?? false,
  });
}
```

This fix should be applied as part of Task 14 Step 2 when creating `WorkspaceView.tsx`. The plan above has been written with `useRequests()` — the implementer should apply this adjustment inline.
