# Task 4: Observability + Test Conventions — Implementation Guide

## 1. Context

This task adds `logger = logging.getLogger(__name__)` to `flask/modules/projects/routes.py` and both chain providers that lack it, a shared `logging.basicConfig(INFO)` call in `create_app.py`, elapsed-time log lines in `adapter.py`, a `make_project_dir` factory in `conftest.py` that replaces repeated ten-line inline setups, and `condition_expectedOutcome` renames across all 11 test files. None of these changes are visible to the Angular frontend; all of them improve debuggability and establish the naming baseline Phase 2 test authors will inherit.

**Trade-offs considered:**
- **`scope="session"` for the app fixture** — rejected: test_project.py and test_context_files.py monkeypatch module-level attributes; session scope would leak mutations between test files.
- **Per-provider loggers in `adapter.py` only** — rejected: the architecture specifies loggers in *each* provider file so that log lines carry the exact provider module path (e.g., `modules.chain.providers.claude`) rather than the adapter wrapper.
- **`python_functions = ["test_*", "[a-z]*_[a-z]*"]`** — rejected in favor of the architecture-specified `["test_*", "*_*"]`; the simpler pattern is what the architecture doc encodes; private helpers are renamed to camelCase in the same commit to neutralize spurious collection.

---

## 2. Pre-flight

```bash
cd {WORKSPACE}/flask                          # all commands below are flask/-relative
git status                                    # confirm clean working tree on target files
git diff HEAD -- tests/ modules/ create_app.py pyproject.toml  # should be empty
python -m pytest --tb=short 2>&1 | tail -5   # record baseline pass count
```

**Baseline recorded**: run `--collect-only` to confirm exact count:
```bash
python -m pytest --collect-only -q 2>&1 | tail -3
```

Expected baseline (no pyproject.toml yet; only `test_*` collected):
- `tests/test_health.py`: 10
- `tests/test_project.py`: 31
- `tests/test_context_files.py`: 21 (4+4+4+1+4+1+1+1 parametrized)
- `tests/test_dtos.py`: 11
- `tests/test_openapi_spec.py`: 51 (8+14+13+3 parametrized + 13 plain)
- `tests/test_ai_rewrite.py`: 10
- `modules/chain/tests/test_adapter.py`: 7
- `modules/chain/tests/test_context_loader.py`: 6
- `modules/chain/tests/test_file_parser.py`: 8
- `modules/chain/tests/test_structural.py`: 1
- `modules/ai/tests/test_prompts.py`: 16

**Total baseline: ~172 passing.** Record actual number before editing.

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

---

## 3. Files

### To Create (new)
- *(none — `pyproject.toml` is created by Task 1 Step 2; this task depends on Task 1 having landed so `python_functions = ["test_*", "*_*"]` is already active)*

### To Modify (cite CODEBASE CONTEXT)
- `flask/create_app.py` — add `import logging` + `logging.basicConfig(INFO, format=...)` at module level
- `flask/modules/projects/routes.py` — add `logger = logging.getLogger(__name__)` + use in `except Exception` blocks
- `flask/modules/chain/providers/claude.py` — add `logger = logging.getLogger(__name__)` + log in error branches
- `flask/modules/chain/providers/cli.py` — add `logger = logging.getLogger(__name__)` + log in error branches
- `flask/modules/chain/adapter.py` — add `logger = logging.getLogger(__name__)` + `logger.info(...)` after `latency_ms` is computed
- `flask/tests/conftest.py` — add `make_project_dir` factory fixture (import `json` and `Path`)
- `flask/tests/test_project.py` — rename `_seed_project` → `_seedProject`, simplify `project_dir` fixture to use `make_project_dir`, rename all 31 test functions
- `flask/tests/test_health.py` — rename all 10 test functions
- `flask/tests/test_context_files.py` — rename all 9 test function names (parametrized ids stay as-is)
- `flask/tests/test_dtos.py` — rename helper `_openapi_schema_names` → `_openapiSchemaNames`, rename all 11 test functions
- `flask/tests/test_openapi_spec.py` — rename all 16 test function names
- `flask/tests/test_ai_rewrite.py` — rename all 10 functions (strip `test_` prefix only)
- `flask/modules/chain/tests/test_adapter.py` — rename all 7 test functions
- `flask/modules/chain/tests/test_context_loader.py` — rename all 6 test functions
- `flask/modules/chain/tests/test_file_parser.py` — rename all 8 test functions
- `flask/modules/chain/tests/test_structural.py` — rename 1 test function
- `flask/modules/ai/tests/test_prompts.py` — rename all 16 functions (strip `test_` prefix only)

