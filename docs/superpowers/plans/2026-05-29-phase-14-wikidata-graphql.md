# Phase 14 — Wikidata GraphQL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a built-in mock GraphQL server backed by real Wikidata data, plus a 3-step GraphQL tutorial arc that drives Drummer's existing GraphQL request pane.

**Architecture:** A one-time dev script fetches real Wikidata entities into a committed static snapshot. `graphql-core` builds an executable schema (with real introspection) over that snapshot, exposed at `POST /mock/wikidata/graphql`. Three GraphQL tutorial steps carry a `graphql` config and flow through the unchanged Phase 8 send pipeline; the frontend passes the config to the real GraphQL UI.

**Tech Stack:** FastAPI + Pydantic + graphql-core (backend), React + TypeScript (frontend), pytest + vitest (tests). Gate: `make check`. Dependencies live directly in `pyproject.toml` (no lockfile); install into `venv/`.

**Spec:** `docs/superpowers/specs/2026-05-29-phase-14-wikidata-graphql-design.md`

---

## File Structure

- Modify `pyproject.toml` — add `graphql-core` to `[project].dependencies`.
- Create `scripts/build_wikidata_snapshot.py` — one-time dev utility (not imported/run by the app).
- Create `drummer/api/mock/wikidata_snapshot.json` — committed static dataset (script output).
- Create `drummer/api/mock/wikidata.py` — graphql-core schema + resolvers + `execute()`.
- Create `tests/unit/test_wikidata_mock.py` — execution + snapshot-integrity tests.
- Modify `drummer/api/routes/mock.py` — add a `/mock/wikidata` router with the GraphQL POST route.
- Modify `drummer/api/app.py` — register the new router.
- Create `tests/integration/test_wikidata_route.py` — route test.
- Modify `drummer/api/routes/tutorial.py` — `TutorialStep.graphql`, pass-through, 3 GraphQL steps.
- Modify `tests/integration/test_tutorial_route.py` — new-step + steps-list tests.
- Modify `frontend/src/types.ts` — `TutorialStep.graphql`.
- Modify `frontend/src/api/tutorial.ts` — `stepToRequestDetail` passes `graphql` through.
- Create `frontend/src/api/tutorial.test.ts` — `stepToRequestDetail` graphql test.
- Modify `drummer/cli.py` — Wikidata attribution block.
- Modify the CLI attribution test (locate under `tests/`), `ROADMAP.md`, `CLAUDE.md`, `README.md`.

---

## Task 1: Dependency + snapshot builder + committed dataset

**Files:**
- Modify: `pyproject.toml`
- Create: `scripts/build_wikidata_snapshot.py`
- Create: `drummer/api/mock/wikidata_snapshot.json` (generated)

- [ ] **Step 1: Add the dependency**

