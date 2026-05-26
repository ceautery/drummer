# Phase 2: Storage Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Drummer storage layer — Pydantic models for YAML-frontmatter request files, parse/write functions, and project/environment loading — so Phase 3 (HTTP engine) has a typed, independently-testable foundation.

**Architecture:** Two focused modules in `drummer/core/storage/`: `formats.py` owns the request-file data model and serialization round-trip using `python-frontmatter`; `project.py` owns project-level structure (metadata YAML, environments, request discovery) using `pyyaml` directly. Both are pure Python with no web-framework dependency, tested entirely with the `tmp_path` pytest fixture.

**Tech Stack:** Python 3.12, Pydantic v2, `python-frontmatter` (YAML frontmatter parsing), `pyyaml` (project/environment YAML), `pytest` + `tmp_path`.

---

### File Map

| Action | Path | Responsibility |
|--------|------|---------------|
| Create | `drummer/core/storage/__init__.py` | Package marker |
| Create | `drummer/core/storage/formats.py` | Enums, Pydantic models, `parse_request_file`, `write_request_file` |
| Create | `drummer/core/storage/project.py` | `ProjectMeta`, `Environment`, project/env/request functions |
| Create | `tests/unit/test_formats.py` | Unit tests for formats module |
| Create | `tests/unit/test_project.py` | Unit tests for project module |
| Modify | `pyproject.toml` | Add `pyyaml>=6` dependency (Task 4) |

---

### Task 1: Package marker and request-file Pydantic models

**Files:**
- Create: `drummer/core/storage/__init__.py`
- Create: `drummer/core/storage/formats.py`
- Create: `tests/unit/test_formats.py`

- [ ] **Step 1: Create the storage package marker**

Create `drummer/core/storage/__init__.py` as an empty file. This marks the directory as a Python package.

- [ ] **Step 2: Write failing tests for the Pydantic models**

Create `tests/unit/test_formats.py`:

```python
from pathlib import Path

import pytest
from pydantic import ValidationError

from drummer.core.storage.formats import (
    AuthConfig,
    AuthType,
    CookieConfig,
    CookieMode,
    GraphQLConfig,
    RequestFile,
    RequestFrontmatter,
)


def test_request_frontmatter_defaults() -> None:
    fm = RequestFrontmatter(name="test")
    assert fm.method == "GET"
    assert fm.url == ""
    assert fm.headers == {}
    assert fm.params == {}
    assert fm.encoding == "utf-8"
    assert fm.cookies.mode == CookieMode.SESSION
    assert fm.auth.type == AuthType.NONE
    assert fm.graphql is None
    assert fm.pre_script == ""
    assert fm.post_script == ""
    assert fm.tags == []
    assert fm.skip is False


def test_cookie_mode_string_values() -> None:
    assert CookieMode.SESSION == "session"
    assert CookieMode.DISABLED == "disabled"
    assert CookieMode.EXPLICIT == "explicit"


def test_auth_type_string_values() -> None:
    assert AuthType.NONE == "none"
    assert AuthType.BEARER == "bearer"
    assert AuthType.BASIC == "basic"
    assert AuthType.API_KEY == "api_key"


def test_request_frontmatter_all_fields() -> None:
    fm = RequestFrontmatter(
        name="List Users",
        method="POST",
        url="{{base_url}}/api/users",
        headers={"Authorization": "Bearer {{token}}"},
        params={"page": "1"},
        cookies=CookieConfig(mode=CookieMode.EXPLICIT),
        auth=AuthConfig(type=AuthType.BEARER, token="{{token}}"),
        tags=["users", "list"],
        skip=True,
    )
    assert fm.method == "POST"
    assert fm.cookies.mode == CookieMode.EXPLICIT
    assert fm.auth.type == AuthType.BEARER
    assert fm.auth.token == "{{token}}"
    assert fm.skip is True


def test_request_frontmatter_invalid_method() -> None:
    with pytest.raises(ValidationError):
        RequestFrontmatter.model_validate({"name": "test", "method": "INVALID"})


def test_graphql_config_defaults() -> None:
    gql = GraphQLConfig()
    assert gql.query == ""
    assert gql.variables == {}


def test_request_file_fields(tmp_path: Path) -> None:
    req_file = tmp_path / "request.md"
    fm = RequestFrontmatter(name="test")
    rf = RequestFile(frontmatter=fm, body="body text", path=req_file)
    assert rf.path == req_file
    assert rf.body == "body text"
    assert rf.frontmatter.name == "test"
```

