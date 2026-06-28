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