### To Leave Alone
- `flask/modules/context/service.py` — already has `logger = logging.getLogger(__name__)` on line 6
- `flask/modules/context/routes.py` — already has `logger = logging.getLogger(__name__)` on line 11
- `flask/modules/chain/providers/mock.py` — pure deterministic function; no I/O, no logger needed
- `flask/modules/chain/tests/test_structural.py` — only structural change is the function rename (above)
- All `__init__.py` files — empty; no logger needed

---

## 4. Implementation Steps

### Step 1: Rename private helpers to camelCase (avoid spurious collection under `*_*`)

**Prerequisite**: Task 1 has landed — confirm with `test -f flask/pyproject.toml && grep -q 'python_functions' flask/pyproject.toml`. If `pyproject.toml` doesn't exist or lacks `python_functions`, stop and run Task 1 first.

**Action**: Rename `_seed_project` → `_seedProject` in `test_project.py` and `_openapi_schema_names` → `_openapiSchemaNames` in `test_dtos.py`. With Task 1's `python_functions = ["test_*", "*_*"]` active, snake_case helpers would be collected as tests; camelCase avoids the collision.

**File**: `flask/tests/test_project.py` — rename helper only (no logic change)
```python
# Before
def _seed_project(tmp_path: Path, project_id: str = "p-1700000000000"):
    ...

# After — camelCase avoids *_* collection by pytest
def _seedProject(tmp_path: Path, project_id: str = "p-1700000000000"):
    ...
```

Update the three callers in the same file:
```python
# Before (lines 274, 285, 345)
_seed_project(tmp_path)
# After
_seedProject(tmp_path)
```

**File**: `flask/tests/test_dtos.py` — rename helper only
```python
# Before (line 34)
def _openapi_schema_names() -> set[str]:
# After
def _openapiSchemaNames() -> set[str]:
```

Update both callers in `test_dtos.py` (lines 52, 68).

**Verify**:
```bash
python -m pytest --collect-only -q 2>&1 | grep "_seed\|_openapi_schema"
```
Expect: zero lines — neither helper is collected.

---

### Step 2: Add logging config to `create_app.py`

**Action**: Add `import logging` and a `basicConfig` call at module level before `create_app`. This establishes INFO as the root logger level; all `getLogger(__name__)` loggers inherit it automatically.

**File**: `flask/create_app.py` (CODEBASE CONTEXT: `flask/create_app.py`)

**Pattern** — insert at top of file after existing imports:
```python
import logging
import importlib
from flask import Flask, jsonify
from flask_cors import CORS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

ENABLED_MODULES = [...]  # unchanged
```

**Verify**:
```bash
python -c "from create_app import create_app; import logging; \
  assert logging.getLogger().level == logging.INFO, 'root logger not INFO'"
```

---

### Step 3: Add logger to `modules/projects/routes.py` and use in `except` blocks

**Action**: Add module-level logger. Replace bare `except Exception:` in all five route handlers with `logger.error(..., exc_info=True)` before the `jsonify` return.

**File**: `flask/modules/projects/routes.py` (CODEBASE CONTEXT: `flask/modules/projects/routes.py`)

**Pattern** — after the `from .service import ...` block (line 26):
```python
import logging

logger = logging.getLogger(__name__)
```

Update all five `except Exception` handlers (lines 36–92):
```python
# list_projects_route (line 36)
except Exception:
    logger.error("list_projects failed", exc_info=True)
    return jsonify({"error": "Failed to list projects"}), 500

# get_project_route
except Exception:
    logger.error("get_project failed project_id=%s", project_id, exc_info=True)
    return jsonify({"error": "Failed to get project"}), 500

# create_project_route
except Exception:
    logger.error("create_project failed name=%s", name, exc_info=True)
    return jsonify({"error": "Failed to create project"}), 500

# update_file_route
except Exception:
    logger.error("update_file failed project_id=%s filename=%s", project_id, filename, exc_info=True)
    return jsonify({"error": "Failed to update file"}), 500

# delete_project_route
except Exception:
    logger.error("delete_project failed project_id=%s", project_id, exc_info=True)
    return jsonify({"error": "Failed to delete project"}), 500
```

