"""Generic skill execution — read SKILL.md, call chain_adapter, validate output.

The SKILL.md contains all AI instructions. Python's only job here is:
1. Build the prompt: SKILL.md content + user input
2. Call chain_adapter.generate()
3. Validate and return parsed output

No AI instruction strings live in this file.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from modules.runtime.chain import adapter as chain_adapter
from modules.runtime.chain.errors import ProviderError
from .output_validator import parse_and_validate

logger = logging.getLogger(__name__)


def _skills_dir() -> Path:
    """Return plugin skills directory. Re-evaluated at call time so PLUGIN_DIR changes work."""
    return Path(os.environ.get("PLUGIN_DIR", "/app/plugin")) / "skills"


def load_skill_registry(skill_name: str) -> dict:
    """Read and return skill.json for the named skill. Raises FileNotFoundError if missing."""
    skill_json = _skills_dir() / skill_name / "skill.json"
    with open(skill_json) as f:
        return json.load(f)


def _load_instructions(skill_name: str) -> str:
    """Return SKILL.md content for the named skill."""
    return (_skills_dir() / skill_name / "SKILL.md").read_text()


def run_skill(skill_name: str, user_input: str, registry: dict) -> Any:
    """Execute a skill synchronously. Returns validated parsed output.

    SKILL.md is passed as the system prompt so it governs Claude's behaviour.
    The user_input JSON is the user message.  The CLI provider routes this via
    --system-prompt (not --agent) so the skill instructions take precedence.
    """
    instructions = _load_instructions(skill_name)
    try:
        result = chain_adapter.generate(instructions, user_input)
    except ProviderError as exc:
        raise RuntimeError(f"AI provider error: {exc.message}") from exc

    output_schema = registry.get("output_schema")
    try:
        return parse_and_validate(result.text, output_schema)
    except ValueError as exc:
        raise RuntimeError(f"skill output validation failed: {exc}") from exc


def run_skill_async(skill_name: str, user_input: str, registry: dict, job_id: str) -> None:
    """Execute skill in a background thread. Updates job store on completion or failure."""
    from modules.ai.job_store import complete_job, fail_job
    try:
        result = run_skill(skill_name, user_input, registry)
        complete_job(job_id, result)
        logger.info("skill %s job %s completed", skill_name, job_id)
    except Exception as exc:
        logger.exception("skill %s job %s failed: %s", skill_name, job_id, exc)
        fail_job(job_id, str(exc))
