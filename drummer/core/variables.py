import base64
import re

from drummer.core.engine import ResolvedRequest
from drummer.core.storage.formats import AuthType, GraphQLConfig, RequestFile

_VAR_RE = re.compile(r"\{\{(\w+)\}\}")
_SCRIPT_TIMEOUT_DEFAULT = 5000


def substitute(text: str, env: dict[str, str]) -> tuple[str, list[str]]:
    warnings: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in env:
            return env[name]
        warnings.append(name)
        return match.group(0)

    return _VAR_RE.sub(_replace, text), warnings


def resolve(
    request_file: RequestFile, env: dict[str, str], project_timeout_ms: int | None = None
) -> ResolvedRequest:
    fm = request_file.frontmatter
    seen: set[str] = set()

    def sub(text: str) -> str:
        result, warns = substitute(text, env)
        seen.update(warns)
        return result

    url = sub(fm.url)
    params = {k: sub(v) for k, v in fm.params.items()}
    headers = {k: sub(v) for k, v in fm.headers.items()}
    body = sub(request_file.body)

    auth = fm.auth
    if auth.type == AuthType.BEARER:
        headers["Authorization"] = f"Bearer {sub(auth.token)}"
    elif auth.type == AuthType.BASIC:
        username = sub(auth.username)
        password = sub(auth.password)
        encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers["Authorization"] = f"Basic {encoded}"
    elif auth.type == AuthType.API_KEY:
        headers[sub(auth.key)] = sub(auth.value)

    effective_timeout = fm.script_timeout_ms or project_timeout_ms or _SCRIPT_TIMEOUT_DEFAULT

    graphql_resolved: GraphQLConfig | None = None
    if fm.graphql is not None:
        graphql_resolved = GraphQLConfig(
            query=sub(fm.graphql.query), variables=fm.graphql.variables
        )

    return ResolvedRequest(
        name=fm.name,
        method=fm.method,
        url=url,
        headers=headers,
        params=params,
        body=body,
        encoding=fm.encoding,
        cookies=fm.cookies,
        warnings=sorted(seen),
        pre_script=fm.pre_script,
        post_script=fm.post_script,
        script_timeout_ms=effective_timeout,
        variables=dict(env),
        graphql=graphql_resolved,
    )