**Verify**:
```bash
python -c "from modules.projects.routes import logger; \
  assert logger.name == 'modules.projects.routes'"
```

---

### Step 4: Add logger to `modules/chain/providers/claude.py`

**Action**: Add module-level logger and log warning/error in each exception branch. The `create_message` and `stream_message` functions already raise `ProviderError`; add a `logger.warning` or `logger.error` before each raise so the stack trace appears in logs.

**File**: `flask/modules/chain/providers/claude.py` (CODEBASE CONTEXT: chain provider)

**Pattern** — add after the `from ..errors import ProviderError` import:
```python
import logging

logger = logging.getLogger(__name__)
```

Update `create_message` error branches:
```python
except RateLimitError:
    logger.warning("claude rate_limit model=%s", model)
    raise ProviderError("AI service is busy. Please try again in a moment.", 503)
except APIConnectionError:
    logger.error("claude connection_failed model=%s", model, exc_info=True)
    raise ProviderError("Cannot connect to AI service. Please try again.", 502)
except APIError as e:
    logger.error("claude api_error model=%s", model, exc_info=True)
    raise ProviderError(f"AI service error: {e.message}", 502)
```

Apply the same pattern to `stream_message` (the `except` branches that currently `yield` error strings).

**Verify**:
```bash
python -c "from modules.chain.providers.claude import logger; \
  assert logger.name == 'modules.chain.providers.claude'"
```

---

### Step 5: Add logger to `modules/chain/providers/cli.py`

**Action**: Add module-level logger and log before each `ProviderError` raise.

**File**: `flask/modules/chain/providers/cli.py` (CODEBASE CONTEXT: chain provider)

**Pattern** — add after `from ..errors import ProviderError`:
```python
import logging

logger = logging.getLogger(__name__)
```

Update error branches in `create_message`:
```python
except subprocess.TimeoutExpired:
    logger.error("cli_timeout model=%s", model)
    raise ProviderError("claude CLI timed out after 600s", 504)
except FileNotFoundError:
    logger.error("cli_not_found — install Claude Code")
    raise ProviderError("claude CLI not found — install Claude Code", 500)
```

**Verify**:
```bash
python -c "from modules.chain.providers.cli import logger; \
  assert logger.name == 'modules.chain.providers.cli'"
```

---

### Step 6: Add logger to `modules/chain/adapter.py` and log elapsed time

**Action**: Add module-level logger. After computing `latency_ms` in both `generate()` and `rewrite()`, emit an `INFO` line with the provider name and elapsed time.

**File**: `flask/modules/chain/adapter.py` (CODEBASE CONTEXT: chain adapter)

**Pattern** — add after the `from .types import ChainResult` import:
```python
import logging

logger = logging.getLogger(__name__)
```

Update `generate()` (after `ChainResult(...)` construction):
```python
result = ChainResult(text=text, latency_ms=int((time.monotonic() - t0) * 1000))
logger.info("generate provider=%s latency_ms=%d", provider.__name__, result.latency_ms)
return result
```

Update `rewrite()` identically (same pattern, different function name):
```python
result = ChainResult(text=text, latency_ms=int((time.monotonic() - t0) * 1000))
logger.info("rewrite provider=%s latency_ms=%d", provider.__name__, result.latency_ms)
return result
```

`stream()` does not build a `ChainResult`; leave it without timing logs (streaming latency is not meaningful in the same way).

**Verify**:
```bash
CHAIN_PROVIDER=mock python -c "
from modules.chain import adapter
import logging, io
buf = io.StringIO()
logging.basicConfig(stream=buf, level=logging.INFO, format='%(message)s')
adapter.generate('sys', 'prompt')
out = buf.getvalue()
assert 'latency_ms=' in out, f'no latency log line: {out!r}'
"
```

---

### Step 7: Update `conftest.py` — add `make_project_dir` factory

**Action**: Add `make_project_dir` as a function-scoped factory fixture. It creates a project directory under `tmp_path`, writes `project.json`, and writes the files dict. Returns `tmp_path` (the projects root), matching the shape callers expect.

