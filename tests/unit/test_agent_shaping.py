from drummer.core.agent_shaping import extract_jsonpath, truncate_body


def test_extract_jsonpath_matches() -> None:
    body = '{"data": {"items": [{"name": "a"}, {"name": "b"}]}}'
    matches, err = extract_jsonpath(body, "$.data.items[*].name")
    assert err is None
    assert matches == ["a", "b"]


def test_extract_jsonpath_no_match_returns_empty() -> None:
    matches, err = extract_jsonpath('{"a": 1}', "$.nope")
    assert err is None
    assert matches == []


def test_extract_jsonpath_non_json_returns_error() -> None:
    matches, err = extract_jsonpath("not json", "$.a")
    assert matches is None
    assert err is not None


def test_extract_jsonpath_invalid_expression_returns_error() -> None:
    matches, err = extract_jsonpath('{"a": 1}', "$$$bad$$$")
    assert matches is None
    assert err is not None


def test_truncate_body_under_threshold() -> None:
    text, truncated, total = truncate_body("hello", 100)
    assert text == "hello"
    assert truncated is False
    assert total == 5


def test_truncate_body_over_threshold() -> None:
    text, truncated, total = truncate_body("hello world", 5)
    assert text == "hello"
    assert truncated is True
    assert total == 11


def test_truncate_body_none_means_full() -> None:
    text, truncated, total = truncate_body("hello world", None)
    assert text == "hello world"
    assert truncated is False
    assert total == 11
