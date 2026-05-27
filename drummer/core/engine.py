import time
from typing import Any

import httpx
from pydantic import BaseModel, Field

from drummer.core.cookies import CookieJar
from drummer.core.encoding import decode_body, detect_encoding, encode_body
from drummer.core.scripting import run_script
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
    pre_script: str = ""
    post_script: str = ""
    script_timeout_ms: int = 5000
    variables: dict[str, str] = Field(default_factory=dict)


class RequestResult(BaseModel):
    status_code: int
    headers: list[tuple[str, str]]
    body: str
    encoding: str
    elapsed_ms: float
    url: str
    warnings: list[str]
    script_logs: list[str] = Field(default_factory=list)
    script_error: str | None = None
    script_suggestion: str | None = None


async def send(
    resolved: ResolvedRequest,
    cookie_jar: CookieJar,
    transport: httpx.AsyncBaseTransport | None = None,
) -> RequestResult:
    all_logs: list[str] = []
    script_error: str | None = None
    script_suggestion: str | None = None
    variables = dict(resolved.variables)

    send_url: str = resolved.url
    send_method: str = resolved.method
    send_headers: dict[str, str] = dict(resolved.headers)
    send_params: dict[str, str] = dict(resolved.params)
    send_body: str = resolved.body

    if resolved.pre_script:
        pre = run_script(
            resolved.pre_script,
            variables=variables,
            request_fields={
                "url": send_url,
                "method": send_method,
                "headers": send_headers,
                "params": send_params,
                "body": send_body,
            },
            response_fields=None,
            timeout_ms=resolved.script_timeout_ms,
        )
        all_logs.extend(pre.logs)
        if pre.error:
            return RequestResult(
                status_code=0,
                headers=[],
                body="",
                encoding="utf-8",
                elapsed_ms=0.0,
                url=resolved.url,
                warnings=resolved.warnings,
                script_logs=all_logs,
                script_error=pre.error,
                script_suggestion=pre.suggestion,
            )
        variables.update(pre.env_mutations)
        mut: dict[str, Any] = pre.request_mutations
        send_url = str(mut.get("url", send_url))
        send_method = str(mut.get("method", send_method))
        send_headers = dict(mut.get("headers", send_headers))
        send_params = dict(mut.get("params", send_params))
        send_body = str(mut.get("body", send_body))

    cookies = cookie_jar.cookies_for_request(
        send_url, resolved.cookies.mode, resolved.cookies.cookies
    )
    content = encode_body(send_body, resolved.encoding) if send_body else None

    async with httpx.AsyncClient(
        transport=transport, cookies=cookies, follow_redirects=False
    ) as client:
        start = time.monotonic()
        response = await client.request(
            method=send_method,
            url=send_url,
            headers=send_headers,
            params=send_params,
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

    if resolved.post_script:
        resp_headers: dict[str, str] = dict(response.headers.items())
        post = run_script(
            resolved.post_script,
            variables=variables,
            request_fields={
                "url": send_url,
                "method": send_method,
                "headers": send_headers,
                "params": send_params,
                "body": send_body,
            },
            response_fields={"status": response.status_code, "headers": resp_headers, "body": body},
            timeout_ms=resolved.script_timeout_ms,
        )
        all_logs.extend(post.logs)
        if post.error:
            script_error = post.error
            script_suggestion = post.suggestion

    return RequestResult(
        status_code=response.status_code,
        headers=list(response.headers.multi_items()),
        body=body,
        encoding=encoding,
        elapsed_ms=elapsed_ms,
        url=str(response.url),
        warnings=resolved.warnings,
        script_logs=all_logs,
        script_error=script_error,
        script_suggestion=script_suggestion,
    )