**File**: `flask/tests/conftest.py` (CODEBASE CONTEXT: `flask/tests/conftest.py`)

**Pattern** — full replacement:
```python
import json
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from create_app import create_app


@pytest.fixture(scope="function")
def app():
    return create_app({'TESTING': True})


@pytest.fixture(scope="function")
def client(app):
    return app.test_client()


@pytest.fixture(scope="function")
def make_project_dir(tmp_path: Path):
    """Factory fixture: creates a project directory under tmp_path.

    Usage:
        def my_test(make_project_dir):
            root = make_project_dir("My Project", {"epic.md": "# Epic"})
            # root is tmp_path; project lives at root / "my-project-1700000000000"

    Returns tmp_path (the projects root), matching the shape service functions expect.
    """
    def _factory(name: str, files: dict) -> Path:
        slug = name.lower().replace(" ", "-")
        project_id = f"{slug}-1700000000000"
        d = tmp_path / project_id
        d.mkdir()
        (d / "project.json").write_text(
            json.dumps({"name": name, "createdAt": "2024-01-15T10:00:00.000Z"}),
            encoding="utf-8",
        )
        for filename, content in files.items():
            (d / filename).write_text(content, encoding="utf-8")
        return tmp_path

    return _factory
```

**File**: `flask/tests/test_project.py` — simplify local `project_dir` fixture (lines 42–53) to use `make_project_dir`:
```python
@pytest.fixture()
def project_dir(make_project_dir) -> Path:
    """Single project with two .md files, ID my-project-1700000000000."""
    return make_project_dir(
        "My Project",
        {"epic.md": "# Epic", "analysis.md": "# Analysis"},
    )
```

Remove the old inline body (the `d = tmp_path / "my-project-1700000000000"` block). The test assertions that reference `"my-project-1700000000000"` remain valid because the slug `"my-project"` + `"-1700000000000"` suffix matches.

**Verify**:
```bash
python -m pytest tests/test_project.py -v --tb=short 2>&1 | tail -10
```
Expect: all 31 tests pass.

---

### Step 8: Rename all test functions — complete rename table

**Action**: Apply the renames below. No logic or assertion body changes — only function names. Where `@pytest.mark.parametrize` is present, rename only the function name, not the parameter values or IDs.

**Critical ordering**: Step 1 (pyproject.toml) must be complete before Step 8 executes, so renamed functions are discovered.

#### `flask/tests/test_health.py`

| Old name | New name |
|---|---|
| `test_health_status_200` | `healthEndpoint_returns200` |
| `test_health_body_is_ok` | `healthEndpoint_returnsStatusOk` |
| `test_health_content_type_is_json` | `healthEndpoint_returnsJsonContentType` |
| `test_cors_header_present_for_angular_origin` | `angularOrigin_corsHeaderPresent` |
| `test_cors_allows_angular_origin_exactly` | `angularOrigin_corsAllowsExactOrigin` |
| `test_cors_does_not_allow_unknown_origin` | `unknownOrigin_corsNotReflected` |
| `test_projects_blueprint_registered` | `createApp_projectsBlueprintRegistered` |
| `test_context_blueprint_registered` | `createApp_contextBlueprintRegistered` |
| `test_ai_blueprint_registered` | `createApp_aiBlueprintRegistered` |
| `test_both_blueprints_registered` | `createApp_allThreeBlueprintsRegistered` |

#### `flask/tests/test_project.py` (test functions only — `_seedProject` rename is in Step 1)

