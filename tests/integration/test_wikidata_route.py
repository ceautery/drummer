from http import HTTPStatus

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_wikidata_graphql_returns_data(client: AsyncClient) -> None:
    resp = await client.post(
        "/mock/wikidata/graphql", json={"query": '{ entity(id: "Q42") { label } }'}
    )
    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["data"]["entity"]["label"] == "Douglas Adams"


@pytest.mark.asyncio
async def test_wikidata_graphql_variables(client: AsyncClient) -> None:
    query = "query($id: ID!) { entity(id: $id) { author { label } } }"
    resp = await client.post(
        "/mock/wikidata/graphql", json={"query": query, "variables": {"id": "Q3107329"}}
    )
    assert resp.json()["data"]["entity"]["author"]["label"] == "Douglas Adams"
