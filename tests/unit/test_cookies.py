from drummer.core.cookies import CookieJar
from drummer.core.storage.formats import CookieMode


async def test_session_cookies_accumulate_and_are_sent() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://api.example.com/login", ["session=abc123"])
    cookies = jar.cookies_for_request("http://api.example.com/users", CookieMode.SESSION, {})
    assert cookies == {"session": "abc123"}


async def test_session_cookies_not_sent_cross_domain() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://api.example.com/login", ["session=abc123"])
    cookies = jar.cookies_for_request("http://other.com/users", CookieMode.SESSION, {})
    assert cookies == {}


async def test_disabled_returns_empty() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://api.example.com/login", ["session=abc123"])
    cookies = jar.cookies_for_request("http://api.example.com/users", CookieMode.DISABLED, {})
    assert cookies == {}


async def test_explicit_returns_only_inline_dict() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://api.example.com/login", ["session=abc123"])
    explicit = {"api_key": "xyz"}
    cookies = jar.cookies_for_request("http://api.example.com/users", CookieMode.EXPLICIT, explicit)
    assert cookies == {"api_key": "xyz"}
    assert "session" not in cookies


async def test_clear_removes_all_cookies() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://api.example.com/login", ["session=abc123"])
    jar.clear()
    cookies = jar.cookies_for_request("http://api.example.com/users", CookieMode.SESSION, {})
    assert cookies == {}


async def test_multiple_set_cookie_headers_all_stored() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://api.example.com/login", ["session=abc123", "user_id=42"])
    cookies = jar.cookies_for_request("http://api.example.com/users", CookieMode.SESSION, {})
    assert cookies == {"session": "abc123", "user_id": "42"}


async def test_later_cookie_overwrites_earlier() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://api.example.com/a", ["session=old"])
    await jar.update_from_response("http://api.example.com/b", ["session=new"])
    cookies = jar.cookies_for_request("http://api.example.com/c", CookieMode.SESSION, {})
    assert cookies == {"session": "new"}


async def test_cookie_with_attributes_strips_to_name_value() -> None:
    jar = CookieJar()
    await jar.update_from_response(
        "http://api.example.com/login", ["session=abc123; Path=/; HttpOnly; SameSite=Strict"]
    )
    cookies = jar.cookies_for_request("http://api.example.com/users", CookieMode.SESSION, {})
    assert cookies == {"session": "abc123"}


async def test_returned_session_dict_is_a_copy() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://x.com/", ["s=1"])
    result = jar.cookies_for_request("http://x.com/", CookieMode.SESSION, {})
    result["injected"] = "evil"
    assert jar.cookies_for_request("http://x.com/", CookieMode.SESSION, {}) == {"s": "1"}
