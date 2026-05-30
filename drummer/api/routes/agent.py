import contextlib
import json
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, cast
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from drummer.api.db.models import ResponseHistoryRecord
from drummer.api.deps import get_cookie_jar, get_oauth_cache, get_project_dir
from drummer.core.agent_shaping import extract_jsonpath, truncate_body
from drummer.core.cookies import CookieJar
from drummer.core.engine import SentRequest
from drummer.core.engine import send as engine_send
from drummer.core.oauth import OAuthError, OAuthTokenCache
from drummer.core.storage.formats import parse_request_file
from drummer.core.storage.project import load_environment, load_project
from drummer.core.variables import resolve

router = APIRouter()

ProjectDir = Annotated[Path, Depends(get_project_dir)]
CookieJarDep = Annotated[CookieJar, Depends(get_cookie_jar)]
OAuthCacheDep = Annotated[OAuthTokenCache, Depends(get_oauth_cache)]


def _safe_path(project_dir: Path, user_path: str) -> Path:
    full = (project_dir / user_path).resolve()
    if not full.is_relative_to(project_dir.resolve()):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Invalid path: outside project directory"
        )
    return full


class AgentSendBody(BaseModel):
    path: str
    environment: str = ""
    overrides: dict[str, str] = Field(default_factory=dict)
    dry_run: bool = False
    extract: str | None = None
    max_body_chars: int | None = 2048


class AgentSendResult(BaseModel):
    dry_run: bool
    status_code: int | None
    url: str
    headers: list[tuple[str, str]] = Field(default_factory=list[tuple[str, str]])
    elapsed_ms: float | None
    encoding: str | None
    sent: SentRequest | None
    warnings: list[str] = Field(default_factory=list)
    variables: dict[str, str] = Field(default_factory=dict)
    body: str | None
    body_truncated: bool = False
    body_total_chars: int = 0
    extracted: list[object] | None = None
    extract_error: str | None = None


@router.post("/agent/send", operation_id="agent_send")
async def agent_send_route(
    body: AgentSendBody,
    request: Request,
    project_dir: ProjectDir,
    cookie_jar: CookieJarDep,
    oauth_cache: OAuthCacheDep,
) -> AgentSendResult:
    environment = body.environment or cast("str", request.app.state.active_environment)
    transport = cast("httpx.AsyncBaseTransport | None", request.app.state.transport)

    req_path = _safe_path(project_dir, body.path)
    if not req_path.exists():
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail=f"Request not found: {body.path}"
        )
    request_file = parse_request_file(req_path)

    env_path = project_dir / ".drummer" / "environments" / f"{environment}.yaml"
    env = load_environment(env_path) if env_path.exists() else None
    variables: dict[str, str] = {**(env.variables if env else {}), **body.overrides}

    project_timeout_ms: int | None = None
    with contextlib.suppress(OSError, ValueError):
        project_timeout_ms = load_project(project_dir).script_timeout_ms

    resolved = resolve(request_file, variables, project_timeout_ms=project_timeout_ms)

    if body.dry_run:
        return AgentSendResult(
            dry_run=True,
            status_code=None,
            url=resolved.url,
            headers=[],
            elapsed_ms=None,
            encoding=None,
            sent=SentRequest(
                method=resolved.method,
                url=resolved.url,
                params=resolved.params,
                headers=resolved.headers,
                body=resolved.body,
            ),
            warnings=resolved.warnings,
            variables=dict(variables),
            body=None,
        )

    try:
        result = await engine_send(
            resolved, cookie_jar, oauth_cache=oauth_cache, transport=transport
        )
    except (httpx.HTTPError, OAuthError) as exc:
        raise HTTPException(
            status_code=HTTPStatus.BAD_GATEWAY, detail=f"Request failed: {exc}"
        ) from exc

    extracted: list[object] | None = None
    extract_error: str | None = None
    out_body: str | None
    truncated = False
    total_chars = len(result.body)

    if body.extract is not None:
        matches, err = extract_jsonpath(result.body, body.extract)
        if err is not None:
            extract_error = err
            out_body, truncated, total_chars = truncate_body(result.body, body.max_body_chars)
        else:
            extracted = matches
            out_body = None
    else:
        out_body, truncated, total_chars = truncate_body(result.body, body.max_body_chars)

    if not (result.script_error and result.status_code == 0):
        db_factory = cast("async_sessionmaker[AsyncSession]", request.app.state.db_factory)
        async with db_factory() as session:
            session.add(
                ResponseHistoryRecord(
                    id=str(uuid4()),
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
            )
            await session.commit()

    return AgentSendResult(
        dry_run=False,
        status_code=result.status_code,
        url=result.url,
        headers=result.headers,
        elapsed_ms=result.elapsed_ms,
        encoding=result.encoding,
        sent=result.sent,
        warnings=result.warnings,
        variables=result.variables,
        body=out_body,
        body_truncated=truncated,
        body_total_chars=total_chars,
        extracted=extracted,
        extract_error=extract_error,
    )
