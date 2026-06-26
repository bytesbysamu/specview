"""Audit coverage for the email service.

Verifies every send outcome is recorded via the house ``audit`` helper:
success carries the Resend provider id, failure carries the error, and an
unset API key is audited as skipped. The contract (returns bool, never raises)
is preserved — auditing only makes the previously-silent result visible.
"""
import structlog

from modules.email import service


class H:
    """Helpers wrapped in a class to dodge this project's permissive
    python_functions glob ('test_*', '*_*'), which would otherwise collect a
    bare module-level helper as a test case."""

    @staticmethod
    def audit_events(captured, event):
        return [e for e in captured if e.get("event") == event]


def test_send_email_audits_success(monkeypatch):
    monkeypatch.setattr(service, "_RESEND_API_KEY", "re_test_key")

    class _FakeEmails:
        @staticmethod
        def send(_payload):
            return {"id": "msg_abc123"}

    fake_resend = type("resend", (), {"api_key": None, "Emails": _FakeEmails})
    monkeypatch.setitem(__import__("sys").modules, "resend", fake_resend)

    with structlog.testing.capture_logs() as cap:
        ok = service.send_email("to@example.com", "Subject", "<p>hi</p>")

    assert ok is True
    sends = H.audit_events(cap, "email.send")
    assert len(sends) == 1
    line = sends[0]
    assert line["audit"] is True
    assert line["outcome"] == "success"
    assert line["to"] == "to@example.com"
    assert line["template"] == "Subject"
    assert line["provider_id"] == "msg_abc123"


def test_send_email_audits_failure(monkeypatch):
    monkeypatch.setattr(service, "_RESEND_API_KEY", "re_test_key")

    class _BoomEmails:
        @staticmethod
        def send(_payload):
            raise RuntimeError("resend 500")

    fake_resend = type("resend", (), {"api_key": None, "Emails": _BoomEmails})
    monkeypatch.setitem(__import__("sys").modules, "resend", fake_resend)

    with structlog.testing.capture_logs() as cap:
        ok = service.send_email("to@example.com", "Subject", "<p>hi</p>")

    assert ok is False  # contract preserved: never raises
    line = H.audit_events(cap, "email.send")[0]
    assert line["outcome"] == "failure"
    assert line["error"] == "resend 500"
    assert line["error_type"] == "RuntimeError"


def test_send_email_audits_skipped_when_key_unset(monkeypatch):
    monkeypatch.setattr(service, "_RESEND_API_KEY", "")

    with structlog.testing.capture_logs() as cap:
        ok = service.send_email("to@example.com", "Subject", "<p>hi</p>")

    assert ok is False
    line = H.audit_events(cap, "email.send")[0]
    assert line["outcome"] == "skipped"
    assert line["reason"] == "resend_api_key_unset"
