from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi_mcp import FastApiMCP

from drummer.api.db.session import async_session_factory, init_db
from drummer.api.mcp.tools import register_mcp_tools
from drummer.api.routes import cookies as cookie_routes
from drummer.api.routes import environments as env_routes
from drummer.api.routes import history as history_routes
from drummer.api.routes import requests as req_routes
from drummer.api.routes import send as send_routes
from drummer.core.cookies import CookieJar

_DEFAULT_DB = str(Path.home() / ".local" / "share" / "drummer" / "history.db")


def create_app(project_dir: Path, db_url: str = f"sqlite+aiosqlite:///{_DEFAULT_DB}") -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
        await init_db(db_url)
        yield

    app = FastAPI(title="Drummer", lifespan=lifespan)
    app.state.project_dir = project_dir
    app.state.cookie_jar = CookieJar()
    app.state.active_environment = "local"
    app.state.db_factory = async_session_factory(db_url)
    app.state.transport = None  # overridden in tests

    app.include_router(req_routes.router, prefix="/api")
    app.include_router(env_routes.router, prefix="/api")
    app.include_router(send_routes.router, prefix="/api")
    app.include_router(history_routes.router, prefix="/api")
    app.include_router(cookie_routes.router, prefix="/api")

    mcp = FastApiMCP(app)
    register_mcp_tools(mcp, app)
    mcp.mount_http()

    return app
