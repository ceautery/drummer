import httpx
import pytest
from pydantic import ValidationError

from drummer.core.cookies import CookieJar
from drummer.core.engine import RequestResult, ResolvedRequest, send
from drummer.core.storage.formats import CookieConfig, CookieMode

_HTTP_OK = 200
_HTTP_NOT_FOUND = 404
_HTTP_INTERNAL_ERROR = 500


def test_resolved_request_requires_name() -> None:
    with pytest.raises(ValidationError):
        ResolvedRequest.model_validate({"method": "GET", "url": "https://example.com"})


def test_resolved_request_invalid_method_raises() -> None:
    with pytest.raises(ValidationError):
        ResolvedRequest.model_validate(
            {"name": "test", "method": "INVALID", "url": "https://example.com"}
        )


def test_resolved_request_defaults() -> None:
    rr = ResolvedRequest(name="Test", method="GET", url="https://example.com")
    assert rr.headers == {}
    assert rr.params == {}
    assert rr.body == ""
    assert rr.encoding == "utf-8"
    assert rr.warnings == []


def test_request_result_stores_all_fields() -> None:
    elapsed_ms = 42.5
    warnings = ["missing_var"]

    result = RequestResult(
        status_code=_HTTP_OK,
        headers=[("content-type", "application/json")],
        body='{"ok": true}',
        encoding="utf-8",
        elapsed_ms=elapsed_ms,
        url="https://example.com",
        warnings=warnings,
    )
    assert result.status_code == _HTTP_OK
    assert result.elapsed_ms == elapsed_ms
    assert result.warnings == warnings


class _MockTransport(httpx.AsyncBaseTransport):
    def __init__(
        self,
        status_code: int = _HTTP_OK,
        headers: dict[str, str] | None = None,
        content: bytes = b"",
    ) -> None:
        self._status_code = status_code
        self._headers = headers or {}
        self._content = content
        self.last_request: httpx.Request | None = None

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.last_request = request
        return httpx.Response(
            status_code=self._status_code,
            headers=self._headers,
            content=self._content,
            request=request,
        )


def _make_resolved(
    url: str = "https://api.example.com/users",
    cookies: CookieConfig | None = None,
    warnings: list[str] | None = None,
) -> ResolvedRequest:
    return ResolvedRequest(
        name="Test",
        method="GET",
        url=url,
        cookies=cookies or CookieConfig(),
        warnings=warnings or [],
    )


async def test_send_returns_status_and_body() -> None:
    transport = _MockTransport(
        status_code=_HTTP_OK,
        headers={"content-type": "application/json; charset=utf-8"},
        content=b'{"users": []}',
    )
    result = await send(_make_resolved(), CookieJar(), transport=transport)
    assert result.status_code == _HTTP_OK
    assert result.body == '{"users": []}'
    assert result.encoding == "utf-8"


async def test_send_records_elapsed_ms() -> None:
    transport = _MockTransport(content=b"")
    result = await send(_make_resolved(), CookieJar(), transport=transport)
    assert result.elapsed_ms >= 0


async def test_send_non_200_does_not_raise() -> None:
    transport = _MockTransport(status_code=_HTTP_NOT_FOUND, content=b"Not Found")
    result = await send(_make_resolved(), CookieJar(), transport=transport)
    assert result.status_code == _HTTP_NOT_FOUND
    assert "Not Found" in result.body


async def test_send_passes_warnings_through() -> None:
    transport = _MockTransport(content=b"")
    resolved = _make_resolved(warnings=["missing_var"])
    result = await send(resolved, CookieJar(), transport=transport)
    assert result.warnings == ["missing_var"]


async def test_send_session_cookies_accumulated_from_response() -> None:
    transport = _MockTransport(headers={"set-cookie": "session=abc123"}, content=b"")
    jar = CookieJar()
    await send(_make_resolved(), jar, transport=transport)
    stored = jar.cookies_for_request("https://api.example.com/other", CookieMode.SESSION, {})
    assert stored == {"session": "abc123"}


async def test_send_disabled_cookies_not_accumulated() -> None:
    transport = _MockTransport(headers={"set-cookie": "session=abc123"}, content=b"")
    jar = CookieJar()
    resolved = _make_resolved(cookies=CookieConfig(mode=CookieMode.DISABLED))
    await send(resolved, jar, transport=transport)
    stored = jar.cookies_for_request("https://api.example.com/other", CookieMode.SESSION, {})
    assert stored == {}


async def test_send_sends_session_cookies_in_request() -> None:
    transport = _MockTransport(content=b"")
    jar = CookieJar()
    await jar.update_from_response("https://api.example.com/login", ["session=abc123"])
    await send(_make_resolved(url="https://api.example.com/users"), jar, transport=transport)
    assert transport.last_request is not None
    cookie_header = transport.last_request.headers.get("cookie", "")
    assert "session=abc123" in cookie_header


async def test_send_500_status_captured() -> None:
    transport = _MockTransport(status_code=_HTTP_INTERNAL_ERROR, content=b"Internal Server Error")
    result = await send(_make_resolved(), CookieJar(), transport=transport)
    assert result.status_code == _HTTP_INTERNAL_ERROR


_PRE_SCRIPT_SET_URL = "dm.request.url = 'https://api.example.com/v2';"


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
    assert result.sent.headers.get("Authorization") == "Bearer tok"
    assert result.warnings == ["missing_var"]
    assert result.variables == {"base_url": "https://api.example.com"}


async def test_send_sent_reflects_pre_script_url_mutation() -> None:
    transport = _MockTransport(status_code=_HTTP_OK, content=b"ok")
    resolved = ResolvedRequest(
        name="t", method="GET", url="https://api.example.com/v1", pre_script=_PRE_SCRIPT_SET_URL
    )
    result = await send(resolved, CookieJar(), transport=transport)
    assert result.sent is not None
    assert result.sent.url == "https://api.example.com/v2"