- [ ] **Step 3: Run test to confirm it fails**

```bash
source venv/bin/activate && pytest tests/unit/test_formats.py -v
```

Expected: `ModuleNotFoundError: No module named 'drummer.core.storage.formats'`

- [ ] **Step 4: Implement formats.py**

Create `drummer/core/storage/formats.py`:

```python
from enum import StrEnum
from pathlib import Path
from typing import Literal

import frontmatter
from pydantic import BaseModel, Field

HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"]


class CookieMode(StrEnum):
    SESSION = "session"
    DISABLED = "disabled"
    EXPLICIT = "explicit"


class AuthType(StrEnum):
    NONE = "none"
    BEARER = "bearer"
    BASIC = "basic"
    API_KEY = "api_key"


class CookieConfig(BaseModel):
    mode: CookieMode = CookieMode.SESSION


class AuthConfig(BaseModel):
    type: AuthType = AuthType.NONE
    token: str = ""
    username: str = ""
    password: str = ""
    key: str = ""
    value: str = ""


class GraphQLConfig(BaseModel):
    query: str = ""
    variables: dict[str, str] = Field(default_factory=dict)


class RequestFrontmatter(BaseModel):
    name: str
    method: HttpMethod = "GET"
    url: str = ""
    headers: dict[str, str] = Field(default_factory=dict)
    params: dict[str, str] = Field(default_factory=dict)
    encoding: str = "utf-8"
    cookies: CookieConfig = Field(default_factory=CookieConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    graphql: GraphQLConfig | None = None
    pre_script: str = ""
    post_script: str = ""
    tags: list[str] = Field(default_factory=list)
    skip: bool = False


class RequestFile(BaseModel):
    frontmatter: RequestFrontmatter
    body: str
    path: Path
```

- [ ] **Step 5: Run test to confirm it passes**

```bash
source venv/bin/activate && pytest tests/unit/test_formats.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add drummer/core/storage/__init__.py drummer/core/storage/formats.py tests/unit/test_formats.py
git commit -m "feat: add storage package and request-file Pydantic models"
```

---

### Task 2: parse_request_file

**Files:**
- Modify: `drummer/core/storage/formats.py` (add function)
- Modify: `tests/unit/test_formats.py` (add tests)

- [ ] **Step 1: Write failing tests for parse_request_file**

Append to `tests/unit/test_formats.py`:

```python
from drummer.core.storage.formats import parse_request_file


def test_parse_request_file_minimal(tmp_path: Path) -> None:
    req_file = tmp_path / "request.md"
    req_file.write_text(
        "---\nname: Test Request\n---\n\nRequest body here.\n",
        encoding="utf-8",
    )
    result = parse_request_file(req_file)
    assert result.frontmatter.name == "Test Request"
    assert result.frontmatter.method == "GET"
    assert result.body.strip() == "Request body here."
    assert result.path == req_file


def test_parse_request_file_full(tmp_path: Path) -> None:
    content = """\
---
name: List Users
method: GET
url: "{{base_url}}/api/users"
headers:
  Authorization: "Bearer {{token}}"
params:
  page: "1"
tags: [users, list]
---

Fetches paginated users.
"""
    req_file = tmp_path / "users.md"
    req_file.write_text(content, encoding="utf-8")
    result = parse_request_file(req_file)
    assert result.frontmatter.name == "List Users"
    assert result.frontmatter.method == "GET"
    assert result.frontmatter.url == "{{base_url}}/api/users"
    assert result.frontmatter.headers == {"Authorization": "Bearer {{token}}"}
    assert result.frontmatter.params == {"page": "1"}
    assert result.frontmatter.tags == ["users", "list"]
    assert "Fetches paginated users" in result.body


def test_parse_request_file_missing_name_raises(tmp_path: Path) -> None:
    req_file = tmp_path / "request.md"
    req_file.write_text("---\nmethod: GET\n---\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        parse_request_file(req_file)


def test_parse_request_file_with_graphql(tmp_path: Path) -> None:
    content = """\
---
name: Get User
method: POST
url: "{{base_url}}/graphql"
graphql:
  query: |
    query GetUser($id: ID!) {
      user(id: $id) { name email }
    }
  variables:
    id: "{{user_id}}"
---
"""
    req_file = tmp_path / "get-user.md"
    req_file.write_text(content, encoding="utf-8")
    result = parse_request_file(req_file)
    assert result.frontmatter.graphql is not None
    assert "GetUser" in result.frontmatter.graphql.query
    assert result.frontmatter.graphql.variables == {"id": "{{user_id}}"}
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
source venv/bin/activate && pytest tests/unit/test_formats.py -k "parse" -v
```

