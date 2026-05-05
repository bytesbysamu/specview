"""Anti-corruption layer: parse ===FILE: {name}=== markers — ported verbatim from references.md:263–341."""
from __future__ import annotations

import re

_FILE_MARKER = re.compile(r"^===FILE:\s*(.+?)\s*===$", re.MULTILINE)
_END_MARKER = re.compile(r"^===END===$", re.MULTILINE)
_LINT_MARKER = re.compile(r"^===LINT===$", re.MULTILINE)
_SCORE_MARKER = re.compile(r"^===SCORE===$", re.MULTILINE)


def parse_file_markers(text: str) -> list[dict[str, str]]:
    """Split marker-delimited text into structured file objects.

    Returns:
        List of {"name": str, "content": str} dicts.

    Raises:
        ValueError: if no ===FILE: {name}=== markers found.
    """
    text = _END_MARKER.sub("", text).rstrip()
    markers = list(_FILE_MARKER.finditer(text))
    if not markers:
        raise ValueError(
            "No ===FILE: {name}=== markers found in output. "
            "Expected multi-file format but got plain text."
        )
    files: list[dict[str, str]] = []
    for i, match in enumerate(markers):
        name = match.group(1).strip()
        start = match.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        content = text[start:end].strip()
        if content:
            files.append({"name": name, "content": content})
    return files


def parse_multi_chain_output(text: str) -> dict:
    """Parse single-call output: ===LINT===, ===FILE:===, ===SCORE===.

    Returns:
        {"files": [{"name": str, "content": str}, ...], "meta": {"lint": str, "score": str}}
    """
    meta: dict[str, str] = {}

    lint_match = _LINT_MARKER.search(text)
    first_file = _FILE_MARKER.search(text)
    if lint_match and first_file and lint_match.start() < first_file.start():
        meta["lint"] = text[lint_match.end():first_file.start()].strip()

    score_match = _SCORE_MARKER.search(text)
    end_match = _END_MARKER.search(text)
    if score_match:
        score_end = (
            end_match.start()
            if end_match and end_match.start() > score_match.start()
            else len(text)
        )
        meta["score"] = text[score_match.end():score_end].strip()

    clean = text
    if lint_match and first_file:
        clean = text[:lint_match.start()] + text[first_file.start():]
    if score_match:
        score_end_pos = (
            end_match.end()
            if end_match and end_match.start() > score_match.start()
            else len(text)
        )
        clean = (
            clean[:clean.find("===SCORE===")] + clean[score_end_pos:]
            if "===SCORE===" in clean
            else clean
        )

    try:
        files = parse_file_markers(clean)
    except ValueError:
        files = [{"name": "output.md", "content": text.strip()}]

    return {"files": files, "meta": meta}
