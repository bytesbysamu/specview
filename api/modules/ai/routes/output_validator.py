"""Strip markdown fences, parse JSON, validate against skill output_schema."""
from __future__ import annotations

import json
import re
from typing import Any


def parse_and_validate(raw_text: str, output_schema: dict | None = None) -> Any:
    """Strip markdown fences, parse JSON. Validates required fields if output_schema given."""
    clean = re.sub(r'```(?:json)?\n?|\n?```', '', raw_text).strip()
    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError as exc:
        raise ValueError(f"skill output is not valid JSON: {exc}") from exc

    if output_schema:
        _validate_required(parsed, output_schema)

    return parsed


def _validate_required(data: Any, schema: dict) -> None:
    required = schema.get("required", [])
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object, got {type(data).__name__}")
    for field_name in required:
        if field_name not in data:
            raise ValueError(f"required field missing from skill output: {field_name!r}")
