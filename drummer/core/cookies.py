from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Protocol
from urllib.parse import urlparse

from drummer.core.storage.formats import CookieMode


class CookiePersistenceProtocol(Protocol):
    async def load(self) -> dict[str, dict[str, tuple[str, datetime | None]]]: ...
    async def save(
        self, hostname: str, name: str, value: str, expires_at: datetime | None
    ) -> None: ...
    async def clear(self) -> None: ...


def _parse_set_cookie(header: str) -> tuple[str, str, datetime | None]:
    parts = [p.strip() for p in header.split(";")]
    name_value = parts[0]
    if "=" not in name_value:
        return "", "", None
    name, _, value = name_value.partition("=")
    name = name.strip()
    value = value.strip()
    expires_at: datetime | None = None
    now = datetime.now(UTC)
    for attr in parts[1:]:
        lower = attr.lower()
        if lower.startswith("max-age="):
            try:
                seconds = int(attr[len("max-age=") :].strip())
                expires_at = now + timedelta(seconds=seconds)
            except ValueError:
                pass
        elif lower.startswith("expires=") and expires_at is None:
            try:
                parsed = parsedate_to_datetime(attr[len("expires=") :].strip())
                expires_at = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
            except (TypeError, ValueError, IndexError):
                pass
    return name, value, expires_at


class CookieJar:
    def __init__(self, persistence: CookiePersistenceProtocol | None = None) -> None:
        self._store: dict[str, dict[str, tuple[str, datetime | None]]] = {}
        self._persistence = persistence

    def cookies_for_request(
        self, url: str, mode: CookieMode, explicit: dict[str, str]
    ) -> dict[str, str]:
        if mode == CookieMode.DISABLED:
            return {}
        if mode == CookieMode.EXPLICIT:
            return dict(explicit)
        hostname = urlparse(url).hostname or ""
        now = datetime.now(UTC)
        return {
            name: value
            for name, (value, expires_at) in self._store.get(hostname, {}).items()
            if expires_at is None or expires_at > now
        }

    async def update_from_response(self, url: str, set_cookie_headers: list[str]) -> None:
        hostname = urlparse(url).hostname or ""
        if hostname not in self._store:
            self._store[hostname] = {}
        now = datetime.now(UTC)
        for header in set_cookie_headers:
            name, value, expires_at = _parse_set_cookie(header)
            if not name:
                continue
            if expires_at is not None and expires_at <= now:
                self._store[hostname].pop(name, None)
            else:
                self._store[hostname][name] = (value, expires_at)
            if self._persistence is not None:
                await self._persistence.save(hostname, name, value, expires_at)

    async def load_from_db(self) -> None:
        if self._persistence is not None:
            data = await self._persistence.load()
            self._store.update(data)

    def clear(self) -> None:
        self._store.clear()

    async def aclear(self) -> None:
        self._store.clear()
        if self._persistence is not None:
            await self._persistence.clear()

    def all_cookies(self) -> dict[str, dict[str, str]]:
        now = datetime.now(UTC)
        return {
            hostname: {
                name: value
                for name, (value, expires_at) in cookies.items()
                if expires_at is None or expires_at > now
            }
            for hostname, cookies in self._store.items()
        }
