from pathlib import Path

from drummer.api.mcp.tools import (
    clear_cookies_impl,
    create_request_impl,
    get_environment_impl,
    get_request_impl,
    list_cookies_impl,
    list_environments_impl,
    list_requests_impl,
    set_variable_impl,
    switch_environment_impl,
    update_request_impl,
)
from drummer.core.cookies import CookieJar


async def test_list_requests_impl_empty(project_dir: Path) -> None:
    result = await list_requests_impl(project_dir)
    assert result == []


async def test_create_and_get_request_impl(project_dir: Path) -> None:
    await create_request_impl(
        project_dir, "api/users.md", "List Users", "GET", "https://api.example.com/users"
    )
    assert (project_dir / "api" / "users.md").exists()

    items = await list_requests_impl(project_dir)
    assert len(items) == 1
    assert items[0]["name"] == "List Users"

    detail = await get_request_impl(project_dir, "api/users.md")
    assert detail["name"] == "List Users"
    assert detail["method"] == "GET"


async def test_update_request_impl(project_dir: Path) -> None:
    await create_request_impl(project_dir, "ping.md", "Ping", "GET", "https://x.com")
    await update_request_impl(project_dir, "ping.md", name="Ping v2", url="https://x.com/v2")
    detail = await get_request_impl(project_dir, "ping.md")
    assert detail["name"] == "Ping v2"
    assert detail["url"] == "https://x.com/v2"


async def test_list_environments_impl(project_dir: Path) -> None:
    envs = await list_environments_impl(project_dir)
    assert len(envs) == 1
    assert envs[0]["name"] == "local"


async def test_get_environment_impl(project_dir: Path) -> None:
    variables = await get_environment_impl(project_dir, "local")
    assert isinstance(variables, dict)


async def test_set_variable_impl(project_dir: Path) -> None:
    await set_variable_impl(project_dir, "local", "base_url", "https://api.example.com")
    variables = await get_environment_impl(project_dir, "local")
    assert variables["base_url"] == "https://api.example.com"


async def test_switch_environment_impl() -> None:
    class FakeState:
        active_environment: str = "local"

    state = FakeState()
    result = await switch_environment_impl(state, "staging")
    assert result == {"active_environment": "staging"}
    assert state.active_environment == "staging"


async def test_list_and_clear_cookies_impl() -> None:
    jar = CookieJar()
    await jar.update_from_response("https://api.example.com/login", ["session=abc"])
    cookies = await list_cookies_impl(jar)
    assert "api.example.com" in cookies

    await clear_cookies_impl(jar)
    assert await list_cookies_impl(jar) == {}
