from fastapi import APIRouter, FastAPI

class FastApiMCP:
    def __init__(
        self,
        fastapi: FastAPI,
        name: str | None = None,
        description: str | None = None,
        describe_all_responses: bool = False,
        describe_full_response_schema: bool = False,
        include_operations: list[str] | None = None,
        exclude_operations: list[str] | None = None,
        include_tags: list[str] | None = None,
        exclude_tags: list[str] | None = None,
        headers: list[str] = ...,
    ) -> None: ...
    def mount_http(
        self, router: FastAPI | APIRouter | None = None, mount_path: str = "/mcp"
    ) -> None: ...
    def mount_sse(
        self, router: FastAPI | APIRouter | None = None, mount_path: str = "/sse"
    ) -> None: ...
    def setup_server(self) -> None: ...