Expected: `ImportError` (function not defined yet).

- [ ] **Step 3: Implement parse_request_file**

Add to the bottom of `drummer/core/storage/formats.py`:

```python
def parse_request_file(path: Path) -> "RequestFile":
    with path.open("r", encoding="utf-8") as f:
        post = frontmatter.load(f)
    fm = RequestFrontmatter.model_validate(post.metadata)
    return RequestFile(frontmatter=fm, body=post.content, path=path)
```

Note: the return type annotation uses the name `RequestFile` which is already defined above it in the same file — the string form avoids any forward-reference issues.

Actually, since `RequestFile` is defined before this function in the file, the annotation does NOT need quotes. Write it without quotes:

```python
def parse_request_file(path: Path) -> RequestFile:
    with path.open("r", encoding="utf-8") as f:
        post = frontmatter.load(f)
    fm = RequestFrontmatter.model_validate(post.metadata)
    return RequestFile(frontmatter=fm, body=post.content, path=path)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
source venv/bin/activate && pytest tests/unit/test_formats.py -k "parse" -v
```

Expected: All 4 parse tests PASS.

- [ ] **Step 5: Commit**

```bash
git add drummer/core/storage/formats.py tests/unit/test_formats.py
git commit -m "feat: implement parse_request_file"
```

---

### Task 3: write_request_file and round-trip

**Files:**
- Modify: `drummer/core/storage/formats.py` (add function)
- Modify: `tests/unit/test_formats.py` (add tests)

- [ ] **Step 1: Write failing tests for write_request_file**

Append to `tests/unit/test_formats.py`:

```python
from drummer.core.storage.formats import write_request_file


def test_write_request_file_creates_file(tmp_path: Path) -> None:
    req_file = tmp_path / "request.md"
    fm = RequestFrontmatter(name="Test", url="https://example.com")
    request = RequestFile(frontmatter=fm, body="Test body.", path=req_file)
    write_request_file(request)
    assert req_file.exists()
    text = req_file.read_text(encoding="utf-8")
    assert "name: Test" in text
    assert "Test body." in text


def test_write_request_file_omits_defaults(tmp_path: Path) -> None:
    req_file = tmp_path / "request.md"
    fm = RequestFrontmatter(name="Simple")
    request = RequestFile(frontmatter=fm, body="", path=req_file)
    write_request_file(request)
    text = req_file.read_text(encoding="utf-8")
    assert "method:" not in text   # "GET" is default — omitted
    assert "encoding:" not in text  # "utf-8" is default — omitted
    assert "skip:" not in text      # False is default — omitted


def test_write_request_file_roundtrip(tmp_path: Path) -> None:
    req_file = tmp_path / "request.md"
    fm = RequestFrontmatter(
        name="Round Trip",
        method="POST",
        url="https://example.com/api",
        headers={"Content-Type": "application/json"},
        tags=["test", "roundtrip"],
    )
    original = RequestFile(frontmatter=fm, body="Some notes.", path=req_file)
    write_request_file(original)
    loaded = parse_request_file(req_file)
    assert loaded.frontmatter.name == "Round Trip"
    assert loaded.frontmatter.method == "POST"
    assert loaded.frontmatter.url == "https://example.com/api"
    assert loaded.frontmatter.headers == {"Content-Type": "application/json"}
    assert loaded.frontmatter.tags == ["test", "roundtrip"]
    assert "Some notes." in loaded.body


def test_write_request_file_roundtrip_with_auth(tmp_path: Path) -> None:
    req_file = tmp_path / "request.md"
    fm = RequestFrontmatter(
        name="Auth Request",
        url="https://api.example.com/data",
        auth=AuthConfig(type=AuthType.BEARER, token="{{token}}"),
        cookies=CookieConfig(mode=CookieMode.DISABLED),
    )
    original = RequestFile(frontmatter=fm, body="", path=req_file)
    write_request_file(original)
    loaded = parse_request_file(req_file)
    assert loaded.frontmatter.auth.type == AuthType.BEARER
    assert loaded.frontmatter.auth.token == "{{token}}"
    assert loaded.frontmatter.cookies.mode == CookieMode.DISABLED
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
source venv/bin/activate && pytest tests/unit/test_formats.py -k "write" -v
```

