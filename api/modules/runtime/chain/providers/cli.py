"""CLI provider — ported verbatim from references.md:178–225."""
from __future__ import annotations

import logging
import subprocess

from ..errors import ProviderError

logger = logging.getLogger(__name__)


def create_message(
    system: str, prompt: str, *, model: str = "claude-sonnet-4-5", max_tokens: int = 4096
) -> tuple[str, None, None]:
    """Subprocess-driven CLI call. Returns ``(text, None, None)``.

    The ``claude`` CLI does not expose token usage to its callers, so the
    second and third tuple positions are always ``None``. The cost
    accumulator treats ``None`` as zero-cost (developer-laptop fallback).
    """
    cmd = ["claude", "-p", "--output-format", "text"]
    if system:
        cmd.extend(["--system-prompt", system])
    try:
        result = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=3600)
        if result.returncode != 0:
            logger.error("cli non_zero_exit model=%s code=%d", model, result.returncode)
            raise ProviderError(
                f"claude CLI exited with code {result.returncode}: {result.stderr[:200]}", 502
            )
        return result.stdout.strip(), None, None
    except subprocess.TimeoutExpired:
        logger.error("cli_timeout model=%s", model)
        raise ProviderError("claude CLI timed out after 3600s", 504)
    except FileNotFoundError:
        logger.error("cli_not_found — install Claude Code")
        raise ProviderError("claude CLI not found — install Claude Code", 500)


def stream_message(system: str, prompt: str, *, model: str = "claude-sonnet-4-5", max_tokens: int = 4096):
    # CLI does not stream; run single-shot and yield the full result as one chunk
    text, _, _ = create_message(system, prompt, model=model, max_tokens=max_tokens)
    yield text
