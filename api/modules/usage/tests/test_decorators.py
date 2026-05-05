"""Tests for the `check_usage_limit` Flask decorator.

Covers:
  - Pro user bypasses all DB access
  - Free user under cap → handler runs and counter is incremented
  - Free user at cap → 429 with canonical UsageLimitError body
  - Counter is NOT incremented on 4xx / 5xx responses
  - 429 body honours UPGRADE_URL config and falls back to "/upgrade"
  - 429 body validates against the UsageLimitError DTO
  - `_status_code` helper handles tuple, three-tuple, and Response shapes

Imports are aliased to non-test-name patterns so pytest's
`python_functions = ["test_*", "*_*"]` rule does not collect them as tests.
"""
from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask, g, jsonify

from dtos.models import UsageLimitError as DtoModel
from modules.usage import decorators as decorators_mod
from modules.usage.service import LIMITS as CAPS

gate = decorators_mod.check_usage_limit
getstatus = decorators_mod._status_code


def mkuser(plan: str = "free", uid: int = 1) -> SimpleNamespace:
    return SimpleNamespace(id=uid, plan=plan)


@pytest.fixture
def app():
    a = Flask(__name__)
    a.config["TESTING"] = True
    return a


@pytest.fixture
def fake_session_ctx():
    """Patches `get_session` to yield a MagicMock session."""
    mock_session = MagicMock()

    @contextmanager
    def _ctx():
        yield mock_session

    return _ctx


# --- auth absent (g.current_user not set) ----------------------------------


def test_no_op_when_g_current_user_unset(app, fake_session_ctx):
    """Routes remain callable in pre-auth environments — decorator passes through."""
    with app.test_request_context("/"):
        # Intentionally do NOT set g.current_user.
        with patch("modules.usage.decorators.get_session", fake_session_ctx):
            with patch(
                "modules.usage.decorators.get_remaining"
            ) as mock_remaining, patch(
                "modules.usage.decorators.increment"
            ) as mock_inc:

                @gate("bootstrap")
                def handler():
                    return jsonify({"ok": True}), 200

                _, status = handler()
                assert status == 200
                mock_remaining.assert_not_called()
                mock_inc.assert_not_called()


# --- pro user bypass --------------------------------------------------------


def test_pro_user_bypasses_decorator_entirely(app, fake_session_ctx):
    with app.test_request_context("/"):
        g.current_user = mkuser(plan="pro")
        with patch("modules.usage.decorators.get_session", fake_session_ctx):
            with patch(
                "modules.usage.decorators.get_remaining"
            ) as mock_remaining, patch(
                "modules.usage.decorators.increment"
            ) as mock_inc:

                @gate("bootstrap")
                def handler():
                    return jsonify({"ok": True}), 200

                _, status = handler()
                assert status == 200
                mock_remaining.assert_not_called()
                mock_inc.assert_not_called()


# --- free user under cap ----------------------------------------------------


def test_free_user_under_cap_runs_handler_and_increments(app, fake_session_ctx):
    with app.test_request_context("/"):
        g.current_user = mkuser(plan="free", uid=7)
        with patch("modules.usage.decorators.get_session", fake_session_ctx):
            with patch(
                "modules.usage.decorators.get_remaining", return_value=2
            ):
                with patch(
                    "modules.usage.decorators.increment"
                ) as mock_inc:

                    @gate("bootstrap")
                    def handler():
                        return jsonify({"result": "ok"}), 200

                    body, status = handler()
                    assert status == 200
                    assert body.get_json()["result"] == "ok"
                    mock_inc.assert_called_once()
                    args, _ = mock_inc.call_args
                    assert args[0] == 7
                    assert args[1] == "bootstrap"


# --- free user at cap → 429 -------------------------------------------------


