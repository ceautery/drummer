from datetime import UTC, datetime, timedelta

from drummer.core.cookies import CookieJar
from drummer.core.storage.formats import CookieMode


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
