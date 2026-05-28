from datetime import UTC, datetime, timedelta

from drummer.core.cookies import CookieJar
from drummer.core.storage.formats import CookieMode


class _MockPersistence:
    def __init__(self) -> None:
        self.saved: list[tuple[str, str, str, datetime | None]] = []
        self.deleted: list[tuple[str, str]] = []
        self.cleared = False
        self.data: dict[str, dict[str, tuple[str, datetime | None]]] = {}

    async def load(self) -> dict[str, dict[str, tuple[str, datetime | None]]]:
        return self.data

    async def save(self, hostname: str, name: str, value: str, expires_at: datetime | None) -> None:
        self.saved.append((hostname, name, value, expires_at))
        if hostname not in self.data:
            self.data[hostname] = {}
        self.data[hostname][name] = (value, expires_at)

    async def delete(self, hostname: str, name: str) -> None:
        self.deleted.append((hostname, name))
        if hostname in self.data:
            self.data[hostname].pop(name, None)

    async def clear(self) -> None:
        self.cleared = True
        self.data.clear()


async def test_expired_cookie_not_returned() -> None:
    jar = CookieJar()
    past = (datetime.now(UTC) - timedelta(seconds=1)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    await jar.update_from_response("http://api.example.com/", [f"session=abc123; expires={past}"])
    cookies = jar.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert "session" not in cookies


async def test_max_age_zero_removes_cookie() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://api.example.com/", ["session=abc123"])
    await jar.update_from_response("http://api.example.com/", ["session=; max-age=0"])
    cookies = jar.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert "session" not in cookies


async def test_max_age_positive_cookie_returned() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://api.example.com/", ["session=abc123; max-age=3600"])
    cookies = jar.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert cookies == {"session": "abc123"}


async def test_future_expires_cookie_returned() -> None:
    jar = CookieJar()
    future = (datetime.now(UTC) + timedelta(hours=1)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    await jar.update_from_response("http://api.example.com/", [f"session=abc123; expires={future}"])
    cookies = jar.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert cookies == {"session": "abc123"}


async def test_no_expiry_cookie_always_returned() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://api.example.com/", ["session=abc123"])
    cookies = jar.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert cookies == {"session": "abc123"}


async def test_in_memory_jar_without_persistence_works() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://api.example.com/", ["x=1"])
    jar.clear()
    cookies = jar.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert cookies == {}


async def test_aclear_removes_all_cookies() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://api.example.com/", ["session=abc123"])
    await jar.aclear()
    cookies = jar.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert cookies == {}


async def test_load_from_db_populates_store() -> None:
    mock = _MockPersistence()
    mock.data = {"api.example.com": {"session": ("abc123", None)}}
    jar = CookieJar(persistence=mock)
    await jar.load_from_db()
    cookies = jar.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert cookies == {"session": "abc123"}


async def test_aclear_calls_persistence_clear() -> None:
    mock = _MockPersistence()
    jar = CookieJar(persistence=mock)
    await jar.update_from_response("http://api.example.com/", ["session=abc123"])
    await jar.aclear()
    assert mock.cleared is True
    cookies = jar.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert cookies == {}


async def test_expired_cookie_calls_delete_not_save() -> None:
    mock = _MockPersistence()
    jar = CookieJar(persistence=mock)
    past = (datetime.now(UTC) - timedelta(seconds=1)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    await jar.update_from_response("http://api.example.com/", [f"session=abc123; expires={past}"])
    assert mock.deleted == [("api.example.com", "session")]
    assert mock.saved == []


async def test_max_age_zero_calls_delete_not_save() -> None:
    mock = _MockPersistence()
    jar = CookieJar(persistence=mock)
    await jar.update_from_response("http://api.example.com/", ["session=abc123"])
    saves_before_expiry = len(mock.saved)
    await jar.update_from_response("http://api.example.com/", ["session=; max-age=0"])
    assert ("api.example.com", "session") in mock.deleted
    assert len(mock.saved) == saves_before_expiry  # expiry path must not call save