| Old name | New name |
|---|---|
| `test_label_plain_filename` | `plainFilename_returnsCapitalizedLabel` |
| `test_label_hyphenated` | `hyphenatedFilename_returnsSpacedLabel` |
| `test_label_task_file` | `taskFilename_returnsFullLabel` |
| `test_label_versioned_file` | `versionedFilename_preservesDotVersion` |
| `test_make_id_format` | `projectName_idHasSlugAndTimestamp` |
| `test_make_id_strips_special_chars` | `specialCharsInName_strippedFromSlug` |
| `test_list_returns_all_projects` | `populatedDir_listReturnsAllProjects` |
| `test_list_specs_shape` | `listResult_specsHaveLabelNotContent` |
| `test_list_skips_dir_without_project_json` | `dirWithoutProjectJson_skippedFromList` |
| `test_list_sorted_newest_first` | `multipleProjects_newestFirst` |
| `test_get_returns_project_with_content` | `existingProject_returnsSpecsWithContent` |
| `test_get_returns_none_for_missing_project` | `missingProject_getReturnsNone` |
| `test_get_rejects_traversal` | `traversalId_getRaisesValueError` |
| `test_create_writes_project_json` | `createProject_writesProjectJson` |
| `test_create_writes_files` | `createProject_writesAllFiles` |
| `test_create_returns_correct_shape` | `createProject_returnsIdNameCreatedAt` |
| `test_update_file_writes_content` | `existingProject_updateWritesContent` |
| `test_update_file_returns_false_for_missing_project` | `missingProject_updateReturnsFalse` |
| `test_update_file_can_create_new_file_in_existing_project` | `existingProject_updateCreatesNewFile` |
| `test_delete_removes_directory` | `existingProject_deleteRemovesDirectory` |
| `test_delete_returns_false_for_missing_project` | `missingProject_deleteReturnsFalse` |
| `test_http_list_200` | `listEndpoint_returns200WithProjects` |
| `test_http_get_200` | `getEndpoint_returns200WithContent` |
| `test_http_get_404_for_missing` | `missingProject_getEndpointReturns404` |
| `test_http_create_201` | `createEndpoint_returns201WithShape` |
| `test_http_create_400_missing_name` | `missingName_createEndpointReturns400` |
| `test_http_create_400_missing_files` | `missingFiles_createEndpointReturns400` |
| `test_http_update_file_200` | `updateFileEndpoint_returns200AndPersists` |
| `test_http_update_file_404` | `missingProject_updateFileEndpointReturns404` |
| `test_http_delete_200` | `deleteEndpoint_returns200AndRemovesDirectory` |
| `test_http_delete_404` | `missingProject_deleteEndpointReturns404` |

#### `flask/tests/test_context_files.py`

| Old name | New name |
|---|---|
| `test_context_paths_resolve_to_workspace_root` | `contextPaths_resolveToWorkspaceRoot` |
| `test_get_returns_empty_content_when_file_missing` | `missingContextFile_returnsEmptyWithExistsFalse` |
| `test_get_returns_content_when_file_exists` | `existingContextFile_returnsContentAndExistsTrue` |
| `test_put_saves_content_and_returns_success` | `validContent_putSavesFileAndReturnsSuccess` |
| `test_put_overwrites_existing_content` | `existingContent_putOverwrites` |
| `test_put_returns_400_for_invalid_body` | `invalidBody_putReturns400WithError` |
| `test_put_returns_400_for_empty_json_body` | `emptyBody_putReturns400` |
| `test_get_reflects_put_content` | `putThenGet_returnsExactSameContent` |
| `test_all_eight_routes_are_registered` | `createApp_allContextRoutesRegistered` |

#### `flask/tests/test_dtos.py` (`_openapiSchemaNames` rename is in Step 1; update both callers here)

| Old name | New name |
|---|---|
| `test_all_openapi_schemas_have_generated_models` | `allOpenApiSchemas_haveGeneratedModels` |
| `test_generated_models_are_pydantic_v2` | `generatedModels_arePydanticV2` |
| `test_project_summary_model_instantiates_with_valid_data` | `validData_projectSummaryInstantiates` |
| `test_project_summary_model_dump_json_createdAt` | `projectSummaryDumpJson_createdAtIsIsoString` |
| `test_project_summary_model_required_fields` | `missingId_projectSummaryRaisesValidationError` |
| `test_context_response_model_with_content` | `withContent_contextResponseInstantiates` |
| `test_context_response_model_empty` | `emptyContent_contextResponseExistsFalse` |
| `test_context_response_required_fields` | `missingContent_contextResponseRaisesValidationError` |
| `test_success_response_model_true` | `successTrue_successResponseSerializes` |
| `test_success_response_model_false` | `successFalse_successResponseSerializes` |
| `test_project_summary_model_validate_from_dict` | `validDict_projectSummaryModelValidate` |

#### `flask/tests/test_openapi_spec.py`

