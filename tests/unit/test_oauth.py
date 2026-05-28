import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from drummer.core.oauth import (
    OAuthError,
    OAuthToken,
    OAuthTokenCache,
    fetch_cc_token,
    get_or_fetch_token,
)
from drummer.core.storage.formats import AuthConfig, AuthType

_TOKEN_URL = "https://auth.example.com/token"
_CLIENT_ID = "client1"
_CLIENT_SECRET = "secret1"
_ACCESS_TOKEN = "test-token-abc"


def _ok_transport(body: dict) -> httpx.AsyncBaseTransport:
    content = json.dumps(body).encode()

    class _T(httpx.AsyncBaseTransport):
        async def handle_async_request(self, req: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=content, request=req)

    return _T()


def _error_transport(status: int = 401) -> httpx.AsyncBaseTransport:
    class _T(httpx.AsyncBaseTransport):
        async def handle_async_request(self, req: httpx.Request) -> httpx.Response:
            return httpx.Response(status, content=b'{"error":"unauthorized"}', request=req)

    return _T()


async def test_cache_miss_returns_none() -> None:
    cache = OAuthTokenCache()
    assert cache.get(_TOKEN_URL, _CLIENT_ID, "") is None


async def test_cache_hit_returns_token() -> None:
    cache = OAuthTokenCache()
    token = OAuthToken(
        access_token=_ACCESS_TOKEN, expires_at=datetime.now(UTC) + timedelta(hours=1)
    )
    cache.set(_TOKEN_URL, _CLIENT_ID, "", token)
    result = cache.get(_TOKEN_URL, _CLIENT_ID, "")
    assert result is not None
    assert result.access_token == _ACCESS_TOKEN


async def test_cache_returns_none_within_grace_window() -> None:
    cache = OAuthTokenCache()
    token = OAuthToken(
        access_token=_ACCESS_TOKEN, expires_at=datetime.now(UTC) + timedelta(seconds=20)
    )
    cache.set(_TOKEN_URL, _CLIENT_ID, "", token)
    assert cache.get(_TOKEN_URL, _CLIENT_ID, "") is None


async def test_cache_returns_token_with_no_expiry() -> None:
    cache = OAuthTokenCache()
    token = OAuthToken(access_token=_ACCESS_TOKEN, expires_at=None)
    cache.set(_TOKEN_URL, _CLIENT_ID, "", token)
    result = cache.get(_TOKEN_URL, _CLIENT_ID, "")
    assert result is not None


async def test_fetch_cc_token_returns_access_token() -> None:
    token = await fetch_cc_token(
        _TOKEN_URL,
        _CLIENT_ID,
        _CLIENT_SECRET,
        "",
        transport=_ok_transport({"access_token": _ACCESS_TOKEN}),
    )
    assert token.access_token == _ACCESS_TOKEN


async def test_fetch_cc_token_includes_scope_when_set() -> None:
    captured: list[httpx.Request] = []

    class _Cap(httpx.AsyncBaseTransport):
        async def handle_async_request(self, req: httpx.Request) -> httpx.Response:
            captured.append(req)
            body = json.dumps({"access_token": _ACCESS_TOKEN}).encode()
            return httpx.Response(200, content=body, request=req)

    await fetch_cc_token(_TOKEN_URL, _CLIENT_ID, _CLIENT_SECRET, "read write", transport=_Cap())
    assert len(captured) == 1
    body_text = captured[0].content.decode()
    assert "scope" in body_text
    assert "read" in body_text


async def test_fetch_cc_token_omits_scope_when_empty() -> None:
    captured: list[httpx.Request] = []

    class _Cap(httpx.AsyncBaseTransport):
        async def handle_async_request(self, req: httpx.Request) -> httpx.Response:
            captured.append(req)
            body = json.dumps({"access_token": _ACCESS_TOKEN}).encode()
            return httpx.Response(200, content=body, request=req)

    await fetch_cc_token(_TOKEN_URL, _CLIENT_ID, _CLIENT_SECRET, "", transport=_Cap())
    body_text = captured[0].content.decode()
    assert "scope" not in body_text


