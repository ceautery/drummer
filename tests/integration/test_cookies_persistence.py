from datetime import UTC, datetime, timedelta
from pathlib import Path

from drummer.api.db.cookie_persistence import CookiePersistence
from drummer.api.db.session import async_session_factory, init_db
from drummer.core.cookies import CookieJar
from drummer.core.storage.formats import CookieMode


def _db_url(tmp_path: Path) -> str:
    return f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"


async def test_cookies_survive_restart(tmp_path: Path) -> None:
    db_url = _db_url(tmp_path)
    await init_db(db_url)
    factory = async_session_factory(db_url)

    jar1 = CookieJar(persistence=CookiePersistence(factory))
    await jar1.update_from_response("http://api.example.com/", ["session=abc123"])

    jar2 = CookieJar(persistence=CookiePersistence(factory))
    await jar2.load_from_db()
    cookies = jar2.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert cookies == {"session": "abc123"}


async def test_expired_cookies_not_loaded(tmp_path: Path) -> None:
    db_url = _db_url(tmp_path)
    await init_db(db_url)
    factory = async_session_factory(db_url)

    past = (datetime.now(UTC) - timedelta(seconds=1)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    jar1 = CookieJar(persistence=CookiePersistence(factory))
    await jar1.update_from_response("http://api.example.com/", [f"session=abc123; expires={past}"])

    jar2 = CookieJar(persistence=CookiePersistence(factory))
    await jar2.load_from_db()
    cookies = jar2.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert "session" not in cookies


async def test_aclear_wipes_db(tmp_path: Path) -> None:
    db_url = _db_url(tmp_path)
    await init_db(db_url)
    factory = async_session_factory(db_url)

    jar1 = CookieJar(persistence=CookiePersistence(factory))
    await jar1.update_from_response("http://api.example.com/", ["session=abc123"])
    await jar1.aclear()

    jar2 = CookieJar(persistence=CookiePersistence(factory))
    await jar2.load_from_db()
    cookies = jar2.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert cookies == {}


async def test_upsert_overwrites_previous_value(tmp_path: Path) -> None:
    db_url = _db_url(tmp_path)
    await init_db(db_url)
    factory = async_session_factory(db_url)

    jar1 = CookieJar(persistence=CookiePersistence(factory))
    await jar1.update_from_response("http://api.example.com/", ["session=old"])
    await jar1.update_from_response("http://api.example.com/", ["session=new"])

    jar2 = CookieJar(persistence=CookiePersistence(factory))
    await jar2.load_from_db()
    cookies = jar2.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert cookies == {"session": "new"}


async def test_expired_cookie_deleted_from_db(tmp_path: Path) -> None:
    db_url = _db_url(tmp_path)
    await init_db(db_url)
    factory = async_session_factory(db_url)

    jar1 = CookieJar(persistence=CookiePersistence(factory))
    future = (datetime.now(UTC) + timedelta(hours=1)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    await jar1.update_from_response(
        "http://api.example.com/", [f"session=abc123; expires={future}"]
    )
    await jar1.update_from_response("http://api.example.com/", ["session=; max-age=0"])

    jar2 = CookieJar(persistence=CookiePersistence(factory))
    await jar2.load_from_db()
    cookies = jar2.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert "session" not in cookies
