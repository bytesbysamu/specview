"""Tests for cli.py — error signal recovery and success path.

Covers:
- Success path returns (text, None, None)
- Non-auth failure raises ProviderError(502)
- Auth signal in stdout raises ProviderError(401)
- Auth signal in stderr raises ProviderError(401)
- Case-insensitive 'authenticate' detection raises 401
- Literal '401' substring detection raises 401
- Timeout raises ProviderError(504)
- Missing binary raises ProviderError(500)
- Error message contains both stdout and stderr snippets
"""
from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from modules.runtime.chain.errors import ProviderError
from modules.runtime.chain.providers import cli


@pytest.fixture()
def make_proc_result():
    """Return a factory that builds a fake subprocess.CompletedProcess-like namespace."""
    def factory(returncode: int, stdout: str = "", stderr: str = "") -> SimpleNamespace:
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)
    return factory


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------

def test_createMessage_successPath_returnsStrippedTextAndNones(monkeypatch, make_proc_result):
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **kw: make_proc_result(0, stdout="  hello world  ")
    )
    text, t_in, t_out = cli.create_message("sys", "prompt")
    assert text == "hello world"
    assert t_in is None
    assert t_out is None


# ---------------------------------------------------------------------------
# Generic (non-auth) failure — must stay 502
# ---------------------------------------------------------------------------

def test_createMessage_nonAuthFailure_raises502(monkeypatch, make_proc_result):
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **kw: make_proc_result(1, stdout="", stderr="network error")
    )
    with pytest.raises(ProviderError) as excinfo:
        cli.create_message("sys", "prompt")
    assert excinfo.value.status_code == 502


def test_createMessage_nonAuthFailure_messageContainsBothStreams(monkeypatch, make_proc_result):
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **kw: make_proc_result(1, stdout="out_content", stderr="err_content"),
    )
    with pytest.raises(ProviderError) as excinfo:
        cli.create_message("sys", "prompt")
    msg = excinfo.value.message
    assert "out_content" in msg
    assert "err_content" in msg


# ---------------------------------------------------------------------------
# Auth signal in stdout -> 401
# ---------------------------------------------------------------------------

def test_createMessage_authIn401Stdout_raises401(monkeypatch, make_proc_result):
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **kw: make_proc_result(1, stdout="Error 401 Unauthorized", stderr=""),
    )
    with pytest.raises(ProviderError) as excinfo:
        cli.create_message("sys", "prompt")
    assert excinfo.value.status_code == 401


def test_createMessage_authenticateInStdout_raises401(monkeypatch, make_proc_result):
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **kw: make_proc_result(1, stdout="Please authenticate first", stderr=""),
    )
    with pytest.raises(ProviderError) as excinfo:
        cli.create_message("sys", "prompt")
    assert excinfo.value.status_code == 401


def test_createMessage_authenticateCaseInsensitive_raises401(monkeypatch, make_proc_result):
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **kw: make_proc_result(1, stdout="AUTHENTICATE your credentials", stderr=""),
    )
    with pytest.raises(ProviderError) as excinfo:
        cli.create_message("sys", "prompt")
    assert excinfo.value.status_code == 401


# ---------------------------------------------------------------------------
# Auth signal in stderr -> 401
# ---------------------------------------------------------------------------

def test_createMessage_authIn401Stderr_raises401(monkeypatch, make_proc_result):
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **kw: make_proc_result(1, stdout="", stderr="HTTP 401 from auth server"),
    )
    with pytest.raises(ProviderError) as excinfo:
        cli.create_message("sys", "prompt")
    assert excinfo.value.status_code == 401


def test_createMessage_authenticateInStderr_raises401(monkeypatch, make_proc_result):
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **kw: make_proc_result(1, stdout="", stderr="Failed to authenticate with API"),
    )
    with pytest.raises(ProviderError) as excinfo:
        cli.create_message("sys", "prompt")
    assert excinfo.value.status_code == 401


# ---------------------------------------------------------------------------
# Timeout and missing binary
# ---------------------------------------------------------------------------

def test_createMessage_timeout_raises504(monkeypatch):
    def raise_timeout(*a, **kw):
        raise subprocess.TimeoutExpired(cmd=["claude"], timeout=3600)

    monkeypatch.setattr(subprocess, "run", raise_timeout)
    with pytest.raises(ProviderError) as excinfo:
        cli.create_message("sys", "prompt")
    assert excinfo.value.status_code == 504


def test_createMessage_missingBinary_raises500(monkeypatch):
    def raise_not_found(*a, **kw):
        raise FileNotFoundError("No such file")

    monkeypatch.setattr(subprocess, "run", raise_not_found)
    with pytest.raises(ProviderError) as excinfo:
        cli.create_message("sys", "prompt")
    assert excinfo.value.status_code == 500


# ---------------------------------------------------------------------------
# Error message structure
# ---------------------------------------------------------------------------

def test_createMessage_errorMsg_containsExitCode(monkeypatch, make_proc_result):
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **kw: make_proc_result(42, stdout="out", stderr="err")
    )
    with pytest.raises(ProviderError) as excinfo:
        cli.create_message("sys", "prompt")
    assert "42" in excinfo.value.message


def test_createMessage_errorMsg_labelsBothStreams(monkeypatch, make_proc_result):
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **kw: make_proc_result(1, stdout="STDOUT_DATA", stderr="STDERR_DATA"),
    )
    with pytest.raises(ProviderError) as excinfo:
        cli.create_message("sys", "prompt")
    msg = excinfo.value.message
    assert "stdout" in msg.lower()
    assert "stderr" in msg.lower()
