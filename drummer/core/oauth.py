from __future__ import annotations

import contextlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from drummer.core.storage.formats import AuthConfig

_GRANT_TYPE = "client_credentials"
_GRACE_SECONDS = 30
_HTTP_ERROR_THRESHOLD = 400


class OAuthError(Exception):
    pass


@dataclass
class OAuthToken:
    access_token: str
    expires_at: datetime | None


class OAuthTokenCache:
    def __init__(self) -> None:
        self._cache: dict[tuple[str, str], OAuthToken] = {}

    def get(self, token_url: str, client_id: str) -> OAuthToken | None:
        token = self._cache.get((token_url, client_id))
        if token is None:
            return None
        if token.expires_at is not None:
            grace_cutoff = token.expires_at - timedelta(seconds=_GRACE_SECONDS)
            if datetime.now(UTC) >= grace_cutoff:
                return None
        return token

    def set(self, token_url: str, client_id: str, token: OAuthToken) -> None:
        self._cache[(token_url, client_id)] = token


async def fetch_cc_token(
    token_url: str,
    client_id: str,
    client_secret: str,
    scope: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> OAuthToken:
    data: dict[str, str] = {
        "grant_type": _GRANT_TYPE,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    if scope:
        data["scope"] = scope

    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.post(token_url, data=data)

    if response.status_code >= _HTTP_ERROR_THRESHOLD:
        msg = f"Token endpoint returned {response.status_code}: {response.text}"
        raise OAuthError(msg)

    try:
        payload: dict[str, object] = response.json()
    except ValueError as exc:
        msg = f"Token response is not valid JSON: {exc}"
        raise OAuthError(msg) from exc

    if "access_token" not in payload:
        msg = "Token response missing 'access_token'"
        raise OAuthError(msg)

    expires_at: datetime | None = None
    raw_expires = payload.get("expires_in")
    if raw_expires is not None:
        with contextlib.suppress(ValueError, TypeError):
            expires_at = datetime.now(UTC) + timedelta(seconds=int(str(raw_expires)))

    return OAuthToken(access_token=str(payload["access_token"]), expires_at=expires_at)


async def get_or_fetch_token(
    cache: OAuthTokenCache, auth: AuthConfig, transport: httpx.AsyncBaseTransport | None = None
) -> str:
    cached = cache.get(auth.token_url, auth.client_id)
    if cached is not None:
        return cached.access_token

    token = await fetch_cc_token(
        auth.token_url, auth.client_id, auth.client_secret, auth.scope, transport=transport
    )
    cache.set(auth.token_url, auth.client_id, token)
    return token.access_token
