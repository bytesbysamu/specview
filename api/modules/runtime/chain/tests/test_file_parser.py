"""File parser tests — single file, multi-file, meta sections, edge cases."""
import pytest
from modules.runtime.chain import file_parser as _fp

# Aliases with no underscores avoid pytest collection under python_functions=["test_*", "*_*"]
parseFileMarkers = _fp.parse_file_markers
parseMultiChainOutput = _fp.parse_multi_chain_output


def singleMarker_extractsOneFile():
    text = "===FILE: output.md===\nHello world\n===END==="
    files = parseFileMarkers(text)
    assert len(files) == 1
    assert files[0]["name"] == "output.md"
    assert files[0]["content"] == "Hello world"


def multipleMarkers_extractsFilesInOrder():
    text = (
        "===FILE: a.md===\nContent A\n"
        "===FILE: b.md===\nContent B\n"
        "===END==="
    )
    files = parseFileMarkers(text)
    assert len(files) == 2
    assert files[0]["name"] == "a.md"
    assert "Content A" in files[0]["content"]
    assert files[1]["name"] == "b.md"
    assert "Content B" in files[1]["content"]


def noMarkers_raisesValueError():
    with pytest.raises(ValueError, match="===FILE:"):
        parseFileMarkers("plain text with no markers here")


def endMarker_notIncludedInContent():
    text = "===FILE: doc.md===\nBody\n===END==="
    files = parseFileMarkers(text)
    assert "===END===" not in files[0]["content"]


def spacedFilename_trimmedInOutput():
    text = "===FILE:   spaced.md   ===\nContent\n===END==="
    files = parseFileMarkers(text)
    assert files[0]["name"] == "spaced.md"


def lintSection_extractedInMeta():
    text = (
        "===LINT===\nlint advisory here\n"
        "===FILE: out.md===\nfile content\n"
        "===END==="
    )
    result = parseMultiChainOutput(text)
    assert result["meta"].get("lint") == "lint advisory here"
    assert result["files"][0]["name"] == "out.md"
    assert result["files"][0]["content"] == "file content"


def scoreSection_extractedInMeta():
    text = (
        "===FILE: out.md===\ncontent\n"
        "===SCORE===\n8.5/10\n"
        "===END==="
    )
    result = parseMultiChainOutput(text)
    assert result["meta"].get("score") == "8.5/10"
    assert result["files"][0]["content"] == "content"


def noMarkers_fallsBackToOutputMd():
    text = "no markers here at all, just plain text output"
    result = parseMultiChainOutput(text)
    assert len(result["files"]) == 1
    assert result["files"][0]["name"] == "output.md"
    assert result["files"][0]["content"] == text.strip()
