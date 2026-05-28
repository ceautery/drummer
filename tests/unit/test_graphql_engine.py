import json
from pathlib import Path

import httpx

from drummer.core.cookies import CookieJar
from drummer.core.engine import ResolvedRequest, send
from drummer.core.storage.formats import GraphQLConfig, RequestFrontmatter
from drummer.core.storage.project import RequestFile
from drummer.core.variables import resolve

_HTTP_OK = 200


class _MockTransport(httpx.AsyncBaseTransport):
    def __init__(self) -> None:
        self.last_request: httpx.Request | None = None

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.last_request = request
        return httpx.Response(
            status_code=_HTTP_OK,
            headers=[("content-type", "application/json")],
            content=b'{"data": {}}',
            request=request,
        )


def _make_request_file(graphql: GraphQLConfig | None = None, body: str = "") -> RequestFile:
    return RequestFile(
        frontmatter=RequestFrontmatter(
            name="test", method="POST", url="https://api.example.com/graphql", graphql=graphql
        ),
        body=body,
        path=Path("test.md"),
    )


def test_resolve_passes_graphql_through() -> None:
    gql = GraphQLConfig(query="{ departments { id } }", variables={"limit": 10, "active": True})
    rf = _make_request_file(graphql=gql)
    resolved = resolve(rf, {})
    assert resolved.graphql is not None
    assert resolved.graphql.query == "{ departments { id } }"
    assert resolved.graphql.variables == {"limit": 10, "active": True}


def test_resolve_substitutes_variables_in_query() -> None:
    gql = GraphQLConfig(query="query { {{field}} { id } }", variables={})
    rf = _make_request_file(graphql=gql)
    resolved = resolve(rf, {"field": "departments"})
    assert resolved.graphql is not None
    assert resolved.graphql.query == "query { departments { id } }"


def test_resolve_graphql_none_when_not_set() -> None:
    rf = _make_request_file()
    resolved = resolve(rf, {})
    assert resolved.graphql is None


async def test_engine_synthesizes_graphql_body() -> None:
    gql = GraphQLConfig(query="{ departments { id } }", variables={"limit": 5})
    transport = _MockTransport()
    resolved = ResolvedRequest(
        name="test", method="POST", url="https://api.example.com/graphql", graphql=gql
    )
    await send(resolved, CookieJar(), transport=transport)
    assert transport.last_request is not None
    body = json.loads(transport.last_request.content)
    assert body["query"] == "{ departments { id } }"
    assert body["variables"] == {"limit": 5}


async def test_engine_injects_content_type_header() -> None:
    gql = GraphQLConfig(query="{ ok }", variables={})
    transport = _MockTransport()
    resolved = ResolvedRequest(
        name="test", method="POST", url="https://api.example.com/graphql", graphql=gql
    )
    await send(resolved, CookieJar(), transport=transport)
    assert transport.last_request is not None
    assert transport.last_request.headers["content-type"] == "application/json"


async def test_engine_does_not_override_existing_content_type() -> None:
    gql = GraphQLConfig(query="{ ok }", variables={})
    transport = _MockTransport()
    resolved = ResolvedRequest(
        name="test",
        method="POST",
        url="https://api.example.com/graphql",
        headers={"Content-Type": "application/json; charset=utf-8"},
        graphql=gql,
    )
    await send(resolved, CookieJar(), transport=transport)
    assert transport.last_request is not None
    assert transport.last_request.headers["content-type"] == "application/json; charset=utf-8"


async def test_engine_ignores_body_when_graphql_set() -> None:
    gql = GraphQLConfig(query="{ ok }", variables={})
    transport = _MockTransport()
    resolved = ResolvedRequest(
        name="test",
        method="POST",
        url="https://api.example.com/graphql",
        body="should be ignored",
        graphql=gql,
    )
    await send(resolved, CookieJar(), transport=transport)
    assert transport.last_request is not None
    raw = transport.last_request.content.decode()
    assert "should be ignored" not in raw
    assert "query" in json.loads(raw)
