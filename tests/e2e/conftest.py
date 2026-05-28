import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

FIXTURE_PROJECT = Path(__file__).parent / "fixtures" / "demo-project"
SERVER_PORT = 8237
_DRUMMER_BIN = Path(sys.executable).parent / "drummer"
_STARTUP_TIMEOUT = 20


def _wait_for_server(host: str, port: int, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return
        except OSError:
            time.sleep(0.25)
    msg = f"Server did not start on {host}:{port} within {timeout}s"
    raise RuntimeError(msg)


@pytest.fixture(scope="session", autouse=True)
def drummer_server():
    proc = subprocess.Popen(
        [str(_DRUMMER_BIN), "serve", "--project", str(FIXTURE_PROJECT), "--port", str(SERVER_PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_server("127.0.0.1", SERVER_PORT, _STARTUP_TIMEOUT)
    except RuntimeError:
        proc.terminate()
        raise
    yield proc
    proc.terminate()
    proc.wait()


@pytest.fixture
def server_url() -> str:
    return f"http://127.0.0.1:{SERVER_PORT}"
