"""Unit tests for ``modules.observability.sentry``.

Coverage:
    - DSN-absent path is a silent no-op (no ``sentry_sdk.init`` call).
    - DSN-present path passes the DSN, FlaskIntegration, env, release,
      and traces sample rate kwargs to ``sentry_sdk.init``.
    - ``SENTRY_TRACES_SAMPLE_RATE`` defaults to 0.1 and is overridable.
    - ``APP_ENV`` and ``APP_RELEASE`` defaults are "production" and "dev".
    - ``send_default_pii`` is False by default.
    - ``set_sentry_user`` delegates to ``sentry_sdk.set_user``.

Note: helpers and the production callables are imported through the module
namespace so pytest's permissive ``python_functions = ["test_*", "*_*"]``
collector does not treat them as test cases.
"""

import os
from unittest.mock import patch

import pytest
from flask import Flask
from sentry_sdk.integrations.flask import FlaskIntegration

from modules.observability import sentry as sentry_mod


class H:
    """Helpers wrapped in a class to bypass pytest's permissive collection."""

    @staticmethod
    def env_without(*keys: str) -> dict:
        return {k: v for k, v in os.environ.items() if k not in keys}


class TestInitSentryNoOp:
    def test_no_init_when_dsn_absent(self):
        app = Flask(__name__)
        env = H.env_without("SENTRY_DSN")
        with patch.dict(os.environ, env, clear=True):
            with patch("sentry_sdk.init") as mock_init:
                sentry_mod.init_sentry(app)
                mock_init.assert_not_called()

    def test_no_init_when_dsn_empty_string(self):
        app = Flask(__name__)
        env = H.env_without("SENTRY_DSN")
        env["SENTRY_DSN"] = ""
        with patch.dict(os.environ, env, clear=True):
            with patch("sentry_sdk.init") as mock_init:
                sentry_mod.init_sentry(app)
                mock_init.assert_not_called()


class TestInitSentryActive:
    DSN = "https://key@o0.ingest.sentry.io/123"

    def test_calls_sdk_init_with_dsn(self):
        app = Flask(__name__)
        env = H.env_without("SENTRY_DSN", "SENTRY_TRACES_SAMPLE_RATE",
                            "APP_ENV", "APP_RELEASE")
        env["SENTRY_DSN"] = self.DSN
        with patch.dict(os.environ, env, clear=True):
            with patch("sentry_sdk.init") as mock_init:
                sentry_mod.init_sentry(app)
                mock_init.assert_called_once()
                assert mock_init.call_args.kwargs["dsn"] == self.DSN

    def test_includes_flask_integration(self):
        app = Flask(__name__)
        env = H.env_without("SENTRY_DSN")
        env["SENTRY_DSN"] = self.DSN
        with patch.dict(os.environ, env, clear=True):
            with patch("sentry_sdk.init") as mock_init:
                sentry_mod.init_sentry(app)
                integrations = mock_init.call_args.kwargs.get(
                    "integrations", []
                )
                assert any(
                    isinstance(i, FlaskIntegration) for i in integrations
                )

    def test_traces_sample_rate_defaults_to_0_1(self):
        app = Flask(__name__)
        env = H.env_without("SENTRY_DSN", "SENTRY_TRACES_SAMPLE_RATE")
        env["SENTRY_DSN"] = self.DSN
        with patch.dict(os.environ, env, clear=True):
            with patch("sentry_sdk.init") as mock_init:
                sentry_mod.init_sentry(app)
                rate = mock_init.call_args.kwargs["traces_sample_rate"]
                assert rate == pytest.approx(0.1)

    def test_traces_sample_rate_env_override(self):
        app = Flask(__name__)
        env = H.env_without("SENTRY_DSN", "SENTRY_TRACES_SAMPLE_RATE")
        env["SENTRY_DSN"] = self.DSN
        env["SENTRY_TRACES_SAMPLE_RATE"] = "0.5"
        with patch.dict(os.environ, env, clear=True):
            with patch("sentry_sdk.init") as mock_init:
                sentry_mod.init_sentry(app)
                rate = mock_init.call_args.kwargs["traces_sample_rate"]
                assert rate == pytest.approx(0.5)

    def test_environment_defaults_to_production(self):
        app = Flask(__name__)
        env = H.env_without("SENTRY_DSN", "APP_ENV")
        env["SENTRY_DSN"] = self.DSN
        with patch.dict(os.environ, env, clear=True):
            with patch("sentry_sdk.init") as mock_init:
                sentry_mod.init_sentry(app)
                assert (
                    mock_init.call_args.kwargs["environment"] == "production"
                )

    def test_environment_env_override(self):
        app = Flask(__name__)
        env = H.env_without("SENTRY_DSN", "APP_ENV")
        env["SENTRY_DSN"] = self.DSN
        env["APP_ENV"] = "staging"
        with patch.dict(os.environ, env, clear=True):
            with patch("sentry_sdk.init") as mock_init:
                sentry_mod.init_sentry(app)
                assert mock_init.call_args.kwargs["environment"] == "staging"

    def test_release_defaults_to_dev(self):
        app = Flask(__name__)
        env = H.env_without("SENTRY_DSN", "APP_RELEASE")
        env["SENTRY_DSN"] = self.DSN
        with patch.dict(os.environ, env, clear=True):
            with patch("sentry_sdk.init") as mock_init:
                sentry_mod.init_sentry(app)
                assert mock_init.call_args.kwargs["release"] == "dev"

    def test_release_env_override(self):
        app = Flask(__name__)
        env = H.env_without("SENTRY_DSN", "APP_RELEASE")
        env["SENTRY_DSN"] = self.DSN
        env["APP_RELEASE"] = "spec-doc@deadbeef"
        with patch.dict(os.environ, env, clear=True):
            with patch("sentry_sdk.init") as mock_init:
                sentry_mod.init_sentry(app)
                assert (
                    mock_init.call_args.kwargs["release"]
                    == "spec-doc@deadbeef"
                )

    def test_send_default_pii_is_false(self):
        app = Flask(__name__)
        env = H.env_without("SENTRY_DSN")
        env["SENTRY_DSN"] = self.DSN
        with patch.dict(os.environ, env, clear=True):
            with patch("sentry_sdk.init") as mock_init:
                sentry_mod.init_sentry(app)
                assert mock_init.call_args.kwargs["send_default_pii"] is False


class TestSetSentryUser:
    def test_delegates_to_sdk_set_user(self):
        with patch("sentry_sdk.set_user") as mock_set:
            sentry_mod.set_sentry_user("user-42")
            mock_set.assert_called_once_with({"id": "user-42"})

    def test_does_not_raise_when_dsn_unconfigured(self):
        # sentry_sdk.set_user is safe to call even when init was not run.
        env = H.env_without("SENTRY_DSN")
        with patch.dict(os.environ, env, clear=True):
            sentry_mod.set_sentry_user("anonymous")