def test_free_user_at_cap_returns_429(app, fake_session_ctx):
    with app.test_request_context("/"):
        g.current_user = mkuser(plan="free", uid=1)
        with patch("modules.usage.decorators.get_session", fake_session_ctx):
            with patch(
                "modules.usage.decorators.get_remaining", return_value=0
            ):
                with patch(
                    "modules.usage.decorators.increment"
                ) as mock_inc:

                    @gate("task_gen")
                    def handler():
                        return jsonify({}), 200

                    body, status = handler()
                    assert status == 429
                    data = body.get_json()
                    assert data["error"] == "free_tier_limit_reached"
                    assert data["feature"] == "task_gen"
                    assert data["limit"] == CAPS["task_gen"]
                    assert "reset_at" in data and data["reset_at"]
                    assert data["upgrade_url"] == "/upgrade"
                    mock_inc.assert_not_called()


def test_429_body_validates_against_usagelimiterror_dto(app, fake_session_ctx):
    with app.test_request_context("/"):
        g.current_user = mkuser(plan="free")
        with patch("modules.usage.decorators.get_session", fake_session_ctx):
            with patch(
                "modules.usage.decorators.get_remaining", return_value=0
            ):

                @gate("spec_gen")
                def handler():
                    return jsonify({}), 200

                body, status = handler()
                assert status == 429
                # Round-trip: must validate cleanly back into the DTO.
                model = DtoModel.model_validate(body.get_json())
                assert model.feature.value == "spec_gen"
                assert model.limit == CAPS["spec_gen"]


def test_429_body_uses_configured_upgrade_url(app, fake_session_ctx):
    app.config["UPGRADE_URL"] = "/billing/upgrade?ref=429"
    with app.test_request_context("/"):
        g.current_user = mkuser(plan="free")
        with patch("modules.usage.decorators.get_session", fake_session_ctx):
            with patch(
                "modules.usage.decorators.get_remaining", return_value=0
            ):

                @gate("bootstrap")
                def handler():
                    return jsonify({}), 200

                body, _ = handler()
                assert body.get_json()["upgrade_url"] == "/billing/upgrade?ref=429"


# --- no increment on error responses ----------------------------------------


@pytest.mark.parametrize("err_status", [400, 401, 422, 500, 502])
def test_counter_not_incremented_on_error_status(app, fake_session_ctx, err_status):
    with app.test_request_context("/"):
        g.current_user = mkuser(plan="free")
        with patch("modules.usage.decorators.get_session", fake_session_ctx):
            with patch(
                "modules.usage.decorators.get_remaining", return_value=3
            ):
                with patch(
                    "modules.usage.decorators.increment"
                ) as mock_inc:

                    @gate("bootstrap")
                    def handler():
                        return jsonify({"error": "x"}), err_status

                    _, status = handler()
                    assert status == err_status
                    mock_inc.assert_not_called()


def test_counter_incremented_on_202_response(app, fake_session_ctx):
    """202 is the bootstrap-project async ack — must still consume quota."""
    with app.test_request_context("/"):
        g.current_user = mkuser(plan="free")
        with patch("modules.usage.decorators.get_session", fake_session_ctx):
            with patch(
                "modules.usage.decorators.get_remaining", return_value=3
            ):
                with patch(
                    "modules.usage.decorators.increment"
                ) as mock_inc:

                    @gate("bootstrap")
                    def handler():
                        return jsonify({"job_id": "x"}), 202

                    _, status = handler()
                    assert status == 202
                    mock_inc.assert_called_once()


# --- _status_code helper ----------------------------------------------------


def test_status_code_from_two_tuple():
    assert getstatus((MagicMock(), 200)) == 200
    assert getstatus((MagicMock(), 429)) == 429


def test_status_code_from_three_tuple():
    assert getstatus((MagicMock(), 400, {"X-H": "v"})) == 400


def test_status_code_from_response_object():
    resp = MagicMock()
    resp.status_code = 201
    assert getstatus(resp) == 201


def test_status_code_defaults_to_200_for_bare_body():
    body = MagicMock(spec=[])  # no status_code attribute
    assert getstatus(body) == 200
