"""The SOLE HTTP boundary to the shared oll-am **write-service**.

This is the seam that retires specview's per-product text-ops backend. Instead of
holding its OWN per-verb SKILL.md prompts + running them in-process against the
chain adapter (a model call inside specview), the inline text verbs now forward to
the shared write-service (``POST /api/write/<verb>``) and reshape the answer for
specview's frontend. ONE text-ops engine, served by write-service, reused by every
product — the "no backend per product" PoC (humaniz.me migrated its rewrite first).

Lifted verbatim in shape from humaniz's ``backend/write_client.py`` — the seam
differs only in that specview has SEVEN verbs to forward, not one, so this exposes
a generic ``run_verb`` plus a ``rewrite`` (which carries the style→instructions
mapping). Per the http-service-adapter house rule: ONE module wraps the vendor
(here, write-service), a module-level function (not scattered ``requests.post``
calls), an explicit timeout on every call, ``raise_for_status``, and a NARROWED
typed return (only the fields specview's response needs).

write-service endpoints wired (exact field names from
services/write/openapi.yaml → <Verb>Request / <Verb>Response):

  POST /api/write/{expand,compress,clarify,simplify,tldr,bullets}
      req  : {"text": str}
      resp : {"text": str, "provider": str, "model": str}
  POST /api/write/rewrite
      req  : {"text": str, "instructions"?: str}   (strength defaults to "medium")
      resp : {"text": str, "provider": str, "model": str}

All are ``Authorization: Bearer <Core JWT>`` gated. The caller's Core JWT is
forwarded verbatim — write-service does the auth + live-plan gate itself (it calls
Core GET /api/auth/me), so specview does NOT double-gate the model call. Narrowed
here to {"text", "provider", "model"}; the specview action route further reshapes
to the frontend contract {"text", "latencyMs"}.

Auth/gating: a missing/expired token or an over-limit free user surfaces as
write-service's own 401 / 402 / 429 envelope, which the action route relays
verbatim (see ``WriteServiceError.upstream_body``). A transport failure
(write-service down, timeout) has no upstream status → the route maps it to a 502.
"""
from __future__ import annotations

from typing import Optional

import requests

import config

# The six single-input verbs write-service serves at POST /api/write/<verb> with a
# bare {"text": ...} body. ``rewrite`` is handled separately (it carries the
# style→instructions mapping). ``brainstorm`` is intentionally ABSENT — write-service
# has no brainstorm endpoint, so that ONE verb stays local in specview (see actions.py).
VERB_PATHS = {
    "expand": "/api/write/expand",
    "compress": "/api/write/compress",
    "clarify": "/api/write/clarify",
    "simplify": "/api/write/simplify",
    "tldr": "/api/write/tldr",
    "bullets": "/api/write/bullets",
}


class WriteServiceError(RuntimeError):
    """A call to write-service failed (non-2xx, timeout, or unparseable body).

    Carries the upstream HTTP status AND the upstream JSON envelope when known, so
    the specview action route can RELAY write-service's own ``{code, message,
    request_id}`` answer verbatim (a 401 stays a 401, a 402/429 stays a 402/429).
    A transport failure leaves both ``None`` → the route maps it to a 502.
    """

    def __init__(
        self,
        message: str,
        *,
        status: Optional[int] = None,
        body: Optional[dict] = None,
    ):
        super().__init__(message)
        self.upstream_status = status
        self.upstream_body = body


def _url(path: str) -> str:
    return f"{config.write_service_base_url()}{path}"


def _post(path: str, payload: dict, bearer_token: str) -> dict:
    """POST ``payload`` to write-service ``path`` and return the narrowed
    ``{"text", "provider", "model"}``.

    The Core JWT (``bearer_token``) is forwarded as ``Authorization: Bearer`` —
    write-service authenticates the user + gates the plan itself, so specview does
    not double-gate. On any non-2xx, raises ``WriteServiceError`` carrying the
    upstream status + JSON envelope (so the route can relay 401/402/429 verbatim).
    On a transport failure (timeout / connection / unparseable body), raises with
    no status → the route maps it to a 502.
    """
    try:
        resp = requests.post(
            _url(path),
            json=payload,
            headers={
                "Authorization": f"Bearer {bearer_token}",
                "Accept": "application/json",
            },
            timeout=config.WRITE_SERVICE_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        body = resp.json()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        # Best-effort: keep write-service's JSON envelope so the route can relay it.
        upstream_body: Optional[dict] = None
        if exc.response is not None:
            try:
                upstream_body = exc.response.json()
            except ValueError:
                upstream_body = None
        raise WriteServiceError(
            f"write-service POST {path} failed: {exc}",
            status=status,
            body=upstream_body,
        ) from exc
    except (requests.RequestException, ValueError) as exc:
        raise WriteServiceError(f"write-service POST {path} failed: {exc}") from exc

    result_text = (body.get("text") or "").strip()
    if not result_text:
        raise WriteServiceError("write-service response missing text")
    return {
        "text": result_text,
        "provider": body.get("provider") or None,
        "model": body.get("model") or None,
    }


def run_verb(verb: str, text: str, bearer_token: str) -> dict:
    """Relay a single-input verb (expand/compress/clarify/simplify/tldr/bullets)
    to write-service and return the narrowed ``{"text", "provider", "model"}``.

    ``verb`` MUST be a key of ``VERB_PATHS`` — the caller (actions.py) only ever
    routes those six here; ``brainstorm`` stays local and ``rewrite`` has its own
    function. A key miss is a programming error, surfaced as ``WriteServiceError``.
    """
    path = VERB_PATHS.get(verb)
    if path is None:
        raise WriteServiceError(f"no write-service endpoint for verb {verb!r}")
    return _post(path, {"text": text}, bearer_token)


def rewrite(text: str, instructions: Optional[str], bearer_token: str) -> dict:
    """Relay a rewrite to write-service (``POST /api/write/rewrite``).

    ``instructions`` is the free-form requirement string write-service folds into
    every rewrite pass — specview maps its named ``style`` (Concise/Technical/…)
    to an explicit instruction upstream in actions.py. Omitted from the payload
    when falsy so write-service applies its own default. ``strength`` is left to
    write-service's default ("medium"). Returns the narrowed
    ``{"text", "provider", "model"}``.
    """
    payload: dict = {"text": text}
    if instructions:
        payload["instructions"] = instructions
    return _post("/api/write/rewrite", payload, bearer_token)
