"""Tests for modules/ai/routes/output_validator.py.

Pure unit tests — no Flask, no I/O. Covers:
- Markdown fence stripping
- JSON parsing
- Required field validation
- Error cases
"""
from __future__ import annotations

import pytest

from modules.ai.routes.output_validator import parse_and_validate as validate


# ---------------------------------------------------------------------------
# Markdown fence stripping
# ---------------------------------------------------------------------------

def test_parses_plain_json():
    result = validate('{"text": "hello"}')
    assert result == {"text": "hello"}


def test_strips_json_fence():
    raw = '```json\n{"text": "hello"}\n```'
    assert validate(raw) == {"text": "hello"}


def test_strips_plain_fence():
    raw = '```\n{"text": "hello"}\n```'
    assert validate(raw) == {"text": "hello"}


def test_strips_fence_without_trailing_newline():
    raw = '```json\n{"text": "hello"}```'
    assert validate(raw) == {"text": "hello"}


def test_strips_leading_and_trailing_whitespace():
    raw = '  \n  {"text": "hello"}  \n  '
    assert validate(raw) == {"text": "hello"}


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------

def test_parses_nested_object():
    raw = '{"scores": {"clarity": 4}, "issues": ["needs more detail"]}'
    result = validate(raw)
    assert result["scores"]["clarity"] == 4
    assert result["issues"] == ["needs more detail"]


def test_parses_array_values():
    raw = '{"questions": [{"area": "auth"}], "recommendations": [], "rewritten_braindump": "x"}'
    result = validate(raw)
    assert len(result["questions"]) == 1


def test_raises_on_invalid_json():
    with pytest.raises(ValueError, match="not valid JSON"):
        validate("this is not json")


def test_raises_on_truncated_json():
    with pytest.raises(ValueError, match="not valid JSON"):
        validate('{"text": "hello"')


# ---------------------------------------------------------------------------
# Schema validation — required fields
# ---------------------------------------------------------------------------

def test_passes_when_required_fields_present():
    schema = {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}}
    result = validate('{"text": "hello"}', schema)
    assert result["text"] == "hello"


def test_raises_when_required_field_missing():
    schema = {"type": "object", "required": ["text"]}
    with pytest.raises(ValueError, match="required field missing"):
        validate('{"other": "value"}', schema)


def test_raises_when_multiple_required_fields_missing():
    schema = {"type": "object", "required": ["questions", "rewritten_braindump"]}
    with pytest.raises(ValueError, match="required field missing"):
        validate('{"recommendations": []}', schema)


def test_passes_with_no_schema():
    # No schema = no validation — any valid JSON is accepted
    result = validate('{"anything": true}')
    assert result["anything"] is True


def test_raises_when_output_is_not_object_but_schema_expects_one():
    schema = {"type": "object", "required": ["text"]}
    with pytest.raises(ValueError, match="expected JSON object"):
        validate('["not", "an", "object"]', schema)


def test_passes_when_extra_fields_present():
    # Extra fields beyond required are always allowed
    schema = {"type": "object", "required": ["text"]}
    result = validate('{"text": "hi", "extra": 42}', schema)
    assert result["extra"] == 42


def test_fence_stripped_before_schema_validation():
    schema = {"type": "object", "required": ["text"]}
    raw = '```json\n{"text": "stripped and valid"}\n```'
    result = validate(raw, schema)
    assert result["text"] == "stripped and valid"
