import pytest
from pydantic import ValidationError

from drummer.core.engine import RequestResult, ResolvedRequest


def test_resolved_request_requires_name() -> None:
    with pytest.raises(ValidationError):
        ResolvedRequest.model_validate({"method": "GET", "url": "https://example.com"})


def test_resolved_request_invalid_method_raises() -> None:
    with pytest.raises(ValidationError):
        ResolvedRequest.model_validate(
            {"name": "test", "method": "INVALID", "url": "https://example.com"}
        )


def test_resolved_request_defaults() -> None:
    rr = ResolvedRequest(name="Test", method="GET", url="https://example.com")
    assert rr.headers == {}
    assert rr.params == {}
    assert rr.body == ""
    assert rr.encoding == "utf-8"
    assert rr.warnings == []


def test_request_result_stores_all_fields() -> None:
    status_code = 200
    elapsed_ms = 42.5
    warnings = ["missing_var"]

    result = RequestResult(
        status_code=status_code,
        headers={"content-type": "application/json"},
        body='{"ok": true}',
        encoding="utf-8",
        elapsed_ms=elapsed_ms,
        url="https://example.com",
        warnings=warnings,
    )
    assert result.status_code == status_code
    assert result.elapsed_ms == elapsed_ms
    assert result.warnings == warnings
