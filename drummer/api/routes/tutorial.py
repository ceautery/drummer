import json
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Annotated, cast

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from drummer.api.deps import get_cookie_jar
from drummer.core.cookies import CookieJar
from drummer.core.engine import send as engine_send
from drummer.core.storage.formats import HttpMethod, RequestFile, RequestFrontmatter
from drummer.core.variables import resolve

router = APIRouter(prefix="/api/tutorial", tags=["tutorial"])

CookieJarDep = Annotated[CookieJar, Depends(get_cookie_jar)]

_VIRTUAL_PATH = Path("<tutorial>")


class TutorialStep(BaseModel):
    title: str
    instructions: str
    method: HttpMethod | None = None
    url: str = ""
    params: dict[str, str] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    body: str = ""
    pre_script: str = ""
    post_script: str = ""
    variable_overrides: dict[str, str] = Field(default_factory=dict)


STEPS: list[TutorialStep] = [
    TutorialStep(
        title="Welcome to Drummer",
        instructions=(
            "Welcome to Drummer!\n\n"
            "This tutorial walks you through the core features using a sample of the "
            "Metropolitan Museum of Art's collection.\n\n"
            "You'll learn:\n"
            "  • How to send HTTP GET requests\n"
            "  • How to use path and query parameters\n"
            "  • How to manage environment variables\n"
            "  • How to run pre- and post-request scripts\n\n"
            "The mock Met API is built into Drummer — no internet connection required.\n\n"
            "Click Next to send your first request."
        ),
    ),
    TutorialStep(
        title="Your first GET request",
        instructions=(
            "The simplest HTTP request is a GET with no parameters. "
            "It retrieves a resource and returns JSON.\n\n"
            "This request fetches all museum departments — five major collection areas "
            "used to organize the Met's 1.5 million objects.\n\n"
            "Click Send to try it. The response appears on the right."
        ),
        method="GET",
        url="http://localhost:8000/mock/met/departments",
    ),
    TutorialStep(
        title="Path parameters",
        instructions=(
            "REST APIs use path parameters to identify a specific resource. "
            "Instead of listing all objects, you can fetch one by its ID.\n\n"
            "Object 45734 is Van Gogh's Self-Portrait with a Straw Hat (1887). "
            "The ID is embedded directly in the URL path.\n\n"
            "Click Send to retrieve it."
        ),
        method="GET",
        url="http://localhost:8000/mock/met/objects/45734",
    ),
    TutorialStep(
        title="Query parameters",
        instructions=(
            "Query parameters (after the ?) filter or refine a request without "
            "changing the path.\n\n"
            "The search endpoint accepts ?q= to search across title, artist, "
            "and medium. After sending, try changing 'sunflowers' to another term.\n\n"
            "Click Send to search."
        ),
        method="GET",
        url="http://localhost:8000/mock/met/search",
        params={"q": "sunflowers"},
    ),
    TutorialStep(
        title="Environment variables",
        instructions=(
            "Hardcoding http://localhost:8000 in every URL is brittle. "
            "Environment variables let you define base_url once and reuse it.\n\n"
            "Notice the URL uses {{base_url}}. Drummer substitutes the variable "
            "value before sending. The 'local' environment defines "
            "base_url=http://localhost:8000.\n\n"
            "Click Send to see variable substitution in action."
        ),
        method="GET",
        url="{{base_url}}/mock/met/departments",
        variable_overrides={"base_url": "http://localhost:8000"},
    ),
    TutorialStep(
        title="Pre-request scripts",
        instructions=(
            "Pre-request scripts run JavaScript before the HTTP call. "
            "They can read and modify the outgoing request.\n\n"
            "This script sets a custom header using dm.request:\n\n"
            '  dm.request.headers["X-Tutorial-Id"] = "drummer-tutorial-step-6";\n'
            '  dm.console.log("Header set:", dm.request.headers["X-Tutorial-Id"]);\n\n'
            "The dm.console.log output appears in the script output panel below the response.\n\n"
            "Click Send to run it."
        ),
        method="GET",
        url="http://localhost:8000/mock/met/objects/45734",
        pre_script=(
            'dm.request.headers["X-Tutorial-Id"] = "drummer-tutorial-step-6";\n'
            'dm.console.log("Header set:", dm.request.headers["X-Tutorial-Id"]);'
        ),
    ),
    TutorialStep(
        title="Post-request scripts",
        instructions=(
            "Post-request scripts run JavaScript after the HTTP call. "
            "They can read the response and extract data.\n\n"
            "This script reads the JSON response and logs the artwork's details:\n\n"
            "  var obj = dm.response.json();\n"
            '  dm.console.log("Title:", obj.title);\n'
            '  dm.console.log("Artist:", obj.artistDisplayName);\n\n'
            'Use dm.env.set("key", value) to store response data as variables '
            "for use in later requests.\n\n"
            "Click Send to run it."
        ),
        method="GET",
        url="http://localhost:8000/mock/met/objects/45734",
        post_script=(
            "var obj = dm.response.json();\n"
            'dm.console.log("Title:", obj.title);\n'
            'dm.console.log("Artist:", obj.artistDisplayName);'
        ),
    ),
]


def _step_to_request_file(step: TutorialStep) -> RequestFile:
    if step.method is None:
        msg = "step.method must not be None"
        raise ValueError(msg)
    fm = RequestFrontmatter(
        name=step.title,
        method=step.method,
        url=step.url,
        params=step.params,
        headers=step.headers,
        pre_script=step.pre_script,
        post_script=step.post_script,
    )
    return RequestFile(frontmatter=fm, body=step.body, path=_VIRTUAL_PATH)


@router.post("/steps/{step_index}/send")
async def send_tutorial_step(
    step_index: int, request: Request, cookie_jar: CookieJarDep
) -> EventSourceResponse:
    if step_index < 0 or step_index >= len(STEPS):
        raise HTTPException(status_code=404, detail=f"Step {step_index} not found")
    step = STEPS[step_index]
    if step.method is None:
        raise HTTPException(status_code=400, detail="Step has no request to send")

    transport = cast("httpx.AsyncBaseTransport | None", request.app.state.transport)

    async def generate() -> AsyncGenerator[dict[str, str], None]:
        try:
            request_file = _step_to_request_file(step)
            resolved = resolve(request_file, step.variable_overrides)
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
        except (ValueError, httpx.HTTPError, httpx.TransportError) as exc:
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}

    return EventSourceResponse(generate())
