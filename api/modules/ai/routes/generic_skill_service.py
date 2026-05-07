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


def _build_prompt(skill_name: str, user_input: str) -> str:
    """Prepend SKILL.md instructions to the user input block."""
    skill_md = _skills_dir() / skill_name / "SKILL.md"
    instructions = skill_md.read_text()
    return f"{instructions}\n\n---\n\n{user_input}"


def run_skill(skill_name: str, user_input: str, registry: dict) -> Any:
    """Execute a skill synchronously. Returns validated parsed output."""
    prompt = _build_prompt(skill_name, user_input)
    try:
        result = chain_adapter.generate("", prompt)
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
