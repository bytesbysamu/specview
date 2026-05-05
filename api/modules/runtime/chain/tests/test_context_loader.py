"""Context loader tests — mock mode, file reading, missing file, key error."""
import pytest
from modules.runtime.chain import context_loader

# Aliases with no underscores avoid pytest collection under python_functions=["test_*", "*_*"]
loadContext = context_loader.load_context
loadAllContext = context_loader.load_all_context


def mockMode_loadContextReturnsMockString(monkeypatch):
    monkeypatch.setenv("CONTEXT_PROVIDER", "mock")
    assert loadContext("builder") == "MOCK_CONTEXT[builder]"
    assert loadContext("principles") == "MOCK_CONTEXT[principles]"


def mockMode_loadAllContextReturnsFourKeys(monkeypatch):
    monkeypatch.setenv("CONTEXT_PROVIDER", "mock")
    result = loadAllContext()
    assert set(result.keys()) == {"builder", "principles", "codebase", "references"}
    assert all(v.startswith("MOCK_CONTEXT[") for v in result.values())


def unknownContextName_raisesKeyError(monkeypatch):
    monkeypatch.setenv("CONTEXT_PROVIDER", "")
    with pytest.raises(KeyError, match="unknown_key"):
        loadContext("unknown_key")


def existingFile_loadContextReadsContent(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXT_PROVIDER", "")
    monkeypatch.setattr(context_loader, "_CONTEXT_FILES", {
        "builder": tmp_path / "builder.md",
        "principles": tmp_path / "principles.md",
        "codebase": tmp_path / "codebase.md",
        "references": tmp_path / "references.md",
    })
    (tmp_path / "builder.md").write_text("# My Builder Profile\nContent here")
    result = loadContext("builder")
    assert "My Builder Profile" in result
    assert "Content here" in result


def missingFile_loadContextReturnsEmpty(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXT_PROVIDER", "")
    monkeypatch.setattr(context_loader, "_CONTEXT_FILES", {
        "builder": tmp_path / "nonexistent.md",
        "principles": tmp_path / "principles.md",
        "codebase": tmp_path / "codebase.md",
        "references": tmp_path / "references.md",
    })
    result = loadContext("builder")
    assert result == ""


def trailingWhitespace_loadContextStrips(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXT_PROVIDER", "")
    monkeypatch.setattr(context_loader, "_CONTEXT_FILES", {
        "builder": tmp_path / "builder.md",
        "principles": tmp_path / "principles.md",
        "codebase": tmp_path / "codebase.md",
        "references": tmp_path / "references.md",
    })
    (tmp_path / "builder.md").write_text("  content with whitespace  \n\n")
    result = loadContext("builder")
    assert result == "content with whitespace"
