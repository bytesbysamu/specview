import os
import re
from pathlib import Path

# Primary: SPEC_DOC_DIR env var (loaded from .env by create_app.py at startup).
# Fallback: parent of flask/ — works when the repo checkout contains the workspace.
_DEFAULT_BASE_DIR = Path(__file__).resolve().parent.parent
BASE_DIR: Path = Path(os.environ.get("SPEC_DOC_DIR") or _DEFAULT_BASE_DIR)

PROJECTS_DIR: Path = BASE_DIR / "projects"

# Static map: context type → filesystem path.
# Architecture decision: static map, no dynamic routing.
CONTEXT_PATHS: dict[str, Path] = {
    "builder":    BASE_DIR / "builder.md",
    "principles": BASE_DIR / "principles.md",
    "codebase":   BASE_DIR / "codebase.md",
    "references": BASE_DIR / "references.md",
    # Self-defensive context blocks — read_context returns "" when the file is
    # absent and PromptBuilder.section() skips empty content, so adding new keys
    # is backward-compatible: deployments without these files behave exactly as
    # before.
    "quality":    BASE_DIR / "quality.md",     # rendered linter + coherence rule list
    "versions":   BASE_DIR / "versions.md",    # deployment fact sheet (model, deps)
}

# Legacy string-keyed alias (for callers still using os.path-style strings).
CONTEXT_FILES: dict[str, str] = {k: str(v) for k, v in CONTEXT_PATHS.items()}


# ── Magic-link per-product verify-page bases ────────────────────────────────
# Core mints sign-in links for many product frontends. The magic-link request
# names a `product`; Core resolves the verify-page base URL from this
# allow-list rather than trusting the request Origin header (which is forgeable
# and absent on service-to-service calls). Configure one env var per product:
#
#   PRODUCT_VERIFY_BASE_<PRODUCT>=https://<frontend-origin>   (PRODUCT upper-cased)
#
# A request with no product — or naming the default product — uses the default
# base, so the existing single-frontend deploy keeps working unchanged. A
# request naming any OTHER product that is not configured is rejected rather
# than silently redirected to the default frontend.

# The product served by the default (FRONTEND_URL/SITE_URL) base.
DEFAULT_PRODUCT: str = (os.environ.get("DEFAULT_PRODUCT") or "specview").strip().lower()


def default_verify_base() -> str:
    """Verify-page base when no product is named (single-frontend default).

    Read at call time so deploy env and tests can override. Falls back to
    SITE_URL, then the public oll.am host.
    """
    return (
        os.environ.get("FRONTEND_URL")
        or os.environ.get("SITE_URL")
        or "https://oll.am"
    ).rstrip("/")


def _product_env_key(product: str) -> str:
    slug = re.sub(r"[^A-Z0-9]+", "_", product.strip().upper()).strip("_")
    return f"PRODUCT_VERIFY_BASE_{slug}"


def verify_base_for_product(product: str | None) -> str | None:
    """Resolve the magic-link verify-page base URL for a ``product`` key.

    - product omitted / equal to ``DEFAULT_PRODUCT`` → the default base.
    - a non-default product configured via ``PRODUCT_VERIFY_BASE_<PRODUCT>`` →
      that base (trailing slash stripped).
    - a non-default product with no configured base → ``None``, signalling the
      caller to reject the request (never leak the link to the wrong origin).
    """
    if not product or product.strip().lower() == DEFAULT_PRODUCT:
        return default_verify_base()
    return (os.environ.get(_product_env_key(product)) or "").rstrip("/") or None


# ── Shared oll-am write-service (the ONE text-ops engine) ────────────────────
# specview's inline text verbs (expand · compress · clarify · simplify · tldr ·
# bullets · rewrite · brainstorm) are NO LONGER served by per-product SKILL.md
# prompts + an in-process model call. All EIGHT are delegated to the shared oll-am
# write-service (POST /api/write/<verb>), which owns BOTH the prompt + the
# oll-model gateway call AND the Core auth/plan gate. This completes the "no
# backend per product" PoC (humaniz.me migrated first) — specview keeps a backend
# only for its stateful surface (spec pipelines, git-backed project data,
# coherence lint), not for flat text ops.
#
# NON-SECRET, so it DEFAULTS to the deployed engine (https://write.oll.am) and is
# NOT required at boot — override WRITE_SERVICE_BASE_URL for local dev (e.g. the
# Docker service name http://write-service:5002 on the shared `ollam` net, or a
# local oll-write). The caller's Bearer JWT is forwarded verbatim; write-service
# does the auth + live-plan gate itself, so specview does not double-gate the model
# call. Config principle: non-secrets get a sensible default in code (configurable
# + simple); only secrets must be set in env.
DEFAULT_WRITE_SERVICE_BASE_URL = "https://write.oll.am"


def write_service_base_url() -> str:
    return (
        os.environ.get("WRITE_SERVICE_BASE_URL") or DEFAULT_WRITE_SERVICE_BASE_URL
    ).rstrip("/")


# Explicit timeout (seconds) on every write-service call — never unbounded. Sized
# to cover write-service's own (possibly multi-pass) model calls, each a gateway
# round-trip. Override via WRITE_SERVICE_HTTP_TIMEOUT.
WRITE_SERVICE_HTTP_TIMEOUT = float(os.environ.get("WRITE_SERVICE_HTTP_TIMEOUT", "90"))
