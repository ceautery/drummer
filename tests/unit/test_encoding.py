from drummer.core.encoding import decode_body, detect_encoding, encode_body


def test_detect_encoding_prefers_content_type_charset() -> None:
    result = detect_encoding("text/html; charset=windows-1252", b"doesn't matter")
    assert result == "windows-1252"


def test_detect_encoding_charset_case_insensitive() -> None:
    result = detect_encoding("text/html; Charset=UTF-8", b"")
    assert result == "UTF-8"


def test_detect_encoding_falls_back_when_no_charset() -> None:
    body = b'{"hello": "world"}'
    result = detect_encoding("application/json", body)
    assert isinstance(result, str)
    assert len(result) > 0


def test_detect_encoding_falls_back_to_utf8_for_empty_body() -> None:
    result = detect_encoding("", b"")
    assert result == "utf-8"


def test_encode_body_utf8() -> None:
    assert encode_body("Hello", "utf-8") == b"Hello"


def test_encode_body_latin1() -> None:
    assert encode_body("café", "latin-1") == "café".encode("latin-1")


def test_decode_body_utf8() -> None:
    assert decode_body(b"Hello", "utf-8") == "Hello"


def test_decode_body_replaces_bad_bytes() -> None:
    bad_bytes = b"\xff\xfe"
    result = decode_body(bad_bytes, "utf-8")
    assert "�" in result
