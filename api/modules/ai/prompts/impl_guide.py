# modules/implementation_guide/prompts.py
"""Prompt constructor for implementation guide generation.

build_implementation_guide_prompt() is the sole public export.
No I/O. No imports from modules.data.context — callers supply pre-loaded strings.
"""
from __future__ import annotations

import os

from modules.ai.prompts.builder import PromptBuilder

# ---------------------------------------------------------------------------
# Executor attribution — read once at module load, injected into every prompt
# ---------------------------------------------------------------------------

#: Canonical production model ID. Update with each deployment.
#: Must match DEFAULT_MODEL in modules/chain/adapter.py.
_PRODUCTION_MODEL = "claude-sonnet-4-5"


def _format_model_display(model_id: str) -> str:
    """Convert a model ID to the display name used in Co-Authored-By trailers.

    Examples::

        'claude-sonnet-4-5' -> 'Claude Sonnet 4.5'
        'claude-opus-4-5'   -> 'Claude Opus 4.5'
        'claude-haiku-3-5'  -> 'Claude Haiku 3.5'
        'sonnet-4-5'        -> 'Claude Sonnet 4.5'  (no prefix case)
    """
    stripped = model_id[len("claude-"):] if model_id.startswith("claude-") else model_id
    parts = stripped.split("-")
    if len(parts) >= 3:
        family = parts[0].capitalize()
        version = ".".join(parts[1:])
        return f"Claude {family} {version}"
    # Fallback for unexpected shapes: capitalise and rejoin.
    return "Claude " + " ".join(p.capitalize() for p in parts)


_model_id = os.environ.get("CLAUDE_CODE_MODEL") or _PRODUCTION_MODEL

#: Injected into every impl-guide prompt. Read at import time — the executor
#: model is a deployment-time fact, not a per-request one.
EXECUTOR_ATTRIBUTION = {
    "model_id": _model_id,
    "co_author_trailer": (
        f"Co-Authored-By: {_format_model_display(_model_id)} <noreply@anthropic.com>"
    ),
}


_SYSTEM = "You are a senior engineer writing executor-ready implementation guides."

_USER_HEADER = """\
## Your ONE Job
Produce an executor-ready implementation guide. Every path must be real or \
marked "(new)". Every test must have a complete assertion body. Every step \
must be verifiable.

## Required Sections (exactly 10, in order)
1. Context  2. Pre-flight  3. Files  4. Implementation Steps  5. Tests
6. Commit Plan  7. Verification  8. Rollback  9. Deviations Allowed  10. Out of Scope

## Hard Rules
- NO absolute personal paths (`/Users/...`, `/home/...`, `C:\\Users\\...`). \
Use `{WORKSPACE}` or workspace-relative paths.
- NO empty test bodies. Forbidden patterns: `/* ... */`, `it(name, () => {})`, \
`def test_x(): pass`. Match the repo's test framework with full assertions.
- NO unfilled placeholders: `<placeholder>`, `<TBD>`, `TODO(executor)`, \
`path/to/whatever` — replace every bracket/brace token with a concrete value.
- Your entire response MUST begin with `#`. No preamble. No `Now I have everything…`. \
No `Let me write the guide…`. No `Writing it now.`.
- The `Co-Authored-By` commit trailer in the Commit Plan MUST be copied \
verbatim from the EXECUTOR ATTRIBUTION block. Never invent a model version.
- Use relative test-count deltas (`N → N+K passing`), never absolute baselines (`192 → 216`).

## Output Gate
Your output is checked by `modules.quality.lint.lint_task_guide()` before it \
is written to disk. The QUALITY GATES section below enumerates the rules. \
Errors return 502 and force regeneration; warnings ship with the file. \
Self-check against those rules before emitting.\
"""


def build_implementation_guide_prompt(
    *,
    task_num: str,
    task_name: str,
    task_effort: str,
    task_desc: str,
    arch: str,
    builder: str = "",
    principles: str = "",
    codebase: str = "",
    references: str = "",
    quality: str = "",
    versions: str = "",
    prior: str = "",
) -> tuple[str, str]:
    """Return (system, user) for implementation guide generation.

    All context strings are caller-supplied; this function performs no I/O.

    Args:
        task_num:     Task number string, e.g. "2".
        task_name:    Task name from the epic table, e.g. "Migrate Prompts to Flask".
        task_effort:  Effort string from the epic table, e.g. "1.5 days".
        task_desc:    ### Task N: ... block extracted from epic.md.
        arch:         Full architecture.md content.
        builder:      Builder profile context (optional).
        principles:   Architecture principles context (optional).
        codebase:     Codebase context (optional).
        references:   Reference code context (optional).
        quality:      Quality-gate context (lint + coherence rules) — optional but
                      strongly recommended; lets the model self-check before emit.
        versions:     Deployment fact sheet (model, Python, framework versions) —
                      pins the runtime so the model never invents a version string.
        prior:        Concatenated prior task guide content (optional).
    """
    user = (
        PromptBuilder(_USER_HEADER)
        .section("BUILDER CONTEXT", builder)
        .section("ARCHITECTURE PRINCIPLES", principles)
        .section("CODEBASE CONTEXT", codebase)
        .section("REFERENCE CODE", references)
        .section("DEPLOYMENT VERSIONS", versions)
        .section("QUALITY GATES", quality)
        .section("PRIOR-TASK CONTRACTS", prior)
        .section("EXECUTOR ATTRIBUTION", EXECUTOR_ATTRIBUTION["co_author_trailer"])
        .raw(f"\n\n---\n\n# Task {task_num}: {task_name}\n\n**Effort**: {task_effort}\n\n")
        .raw(f"CONTEXT FROM EPIC:\n{task_desc}\n\n")
        .raw(f"CONTEXT FROM ARCHITECTURE:\n{arch}\n\n")
        .raw("Generate a concrete, executor-ready implementation guide for this task.")
        .build()
    )
    return _SYSTEM, user