Expected: `ImportError` (function not defined yet).

- [ ] **Step 3: Implement write_request_file**

Add to the bottom of `drummer/core/storage/formats.py`:

```python
def write_request_file(request: RequestFile) -> None:
    fm_dict = request.frontmatter.model_dump(
        exclude_defaults=True,
        exclude_none=True,
        mode="json",
    )
    post = frontmatter.Post(request.body, **fm_dict)
    request.path.write_text(frontmatter.dumps(post), encoding="utf-8")
```

`model_dump(exclude_defaults=True, exclude_none=True, mode="json")` produces a dict with only non-default, non-None values. Nested Pydantic models (`CookieConfig`, `AuthConfig`, `GraphQLConfig`) become nested dicts. `frontmatter.Post(body, **dict)` sets that dict as the YAML frontmatter metadata. `frontmatter.dumps(post)` serializes to the `---\n...\n---\nbody` format.

- [ ] **Step 4: Run all formats tests**

```bash
source venv/bin/activate && pytest tests/unit/test_formats.py -v
```

Expected: All tests PASS (7 model tests + 4 parse tests + 4 write tests = 15 total).

- [ ] **Step 5: Commit**

```bash
git add drummer/core/storage/formats.py tests/unit/test_formats.py
git commit -m "feat: implement write_request_file with round-trip serialization"
```

---

### Task 4: pyyaml dependency + ProjectMeta + project load/save/create

**Files:**
- Modify: `pyproject.toml` (add pyyaml)
- Create: `drummer/core/storage/project.py`
- Create: `tests/unit/test_project.py`

- [ ] **Step 1: Add pyyaml to pyproject.toml**

In `pyproject.toml`, add `pyyaml>=6` to the `dependencies` list (after `chardet`):

```toml
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "httpx>=0.27",
    "quickjs>=1.19",
    "python-frontmatter>=1.1",
    "pydantic>=2.7",
    "aiosqlite>=0.20",
    "sqlalchemy>=2.0",
    "fastapi-mcp>=0.3",
    "chardet>=5.2",
    "pyyaml>=6",
    "typer>=0.12",
]
```

Then reinstall so the package is tracked:

```bash
source venv/bin/activate && pip install -e ".[dev]" -q
```

- [ ] **Step 2: Write failing tests for ProjectMeta + project functions**

Create `tests/unit/test_project.py`:

```python
from pathlib import Path

import pytest

from drummer.core.storage.project import (
    ProjectMeta,
    create_project,
    load_project,
    save_project,
)


def test_create_project_creates_files(tmp_path: Path) -> None:
    meta = create_project(tmp_path, "My API")
    assert meta.name == "My API"
    assert meta.version == "1"
    assert meta.default_environment == "local"
    assert (tmp_path / ".drummer" / "project.yaml").exists()
    assert (tmp_path / ".drummer" / "environments" / "local.yaml").exists()


def test_load_project_roundtrip(tmp_path: Path) -> None:
    create_project(tmp_path, "My API")
    meta = load_project(tmp_path)
    assert meta.name == "My API"
    assert meta.default_environment == "local"


def test_save_project_updates_yaml(tmp_path: Path) -> None:
    create_project(tmp_path, "Original")
    meta = ProjectMeta(name="Updated", default_environment="staging")
    save_project(meta, tmp_path)
    loaded = load_project(tmp_path)
    assert loaded.name == "Updated"
    assert loaded.default_environment == "staging"


def test_project_meta_defaults() -> None:
    meta = ProjectMeta(name="Test")
    assert meta.version == "1"
    assert meta.default_environment == "local"


def test_create_project_missing_name_raises() -> None:
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ProjectMeta.model_validate({"version": "1"})
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
source venv/bin/activate && pytest tests/unit/test_project.py -v
```

