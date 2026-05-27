import subprocess
import sys
import time
from pathlib import Path

import pytest

FIXTURE_PROJECT = Path(__file__).parent / "fixtures" / "demo-project"
SERVER_PORT = 8237
_DRUMMER_BIN = Path(sys.executable).parent / "drummer"


@pytest.fixture(scope="session", autouse=True)
def drummer_server():
    proc = subprocess.Popen(
        [str(_DRUMMER_BIN), "serve", "--project", str(FIXTURE_PROJECT), "--port", str(SERVER_PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)
    yield proc
    proc.terminate()
    proc.wait()


@pytest.fixture
def server_url() -> str:
    return f"http://127.0.0.1:{SERVER_PORT}"
