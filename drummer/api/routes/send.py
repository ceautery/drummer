import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, cast
from uuid import uuid4

import httpx
import yaml
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError
from sse_starlette.sse import EventSourceResponse

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from drummer.api.db.models import ResponseHistoryRecord
from drummer.api.deps import get_cookie_jar, get_project_dir
from drummer.core.cookies import CookieJar
from drummer.core.engine import send as engine_send
from drummer.core.storage.formats import parse_request_file
from drummer.core.storage.project import load_environment, load_project
from drummer.core.variables import resolve

router = APIRouter()

ProjectDir = Annotated[Path, Depends(get_project_dir)]
CookieJarDep = Annotated[CookieJar, Depends(get_cookie_jar)]


def _safe_path(project_dir: Path, user_path: str) -> Path:
    resolved = (project_dir / user_path).resolve()
    if not resolved.is_relative_to(project_dir.resolve()):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Invalid path: outside project directory"
        )
    return resolved


class SendRequest(BaseModel):
    path: str
    environment: str = ""
    overrides: dict[str, str] = Field(default_factory=dict)


@router.post("/send")
async def send_request_route(
    body: SendRequest, request: Request, project_dir: ProjectDir, cookie_jar: CookieJarDep
) -> EventSourceResponse:
    environment = body.environment or cast("str", request.app.state.active_environment)
    transport = cast("httpx.AsyncBaseTransport | None", request.app.state.transport)
    db_factory = cast("async_sessionmaker[AsyncSession]", request.app.state.db_factory)

    async def generate() -> AsyncGenerator[dict[str, str], None]:
        try:
            req_path = _safe_path(project_dir, body.path)
            request_file = parse_request_file(req_path)
            env_path = project_dir / ".drummer" / "environments" / f"{environment}.yaml"
            env = load_environment(env_path) if env_path.exists() else None
            variables: dict[str, str] = {**(env.variables if env else {}), **body.overrides}

            project_timeout_ms: int | None = None
            try:
                meta = load_project(project_dir)
                project_timeout_ms = meta.script_timeout_ms
            except (OSError, ValueError):
                pass

            resolved = resolve(request_file, variables, project_timeout_ms=project_timeout_ms)
            result = await engine_send(resolved, cookie_jar, transport=transport)

            if result.script_error and result.status_code == 0:
                yield {
                    "event": "done",
                    "data": json.dumps(
                        {
                            "history_id": None,
                            "script_logs": result.script_logs,
                            "script_error": result.script_error,
                            "script_suggestion": result.script_suggestion,
                        }
                    ),
                }
                return

            yield {
                "event": "status",
                "data": json.dumps({"status_code": result.status_code, "url": result.url}),
            }
            yield {"event": "headers", "data": json.dumps(result.headers)}
            yield {
                "event": "body",
                "data": json.dumps(
                    {
                        "body": result.body,
                        "encoding": result.encoding,
                        "elapsed_ms": result.elapsed_ms,
                    }
                ),
            }

            record_id = str(uuid4())
            async with db_factory() as session:
                record = ResponseHistoryRecord(
                    id=record_id,
                    sent_at=datetime.now(UTC),
                    request_path=body.path,
                    request_name=request_file.frontmatter.name,
                    environment=environment,
                    method=resolved.method,
                    url=result.url,
                    status_code=result.status_code,
                    elapsed_ms=result.elapsed_ms,
                    request_headers=json.dumps(list(resolved.headers.items())),
                    request_body=resolved.body,
                    response_headers=json.dumps(result.headers),
                    response_body=result.body,
                    encoding=result.encoding,
                    warnings=json.dumps(result.warnings),
                )
                session.add(record)
                await session.commit()

            yield {
                "event": "done",
                "data": json.dumps(
                    {
                        "history_id": record_id,
                        "script_logs": result.script_logs,
                        "script_error": result.script_error,
                        "script_suggestion": result.script_suggestion,
                    }
                ),
            }

        except (
            OSError,
            ValueError,
            ValidationError,
            httpx.HTTPError,
            httpx.TransportError,
            yaml.YAMLError,
        ) as exc:
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}

    return EventSourceResponse(generate())
