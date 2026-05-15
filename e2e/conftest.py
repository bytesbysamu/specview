"""E2E session-scoped server fixtures for pytest-playwright + pytest-bdd."""
import json
import os
import socket
import subprocess
import tempfile
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
def scenario_context():
    """Mutable dict shared across steps in a single scenario.

    Function-scoped (default) so values from one scenario never leak into the
    next. Do not elevate this to session or module scope — step definitions store
    page object references here, and those are bound to a single browser page.

    Named scenario_context (not context) to avoid shadowing pytest-playwright's
    built-in 'context' fixture which creates browser contexts.
    """
    return {}


@pytest.fixture
def context(scenario_context):
    """Alias for scenario_context — preserves step definition signatures.

    pytest-playwright's 'context' fixture is only requested by the 'page'
    fixture.  By yielding our dict here *and* not requesting 'page' ourselves,
    we let pytest-playwright's own 'context' win whenever 'page' is resolved.

    However, because pytest resolves fixtures by name and our function-scoped
    'context' shadows the session-scoped playwright one, we need to override
    'page' to break the conflict.
    """
    return scenario_context


@pytest.fixture
def page(browser):
    """Override pytest-playwright's page fixture to avoid the context conflict.

    The default page fixture calls context.new_page(), but our 'context' fixture
    returns a dict.  This override creates the page directly from the browser.
    """
    pg = browser.new_page()
    yield pg
    pg.close()


@pytest.fixture(scope="session")
def flask_server():
    """Start Flask on port 5001 with mock provider and auth bypass for E2E.

    Session-scoped so the server process starts once and is reused across all
    scenarios. Starting a new Flask process per test would add ~1–2 s per
    scenario and destroy the in-process bootstrap job registry that the Active
    seed project depends on.
    """
    env = {
        **os.environ,
        "CHAIN_PROVIDER": "mock",
        "FLASK_APP": "create_app:create_app",
        # SKIP_AUTH=1 + FLASK_ENV=development bypass JWT verification so the
        # seed helpers can call POST /api/projects and bootstrap endpoints
        # with "Bearer test-token" without a real user in the database.
        "SKIP_AUTH": "1",
        "FLASK_ENV": "development",
    }
    import sys
    proc = subprocess.Popen(
        [sys.executable, "-m", "flask", "run", "--port", "5001"],
        cwd=str(os.path.join(os.path.dirname(__file__), "..", "api")),
        env=env,
    )
    _wait_for_port("127.0.0.1", 5001)
    yield "http://127.0.0.1:5001"
    proc.terminate()
    proc.wait()


@pytest.fixture(scope="session")
def angular_server(flask_server):
    """Start Angular dev server on port 4201 with API proxy to E2E Flask.

    Session-scoped for the same reason as flask_server — the Angular build
    takes 15–30 s on first compile and must be shared across scenarios. The
    dev server is stateless from the test perspective; each scenario controls
    state via localStorage and JWT injection, not by restarting the server.

    Depends on flask_server so the proxy target is the E2E Flask instance
    (port 5001) rather than the Docker container (port 8095).
    """
    proxy_conf = {
        "/api": {
            "target": flask_server,
            "secure": False,
            "changeOrigin": True,
        }
    }
    proxy_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix="e2e-proxy-", delete=False
    )
    json.dump(proxy_conf, proxy_file)
    proxy_file.close()

    proc = subprocess.Popen(
        [
            "npx", "ng", "serve",
            "--port", "4201",
            "--host", "127.0.0.1",
            "--proxy-config", proxy_file.name,
            "--poll", "0",
        ],
        cwd=str(os.path.join(os.path.dirname(__file__), "..", "web-ng")),
    )
    _wait_for_port("127.0.0.1", 4201, timeout=120.0)
    yield "http://localhost:4201"
    proc.terminate()
    proc.wait()
    os.unlink(proxy_file.name)


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
