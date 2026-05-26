import chardet


def detect_encoding(content_type: str, body_bytes: bytes) -> str:
    for part in content_type.split(";"):
        stripped = part.strip()
        if stripped.lower().startswith("charset="):
            return stripped.split("=", 1)[1].strip().strip('"')
    if body_bytes:
        detected = chardet.detect(body_bytes)
        encoding = detected.get("encoding")
        if encoding:
            return encoding
    return "utf-8"


def encode_body(body: str, charset: str) -> bytes:
    return body.encode(charset)


def decode_body(body_bytes: bytes, charset: str) -> str:
    return body_bytes.decode(charset, errors="replace")
