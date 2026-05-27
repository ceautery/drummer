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
    parse_request_file,
    write_request_file,
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
    placeholder = "{{token}}"
    fm = RequestFrontmatter(
        name="List Users",
        method="POST",
        url="{{base_url}}/api/users",
        headers={"Authorization": "Bearer {{token}}"},
        params={"page": "1"},
        cookies=CookieConfig(mode=CookieMode.EXPLICIT),
        auth=AuthConfig(type=AuthType.BEARER, token=placeholder),
        tags=["users", "list"],
        skip=True,
    )
    assert fm.method == "POST"
    assert fm.cookies.mode == CookieMode.EXPLICIT
    assert fm.auth.type == AuthType.BEARER
    assert fm.auth.token == placeholder
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


def test_parse_request_file_minimal(tmp_path: Path) -> None:
    req_file = tmp_path / "request.md"
    req_file.write_text("---\nname: Test Request\n---\n\nRequest body here.\n", encoding="utf-8")
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
    placeholder_id = "{{user_id}}"
    content = f"""\
---
name: Get User
method: POST
url: "{{{{base_url}}}}/graphql"
graphql:
  query: |
    query GetUser($id: ID!) {{{{
      user(id: $id) {{ name email }}
    }}}}
  variables:
    id: "{placeholder_id}"
---
"""
    req_file = tmp_path / "get-user.md"
    req_file.write_text(content, encoding="utf-8")
    result = parse_request_file(req_file)
    assert result.frontmatter.graphql is not None
    assert "GetUser" in result.frontmatter.graphql.query
    assert result.frontmatter.graphql.variables == {"id": placeholder_id}


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
    assert "method:" not in text  # "GET" is default — omitted
    assert "encoding:" not in text  # "utf-8" is default — omitted
    assert "skip:" not in text  # False is default — omitted


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
    placeholder = "my-token"
    fm = RequestFrontmatter(
        name="Auth Request",
        url="https://api.example.com/data",
        auth=AuthConfig(type=AuthType.BEARER, token=placeholder),
        cookies=CookieConfig(mode=CookieMode.DISABLED),
    )
    original = RequestFile(frontmatter=fm, body="", path=req_file)
    write_request_file(original)
    loaded = parse_request_file(req_file)
    assert loaded.frontmatter.auth.type == AuthType.BEARER
    assert loaded.frontmatter.auth.token == placeholder
    assert loaded.frontmatter.cookies.mode == CookieMode.DISABLED


def test_request_frontmatter_default_script_timeout_is_none() -> None:
    fm = RequestFrontmatter(name="Test")
    assert fm.script_timeout_ms is None


def test_request_frontmatter_parses_script_timeout(tmp_path: Path) -> None:
    timeout_value = 10000
    (tmp_path / "req.md").write_text(
        f"---\nname: T\nmethod: GET\nurl: http://x.com\nscript_timeout_ms: {timeout_value}\n---\n",
        encoding="utf-8",
    )
    rf = parse_request_file(tmp_path / "req.md")
    assert rf.frontmatter.script_timeout_ms == timeout_value
