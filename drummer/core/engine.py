from pydantic import BaseModel, Field

from drummer.core.storage.formats import CookieConfig, HttpMethod


class ResolvedRequest(BaseModel):
    name: str
    method: HttpMethod
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    params: dict[str, str] = Field(default_factory=dict)
    body: str = ""
    encoding: str = "utf-8"
    cookies: CookieConfig = Field(default_factory=CookieConfig)
    warnings: list[str] = Field(default_factory=list)


class RequestResult(BaseModel):
    status_code: int
    headers: dict[str, str]
    body: str
    encoding: str
    elapsed_ms: float
    url: str
    warnings: list[str]