| Old name | New name |
|---|---|
| `test_openapi_yaml_exists` | `openapiYaml_exists` |
| `test_openapi_yaml_is_non_empty` | `openapiYaml_isNonEmpty` |
| `test_spec_is_valid_openapi_30` | `spec_validOpenApi30` |
| `test_openapi_version_is_3` | `spec_versionIsOpenApi3` |
| `test_info_title_present` | `specInfo_titlePresent` |
| `test_info_version_present` | `specInfo_versionPresent` |
| `test_required_path_present` | `requiredPath_presentInSpec` |
| `test_method_present` | `requiredMethod_presentInPath` |
| `test_schema_component_present` | `requiredSchema_presentInComponents` |
| `test_project_summary_has_required_fields` | `projectSummary_hasRequiredFields` |
| `test_project_detail_has_required_fields` | `projectDetail_hasRequiredFields` |
| `test_spec_detail_includes_content_field` | `specDetail_includesContentField` |
| `test_spec_summary_omits_content_field` | `specSummary_omitsContentField` |
| `test_context_response_has_exists_field` | `contextResponse_hasExistsField` |
| `test_project_create_returns_201` | `projectCreate_returns201` |
| `test_error_response_has_error_field` | `errorResponse_hasErrorField` |
| `test_response_component_present` | `requiredResponseComponent_present` |

#### `flask/tests/test_ai_rewrite.py` (strip `test_` prefix; assertion bodies unchanged)

| Old name | New name |
|---|---|
| `test_validTextAndInstructions_returns200WithEnvelope` | `validTextAndInstructions_returns200WithEnvelope` |
| `test_missingTextKey_returns400WithError` | `missingTextKey_returns400WithError` |
| `test_whitespaceOnlyText_returns400` | `whitespaceOnlyText_returns400` |
| `test_missingInstructions_returns200` | `missingInstructions_returns200` |
| `test_emptyJsonBody_returns400` | `emptyJsonBody_returns400` |
| `test_mockProvider_textStartsWithMockMarker` | `mockProvider_textStartsWithMockMarker` |
| `test_rewritePrompt_withInstructions_includesTextAndInstructions` | `rewritePrompt_withInstructions_includesTextAndInstructions` |
| `test_rewritePrompt_withoutInstructions_stillIncludesText` | `rewritePrompt_withoutInstructions_stillIncludesText` |
| `test_adapterRewrite_withMock_returnsChainResult` | `adapterRewrite_withMock_returnsChainResult` |
| `test_adapterRewrite_noBuilderContext_textExcludesBuilderMarker` | `adapterRewrite_noBuilderContext_textExcludesBuilderMarker` |

#### `flask/modules/chain/tests/test_adapter.py`

| Old name | New name |
|---|---|
| `test_generate_with_mock_provider_returns_chain_result` | `mockProvider_generateReturnsChainResult` |
| `test_generate_embeds_model_in_mock_text` | `customModel_generateEmbedsModelName` |
| `test_generate_prepends_builder_context_to_system` | `builderContext_generatePrependsToSystem` |
| `test_generate_prepends_principles_to_system` | `principles_generatePrependsToSystem` |
| `test_stream_with_mock_yields_multiple_chunks` | `mockProvider_streamYieldsMultipleChunks` |
| `test_unknown_chain_provider_raises_value_error` | `unknownProvider_selectProviderRaisesValueError` |
| `test_chain_result_is_immutable` | `chainResult_isImmutable` |

#### `flask/modules/chain/tests/test_context_loader.py`

| Old name | New name |
|---|---|
| `test_mock_mode_returns_mock_string` | `mockMode_loadContextReturnsMockString` |
| `test_load_all_context_mock_returns_four_keys` | `mockMode_loadAllContextReturnsFourKeys` |
| `test_unknown_context_name_raises_key_error` | `unknownContextName_raisesKeyError` |
| `test_load_context_reads_file` | `existingFile_loadContextReadsContent` |
| `test_missing_file_returns_empty_string` | `missingFile_loadContextReturnsEmpty` |
| `test_load_context_strips_trailing_whitespace` | `trailingWhitespace_loadContextStrips` |

#### `flask/modules/chain/tests/test_file_parser.py`

