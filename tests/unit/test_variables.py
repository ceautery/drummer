import base64
from pathlib import Path

from drummer.core.storage.formats import AuthConfig, AuthType, RequestFile, RequestFrontmatter
from drummer.core.variables import resolve, substitute


def test_substitute_replaces_known_var() -> None:
    result, warnings = substitute("{{base_url}}/users", {"base_url": "https://api.example.com"})
    assert result == "https://api.example.com/users"
    assert warnings == []


def test_substitute_leaves_unknown_var_as_placeholder() -> None:
    result, warnings = substitute("{{base_url}}/users", {})
    assert result == "{{base_url}}/users"
    assert "base_url" in warnings


def test_substitute_multiple_vars_partial_resolution() -> None:
    env = {"proto": "https", "host": "api.example.com"}
    result, warnings = substitute("{{proto}}://{{host}}/{{path}}", env)
    assert result == "https://api.example.com/{{path}}"
    assert warnings == ["path"]


def test_substitute_empty_string() -> None:
    result, warnings = substitute("", {"x": "y"})
    assert result == ""
    assert warnings == []


def test_resolve_substitutes_url(tmp_path: Path) -> None:
    fm = RequestFrontmatter(name="Test", url="{{base_url}}/users")
    rf = RequestFile(frontmatter=fm, body="", path=tmp_path / "req.md")
    resolved = resolve(rf, {"base_url": "https://api.example.com"})
    assert resolved.url == "https://api.example.com/users"
    assert resolved.warnings == []


def test_resolve_substitutes_header_values(tmp_path: Path) -> None:
    fm = RequestFrontmatter(
        name="Test", url="https://api.example.com", headers={"Authorization": "Bearer {{token}}"}
    )
    rf = RequestFile(frontmatter=fm, body="", path=tmp_path / "req.md")
    resolved = resolve(rf, {"token": "secret"})
    assert resolved.headers["Authorization"] == "Bearer secret"


def test_resolve_substitutes_params(tmp_path: Path) -> None:
    fm = RequestFrontmatter(
        name="Test", url="https://api.example.com", params={"tenant": "{{tenant_id}}"}
    )
    rf = RequestFile(frontmatter=fm, body="", path=tmp_path / "req.md")
    resolved = resolve(rf, {"tenant_id": "acme"})
    assert resolved.params["tenant"] == "acme"


def test_resolve_substitutes_body(tmp_path: Path) -> None:
    fm = RequestFrontmatter(name="Test", url="https://api.example.com")
    rf = RequestFile(frontmatter=fm, body='{"name": "{{username}}"}', path=tmp_path / "req.md")
    resolved = resolve(rf, {"username": "alice"})
    assert resolved.body == '{"name": "alice"}'


def test_resolve_bearer_auth_header(tmp_path: Path) -> None:
    placeholder = "my-token"
    fm = RequestFrontmatter(
        name="Test",
        url="https://api.example.com",
        auth=AuthConfig(type=AuthType.BEARER, token=placeholder),
    )
    rf = RequestFile(frontmatter=fm, body="", path=tmp_path / "req.md")
    resolved = resolve(rf, {})
    assert resolved.headers["Authorization"] == f"Bearer {placeholder}"


def test_resolve_bearer_auth_token_substituted(tmp_path: Path) -> None:
    placeholder = "{{token}}"
    fm = RequestFrontmatter(
        name="Test",
        url="https://api.example.com",
        auth=AuthConfig(type=AuthType.BEARER, token=placeholder),
    )
    rf = RequestFile(frontmatter=fm, body="", path=tmp_path / "req.md")
    resolved = resolve(rf, {"token": "secret123"})
    assert resolved.headers["Authorization"] == "Bearer secret123"


def test_resolve_basic_auth_header(tmp_path: Path) -> None:
    username = "user"
    credential = "pass"
    fm = RequestFrontmatter(
        name="Test",
        url="https://api.example.com",
        auth=AuthConfig(type=AuthType.BASIC, username=username, password=credential),
    )
    rf = RequestFile(frontmatter=fm, body="", path=tmp_path / "req.md")
    resolved = resolve(rf, {})
    expected = "Basic " + base64.b64encode(f"{username}:{credential}".encode()).decode()
    assert resolved.headers["Authorization"] == expected


def test_resolve_api_key_auth_header(tmp_path: Path) -> None:
    fm = RequestFrontmatter(
        name="Test",
        url="https://api.example.com",
        auth=AuthConfig(type=AuthType.API_KEY, key="X-API-Key", value="mykey"),
    )
    rf = RequestFile(frontmatter=fm, body="", path=tmp_path / "req.md")
    resolved = resolve(rf, {})
    assert resolved.headers["X-API-Key"] == "mykey"


def test_resolve_no_auth_adds_no_authorization_header(tmp_path: Path) -> None:
    fm = RequestFrontmatter(name="Test", url="https://api.example.com")
    rf = RequestFile(frontmatter=fm, body="", path=tmp_path / "req.md")
    resolved = resolve(rf, {})
    assert "Authorization" not in resolved.headers


def test_resolve_collects_warnings_across_fields(tmp_path: Path) -> None:
    fm = RequestFrontmatter(
        name="Test", url="{{base_url}}/users", headers={"X-Tenant": "{{tenant}}"}
    )
    rf = RequestFile(frontmatter=fm, body="", path=tmp_path / "req.md")
    resolved = resolve(rf, {})
    assert set(resolved.warnings) == {"base_url", "tenant"}


def test_resolve_deduplicates_warnings(tmp_path: Path) -> None:
    fm = RequestFrontmatter(
        name="Test", url="{{base_url}}/path", headers={"X-Base": "{{base_url}}"}
    )
    rf = RequestFile(frontmatter=fm, body="", path=tmp_path / "req.md")
    resolved = resolve(rf, {})
    assert resolved.warnings.count("base_url") == 1
