from enum import StrEnum
from pathlib import Path
from typing import Literal

import frontmatter
from pydantic import BaseModel, Field

HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"]


class CookieMode(StrEnum):
    SESSION = "session"
    DISABLED = "disabled"
    EXPLICIT = "explicit"


class AuthType(StrEnum):
    NONE = "none"
    BEARER = "bearer"
    BASIC = "basic"
    API_KEY = "api_key"


class CookieConfig(BaseModel):
    mode: CookieMode = CookieMode.SESSION
    cookies: dict[str, str] = Field(default_factory=dict)


class AuthConfig(BaseModel):
    type: AuthType = AuthType.NONE
    token: str = ""
    username: str = ""
    password: str = ""
    key: str = ""
    value: str = ""


class GraphQLConfig(BaseModel):
    query: str = ""
    variables: dict[str, str] = Field(default_factory=dict)


class RequestFrontmatter(BaseModel):
    name: str
    method: HttpMethod = "GET"
    url: str = ""
    headers: dict[str, str] = Field(default_factory=dict)
    params: dict[str, str] = Field(default_factory=dict)
    encoding: str = "utf-8"
    cookies: CookieConfig = Field(default_factory=CookieConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    graphql: GraphQLConfig | None = None
    pre_script: str = ""
    post_script: str = ""
    tags: list[str] = Field(default_factory=list)
    skip: bool = False


class RequestFile(BaseModel):
    frontmatter: RequestFrontmatter
    body: str
    path: Path


def parse_request_file(path: Path) -> RequestFile:
    post = frontmatter.load(path)
    fm = RequestFrontmatter.model_validate(post.metadata)
    return RequestFile(frontmatter=fm, body=post.content, path=path)


def write_request_file(request: RequestFile) -> None:
    fm_dict = request.frontmatter.model_dump(exclude_defaults=True, exclude_none=True, mode="json")
    post = frontmatter.Post(request.body, **fm_dict)
    request.path.write_text(frontmatter.dumps(post), encoding="utf-8")


__all__ = [
    "AuthConfig",
    "AuthType",
    "CookieConfig",
    "CookieMode",
    "GraphQLConfig",
    "HttpMethod",
    "RequestFile",
    "RequestFrontmatter",
    "parse_request_file",
    "write_request_file",
]
