import json
from http import HTTPStatus
from typing import cast

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

router = APIRouter()

_INTROSPECTION_QUERY = """
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    subscriptionType { name }
    types { ...FullType }
    directives {
      name
      description
      locations
      args { ...InputValue }
    }
  }
}
fragment FullType on __Type {
  kind
  name
  description
  fields(includeDeprecated: true) {
    name
    description
    args { ...InputValue }
    type { ...TypeRef }
    isDeprecated
    deprecationReason
  }
  inputFields { ...InputValue }
  interfaces { ...TypeRef }
  enumValues(includeDeprecated: true) {
    name
    description
    isDeprecated
    deprecationReason
  }
  possibleTypes { ...TypeRef }
}
fragment InputValue on __InputValue {
  name
  description
  type { ...TypeRef }
  defaultValue
}
fragment TypeRef on __Type {
  kind
  name
  ofType {
    kind
    name
    ofType {
      kind
      name
      ofType {
        kind
        name
        ofType {
          kind
          name
          ofType { kind name ofType { kind name ofType { kind name } } }
        }
      }
    }
  }
}
"""


class IntrospectRequest(BaseModel):
    url: str
    headers: dict[str, str] = Field(default_factory=dict)


@router.post("/graphql/introspect")
async def introspect(body: IntrospectRequest, request: Request) -> JSONResponse:
    transport = cast("httpx.AsyncBaseTransport | None", request.app.state.transport)
    payload = json.dumps({"query": _INTROSPECTION_QUERY}).encode()
    headers = {"Content-Type": "application/json", **body.headers}
    try:
        async with httpx.AsyncClient(transport=transport) as client:
            upstream = await client.post(body.url, content=payload, headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=HTTPStatus.BAD_GATEWAY, detail=str(exc)) from exc
    if not upstream.is_success:
        raise HTTPException(status_code=HTTPStatus.BAD_GATEWAY, detail=upstream.text)
    return JSONResponse(content=upstream.json())
