import re

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"dm\.response is not available in pre-scripts", re.IGNORECASE),
        "dm.response is not available in pre-scripts — move this logic to a post-script.",
    ),
    (
        re.compile(r"'[^']*' is read-only|object is not extensible", re.IGNORECASE),
        "dm.request is read-only in post-scripts — move request mutations to a pre-script.",
    ),
    (
        re.compile(r"TypeError.*undefined.*not.*object", re.IGNORECASE),
        "Response may not be JSON — check Content-Type. Try dm.response.text() first.",
    ),
    (
        re.compile(r"InternalError: interrupted"),
        "Script timed out. Check for infinite loops or expensive operations.",
    ),
    (
        re.compile(r"SyntaxError"),
        "Syntax error in script — check for missing brackets, quotes, or semicolons.",
    ),
    (
        re.compile(r"ReferenceError|TypeError"),
        "Uncaught exception — check the stack trace above for the error location.",
    ),
]


def suggest(error: str) -> str | None:
    for pattern, message in _PATTERNS:
        if pattern.search(error):
            return message
    return None