Expected: `ModuleNotFoundError: No module named 'drummer.core.storage.project'`

- [ ] **Step 4: Implement project.py with ProjectMeta + project functions**

Create `drummer/core/storage/project.py`:

```python
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError

from drummer.core.storage.formats import parse_request_file


class ProjectMeta(BaseModel):
    name: str
    version: str = "1"
    default_environment: str = "local"


class Environment(BaseModel):
    name: str
    variables: dict[str, str] = Field(default_factory=dict)


def load_project(project_dir: Path) -> ProjectMeta:
    config_path = project_dir / ".drummer" / "project.yaml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return ProjectMeta.model_validate(data)


def save_project(meta: ProjectMeta, project_dir: Path) -> None:
    config_path = project_dir / ".drummer" / "project.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.dump(
            meta.model_dump(mode="json"),
            default_flow_style=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def create_project(project_dir: Path, name: str) -> ProjectMeta:
    meta = ProjectMeta(name=name)
    save_project(meta, project_dir)
    env_dir = project_dir / ".drummer" / "environments"
    env_dir.mkdir(parents=True, exist_ok=True)
    save_environment(Environment(name="local"), project_dir)
    return meta


def load_environment(path: Path) -> Environment:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Environment.model_validate(data)


def save_environment(env: Environment, project_dir: Path) -> None:
    env_dir = project_dir / ".drummer" / "environments"
    env_dir.mkdir(parents=True, exist_ok=True)
    env_path = env_dir / f"{env.name}.yaml"
    env_path.write_text(
        yaml.dump(
            env.model_dump(mode="json"),
            default_flow_style=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def list_environments(project_dir: Path) -> list[Environment]:
    env_dir = project_dir / ".drummer" / "environments"
    if not env_dir.exists():
        return []
    return [load_environment(path) for path in sorted(env_dir.glob("*.yaml"))]


def list_requests(project_dir: Path) -> list[Path]:
    drummer_dir = (project_dir / ".drummer").resolve()
    result: list[Path] = []
    for path in sorted(project_dir.rglob("*.md")):
        if path.resolve().is_relative_to(drummer_dir):
            continue
        try:
            parse_request_file(path)
        except (ValidationError, OSError, yaml.YAMLError):
            continue
        result.append(path)
    return result
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
source venv/bin/activate && pytest tests/unit/test_project.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml drummer/core/storage/project.py tests/unit/test_project.py
git commit -m "feat: implement ProjectMeta and project load/save/create"
```

---

### Task 5: Environment load/save/list

**Files:**
- Modify: `tests/unit/test_project.py` (add tests; project.py already has the functions)

- [ ] **Step 1: Write failing tests for environment functions**

Append to `tests/unit/test_project.py`:

```python
from drummer.core.storage.project import (
    Environment,
    list_environments,
    load_environment,
    save_environment,
)


def test_environment_defaults() -> None:
    env = Environment(name="local")
    assert env.variables == {}


def test_save_and_load_environment(tmp_path: Path) -> None:
    create_project(tmp_path, "Test")
    env = Environment(
        name="staging",
        variables={"base_url": "https://staging.example.com", "token": "abc123"},
    )
    save_environment(env, tmp_path)
    loaded = load_environment(tmp_path / ".drummer" / "environments" / "staging.yaml")
    assert loaded.name == "staging"
    assert loaded.variables["base_url"] == "https://staging.example.com"
    assert loaded.variables["token"] == "abc123"


def test_list_environments_returns_all(tmp_path: Path) -> None:
    create_project(tmp_path, "Test")  # creates local env
    save_environment(Environment(name="staging", variables={"url": "https://staging.example.com"}), tmp_path)
    save_environment(Environment(name="prod", variables={"url": "https://prod.example.com"}), tmp_path)
    envs = list_environments(tmp_path)
    names = {e.name for e in envs}
    assert names == {"local", "staging", "prod"}


def test_list_environments_empty_dir(tmp_path: Path) -> None:
    (tmp_path / ".drummer" / "environments").mkdir(parents=True)
    envs = list_environments(tmp_path)
    assert envs == []


def test_list_environments_missing_dir(tmp_path: Path) -> None:
    envs = list_environments(tmp_path)
    assert envs == []
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
source venv/bin/activate && pytest tests/unit/test_project.py -k "environment" -v
```

