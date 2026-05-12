"""CLI provider — subprocess call to claude CLI.

Auth is handled entirely by the Claude CLI's own persistent session stored in
~/.claude/.credentials.json, which is mounted into the Docker container as a
volume. No ANTHROPIC_CLI_KEY or --bare mode is used.
"""
from __future__ import annotations

import logging
import os
import subprocess

from ..errors import ProviderError

logger = logging.getLogger(__name__)

_CHAIN_AGENT = os.environ.get("CHAIN_AGENT", "")  # e.g. "chain-agent"
_SPEC_DOC_DIR = os.environ.get("SPEC_DOC_DIR", "")  # e.g. "/data/spec-doc"


def _build_cmd(system: str) -> list[str]:
    if _CHAIN_AGENT and not system:
        # Route through the named Claude Code agent only when the caller
        # provides no explicit system prompt (general generation calls).
        # Skill execution passes SKILL.md as the system prompt, which must
        # take precedence — so we fall through to the --system-prompt path.
        cmd = ["claude", "--agent", _CHAIN_AGENT, "-p", "--output-format", "text"]
    else:
        cmd = ["claude", "-p", "--output-format", "text"]
        if system:
            cmd.extend(["--system-prompt", system])
    # Grant data directory access only for agent/generation calls (not skill calls).
    # Skill calls have a system prompt and are self-contained text transforms —
    # they don't need file access, and --add-dir adds ~4s overhead per call.
    if _SPEC_DOC_DIR and not system:
        cmd.extend(["--add-dir", _SPEC_DOC_DIR])
    return cmd


def create_message(
    system: str, prompt: str, *, model: str = "claude-opus-4-6", max_tokens: int = 4096
) -> tuple[str, None, None]:
    """Subprocess-driven CLI call. Returns ``(text, None, None)``."""
    cmd = _build_cmd(system)
    cmd.extend(["--model", model])
    try:
        result = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True, timeout=3600
        )
        if result.returncode != 0:
            stdout_snippet = result.stdout[:200]
            stderr_snippet = result.stderr[:200]
            combined = f"stdout: {stdout_snippet} | stderr: {stderr_snippet}"
            logger.error(
                "cli non_zero_exit model=%s code=%d %s", model, result.returncode, combined
            )
            auth_signal = "401" in combined or "authenticate" in combined.lower()
            status = 401 if auth_signal else 502
            raise ProviderError(
                f"claude CLI exited with code {result.returncode}: {combined}", status
            )
        return result.stdout.strip(), None, None
    except subprocess.TimeoutExpired:
        logger.error("cli_timeout model=%s", model)
        raise ProviderError("claude CLI timed out after 3600s", 504)
    except FileNotFoundError:
        logger.error("cli_not_found — install Claude Code")
        raise ProviderError("claude CLI not found — install Claude Code", 500)


def stream_message(system: str, prompt: str, *, model: str = "claude-opus-4-6", max_tokens: int = 4096):
    text, _, _ = create_message(system, prompt, model=model, max_tokens=max_tokens)
    yield text
