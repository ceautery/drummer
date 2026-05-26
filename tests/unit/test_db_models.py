import json
from datetime import UTC, datetime

from drummer.api.db.models import ResponseHistoryRecord

EXPECTED_STATUS_OK = 200
EXPECTED_ELAPSED_MS = 42.5
EXPECTED_HEADER_COUNT = 2


def test_record_to_dict_roundtrips_fields() -> None:
    sent = datetime(2026, 5, 26, 12, 0, 0, tzinfo=UTC)
    record = ResponseHistoryRecord(
        id="abc-123",
        sent_at=sent,
        request_path="auth/login.md",
        request_name="Login",
        environment="local",
        method="POST",
        url="https://api.example.com/login",
        status_code=200,
        elapsed_ms=42.5,
        request_headers=json.dumps([["content-type", "application/json"]]),
        request_body='{"user": "alice"}',
        response_headers=json.dumps([["set-cookie", "session=abc"]]),
        response_body='{"token": "xyz"}',
        encoding="utf-8",
        warnings=json.dumps(["missing_var"]),
    )
    d = record.to_dict()
    assert d["id"] == "abc-123"
    assert d["sent_at"] == "2026-05-26T12:00:00+00:00"
    assert d["status_code"] == EXPECTED_STATUS_OK
    assert d["elapsed_ms"] == EXPECTED_ELAPSED_MS
    assert d["request_headers"] == [["content-type", "application/json"]]
    assert d["response_headers"] == [["set-cookie", "session=abc"]]
    assert d["warnings"] == ["missing_var"]


def test_record_to_dict_returns_parsed_json_fields() -> None:
    record = ResponseHistoryRecord(
        id="x",
        sent_at=datetime.now(UTC),
        request_path="r.md",
        request_name="R",
        environment="local",
        method="GET",
        url="https://x.com",
        status_code=200,
        elapsed_ms=1.0,
        request_headers=json.dumps([]),
        request_body="",
        response_headers=json.dumps([["content-type", "text/plain"], ["x-custom", "foo"]]),
        response_body="hello",
        encoding="utf-8",
        warnings=json.dumps([]),
    )
    d = record.to_dict()
    assert isinstance(d["response_headers"], list)
    assert len(d["response_headers"]) == EXPECTED_HEADER_COUNT