| Old name | New name |
|---|---|
| `test_single_file_extracted` | `singleMarker_extractsOneFile` |
| `test_multiple_files_extracted_in_order` | `multipleMarkers_extractsFilesInOrder` |
| `test_no_markers_raises_value_error` | `noMarkers_raisesValueError` |
| `test_end_marker_not_in_content` | `endMarker_notIncludedInContent` |
| `test_whitespace_around_filename_trimmed` | `spacedFilename_trimmedInOutput` |
| `test_parse_multi_chain_output_extracts_lint_meta` | `lintSection_extractedInMeta` |
| `test_parse_multi_chain_output_extracts_score_meta` | `scoreSection_extractedInMeta` |
| `test_parse_multi_chain_output_plain_text_fallback` | `noMarkers_fallsBackToOutputMd` |

#### `flask/modules/chain/tests/test_structural.py`

| Old name | New name |
|---|---|
| `test_feature_modules_must_not_import_providers_directly` | `featureModules_mustNotImportProvidersDirectly` |

#### `flask/modules/ai/tests/test_prompts.py` (strip `test_` prefix)

| Old name | New name |
|---|---|
| `test_rewrite_prompt_embedsTextAndInstructions` | `rewritePrompt_embedsTextAndInstructions` |
| `test_rewrite_prompt_systemHasNoBuilderContext` | `rewritePrompt_systemHasNoBuilderContext` |
| `test_generate_prompt_embedsBuilderInSystem` | `generatePrompt_embedsBuilderInSystem` |
| `test_generate_prompt_omitsBuilderSectionWhenEmpty` | `generatePrompt_omitsBuilderSectionWhenEmpty` |
| `test_generate_prompt_embedsToneInSystem` | `generatePrompt_embedsToneInSystem` |
| `test_iterate_prompt_embedsBaseSpec` | `iteratePrompt_embedsBaseSpec` |
| `test_iterate_prompt_embedsCurrentContent` | `iteratePrompt_embedsCurrentContent` |
| `test_iterate_prompt_embedsPrinciplesInSystem` | `iteratePrompt_embedsPrinciplesInSystem` |
| `test_generate_spec_prompt_containsFileMarkerInstruction` | `generateSpecPrompt_containsFileMarkerInstruction` |
| `test_generate_spec_prompt_embedsPrinciples` | `generateSpecPrompt_embedsPrinciples` |
| `test_review_prompt_systemContainsAllSixDimensions` | `reviewPrompt_systemContainsAllSixDimensions` |
| `test_review_prompt_requestsJsonOutput` | `reviewPrompt_requestsJsonOutput` |
| `test_lint_braindump_prompt_embedsBraindump` | `lintBraindumpPrompt_embedsBraindump` |
| `test_lint_braindump_prompt_requestsJsonOutput` | `lintBraindumpPrompt_requestsJsonOutput` |
| `test_scan_prompt_embedsTreeText` | `scanPrompt_embedsTreeText` |
| `test_scan_prompt_systemProhibitsWriteOperations` | `scanPrompt_systemProhibitsWriteOperations` |

**Verify** after all renames in Step 8:
```bash
python -m pytest --collect-only -q 2>&1 | tail -3
```
Expect: same total as baseline (renames do not add or remove tests).

---

## 5. Tests

No new test cases in this task. The complete assertion bodies for all existing tests remain unchanged — only function names move. The "tests" deliverable for this task is the `make_project_dir` fixture, verified by the pre-existing `project_dir` consumer tests:

```python
# flask/tests/test_project.py — project_dir fixture after Step 7
# Assertion body unchanged; only the fixture internals change:
@pytest.fixture()
def project_dir(make_project_dir) -> Path:
    return make_project_dir(
        "My Project",
        {"epic.md": "# Epic", "analysis.md": "# Analysis"},
    )

# Existing test — unchanged assertion, new fixture source:
def existingProject_returnsSpecsWithContent(project_dir: Path):
    result = get_project(project_dir, "my-project-1700000000000")
    assert result is not None
    assert result["id"] == "my-project-1700000000000"
    specs = result["specs"]
    epic = next(s for s in specs if s["filename"] == "epic.md")
    assert epic["content"] == "# Epic"
    assert epic["label"] == "Epic"
```

The slug `"my-project"` + suffix `"-1700000000000"` in `make_project_dir` produces the same project ID the existing assertions expect. No assertion changes needed.

---

## 6. Commit Plan

