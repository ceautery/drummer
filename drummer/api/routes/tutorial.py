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
from drummer.core.storage.formats import GraphQLConfig, HttpMethod, RequestFile, RequestFrontmatter
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
    graphql: GraphQLConfig | None = None


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
            "It retrieves a resource — the response format depends on the endpoint, "
            "though JSON is a common choice for APIs.\n\n"
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
            "Object 436532 is Van Gogh's Self-Portrait with a Straw Hat (1887). "
            "The ID is embedded directly in the URL path.\n\n"
            "Click Send to retrieve it."
        ),
        method="GET",
        url="http://localhost:8000/mock/met/objects/436532",
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
        url="http://localhost:8000/mock/met/objects/436532",
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
        url="http://localhost:8000/mock/met/objects/436532",
        post_script=(
            "var obj = dm.response.json();\n"
            'dm.console.log("Title:", obj.title);\n'
            'dm.console.log("Artist:", obj.artistDisplayName);'
        ),
    ),
    TutorialStep(
        title="Your first GraphQL query",
        instructions=(
            "GraphQL uses a single endpoint and a query that names exactly the fields "
            "you want back.\n\n"
            "This queries Drummer's built-in mock of real Wikidata data. It fetches entity "
            "Q42 (Douglas Adams) and asks for its label, description, and what it is an "
            "instance of.\n\n"
            "The query lives in the Body tab (GraphQL mode). Click Send to run it."
        ),
        method="POST",
        url="http://localhost:8000/mock/wikidata/graphql",
        graphql=GraphQLConfig(
            query=(
                "{\n"
                '  entity(id: "Q42") {\n'
                "    label\n"
                "    description\n"
                "    instanceOf { label }\n"
                "  }\n"
                "}"
            )
        ),
    ),
    TutorialStep(
        title="Nested selection and variables",
        instructions=(
            "GraphQL's strength is following relations in one request. This query starts "
            "from a book and walks to its author, then the author's place of birth, then "
            "that place's country.\n\n"
            "It also uses a GraphQL operation variable, $id, supplied in the Variables "
            "sub-tab — distinct from Drummer's environment variables. Here $id is "
            '"Q3107329" (The Hitchhiker\'s Guide to the Galaxy).\n\n'
            "Click Send, then try changing $id to another entity."
        ),
        method="POST",
        url="http://localhost:8000/mock/wikidata/graphql",
        graphql=GraphQLConfig(
            query=(
                "query ($id: ID!) {\n"
                "  entity(id: $id) {\n"
                "    label\n"
                "    author {\n"
                "      label\n"
                "      placeOfBirth { label country { label } }\n"
                "    }\n"
                "  }\n"
                "}"
            ),
            variables={"id": "Q3107329"},
        ),
    ),
    TutorialStep(
        title="Explore the schema",
        instructions=(
            "Because the mock supports GraphQL introspection, Drummer can show you the "
            "schema. Open the Body tab's Schema sub-tab to browse the Query and Entity "
            "types and their fields — autocomplete in the query editor is driven by the "
            "same introspection.\n\n"
            "This query lists a few entities via search. Click Send to run it, and explore "
            "the Schema sub-tab."
        ),
        method="POST",
        url="http://localhost:8000/mock/wikidata/graphql",
        graphql=GraphQLConfig(query=('{\n  search(term: "novel") {\n    id\n    label\n  }\n}')),
    ),
]


@router.get("/steps")
def list_tutorial_steps() -> list[TutorialStep]:
    return STEPS


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
        graphql=step.graphql,
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
                            "warnings": resolved.warnings,
                            "script_logs": result.script_logs,
                            "script_error": result.script_error,
                            "script_suggestion": result.script_suggestion,
                        }
                    ),
                }
                return

            yield {
                "event": "status",
                "data": json.dumps(
                    {
                        "status_code": result.status_code,
                        "url": result.url,
                        "warnings": resolved.warnings,
                    }
                ),
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
        except (ValueError, httpx.HTTPError) as exc:
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}

    return EventSourceResponse(generate())
