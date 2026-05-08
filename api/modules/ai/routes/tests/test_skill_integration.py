"""Validates each plugin skill without making an AI call."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import modules.ai.routes.generic_skill_service as _skill_svc

SKILLS_DIR = Path(__file__).parents[5] / "plugin" / "skills"
# Only include skills that have both SKILL.md and skill.json (i.e. callable API skills).
# Dev-tool skills (dev-build, dev-test, etc.) are Claude Code skills and have no skill.json.
SKILL_DIRS = [
    p.parent
    for p in SKILLS_DIR.glob("*/SKILL.md")
    if (p.parent / "skill.json").exists()
]


@pytest.mark.parametrize("skill_dir", SKILL_DIRS, ids=lambda p: p.name)
class TestSkillIntegration:
    def test_skill_md_exists(self, skill_dir):
        assert (skill_dir / "SKILL.md").is_file()
        assert (skill_dir / "SKILL.md").read_text().strip()

    def test_skill_json_has_required_keys(self, skill_dir):
        data = json.loads((skill_dir / "skill.json").read_text())
        assert "name" in data
        assert "description" in data
        assert "execution_model" in data

    def test_load_skill_registry_succeeds(self, skill_dir, monkeypatch):
        monkeypatch.setenv("PLUGIN_DIR", str(skill_dir.parents[1]))
        registry = _skill_svc.load_skill_registry(skill_dir.name)
        assert registry["name"] == skill_dir.name

    def test_load_instructions_succeeds(self, skill_dir, monkeypatch):
        monkeypatch.setenv("PLUGIN_DIR", str(skill_dir.parents[1]))
        instructions = _skill_svc._load_instructions(skill_dir.name)
        assert len(instructions) > 0
