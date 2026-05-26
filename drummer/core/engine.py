import time

import httpx
from pydantic import BaseModel, Field

from drummer.core.cookies import CookieJar
from drummer.core.encoding import decode_body, detect_encoding, encode_body
from drummer.core.storage.formats import CookieConfig, CookieMode, HttpMethod


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
    headers: list[tuple[str, str]]
    body: str
    encoding: str
    elapsed_ms: float
    url: str
    warnings: list[str]


async def send(
    resolved: ResolvedRequest,
    cookie_jar: CookieJar,
    transport: httpx.AsyncBaseTransport | None = None,
) -> RequestResult:
    cookies = cookie_jar.cookies_for_request(
        resolved.url, resolved.cookies.mode, resolved.cookies.cookies
    )
    content = encode_body(resolved.body, resolved.encoding) if resolved.body else None

    async with httpx.AsyncClient(
        transport=transport, cookies=cookies, follow_redirects=False
    ) as client:
        start = time.monotonic()
        response = await client.request(
            method=resolved.method,
            url=resolved.url,
            headers=resolved.headers,
            params=resolved.params,
            content=content,
        )
        elapsed_ms = (time.monotonic() - start) * 1000

    if resolved.cookies.mode == CookieMode.SESSION:
        set_cookie_headers = [
            v for k, v in response.headers.multi_items() if k.lower() == "set-cookie"
        ]
        if set_cookie_headers:
            cookie_jar.update_from_response(str(response.url), set_cookie_headers)

    encoding = detect_encoding(response.headers.get("content-type", ""), response.content)
    body = decode_body(response.content, encoding)

    return RequestResult(
        status_code=response.status_code,
        headers=list(response.headers.multi_items()),
        body=body,
        encoding=encoding,
        elapsed_ms=elapsed_ms,
        url=str(response.url),
        warnings=resolved.warnings,
    )