Expected: `ImportError` (the new symbols aren't imported in the test file yet — the functions exist but aren't imported at the top of the test file).

Update the import at the top of `tests/unit/test_project.py` to include the new symbols:

```python
from drummer.core.storage.project import (
    Environment,
    ProjectMeta,
    create_project,
    list_environments,
    load_environment,
    load_project,
    save_environment,
    save_project,
)
```

- [ ] **Step 3: Run tests again**

```bash
source venv/bin/activate && pytest tests/unit/test_project.py -k "environment" -v
```

Expected: All 5 environment tests PASS (the functions were already implemented in Task 4).

- [ ] **Step 4: Run all project tests**

```bash
source venv/bin/activate && pytest tests/unit/test_project.py -v
```

Expected: All 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_project.py
git commit -m "test: add environment load/save/list tests"
```

---

### Task 6: list_requests

**Files:**
- Modify: `tests/unit/test_project.py` (add tests; project.py already has the function)

- [ ] **Step 1: Write failing tests for list_requests**

Append to `tests/unit/test_project.py`:

```python
from drummer.core.storage.project import list_requests


def test_list_requests_finds_valid_files(tmp_path: Path) -> None:
    create_project(tmp_path, "Test")
    (tmp_path / "get-users.md").write_text(
        "---\nname: Get Users\nmethod: GET\nurl: https://api.example.com/users\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "auth" ).mkdir()
    (tmp_path / "auth" / "login.md").write_text(
        "---\nname: Login\nmethod: POST\nurl: https://api.example.com/login\n---\n",
        encoding="utf-8",
    )
    paths = list_requests(tmp_path)
    assert len(paths) == 2
    names = {p.name for p in paths}
    assert names == {"get-users.md", "login.md"}


def test_list_requests_skips_non_request_md(tmp_path: Path) -> None:
    create_project(tmp_path, "Test")
    (tmp_path / "README.md").write_text("# My API\n\nNo frontmatter here.\n", encoding="utf-8")
    (tmp_path / "request.md").write_text(
        "---\nname: Valid Request\nmethod: GET\nurl: https://api.example.com\n---\n",
        encoding="utf-8",
    )
    paths = list_requests(tmp_path)
    assert len(paths) == 1
    assert paths[0].name == "request.md"


def test_list_requests_excludes_drummer_dir(tmp_path: Path) -> None:
    create_project(tmp_path, "Test")
    # Place a structurally valid .md inside .drummer/ — must be excluded
    internal = tmp_path / ".drummer" / "notes.md"
    internal.write_text(
        "---\nname: Internal\nmethod: GET\nurl: https://api.example.com\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "request.md").write_text(
        "---\nname: Real Request\nmethod: GET\nurl: https://api.example.com\n---\n",
        encoding="utf-8",
    )
    paths = list_requests(tmp_path)
    assert len(paths) == 1
    assert paths[0].name == "request.md"


def test_list_requests_empty_project(tmp_path: Path) -> None:
    create_project(tmp_path, "Empty")
    paths = list_requests(tmp_path)
    assert paths == []


def test_list_requests_returns_sorted(tmp_path: Path) -> None:
    create_project(tmp_path, "Test")
    for name in ["c-request.md", "a-request.md", "b-request.md"]:
        (tmp_path / name).write_text(
            f"---\nname: {name}\nmethod: GET\nurl: https://api.example.com\n---\n",
            encoding="utf-8",
        )
    paths = list_requests(tmp_path)
    assert [p.name for p in paths] == ["a-request.md", "b-request.md", "c-request.md"]
```

Also update the imports at the top of `tests/unit/test_project.py` to include `list_requests`:

```python
from drummer.core.storage.project import (
    Environment,
    ProjectMeta,
    create_project,
    list_environments,
    list_requests,
    load_environment,
    load_project,
    save_environment,
    save_project,
)
```

- [ ] **Step 2: Run tests to confirm they fail (import error only)**

```bash
source venv/bin/activate && pytest tests/unit/test_project.py -k "list_requests" -v
```

Expected: Tests fail with `ImportError` until the import is added. Once the import is in place and `list_requests` is called, they should all PASS because `list_requests` was already implemented in Task 4.

- [ ] **Step 3: Run all project tests**

```bash
source venv/bin/activate && pytest tests/unit/test_project.py -v
```

Expected: All 15 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/unit/test_project.py
git commit -m "test: add list_requests tests"
```

---

### Task 7: Final make check and cleanup

**Files:**
- No new files — verification only.

- [ ] **Step 1: Run the full check suite**

```bash
source venv/bin/activate && make check
```

This runs `ruff check .`, `ruff format --check .`, `pyright drummer`, and `pytest tests/unit tests/integration`. All must pass.

- [ ] **Step 2: Fix any lint or type errors**

Common things to watch for:

- **`ANN401`** — `Any` used in annotation. Fix: use a more specific type.
- **`TCH001/TCH002`** — import should be in `TYPE_CHECKING` block. Fix: move the import into `if TYPE_CHECKING:`.
- **`PLC0415`** — import not at top of file. Fix: move import to top.
- **`B008`** — `Field(default_factory=...)` used correctly — not a default value call.
- **Pyright `reportUnknownVariableType`** — usually from untyped YAML return. Fix: add explicit type annotation to the variable:

  ```python
  data: dict[str, object] = yaml.safe_load(...)
  ```

  Then use `model_validate(data)` which accepts `dict[str, object]`.

- [ ] **Step 3: Re-run make check after any fixes**

```bash
source venv/bin/activate && make check
```

Expected: All checks pass cleanly with no warnings.

- [ ] **Step 4: Commit if any fixes were needed**

```bash
git add -p   # stage only the lint/type fixes
git commit -m "fix: resolve lint and type errors in storage layer"
```

- [ ] **Step 5: Update TODO.md**

Replace the Phase 2 todo items in `TODO.md` with a completion note:

```markdown
# TODO

Current sprint: **Phase 3 — HTTP Engine**

- [ ] Implement `drummer/core/engine.py` — send pipeline (load → resolve → build → send → store)
- [ ] Implement `drummer/core/variables.py` — variable substitution + environment resolution
```

(Adjust the Phase 3 tasks to match the Phase 3 plan when it is written.)

For now, mark Phase 2 done:

```markdown
# TODO

Current sprint: **Phase 2 — Storage layer** ✅ Complete

Phase 3 plan not yet written.
```

- [ ] **Step 6: Final commit**

```bash
git add TODO.md
git commit -m "chore: mark Phase 2 storage complete in TODO"
```

---

## Self-Review

**Spec coverage:**
- ✅ `RequestFrontmatter` covers all fields shown in the spec YAML sample (name, method, url, headers, params, encoding, cookies, auth, pre_script, post_script, tags, skip)
- ✅ `GraphQLConfig` covers the GraphQL block (query, variables)
- ✅ `parse_request_file` handles YAML frontmatter + Markdown body via `python-frontmatter`
- ✅ `write_request_file` round-trips cleanly, omits defaults
- ✅ Project structure: `.drummer/project.yaml` + `.drummer/environments/*.yaml`
- ✅ `list_requests` excludes `.drummer/`, skips non-request `.md` files
- ✅ All functions are pure Python with no web-framework dependency
- ✅ All tests use `tmp_path` — no filesystem side effects

**Placeholder scan:** No TBDs, no "implement later", no vague steps. All code blocks are complete and runnable.

**Type consistency:**
- `parse_request_file(path: Path) -> RequestFile` — used consistently in Task 2 tests and in `list_requests`
- `write_request_file(request: RequestFile) -> None` — consistent in Task 3 tests
- `create_project(project_dir, name) -> ProjectMeta` — consistent across Task 4 tests and Task 6 tests
- `save_environment(env, project_dir)` — note: `project_dir` is the project root, not the environments directory; consistent throughout
- `load_environment(path)` — takes the full `.yaml` file path, not the project root; consistent in tests