In `pyproject.toml`, add `"graphql-core>=3.2",` to the `[project].dependencies` list (after `"fastapi-mcp>=0.3",` is fine — order isn't enforced).

- [ ] **Step 2: Install it into the venv**

Run: `venv/bin/pip install "graphql-core>=3.2"`
Expected: installs successfully; `venv/bin/python -c "import graphql; print(graphql.__version__)"` prints a 3.2+ version. (graphql-core ships `py.typed`, so pyright needs no extra stubs.)

- [ ] **Step 3: Write the builder script**

Create `scripts/build_wikidata_snapshot.py`:

```python
"""One-time dev utility: build drummer/api/mock/wikidata_snapshot.json from real Wikidata data.

Run manually with `venv/bin/python scripts/build_wikidata_snapshot.py`.
NOT imported or executed by the app or its build — the app reads only the committed JSON.
"""

import json
from pathlib import Path
from typing import Any

import httpx

# Curated, interlinked entity set. Relation targets outside this set are dropped so the
# snapshot graph is closed (no dangling references). Comments are the EXPECTED entity for
# each Q-id — verify the printed labels match and correct any Q-id that doesn't.
QIDS = [
    "Q42",       # Douglas Adams (human)
    "Q3107329",  # The Hitchhiker's Guide to the Galaxy (novel)
    "Q42441",    # Mary Shelley (human)
    "Q172667",   # Frankenstein (novel)
    "Q692",      # William Shakespeare (human)
    "Q41567",    # Hamlet (play)
    "Q350",      # Cambridge
    "Q84",       # London
    "Q189288",   # Stratford-upon-Avon
    "Q145",      # United Kingdom
    "Q5",        # human (class)
    "Q8261",     # novel (class)
    "Q25379",    # play (class)
    "Q7725634",  # literary work (class)
    "Q515",      # city (class)
]

SINGLE_REL = {"author": "P50", "placeOfBirth": "P19", "country": "P17"}
LIST_REL = {"instanceOf": "P31", "notableWork": "P800"}
PUB_DATE_PID = "P577"
ENTITY_DATA = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"


def _claim_ids(entity: dict[str, Any], pid: str) -> list[str]:
    ids: list[str] = []
    for claim in entity.get("claims", {}).get(pid, []):
        val = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(val, dict) and "id" in val:
            ids.append(val["id"])
    return ids


def _pub_date(entity: dict[str, Any]) -> str | None:
    for claim in entity.get("claims", {}).get(PUB_DATE_PID, []):
        val = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(val, dict) and "time" in val:
            # "+1979-10-12T00:00:00Z" -> "1979-10-12"
            return str(val["time"]).lstrip("+").split("T")[0]
    return None


def main() -> None:
    qset = set(QIDS)
    snapshot: dict[str, Any] = {}
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for qid in QIDS:
            resp = client.get(ENTITY_DATA.format(qid=qid))
            resp.raise_for_status()
            entity = resp.json()["entities"][qid]
            label = entity.get("labels", {}).get("en", {}).get("value", qid)
            record: dict[str, Any] = {
                "id": qid,
                "label": label,
                "description": entity.get("descriptions", {}).get("en", {}).get("value"),
                "publicationDate": _pub_date(entity),
            }
            for field, pid in LIST_REL.items():
                record[field] = [i for i in _claim_ids(entity, pid) if i in qset]
            for field, pid in SINGLE_REL.items():
                record[field] = next((i for i in _claim_ids(entity, pid) if i in qset), None)
            snapshot[qid] = record
            print(f"{qid}: {label}")
    out_path = Path("drummer/api/mock/wikidata_snapshot.json")
    out_path.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(snapshot)} entities to {out_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Generate the snapshot**

Run: `venv/bin/python scripts/build_wikidata_snapshot.py`
Expected: prints one `Qxx: <label>` line per entity and `wrote 15 entities ...`.

**Verify each printed label matches its comment.** Confirm specifically: `Q42: Douglas Adams`, `Q3107329: The Hitchhiker's Guide to the Galaxy`, `Q350: Cambridge`, `Q145: United Kingdom`, `Q5: human`. If any Q-id resolves to the wrong entity (e.g. a Shakespeare/play/class id differs), fix the Q-id in `QIDS` and re-run. The tutorial queries depend on Q42 / Q3107329 / Q350 / Q145 being correct.

If the network is unreachable from `Bash`: report **BLOCKED** — the controller will fetch each entity via WebFetch (`https://www.wikidata.org/wiki/Special:EntityData/<qid>.json`) and hand back the JSON to build the snapshot.

- [ ] **Step 5: Sanity-check the generated JSON**

Run:
```bash
venv/bin/python -c "import json; d=json.load(open('drummer/api/mock/wikidata_snapshot.json')); \
print(d['Q42']['label'], d['Q42']['placeOfBirth'], d['Q42']['instanceOf']); \
print(d['Q3107329']['author'], d['Q350']['country'])"
```
Expected: `Douglas Adams Q350 ['Q5']` and `Q42 Q145`. (If `placeOfBirth`/`country` are null or `instanceOf` is empty for these, the real claims weren't extracted — investigate before continuing, since Task 2/4 tests assert these.)

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml scripts/build_wikidata_snapshot.py drummer/api/mock/wikidata_snapshot.json
git commit -m "feat(mock): add graphql-core dep + real Wikidata snapshot + builder script

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Mock GraphQL execution module

**Files:**
- Create: `drummer/api/mock/wikidata.py`
- Test: `tests/unit/test_wikidata_mock.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_wikidata_mock.py`:

```python
from drummer.api.mock import wikidata


def test_entity_returns_real_scalar_fields() -> None:
    result = wikidata.execute('{ entity(id: "Q42") { id label instanceOf { label } } }')
    assert "errors" not in result
    entity = result["data"]["entity"]
    assert entity["id"] == "Q42"
    assert entity["label"] == "Douglas Adams"
    assert {t["label"] for t in entity["instanceOf"]} == {"human"}


def test_nested_relation_resolves_end_to_end() -> None:
    query = (
        "query($id: ID!) { entity(id: $id) { label "
        "author { label placeOfBirth { label country { label } } } } }"
    )
    result = wikidata.execute(query, {"id": "Q3107329"})
    assert "errors" not in result
    entity = result["data"]["entity"]
    assert entity["author"]["label"] == "Douglas Adams"
    assert entity["author"]["placeOfBirth"]["label"] == "Cambridge"
    assert entity["author"]["placeOfBirth"]["country"]["label"] == "United Kingdom"


def test_search_matches_label_substring() -> None:
    result = wikidata.execute('{ search(term: "adams") { id } }')
    ids = {e["id"] for e in result["data"]["search"]}
    assert "Q42" in ids


def test_unknown_entity_returns_null() -> None:
    result = wikidata.execute('{ entity(id: "Q0") { label } }')
    assert result["data"]["entity"] is None


def test_malformed_query_returns_errors() -> None:
    result = wikidata.execute("{ entity { label } }")  # missing required id arg
    assert "errors" in result
    assert result["data"] is None


def test_introspection_returns_schema() -> None:
    result = wikidata.execute("{ __schema { queryType { name } } }")
    assert result["data"]["__schema"]["queryType"]["name"] == "Query"


def test_snapshot_has_no_dangling_relation_refs() -> None:
    index = wikidata._INDEX  # noqa: SLF001
    list_fields = ("instanceOf", "notableWork")
    single_fields = ("author", "placeOfBirth", "country")
    for entity in index.values():
        for field in list_fields:
            for ref in entity.get(field, []):
                assert ref in index, f"{entity['id']}.{field} -> missing {ref}"
        for field in single_fields:
            ref = entity.get(field)
            assert ref is None or ref in index, f"{entity['id']}.{field} -> missing {ref}"
```

Note: `test_snapshot_has_no_dangling_relation_refs` reads the module-private `_INDEX`; the `# noqa: SLF001` is permitted here because the test file already enjoys broad per-file ignores, but prefer adding nothing — `tests/**` ignores `SLF001`? It does NOT by default. If ruff flags SLF001, expose a module-level `INDEX` constant (public) in `wikidata.py` instead and use that, rather than a suppression. (See Step 3.)

- [ ] **Step 2: Run, verify FAIL**

Run: `venv/bin/pytest tests/unit/test_wikidata_mock.py -v`
Expected: import error / fail — `drummer.api.mock.wikidata` doesn't exist yet.

- [ ] **Step 3: Implement `drummer/api/mock/wikidata.py`**

```python
import json
from pathlib import Path
from typing import Any

from graphql import GraphQLResolveInfo, build_schema, graphql_sync

_SNAPSHOT_PATH = Path(__file__).parent / "wikidata_snapshot.json"
_raw: Any = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))
INDEX: dict[str, dict[str, Any]] = {qid: entity for qid, entity in _raw.items()}

_SDL = '''
type Query {
  "Look up a single entity by its Wikidata Q-id."
  entity(id: ID!): Entity
  "Case-insensitive substring search over label and description."
  search(term: String!): [Entity!]!
}

type Entity {
  "The Wikidata Q-id, e.g. \\"Q42\\"."
  id: ID!
  "English label (rdfs:label)."
  label: String!
  "English description (schema:description)."
  description: String
  "instance of (P31)"
  instanceOf: [Entity!]!
  "author (P50)"
  author: Entity
  "place of birth (P19)"
  placeOfBirth: Entity
  "country (P17)"
  country: Entity
  "publication date (P577)"
  publicationDate: String
  "notable work (P800)"
  notableWork: [Entity!]
}
'''

_schema = build_schema(_SDL)

_LIST_RELATIONS = ("instanceOf", "notableWork")
_SINGLE_RELATIONS = ("author", "placeOfBirth", "country")


def _resolve_entity(_root: Any, _info: GraphQLResolveInfo, **args: Any) -> dict[str, Any] | None:
    return INDEX.get(args["id"])


def _resolve_search(_root: Any, _info: GraphQLResolveInfo, **args: Any) -> list[dict[str, Any]]:
    term = args["term"].lower()
    return [
        e
        for e in INDEX.values()
        if term in e["label"].lower() or term in (e.get("description") or "").lower()
    ]


def _make_list_resolver(field: str) -> Any:
    def resolve(source: dict[str, Any], _info: GraphQLResolveInfo) -> list[dict[str, Any]]:
        return [INDEX[ref] for ref in source.get(field, [])]

    return resolve


def _make_single_resolver(field: str) -> Any:
    def resolve(source: dict[str, Any], _info: GraphQLResolveInfo) -> dict[str, Any] | None:
        ref = source.get(field)
        return INDEX[ref] if ref is not None else None

    return resolve


_query_type = _schema.query_type
assert _query_type is not None  # noqa: S101 -- schema is built from a literal SDL with a Query type
_query_type.fields["entity"].resolve = _resolve_entity
_query_type.fields["search"].resolve = _resolve_search

_entity_type: Any = _schema.type_map["Entity"]
for _field in _LIST_RELATIONS:
    _entity_type.fields[_field].resolve = _make_list_resolver(_field)
for _field in _SINGLE_RELATIONS:
    _entity_type.fields[_field].resolve = _make_single_resolver(_field)


def execute(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    result = graphql_sync(_schema, query, variable_values=variables or {})
    out: dict[str, Any] = {"data": result.data}
    if result.errors:
        out["errors"] = [error.formatted for error in result.errors]
    return out
```

Notes:
- The test uses `wikidata._INDEX`; this module exposes it as **`INDEX`** (public). Update the test in Step 1 to reference `wikidata.INDEX` and drop the `# noqa` — no suppression needed. (Adjust the test before running Step 4.)
- The single `assert _query_type is not None` carries an inline `# noqa: S101` because `assert` is flagged by ruff outside tests; alternatively raise: `if _query_type is None: raise RuntimeError(...)`. **Prefer the explicit raise to avoid any suppression** — replace the two asserted lines with:
  ```python
  _query_type = _schema.query_type
  if _query_type is None:  # pragma: no cover - SDL always defines Query
      raise RuntimeError("schema missing Query type")
  ```
  Do not use `# noqa`. (`# pragma: no cover` is a coverage hint, not a lint/type suppression, and is acceptable.)

- [ ] **Step 4: Fix the test's INDEX reference, run, verify PASS**

Edit `test_snapshot_has_no_dangling_relation_refs` to use `wikidata.INDEX` (not `_INDEX`, no `# noqa`). Then:
Run: `venv/bin/pytest tests/unit/test_wikidata_mock.py -v`
Expected: all 7 tests pass.

- [ ] **Step 5: Lint/type check the new files**

Run: `venv/bin/ruff check drummer/api/mock/wikidata.py tests/unit/test_wikidata_mock.py && venv/bin/pyright drummer`
Expected: clean. Fix any issue at the root (no `# noqa`/`# type: ignore`).

- [ ] **Step 6: Commit**

```bash
git add drummer/api/mock/wikidata.py tests/unit/test_wikidata_mock.py
git commit -m "feat(mock): graphql-core executable schema over the Wikidata snapshot

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Mock GraphQL route

**Files:**
- Modify: `drummer/api/routes/mock.py`
- Modify: `drummer/api/app.py`
- Test: `tests/integration/test_wikidata_route.py`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_wikidata_route.py`:

```python
from http import HTTPStatus
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from drummer.api.app import create_app
from drummer.api.db.session import init_db


def _db_url(tmp_path: Path) -> str:
    return f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"


@pytest.mark.asyncio
async def test_wikidata_graphql_returns_data(tmp_path: Path) -> None:
    db_url = _db_url(tmp_path)
    app = create_app(db_url=db_url)
    await init_db(db_url)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/mock/wikidata/graphql",
            json={"query": '{ entity(id: "Q42") { label } }'},
        )
    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["data"]["entity"]["label"] == "Douglas Adams"


@pytest.mark.asyncio
async def test_wikidata_graphql_variables(tmp_path: Path) -> None:
    db_url = _db_url(tmp_path)
    app = create_app(db_url=db_url)
    await init_db(db_url)
    query = "query($id: ID!) { entity(id: $id) { author { label } } }"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/mock/wikidata/graphql",
            json={"query": query, "variables": {"id": "Q3107329"}},
        )
    assert resp.json()["data"]["entity"]["author"]["label"] == "Douglas Adams"
```

- [ ] **Step 2: Run, verify FAIL**

Run: `venv/bin/pytest tests/integration/test_wikidata_route.py -v`
Expected: 404 (route not registered yet).

- [ ] **Step 3: Add the route in `drummer/api/routes/mock.py`**

Add imports at the top (alongside the existing imports):
```python
from pydantic import BaseModel, Field

from drummer.api.mock.wikidata import execute as execute_wikidata
```
At the end of the file, add a second router:
```python
wikidata_router = APIRouter(prefix="/mock/wikidata", tags=["mock"])


class GraphQLQuery(BaseModel):
    query: str
    variables: dict[str, Any] = Field(default_factory=dict)


@wikidata_router.post("/graphql")
def wikidata_graphql_route(body: GraphQLQuery) -> JSONResponse:
    return JSONResponse(execute_wikidata(body.query, body.variables))
```
(`Any` is already imported in mock.py.)

- [ ] **Step 4: Register it in `drummer/api/app.py`**

After the existing `app.include_router(mock_routes.router)` line, add:
```python
    app.include_router(mock_routes.wikidata_router)
```

- [ ] **Step 5: Run, verify PASS**

Run: `venv/bin/pytest tests/integration/test_wikidata_route.py -v`
Expected: both tests pass.

- [ ] **Step 6: Commit**

```bash
git add drummer/api/routes/mock.py drummer/api/app.py tests/integration/test_wikidata_route.py
git commit -m "feat(api): POST /mock/wikidata/graphql endpoint

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Tutorial GraphQL steps

**Files:**
- Modify: `drummer/api/routes/tutorial.py`
- Test: `tests/integration/test_tutorial_route.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/integration/test_tutorial_route.py`:

```python
@pytest.mark.asyncio
async def test_list_steps_includes_graphql_steps(tmp_path: Path) -> None:
    app = _make_tutorial_app(tmp_path)
    await init_db(_db_url(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/tutorial/steps")
    steps = response.json()
    assert len(steps) == 10
    graphql_steps = [s for s in steps if s["graphql"] is not None]
    assert len(graphql_steps) == 3
    assert graphql_steps[0]["method"] == "POST"
    assert "entity" in graphql_steps[0]["graphql"]["query"]


@pytest.mark.asyncio
async def test_graphql_step_sends_and_returns_data(tmp_path: Path) -> None:
    app = _make_tutorial_app(tmp_path)
    await init_db(_db_url(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/tutorial/steps/7/send")
    assert response.status_code == HTTPStatus.OK
    events = parse_sse(response.text)
    body_event = next(e for e in events if e["event"] == "body")
    assert "Douglas Adams" in body_event["data"]["body"]  # type: ignore[index]
```

Note: step index 7 is the first GraphQL step (0–6 are the existing REST steps). Its query targets `Q42` (Douglas Adams). Update the index if the first GraphQL step lands elsewhere.

The existing `test_list_steps_returns_all_steps` asserts `len(steps) == 7`; change that assertion to `== 10` (there are now 10 steps), keeping its other field assertions.

- [ ] **Step 2: Run, verify FAIL**

Run: `venv/bin/pytest tests/integration/test_tutorial_route.py -v`
Expected: failures — `graphql` key missing / only 7 steps / step 7 not found.

- [ ] **Step 3: Add `graphql` to the tutorial model + pass-through**

In `drummer/api/routes/tutorial.py`:
1. Add to the imports from formats: `GraphQLConfig` (i.e. `from drummer.core.storage.formats import GraphQLConfig, HttpMethod, RequestFile, RequestFrontmatter`).
2. Add a field to `TutorialStep` (after `post_script`):
   ```python
       graphql: GraphQLConfig | None = None
   ```
3. In `_step_to_request_file`, pass it into `RequestFrontmatter(...)`:
   ```python
       fm = RequestFrontmatter(
           name=step.title,
           method=step.method,
           url=step.url,
           params=step.params,
           headers=step.headers,
           pre_script=step.pre_script,
           post_script=step.post_script,
           graphql=step.graphql,
       )
   ```

- [ ] **Step 4: Append the 3 GraphQL steps to `STEPS`**

Add these three `TutorialStep(...)` entries at the end of the `STEPS` list (use `GraphQLConfig` already imported):

```python
    TutorialStep(
        title="Your first GraphQL query",
        instructions=(
            "GraphQL uses a single endpoint and a query that names exactly the fields "
            "you want back.\n\n"
            "This queries Drummer's built-in mock of real Wikidata data. It fetches entity "
            "Q42 (Douglas Adams) and asks for its label, description, and what it is an "
            "instance of.\n\n"
            "The query lives in the Body tab (GraphQL mode). Click Send to run it."
        ),
        method="POST",
        url="http://localhost:8000/mock/wikidata/graphql",
        graphql=GraphQLConfig(
            query=(
                "{\n"
                '  entity(id: "Q42") {\n'
                "    label\n"
                "    description\n"
                "    instanceOf { label }\n"
                "  }\n"
                "}"
            )
        ),
    ),
    TutorialStep(
        title="Nested selection and variables",
        instructions=(
            "GraphQL's strength is following relations in one request. This query starts "
            "from a book and walks to its author, then the author's place of birth, then "
            "that place's country.\n\n"
            "It also uses a GraphQL operation variable, $id, supplied in the Variables "
            "sub-tab — distinct from Drummer's environment variables. Here $id is "
            '"Q3107329" (The Hitchhiker\'s Guide to the Galaxy).\n\n'
            "Click Send, then try changing $id to another entity."
        ),
        method="POST",
        url="http://localhost:8000/mock/wikidata/graphql",
        graphql=GraphQLConfig(
            query=(
                "query ($id: ID!) {\n"
                "  entity(id: $id) {\n"
                "    label\n"
                "    author {\n"
                "      label\n"
                "      placeOfBirth { label country { label } }\n"
                "    }\n"
                "  }\n"
                "}"
            ),
            variables={"id": "Q3107329"},
        ),
    ),
    TutorialStep(
        title="Explore the schema",
        instructions=(
            "Because the mock supports GraphQL introspection, Drummer can show you the "
            "schema. Open the Body tab's Schema sub-tab to browse the Query and Entity "
            "types and their fields — autocomplete in the query editor is driven by the "
            "same introspection.\n\n"
            "This query lists a few entities via search. Click Send to run it, and explore "
            "the Schema sub-tab."
        ),
        method="POST",
        url="http://localhost:8000/mock/wikidata/graphql",
        graphql=GraphQLConfig(
            query=(
                "{\n"
                '  search(term: "novel") {\n'
                "    id\n"
                "    label\n"
                "  }\n"
                "}"
            )
        ),
    ),
```

- [ ] **Step 5: Run, verify PASS**

Run: `venv/bin/pytest tests/integration/test_tutorial_route.py -v`
Expected: all tutorial route tests pass (including the updated `== 10` and the two new tests). If `test_graphql_step_sends_and_returns_data` fails because step 7 isn't the first GraphQL step, confirm the REST steps still number 0–6 and adjust the index.

- [ ] **Step 6: Commit**

```bash
git add drummer/api/routes/tutorial.py tests/integration/test_tutorial_route.py
git commit -m "feat(api): 3 GraphQL tutorial steps over the Wikidata mock

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Frontend — carry `graphql` into the tutorial request pane

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/tutorial.ts`
- Test: `frontend/src/api/tutorial.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/api/tutorial.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { stepToRequestDetail } from "./tutorial";
import type { TutorialStep } from "../types";

const baseStep: TutorialStep = {
  title: "GraphQL step",
  instructions: "",
  method: "POST",
  url: "http://localhost:8000/mock/wikidata/graphql",
  params: {},
  headers: {},
  body: "",
  pre_script: "",
  post_script: "",
  variable_overrides: {},
  graphql: { query: "{ entity(id: \"Q42\") { label } }", variables: {} },
};

describe("stepToRequestDetail", () => {
  it("carries the graphql config into the frontmatter", () => {
    const detail = stepToRequestDetail(baseStep);
    expect(detail.frontmatter.graphql).toEqual(baseStep.graphql);
    expect(detail.frontmatter.method).toBe("POST");
  });

  it("leaves graphql undefined when the step has none", () => {
    const detail = stepToRequestDetail({ ...baseStep, graphql: undefined });
    expect(detail.frontmatter.graphql).toBeUndefined();
  });
});
```

- [ ] **Step 2: Add `graphql` to the `TutorialStep` type**

In `frontend/src/types.ts`, add to the `TutorialStep` interface (after `variable_overrides`):
```ts
  graphql?: GraphQLConfig | null;
```
`GraphQLConfig` is already defined and exported in this file (Phase 8) — no new import.

- [ ] **Step 3: Run, verify FAIL**

Run: `cd frontend && npm run test -- --run tutorial.test`
Expected: FAIL — `stepToRequestDetail` doesn't set `frontmatter.graphql` yet.

- [ ] **Step 4: Pass `graphql` through in `stepToRequestDetail`**

In `frontend/src/api/tutorial.ts`, inside the `frontmatter` object returned by `stepToRequestDetail`, add (e.g. after `post_script: step.post_script,`):
```ts
      graphql: step.graphql ?? undefined,
```

- [ ] **Step 5: Run, verify PASS + full check**

Run: `cd frontend && npm run test -- --run tutorial.test && npm run check`
Expected: both new tests pass; biome + tsc clean. (`RequestFrontmatter.graphql` is `GraphQLConfig | undefined` in TS, so `?? undefined` type-checks.)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/tutorial.ts frontend/src/api/tutorial.test.ts
git commit -m "feat(frontend): carry tutorial step graphql config into the request pane

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Attribution + docs

**Files:**
- Modify: `drummer/cli.py`
- Modify: the CLI attribution test (find it under `tests/`)
- Modify: `ROADMAP.md`, `CLAUDE.md`, `README.md`

- [ ] **Step 1: Locate the attribution test**

Run: `grep -rl "attribution\|Metropolitan\|CC0" tests/`
Note the file/test that asserts `--attribution` output (likely `tests/integration/` or `tests/unit/`). Read it to match its invocation style (typer `CliRunner`).

- [ ] **Step 2: Extend the attribution assertion (failing)**

In that test, add an assertion that the `--attribution` output contains `"Wikidata"` (and `"wikidata.org"`). Run it and confirm it FAILS.

Run: `venv/bin/pytest <that test file> -v`
Expected: FAIL (Wikidata not yet in the output).

- [ ] **Step 3: Extend `_ATTRIBUTION` in `drummer/cli.py`**

Replace the `_ATTRIBUTION` string with one that keeps the Met block and appends a Wikidata block:

```python
_ATTRIBUTION = (
    "Drummer includes data from the Metropolitan Museum of Art Open Access collection.\n"
    "License: Creative Commons Zero (CC0)\n"
    "Source: https://www.metmuseum.org/about-the-met/policies-and-documents/open-access\n"
    "The Met makes its Open Access data available for unrestricted use.\n"
    "\n"
    "Drummer includes a snapshot of data from Wikidata.\n"
    "License: Creative Commons Zero (CC0)\n"
    "Source: https://www.wikidata.org\n"
    "Wikidata data is dedicated to the public domain."
)
```

- [ ] **Step 4: Run, verify PASS**

Run: `venv/bin/pytest <that test file> -v`
Expected: PASS.

- [ ] **Step 5: Update docs**

- `ROADMAP.md`: change the Phase 14 row status to `✅ Done`.
- `CLAUDE.md`: change the current-phase line to `Current phase: **14 — Wikidata GraphQL**`.
- `README.md`: find where the Met mock / tutorial is described and add a sentence that the tutorial also includes a mock GraphQL endpoint backed by a Wikidata snapshot (CC0). If the README has an attribution/credits section, add Wikidata there too. (Read the relevant README section first; keep the edit minimal and consistent with the existing wording.)

- [ ] **Step 6: Commit**

```bash
git add drummer/cli.py <that test file> ROADMAP.md CLAUDE.md README.md
git commit -m "docs: Wikidata attribution + mark Phase 14 done

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Final gate + milestone push

- [ ] **Step 1: Full backend + lint/type gate**

Run: `make check`
Expected: ruff + ruff format + pyright + biome + tsc + pytest all pass. The pytest count grows by the new wikidata/route/tutorial tests.

- [ ] **Step 2: Full frontend test suite**

Run: `cd frontend && npm run test -- --run`
Expected: all vitest suites pass (including the new `tutorial.test.ts`).

- [ ] **Step 3: Manual smoke check (recommended)**

Launch the app, open the Tutorial tab, advance to the GraphQL steps: step 8 shows the query in the Body tab (GraphQL mode); Send streams real Wikidata data into the response pane; step 9's nested query returns Douglas Adams → Cambridge → United Kingdom; the Schema sub-tab populates via introspection. Run `drummer --attribution` and confirm both Met and Wikidata blocks print.

- [ ] **Step 4: Push to main**

```bash
git push origin main
```

---

## Self-Review

**Spec coverage:**
- Mock GraphQL endpoint with real execution + introspection → Tasks 2, 3. ✔
- Real Wikidata data, built once and committed; one-time dev script, no build/runtime fetch → Task 1. ✔
- Real field semantics (camelCase + documented P-id in SDL descriptions) → Task 2 SDL. ✔
- Relational mini-schema (entity/search + relation fields) → Task 2. ✔
- 3-step GraphQL tutorial arc; `TutorialStep.graphql` + pass-through; reuses send pipeline → Task 4. ✔
- Frontend carries graphql into the real GraphQL pane → Task 5. ✔
- Wikidata attribution → Task 6. ✔
- graphql-core dependency → Task 1. ✔
- Tests (execution, integrity, route, tutorial, attribution, frontend) + green gate → Tasks 2–7. ✔
- Docs (ROADMAP done, current phase, README) → Task 6. ✔

**Placeholder scan:** No TBD/TODO; every code step shows complete code. Snapshot *values* are produced by the Task 1 script (real data) rather than hardcoded — intentional; tests assert only stable real facts (Q42=Douglas Adams, Q3107329.author=Q42, Q350.country=Q145).

**Type/name consistency:** `execute(query, variables)` signature consistent across `wikidata.py` (def), the route (`execute_wikidata(body.query, body.variables)`), and unit tests. `INDEX` (public) is the name used by both module and integrity test. `GraphQLConfig` fields (`query`, `variables`) match `formats.py` and the frontend `GraphQLConfig`. `TutorialStep.graphql` is `GraphQLConfig | None` (backend) / `GraphQLConfig | null` (frontend), passed through in both `_step_to_request_file` and `stepToRequestDetail`. Snapshot relation field names (`instanceOf`, `author`, `placeOfBirth`, `country`, `notableWork`, `publicationDate`) match the SDL, the builder script, and the resolver lists.

**Risk note:** Task 1 needs network to reach Wikidata; if `Bash` is sandboxed without network, the task reports BLOCKED and the controller fetches via WebFetch. Q-ids in `QIDS` are best-effort and verified-by-label in Task 1 Step 4 before anything depends on them.
