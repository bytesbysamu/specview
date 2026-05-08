"""CLI provider — subprocess call to claude CLI.

In Docker, set ANTHROPIC_CLI_KEY to the OAuth access token extracted from the
macOS keychain. The provider passes it as ANTHROPIC_API_KEY to the subprocess
and adds --bare so the CLI skips keychain reads.

On the host (mac), leave ANTHROPIC_CLI_KEY unset — the CLI uses the keychain
automatically.
"""
from __future__ import annotations

import logging
import os
import subprocess

from ..errors import ProviderError

logger = logging.getLogger(__name__)

_CLI_KEY = os.environ.get("ANTHROPIC_CLI_KEY", "")
_CHAIN_AGENT = os.environ.get("CHAIN_AGENT", "")  # e.g. "chain-agent"
_SPEC_DOC_DIR = os.environ.get("SPEC_DOC_DIR", "")  # e.g. "/data/spec-doc"


def _build_cmd(system: str) -> list[str]:
    if _CHAIN_AGENT and not system:
        # Route through the named Claude Code agent only when the caller
        # provides no explicit system prompt (general generation calls).
        # Skill execution passes SKILL.md as the system prompt, which must
        # take precedence — so we fall through to the --system-prompt path.
        cmd = ["claude", "--agent", _CHAIN_AGENT, "-p", "--output-format", "text"]
        if _CLI_KEY:
            cmd.append("--bare")  # skip keychain reads in Docker; auth via ANTHROPIC_API_KEY env
    else:
        cmd = ["claude", "-p", "--output-format", "text"]
        if _CLI_KEY:
            cmd.append("--bare")  # skip keychain reads; auth via ANTHROPIC_API_KEY env
        if system:
            cmd.extend(["--system-prompt", system])
    # Grant data directory access only for agent/generation calls (not skill calls).
    # Skill calls have a system prompt and are self-contained text transforms —
    # they don't need file access, and --add-dir adds ~4s overhead per call.
    if _SPEC_DOC_DIR and not system:
        cmd.extend(["--add-dir", _SPEC_DOC_DIR])
    return cmd


def _build_env() -> dict | None:
    if not _CLI_KEY:
        return None
    env = os.environ.copy()
    env["ANTHROPIC_API_KEY"] = _CLI_KEY
    return env


def create_message(
    system: str, prompt: str, *, model: str = "claude-sonnet-4-5", max_tokens: int = 4096
) -> tuple[str, None, None]:
    """Subprocess-driven CLI call. Returns ``(text, None, None)``."""
    cmd = _build_cmd(system)
    env = _build_env()
    try:
        result = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True, timeout=3600, env=env
        )
        if result.returncode != 0:
            logger.error("cli non_zero_exit model=%s code=%d stderr=%s", model, result.returncode, result.stderr[:200])
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
    text, _, _ = create_message(system, prompt, model=model, max_tokens=max_tokens)
    yield text
