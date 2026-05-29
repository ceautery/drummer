from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi_mcp import FastApiMCP

from drummer.api.db.cookie_persistence import CookiePersistence
from drummer.api.db.session import async_session_factory, init_db
from drummer.api.mcp.tools import register_mcp_tools
from drummer.api.routes import cookies as cookie_routes
from drummer.api.routes import environments as env_routes
from drummer.api.routes import graphql_routes
from drummer.api.routes import history as history_routes
from drummer.api.routes import mock as mock_routes
from drummer.api.routes import project as project_routes
from drummer.api.routes import requests as req_routes
from drummer.api.routes import send as send_routes
from drummer.api.routes import settings as settings_routes
from drummer.api.routes import tutorial as tutorial_routes
from drummer.api.routes import workspaces as workspace_routes
from drummer.core.cookies import CookieJar
from drummer.core.oauth import OAuthTokenCache

_DEFAULT_DB = str(Path.home() / ".local" / "share" / "drummer" / "history.db")
_STATIC_DIR = Path(__file__).parent / "static"


def create_app(
    project_dir: Path | None = None, db_url: str = f"sqlite+aiosqlite:///{_DEFAULT_DB}"
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
        await init_db(db_url)
        await _app.state.cookie_jar.load_from_db()
        yield

    app = FastAPI(title="Drummer", lifespan=lifespan)
    app.state.project_dir = project_dir
    factory = async_session_factory(db_url)
    app.state.cookie_jar = CookieJar(persistence=CookiePersistence(factory))
    app.state.oauth_cache = OAuthTokenCache()
    app.state.active_environment = "local"
    app.state.db_factory = factory
    app.state.transport = None  # overridden in tests

    app.include_router(project_routes.router, prefix="/api")
    app.include_router(settings_routes.router, prefix="/api")
    app.include_router(workspace_routes.router, prefix="/api")
    app.include_router(req_routes.router, prefix="/api")
    app.include_router(env_routes.router, prefix="/api")
    app.include_router(graphql_routes.router, prefix="/api")
    app.include_router(send_routes.router, prefix="/api")
    app.include_router(history_routes.router, prefix="/api")
    app.include_router(cookie_routes.router, prefix="/api")
    app.include_router(mock_routes.router)
    app.include_router(tutorial_routes.router)

    mcp = FastApiMCP(app)
    register_mcp_tools(mcp, app)
    mcp.mount_http()

    if _STATIC_DIR.exists():
        app.mount("/assets", StaticFiles(directory=_STATIC_DIR / "assets"), name="assets")

        async def spa_fallback(_full_path: str) -> FileResponse:
            return FileResponse(_STATIC_DIR / "index.html")

        app.add_api_route("/{_full_path:path}", spa_fallback, include_in_schema=False)

    return app
