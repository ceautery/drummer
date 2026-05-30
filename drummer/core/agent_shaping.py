import json

from jsonpath_ng.exceptions import JsonPathLexerError, JsonPathParserError
from jsonpath_ng.ext import parse as jsonpath_parse


def extract_jsonpath(body_text: str, expr: str) -> tuple[list[object] | None, str | None]:
    try:
        data = json.loads(body_text)
    except ValueError:
        return None, "response body is not valid JSON"
    try:
        expression = jsonpath_parse(expr)
    except (JsonPathParserError, JsonPathLexerError) as exc:
        return None, f"invalid JSONPath expression: {exc}"
    return [match.value for match in expression.find(data)], None


def truncate_body(body: str, max_chars: int | None) -> tuple[str, bool, int]:
    total = len(body)
    if max_chars is None or total <= max_chars:
        return body, False, total
    return body[:max_chars], True, total