async def test_fetch_cc_token_parses_expires_in() -> None:
    token = await fetch_cc_token(
        _TOKEN_URL,
        _CLIENT_ID,
        _CLIENT_SECRET,
        "",
        transport=_ok_transport({"access_token": _ACCESS_TOKEN, "expires_in": 3600}),
    )
    assert token.expires_at is not None
    assert token.expires_at > datetime.now(UTC) + timedelta(seconds=3590)


async def test_fetch_cc_token_no_expires_in_gives_none() -> None:
    token = await fetch_cc_token(
        _TOKEN_URL,
        _CLIENT_ID,
        _CLIENT_SECRET,
        "",
        transport=_ok_transport({"access_token": _ACCESS_TOKEN}),
    )
    assert token.expires_at is None


async def test_fetch_cc_token_raises_on_http_error() -> None:
    with pytest.raises(OAuthError):
        await fetch_cc_token(
            _TOKEN_URL, _CLIENT_ID, _CLIENT_SECRET, "", transport=_error_transport(401)
        )


async def test_fetch_cc_token_raises_on_missing_access_token() -> None:
    with pytest.raises(OAuthError):
        await fetch_cc_token(
            _TOKEN_URL,
            _CLIENT_ID,
            _CLIENT_SECRET,
            "",
            transport=_ok_transport({"token_type": "Bearer"}),
        )


async def test_get_or_fetch_uses_cache_on_hit() -> None:
    cache = OAuthTokenCache()
    token = OAuthToken(
        access_token=_ACCESS_TOKEN, expires_at=datetime.now(UTC) + timedelta(hours=1)
    )
    cache.set(_TOKEN_URL, _CLIENT_ID, "", token)
    auth = AuthConfig(
        type=AuthType.OAUTH2_CC,
        token_url=_TOKEN_URL,
        client_id=_CLIENT_ID,
        client_secret=_CLIENT_SECRET,
    )

    class _NeverCalled(httpx.AsyncBaseTransport):
        async def handle_async_request(self, _req: httpx.Request) -> httpx.Response:
            msg = "should not call token endpoint"
            raise AssertionError(msg)

    result = await get_or_fetch_token(cache, auth, transport=_NeverCalled())
    assert result == _ACCESS_TOKEN


async def test_get_or_fetch_stores_token_on_miss() -> None:
    cache = OAuthTokenCache()
    auth = AuthConfig(
        type=AuthType.OAUTH2_CC,
        token_url=_TOKEN_URL,
        client_id=_CLIENT_ID,
        client_secret=_CLIENT_SECRET,
    )
    result = await get_or_fetch_token(
        cache, auth, transport=_ok_transport({"access_token": _ACCESS_TOKEN, "expires_in": 3600})
    )
    assert result == _ACCESS_TOKEN
    cached = cache.get(_TOKEN_URL, _CLIENT_ID, "")
    assert cached is not None
    assert cached.access_token == _ACCESS_TOKEN


async def test_fetch_cc_token_handles_float_expires_in() -> None:
    token = await fetch_cc_token(
        _TOKEN_URL,
        _CLIENT_ID,
        _CLIENT_SECRET,
        "",
        transport=_ok_transport({"access_token": _ACCESS_TOKEN, "expires_in": 3600.0}),
    )
    assert token.expires_at is not None
    assert token.expires_at > datetime.now(UTC) + timedelta(seconds=3590)


async def test_fetch_cc_token_malformed_expires_in_gives_none() -> None:
    token = await fetch_cc_token(
        _TOKEN_URL,
        _CLIENT_ID,
        _CLIENT_SECRET,
        "",
        transport=_ok_transport({"access_token": _ACCESS_TOKEN, "expires_in": "bad"}),
    )
    assert token.expires_at is None