**Commit 1**: `chore(flask/tests): rename private helpers to camelCase`
- Files: `flask/tests/test_project.py` (`_seed_project` → `_seedProject` + 3 caller sites), `flask/tests/test_dtos.py` (`_openapi_schema_names` → `_openapiSchemaNames` + 2 caller sites)
- What: renames private helpers to camelCase to prevent collection under Task 1's `python_functions = ["test_*", "*_*"]`; pyproject.toml is owned by Task 1

**Commit 2**: `feat(flask): add logging config and module-level loggers`
- Files: `flask/create_app.py`, `flask/modules/projects/routes.py`, `flask/modules/chain/providers/claude.py`, `flask/modules/chain/providers/cli.py`, `flask/modules/chain/adapter.py`
- What: root logger at INFO; error branches log with `exc_info=True`; adapter logs `latency_ms` per call

**Commit 3**: `refactor(flask/tests): add make_project_dir factory to conftest`
- Files: `flask/tests/conftest.py`, `flask/tests/test_project.py` (fixture simplification only)
- What: factory fixture added; local `project_dir` body replaced with `make_project_dir(...)` call; test assertions unchanged

**Commit 4**: `refactor(flask/tests): rename all test functions to condition_expectedOutcome`
- Files: all 11 test files listed in Step 8
- What: pure name changes; no assertion body changes; `python_functions = ["test_*", "*_*"]` in pyproject.toml (commit 1) ensures renamed functions are discovered

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/flask
python -m pytest --tb=short -q
```

**Expected delta**: baseline → baseline passing. Zero net change in test count (renames, not additions). Zero pre-existing tests broken.

After Step 1 specifically (before renames):
```bash
python -m pytest --collect-only -q 2>&1 | grep "_seed_project\|_openapi_schema_names"
```
Expect: empty output — private helpers no longer collected.

After all commits:
```bash
python -m pytest --collect-only -q 2>&1 | grep "test session starts" -A 3
```
Expect: same collected count as baseline. All pass.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>` — reverting commit 4 restores old function names; pytest discovers them via `test_*` pattern still in pyproject.toml.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` returns the branch to the pre-task state. The pyproject.toml simply won't exist; pytest falls back to `test_*` discovery and all pre-existing tests pass as before.
- **Task 1 rollback edge case**: if Task 1's pyproject.toml is reverted while this task's commit 4 renames are present, renamed functions (`condition_expectedOutcome`) will be silently skipped. Coordinate rollback: always revert commit 4 before Task 1's pyproject.toml commit if rolling back individually.

---

## 9. Deviations Allowed

- **`_seed_project` is already camelCase** — skip that rename; update the caller sites only.
- **Additional private helpers with underscores discovered** — apply the same camelCase rename rule to any `_snake_case_helper` in a test file before commit 1 verification.
- **Logger already present in a target file** — skip that file's logger addition; note in commit body as `Deviations: {file} already had logger`.
- **Test framework mismatch** — this codebase uses pytest throughout; translate silently if any file is discovered to use a different runner, note in commit body.
- **Side-effect required** (push, schema migration) — STOP, mark `[REQUIRES APPROVAL]` and flag to user.
- **Step N simplification visible** — take it, log in commit body as `Deviations: simplified {what} at step N`.

---

## 10. Out of Scope

This task adds loggers, a logging config, a factory fixture, and renames test functions. It does not restructure the architecture, add new test cases, or touch the Angular frontend. The following are explicitly deferred and must not be absorbed:

- **`SpecDocError` base class and hierarchy** — deferred until the fourth module registers its own exception type; the flat per-module exception pattern (Task 3) is the current design
- **CI pipeline integration for `make check-dtos`** — no GitHub Actions workflow exists for spec-doc-api yet; wiring `check-dtos` into CI before a workflow exists is premature
- **mypy or type annotation pass** — a separate quality epic; not blocking Phase 2
- **New test assertions for logging behavior** — the logging changes are additive; verifying that log lines appear at runtime is out of scope for this task's test budget
- **`stream()` elapsed-time logging in `adapter.py`** — streaming latency is distributed across chunks; adding meaningful timing there requires a different shape (accumulated yield count vs. wall time); deferred until a concrete requirement emerges

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale for logging config, convention-in-config, and fixture factory
- [Epic](./epic.md) — Task scope and port budget
- [Timeline](./timeline.md) — Update task status after verification passes