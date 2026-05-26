from urllib.parse import urlparse

from drummer.core.storage.formats import CookieMode


class CookieJar:
    def __init__(self) -> None:
        self._store: dict[str, dict[str, str]] = {}  # hostname → {name: value}

    def cookies_for_request(
        self, url: str, mode: CookieMode, explicit: dict[str, str]
    ) -> dict[str, str]:
        if mode == CookieMode.DISABLED:
            return {}
        if mode == CookieMode.EXPLICIT:
            return dict(explicit)
        hostname = urlparse(url).hostname or ""
        return dict(self._store.get(hostname, {}))

    def update_from_response(self, url: str, set_cookie_headers: list[str]) -> None:
        hostname = urlparse(url).hostname or ""
        if hostname not in self._store:
            self._store[hostname] = {}
        for header in set_cookie_headers:
            name_value = header.split(";")[0].strip()
            if "=" in name_value:
                name, _, value = name_value.partition("=")
                if name.strip():
                    self._store[hostname][name.strip()] = value.strip()

    def clear(self) -> None:
        self._store.clear()

    def all_cookies(self) -> dict[str, dict[str, str]]:
        return {hostname: dict(cookies) for hostname, cookies in self._store.items()}
