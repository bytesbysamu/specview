"""E2E session-scoped server fixtures for pytest-playwright + pytest-bdd."""
import os
import socket
import subprocess
import time

import pytest

# Make step definitions discoverable by pytest-bdd
pytest_plugins = ["e2e.steps.common_steps"]


def _wait_for_port(host: str, port: int, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError(f"Server did not start on {host}:{port} within {timeout}s")


@pytest.fixture
def context():
    """Mutable dict shared across steps in a single scenario."""
    return {}


@pytest.fixture(scope="session")
def flask_server():
    """Start Flask on port 5001 with mock provider."""
    env = {**os.environ, "CHAIN_PROVIDER": "mock", "FLASK_APP": "create_app:create_app"}
    proc = subprocess.Popen(
        ["python", "-m", "flask", "run", "--port", "5001"],
        cwd=str(os.path.join(os.path.dirname(__file__), "..", "api")),
        env=env,
    )
    _wait_for_port("127.0.0.1", 5001)
    yield "http://127.0.0.1:5001"
    proc.terminate()
    proc.wait()


@pytest.fixture(scope="session")
def angular_server():
    """Start Angular dev server on port 4201."""
    proc = subprocess.Popen(
        ["npx", "ng", "serve", "--port", "4201", "--poll", "0"],
        cwd=str(os.path.join(os.path.dirname(__file__), "..", "web-ng")),
    )
    _wait_for_port("127.0.0.1", 4201, timeout=60.0)
    yield "http://localhost:4201"
    proc.terminate()
    proc.wait()
