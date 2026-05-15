"""E2E session-scoped server fixtures for pytest-playwright + pytest-bdd."""
import os
import socket
import subprocess
import time

import pytest

from e2e.helpers.seed_projects import seed_project_matrix, teardown_seed_matrix

# Make step definitions discoverable by pytest-bdd
pytest_plugins = [
    "e2e.steps.common_steps",
    "e2e.steps.overview_preconditions",
    "e2e.steps.overview_steps",
]


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
def step_context():
    """Mutable dict shared across steps in a single scenario.

    Named step_context (not context) to avoid shadowing pytest-playwright's
    context fixture which provides the browser context for page creation.

    Function-scoped (default) so values from one scenario never leak into the
    next. Do not elevate this to session or module scope — step definitions store
    page object references here, and those are bound to a single browser page.
    """
    return {}


@pytest.fixture(scope="session")
def flask_server():
    """API base URL for E2E tests.

    When E2E_API_URL is set, uses that URL directly (for running against
    Docker Compose or a deployed environment). Otherwise starts a standalone
    Flask process on port 5001 with mock provider and auth bypass.
    """
    external = os.environ.get("E2E_API_URL")
    if external:
        yield external
        return

    env = {
        **os.environ,
        "CHAIN_PROVIDER": "mock",
        "FLASK_APP": "create_app:create_app",
        "SKIP_AUTH": "1",
        "FLASK_ENV": "development",
    }
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
    """Frontend base URL for E2E tests.

    When E2E_BASE_URL is set, uses that URL directly (for running against
    Docker Compose or a deployed environment). Otherwise starts Angular
    dev server on port 4201.
    """
    external = os.environ.get("E2E_BASE_URL")
    if external:
        yield external
        return

    proc = subprocess.Popen(
        ["npx", "ng", "serve", "--port", "4201", "--poll", "0"],
        cwd=str(os.path.join(os.path.dirname(__file__), "..", "web-ng")),
    )
    _wait_for_port("127.0.0.1", 4201, timeout=120.0)
    yield "http://localhost:4201"
    proc.terminate()
    proc.wait()


@pytest.fixture(scope="session")
def seed_data(flask_server):
    """Provision the eight-project seed matrix once per test session.

    Session-scoped because provisioning writes eight project directories and
    makes one real HTTP call to the bootstrap API. Overview scenarios are
    read-only with respect to seed data — they never modify, rename, or delete
    seeded projects — so sharing the matrix across all scenarios is safe.

    Do not change this to function scope. If a future scenario needs isolated
    write-capable projects, create a separate function-scoped fixture in that
    test module rather than downgrading this one.

    Creates three Specced, two Ready to Build, two Braindumps, and one Active
    project. Projects are written directly to the filesystem (no auth needed)
    except for the Active project which is created via the bootstrap API.

    Yields a SeedMatrix dict with all project metadata so step definitions can
    reference known project names and IDs in assertions.

    A finalizer removes all seeded project directories after the session ends.
    """
    matrix = seed_project_matrix(api_base_url=flask_server)

    yield matrix

    teardown_seed_matrix(matrix)
