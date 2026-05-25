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
