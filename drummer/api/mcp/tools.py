from pathlib import Path
from typing import Protocol

from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from drummer.api.db.models import ResponseHistoryRecord
from drummer.core.cookies import CookieJar
from drummer.core.engine import send as engine_send
from drummer.core.storage.formats import (
    RequestFile,
    RequestFrontmatter,
    ensure_request_dir,
    parse_request_file,
    write_request_file,
)
from drummer.core.storage.project import (
    Environment,
    list_environments,
    list_request_files,
    load_environment,
    save_environment,
)
from drummer.core.variables import resolve


async def list_requests_impl(project_dir: Path) -> list[dict[str, str]]:
    files = list_request_files(project_dir)
    return [
        {
            "path": str(f.path.relative_to(project_dir)),
            "name": f.frontmatter.name,
            "method": f.frontmatter.method,
            "url": f.frontmatter.url,
        }
        for f in files
    ]


async def get_request_impl(project_dir: Path, path: str) -> dict[str, object]:
    rf = parse_request_file(project_dir / path)
    return rf.frontmatter.model_dump(mode="json")


async def create_request_impl(
    project_dir: Path, path: str, name: str, method: str = "GET", url: str = ""
) -> dict[str, str]:
    full_path = project_dir / path
    ensure_request_dir(full_path)
    fm = RequestFrontmatter.model_validate({"name": name, "method": method, "url": url})
    write_request_file(RequestFile(frontmatter=fm, body="", path=full_path))
    return {"path": path, "name": name}


async def update_request_impl(project_dir: Path, path: str, **kwargs: object) -> dict[str, str]:
    full_path = project_dir / path
    rf = parse_request_file(full_path)
    updates = {k: v for k, v in kwargs.items() if v is not None}
    updated_fm = rf.frontmatter.model_copy(update=updates)
    write_request_file(RequestFile(frontmatter=updated_fm, body=rf.body, path=full_path))
    return {"path": path}


class _SendContext:
    def __init__(self, project_dir: Path, cookie_jar: CookieJar, active_environment: str) -> None:
        self.project_dir = project_dir
        self.cookie_jar = cookie_jar
        self.active_environment = active_environment


async def send_request_impl(
    ctx: _SendContext, path: str, environment: str = "", overrides: dict[str, str] | None = None
) -> dict[str, object]:
    env_name = environment or ctx.active_environment
    request_file = parse_request_file(ctx.project_dir / path)
    env_path = ctx.project_dir / ".drummer" / "environments" / f"{env_name}.yaml"
    env = load_environment(env_path)
    variables: dict[str, str] = {**env.variables, **(overrides or {})}
    resolved = resolve(request_file, variables)
    result = await engine_send(resolved, ctx.cookie_jar)
    return {
        "status_code": result.status_code,
        "url": result.url,
        "headers": result.headers,
        "body": result.body,
        "encoding": result.encoding,
        "elapsed_ms": result.elapsed_ms,
        "warnings": result.warnings,
    }


async def get_history_impl(
    db_factory: async_sessionmaker[AsyncSession], request_path: str = "", limit: int = 50
) -> list[dict[str, object]]:
    async with db_factory() as session:
        stmt = (
            select(ResponseHistoryRecord)
            .order_by(ResponseHistoryRecord.sent_at.desc())
            .limit(limit)
        )
        if request_path:
            stmt = stmt.where(ResponseHistoryRecord.request_path == request_path)
        result = await session.execute(stmt)
        return [r.to_dict() for r in result.scalars().all()]


async def list_environments_impl(project_dir: Path) -> list[dict[str, str]]:
    envs = list_environments(project_dir)
    return [{"name": e.name, "variable_count": str(len(e.variables))} for e in envs]


async def get_environment_impl(project_dir: Path, name: str) -> dict[str, str]:
    env_path = project_dir / ".drummer" / "environments" / f"{name}.yaml"
    env = load_environment(env_path)
    return env.variables


async def set_variable_impl(
    project_dir: Path, environment: str, key: str, value: str
) -> dict[str, str]:
    env_path = project_dir / ".drummer" / "environments" / f"{environment}.yaml"
    env = load_environment(env_path)
    updated = Environment(name=environment, variables={**env.variables, key: value})
    save_environment(updated, project_dir)
    return {key: value}


class _HasActiveEnvironment(Protocol):
    active_environment: str


async def switch_environment_impl(app_state: _HasActiveEnvironment, name: str) -> dict[str, str]:
    app_state.active_environment = name
    return {"active_environment": name}


async def list_cookies_impl(cookie_jar: CookieJar) -> dict[str, dict[str, str]]:
    return cookie_jar.all_cookies()


async def clear_cookies_impl(cookie_jar: CookieJar) -> dict[str, str]:
    cookie_jar.clear()
    return {"status": "cleared"}


def register_mcp_tools(mcp: FastApiMCP, app: FastAPI) -> None:
    # fastapi-mcp 0.4.x exposes REST routes as MCP tools automatically via
    # OpenAPI-to-MCP conversion. The _impl functions above are the pure-Python
    # business logic used directly by tests; they are also reachable through
    # the REST API that fastapi-mcp mirrors into MCP tools.
    pass
