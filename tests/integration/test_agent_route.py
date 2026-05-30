from http import HTTPStatus
from pathlib import Path

from httpx import AsyncClient


def _write_request(project_dir: Path, name: str, body: str) -> None:
    (project_dir / name).write_text(body, encoding="utf-8")


async def test_agent_send_returns_structured_result(
    client_with_mock: AsyncClient, project_dir: Path
) -> None:
    _write_request(
        project_dir, "r.md", '---\nname: R\nmethod: GET\nurl: "https://api.test/x"\n---\n'
    )
    resp = await client_with_mock.post("/api/agent/send", json={"path": "r.md"})
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert data["dry_run"] is False
    assert data["status_code"] == HTTPStatus.OK
    assert data["sent"]["method"] == "GET"
    assert data["sent"]["url"] == "https://api.test/x"
    assert data["body_total_chars"] > 0


async def test_agent_send_dry_run_does_not_send_or_record(
    client_with_mock: AsyncClient, project_dir: Path
) -> None:
    _write_request(project_dir, "d.md", '---\nname: D\nmethod: GET\nurl: "{{base_url}}/x"\n---\n')
    resp = await client_with_mock.post(
        "/api/agent/send",
        json={"path": "d.md", "dry_run": True, "overrides": {"base_url": "https://sub.example"}},
    )
    data = resp.json()
    assert data["dry_run"] is True
    assert data["status_code"] is None
    assert data["sent"]["url"] == "https://sub.example/x"
    assert data["body"] is None
    history = (await client_with_mock.get("/api/history")).json()
    assert all(h["request_path"] != "d.md" for h in history)


async def test_agent_send_extract_returns_value_and_omits_body(
    client_with_mock: AsyncClient, project_dir: Path
) -> None:
    _write_request(
        project_dir, "e.md", '---\nname: E\nmethod: GET\nurl: "https://api.test/x"\n---\n'
    )
    resp = await client_with_mock.post("/api/agent/send", json={"path": "e.md", "extract": "$.ok"})
    data = resp.json()
    assert data["extracted"] == [True]
    assert data["extract_error"] is None
    assert data["body"] is None


async def test_agent_send_extract_error_keeps_body(
    client_with_mock: AsyncClient, project_dir: Path
) -> None:
    _write_request(
        project_dir, "e2.md", '---\nname: E2\nmethod: GET\nurl: "https://api.test/x"\n---\n'
    )
    resp = await client_with_mock.post(
        "/api/agent/send", json={"path": "e2.md", "extract": "$$$bad$$$"}
    )
    data = resp.json()
    assert data["extracted"] is None
    assert data["extract_error"] is not None
    assert data["body"] is not None


async def test_agent_send_truncates_body(client_with_mock: AsyncClient, project_dir: Path) -> None:
    _write_request(
        project_dir, "t.md", '---\nname: T\nmethod: GET\nurl: "https://api.test/x"\n---\n'
    )
    resp = await client_with_mock.post(
        "/api/agent/send", json={"path": "t.md", "max_body_chars": 3}
    )
    data = resp.json()
    assert data["body_truncated"] is True
    assert len(data["body"]) == 3
    assert data["body_total_chars"] > 3


async def test_agent_send_surfaces_unresolved_warnings(
    client_with_mock: AsyncClient, project_dir: Path
) -> None:
    _write_request(
        project_dir, "w.md", '---\nname: W\nmethod: GET\nurl: "https://api.test/{{missing}}"\n---\n'
    )
    resp = await client_with_mock.post("/api/agent/send", json={"path": "w.md"})
    assert "missing" in resp.json()["warnings"]


async def test_agent_send_missing_request_404(client_with_mock: AsyncClient) -> None:
    resp = await client_with_mock.post("/api/agent/send", json={"path": "nope.md"})
    assert resp.status_code == HTTPStatus.NOT_FOUND


async def test_agent_send_rejects_path_traversal(client_with_mock: AsyncClient) -> None:
    resp = await client_with_mock.post("/api/agent/send", json={"path": "../escape.md"})
    assert resp.status_code == HTTPStatus.BAD_REQUEST


async def test_agent_send_malformed_request_file_422(
    client_with_mock: AsyncClient, project_dir: Path
) -> None:
    (project_dir / "bad.md").write_text("---\nthis: is: not: valid: yaml\n---\n", encoding="utf-8")
    resp = await client_with_mock.post("/api/agent/send", json={"path": "bad.md"})
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
