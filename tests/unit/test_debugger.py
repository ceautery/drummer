from drummer.core.debugger import suggest


def test_undefined_not_object_suggests_json_check() -> None:
    result = suggest("TypeError: undefined is not an object")
    assert result is not None
    assert "JSON" in result or "Content-Type" in result


def test_timeout_suggests_infinite_loop() -> None:
    result = suggest("InternalError: interrupted")
    assert result is not None
    assert "timed out" in result.lower()


def test_syntax_error_returns_suggestion() -> None:
    result = suggest("SyntaxError: expecting ';'\n    at <input>:3")
    assert result is not None


def test_uncaught_exception_returns_suggestion() -> None:
    result = suggest("ReferenceError: foo is not defined\n    at <eval>")
    assert result is not None


def test_unrecognised_error_returns_none() -> None:
    result = suggest("some completely unknown error message xyz")
    assert result is None


def test_dm_response_in_prescript_suggests_move_to_post() -> None:
    result = suggest("dm.response is not available in pre-scripts")
    assert result is not None
    assert "post-script" in result.lower()


def test_dm_request_read_only_extensible_suggests_pre_script() -> None:
    result = suggest("TypeError: object is not extensible\n    at <anonymous> (<input>)\n")
    assert result is not None
    assert "pre-script" in result.lower()


def test_dm_request_read_only_property_suggests_pre_script() -> None:
    result = suggest("TypeError: 'url' is read-only\n    at <anonymous> (<input>)\n")
    assert result is not None
    assert "pre-script" in result.lower()
