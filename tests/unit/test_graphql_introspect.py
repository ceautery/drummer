import pytest
from pydantic import ValidationError

from drummer.api.routes.graphql_routes import IntrospectRequest


def test_introspect_request_requires_url() -> None:
    with pytest.raises(ValidationError):
        IntrospectRequest.model_validate({})


def test_introspect_request_accepts_optional_headers() -> None:
    req = IntrospectRequest.model_validate({"url": "https://api.example.com/graphql"})
    assert req.headers == {}


def test_introspect_request_stores_provided_headers() -> None:
    req = IntrospectRequest.model_validate(
        {"url": "https://api.example.com/graphql", "headers": {"Authorization": "Bearer tok"}}
    )
    assert req.headers["Authorization"] == "Bearer tok"
