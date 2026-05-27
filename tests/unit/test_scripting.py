import hashlib
import hmac

from drummer.core.scripting import run_script

_REQ: dict[str, object] = {
    "url": "http://example.com/api",
    "method": "GET",
    "headers": {},
    "params": {},
    "body": "",
}


def test_console_log_captured() -> None:
    result = run_script(
        "dm.console.log('hello', 'world');",
        variables={},
        request_fields=dict(_REQ),
        response_fields=None,
    )
    assert result.logs == ["hello world"]
    assert result.error is None


def test_env_get_returns_variable() -> None:
    result = run_script(
        "dm.console.log(dm.env.get('token'));",
        variables={"token": "abc123"},
        request_fields=dict(_REQ),
        response_fields=None,
    )
    assert result.logs == ["abc123"]


def test_env_set_captured_in_mutations() -> None:
    result = run_script(
        "dm.env.set('token', 'newvalue');",
        variables={},
        request_fields=dict(_REQ),
        response_fields=None,
    )
    assert result.env_mutations == {"token": "newvalue"}
    assert result.error is None


def test_env_set_visible_to_subsequent_get() -> None:
    result = run_script(
        "dm.env.set('x', '42'); dm.console.log(dm.env.get('x'));",
        variables={},
        request_fields=dict(_REQ),
        response_fields=None,
    )
    assert result.logs == ["42"]


def test_request_header_mutation() -> None:
    result = run_script(
        "dm.request.headers['X-Custom'] = 'test-value';",
        variables={},
        request_fields=dict(_REQ),
        response_fields=None,
    )
    assert result.request_mutations["headers"]["X-Custom"] == "test-value"
    assert result.error is None


def test_request_url_mutation() -> None:
    result = run_script(
        "dm.request.url = 'http://other.com/api';",
        variables={},
        request_fields=dict(_REQ),
        response_fields=None,
    )
    assert result.request_mutations["url"] == "http://other.com/api"


def test_timeout_returns_error() -> None:
    result = run_script(
        "while(true) {}",
        variables={},
        request_fields=dict(_REQ),
        response_fields=None,
        timeout_ms=100,
    )
    assert result.error is not None
    assert "interrupted" in result.error.lower() or "timed" in (result.suggestion or "").lower()


def test_syntax_error_captured() -> None:
    result = run_script(
        "this is not valid JS !!!", variables={}, request_fields=dict(_REQ), response_fields=None
    )
    assert result.error is not None
    assert "SyntaxError" in result.error


def test_dm_response_in_pre_script_raises_error() -> None:
    result = run_script(
        "dm.response.status;", variables={}, request_fields=dict(_REQ), response_fields=None
    )
    assert result.error is not None
    assert "pre-script" in result.error.lower()


def test_post_script_can_read_response_status() -> None:
    result = run_script(
        "dm.env.set('code', String(dm.response.status));",
        variables={},
        request_fields=dict(_REQ),
        response_fields={"status": 201, "headers": {}, "body": "{}"},
    )
    assert result.env_mutations == {"code": "201"}
    assert result.error is None


def test_post_script_response_json() -> None:
    result = run_script(
        "var body = dm.response.json(); dm.env.set('id', String(body.id));",
        variables={},
        request_fields=dict(_REQ),
        response_fields={"status": 200, "headers": {}, "body": '{"id": 99}'},
    )
    assert result.env_mutations == {"id": "99"}


def test_crypto_hmac_sha256() -> None:
    result = run_script(
        "dm.env.set('sig', dm.crypto.hmacSha256('secret', 'payload'));",
        variables={},
        request_fields=dict(_REQ),
        response_fields=None,
    )
    expected = hmac.new(b"secret", b"payload", hashlib.sha256).hexdigest()
    assert result.env_mutations.get("sig") == expected


def test_crypto_hmac_sha256_non_ascii_key() -> None:
    result = run_script(
        "dm.env.set('sig', dm.crypto.hmacSha256('🔑', 'payload'));",
        variables={},
        request_fields=dict(_REQ),
        response_fields=None,
    )
    expected = hmac.new("🔑".encode(), b"payload", hashlib.sha256).hexdigest()
    assert result.env_mutations.get("sig") == expected


def test_multiple_console_logs_captured_in_order() -> None:
    result = run_script(
        "dm.console.log('a'); dm.console.log('b'); dm.console.log('c');",
        variables={},
        request_fields=dict(_REQ),
        response_fields=None,
    )
    assert result.logs == ["a", "b", "c"]


def test_dm_request_mutation_in_post_script_raises_error() -> None:
    result = run_script(
        "dm.request.headers['X-Test'] = 'bad';",
        variables={},
        request_fields=dict(_REQ),
        response_fields={"status": 200, "headers": {}, "body": "{}"},
    )
    assert result.error is not None


def test_console_log_captured_before_exception() -> None:
    result = run_script(
        "dm.console.log('before error'); throw new Error('oops');",
        variables={},
        request_fields=dict(_REQ),
        response_fields=None,
    )
    assert result.error is not None
    assert result.logs == ["before error"]
