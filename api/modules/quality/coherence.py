"""Multi-doc coherence pass — eight cross-document invariants.

lint_capability(project_dir) is the sole public API.
Imports Flag from modules.quality.lint to keep the flag shape uniform
across both quality functions.

Invariants (all run unconditionally, results accumulated):
  1. symbol_uniqueness          — no (new) path declared in two task guides
  2. import_path_consistency    — local module imports in code fences resolve
                                  to a declared new file
  3. epic_filename_alignment    — epic table rows ↔ task-N-*.md files
  4. spec_index_accuracy        — spec-index.md entries exist on disk
  5. timeline_epic_alignment    — every epic task appears in timeline.md
  6. architecture_task_coverage — architecture components mentioned in ≥1 task
  7. preflight_dependency_order — pre-flight sections don't reference files
                                  first created by a later task
  8. content_routing            — status vocabulary confined to timeline.md
"""
from __future__ import annotations

import re
from pathlib import Path

from modules.quality.lint import Flag


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def lint_capability(project_dir: Path) -> list[Flag]:
    """Run all eight coherence invariants against a completed project directory.

    Pure function: reads .md files, returns Flag list. Caller decides policy.
    All eight checks run unconditionally; results are accumulated, not short-circuited.
    """
    flags: list[Flag] = []
    flags.extend(_check_symbol_uniqueness(project_dir))
    flags.extend(_check_import_path_consistency(project_dir))
    flags.extend(_check_epic_filename_alignment(project_dir))
    flags.extend(_check_spec_index_accuracy(project_dir))
    flags.extend(_check_timeline_epic_alignment(project_dir))
    flags.extend(_check_architecture_task_coverage(project_dir))
    flags.extend(_check_preflight_dependency_order(project_dir))
    flags.extend(_check_content_routing(project_dir))
    return flags


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _task_files(project_dir: Path) -> list[Path]:
    """Return task-N-*.md files sorted by filename (ascending task number)."""
    return sorted(project_dir.glob("task-*.md"))


def _task_num(filename: str) -> int | None:
    """Extract the leading integer from a 'task-N-...' filename."""
    m = re.match(r"task-(\d+)-", filename)
    return int(m.group(1)) if m else None


def _read(path: Path) -> str:
    """Read a file safely, returning '' if absent or unreadable."""
    try:
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except OSError:
        return ""


def _extract_section(text: str, heading_re: str) -> str:
    """Return body of the first heading matching heading_re, up to the next
    same-or-higher-level heading or end of document."""
    m = re.search(rf"(?m)^{heading_re}\n(.*?)(?=\n#{{1,3}} |\Z)", text, re.DOTALL)
    return m.group(1) if m else ""


def _extract_creates(text: str) -> list[str]:
    """Return backtick-quoted paths from the '### To Create' subsection."""
    section = _extract_section(text, r"###\s+To Create[^\n]*")
    return re.findall(r"`([^`]+\.[^`]+)`", section)


def _extract_epic_task_nums(text: str) -> list[str]:
    """Parse task numbers from an epic's backlog markdown table.

    Matches rows like: | 1 |, | **1** |, | Task 1 |
    Returns numeric strings: ['1', '2', '3', ...]
    """
    return re.findall(
        r"^\|\s*\*{0,2}(?:Task\s+)?(\d+)\*{0,2}\s*\|",
        text,
        re.MULTILINE,
    )


# ---------------------------------------------------------------------------
# Invariant 1 — Symbol uniqueness
# ---------------------------------------------------------------------------

def _check_symbol_uniqueness(project_dir: Path) -> list[Flag]:
    """No (new) file path may be declared in more than one task guide."""
    path_to_tasks: dict[str, list[str]] = {}
    for tf in _task_files(project_dir):
        for path in _extract_creates(_read(tf)):
            path_to_tasks.setdefault(path, []).append(tf.name)

    return [
        Flag(
            rule="symbol_uniqueness",
            severity="error",
            message=(
                f"'{path}' declared as (new) in multiple task guides: "
                + ", ".join(tasks)
            ),
        )
        for path, tasks in path_to_tasks.items()
        if len(tasks) > 1
    ]


# ---------------------------------------------------------------------------
# Invariant 2 — Cross-task import-path consistency
# ---------------------------------------------------------------------------

_LOCAL_IMPORT_RE = re.compile(
    r"from\s+(modules\.\S+)\s+import|^import\s+(modules\.\S+)",
    re.MULTILINE,
)


def _check_import_path_consistency(project_dir: Path) -> list[Flag]:
    """Local module imports in code fences must resolve to a declared new file.

    Derivation: 'modules.quality.lint' → 'modules/quality/lint.py'
    A warning (not error) because stdlib or existing modules cause false positives
    when their task guides predate this check.
    """
    declared: set[str] = set()
    for tf in _task_files(project_dir):
        declared.update(_extract_creates(_read(tf)))

    flags: list[Flag] = []
    for tf in _task_files(project_dir):
        text = _read(tf)
        for fence_m in re.finditer(r"```[^\n]*\n(.*?)```", text, re.DOTALL):
            for imp_m in _LOCAL_IMPORT_RE.finditer(fence_m.group(1)):
                module_path = imp_m.group(1) or imp_m.group(2)
                fs_path = module_path.replace(".", "/") + ".py"
                if fs_path not in declared:
                    flags.append(Flag(
                        rule="import_path_consistency",
                        severity="warning",
                        message=(
                            f"{tf.name}: import '{module_path}' has no "
                            f"corresponding declared new file ('{fs_path}' "
                            f"not in any task's To Create section)"
                        ),
                    ))
    return flags


# ---------------------------------------------------------------------------
# Invariant 3 — Epic task-table-to-filename alignment
# ---------------------------------------------------------------------------

def _check_epic_filename_alignment(project_dir: Path) -> list[Flag]:
    """Epic backlog rows ↔ task-N-*.md files must be in 1-to-1 correspondence."""
    epic_text = _read(project_dir / "epic.md")
    epic_nums = set(_extract_epic_task_nums(epic_text))

    disk_nums: dict[str, str] = {}  # num_str → filename
    for tf in _task_files(project_dir):
        n = _task_num(tf.name)
        if n is not None:
            disk_nums[str(n)] = tf.name

    flags: list[Flag] = []
    for num in sorted(epic_nums, key=int):
        if num not in disk_nums:
            flags.append(Flag(
                rule="epic_filename_alignment",
                severity="error",
                message=(
                    f"Epic lists task {num} but no task-{num}-*.md "
                    f"file exists in the project directory"
                ),
            ))
    for num, filename in sorted(disk_nums.items(), key=lambda x: int(x[0])):
        if num not in epic_nums:
            flags.append(Flag(
                rule="epic_filename_alignment",
                severity="warning",
                message=(
                    f"'{filename}' exists but task {num} "
                    f"has no row in epic.md"
                ),
            ))
    return flags


# ---------------------------------------------------------------------------
# Invariant 4 — spec-index.md accuracy
# ---------------------------------------------------------------------------

def _check_spec_index_accuracy(project_dir: Path) -> list[Flag]:
    """Every file referenced in spec-index.md must exist in the project directory.

    Missing spec-index.md itself is not flagged here — the repair endpoint handles
    structural-file absence.
    """
    text = _read(project_dir / "spec-index.md")
    if not text:
        return []

    # Match markdown links: [label](./filename.md) or [label](filename.md)
    linked = re.findall(r"\[[^\]]+\]\(\./?([\w.-]+\.md)\)", text)
    # Match bare backtick-quoted filenames
    backtick = re.findall(r"`([\w.-]+\.md)`", text)
    referenced = sorted(set(linked + backtick))

    return [
        Flag(
            rule="spec_index_accuracy",
            severity="error",
            message=(
                f"spec-index.md references '{filename}' "
                f"but it does not exist in the project directory"
            ),
        )
        for filename in referenced
        if not (project_dir / filename).exists()
    ]


# ---------------------------------------------------------------------------
# Invariant 5 — timeline.md-to-epic backlog alignment
# ---------------------------------------------------------------------------

def _check_timeline_epic_alignment(project_dir: Path) -> list[Flag]:
    """Every task number in the epic backlog must appear in timeline.md."""
    epic_text = _read(project_dir / "epic.md")
    timeline_text = _read(project_dir / "timeline.md")
    if not epic_text or not timeline_text:
        return []

    flags: list[Flag] = []
    for num in sorted(_extract_epic_task_nums(epic_text), key=int):
        # Accept: "task 3", "Task 3", "task-3", "Task-3"
        if not re.search(rf"(?i)\btask[- ]{num}\b", timeline_text):
            flags.append(Flag(
                rule="timeline_epic_alignment",
                severity="warning",
                message=f"Epic task {num} has no corresponding entry in timeline.md",
            ))
    return flags


# ---------------------------------------------------------------------------
# Invariant 6 — Architecture-component-to-task coverage
# ---------------------------------------------------------------------------

# Matches: "### Component Name — `path/to/file.py`" (em-dash, en-dash, or hyphen)
_COMPONENT_HEADING_RE = re.compile(r"###\s+(.+?)\s*[—–-]\s*`[^`]+`")


def _check_architecture_task_coverage(project_dir: Path) -> list[Flag]:
    """Each named component in architecture.md must be mentioned in ≥1 task guide."""
    arch_text = _read(project_dir / "architecture.md")
    if not arch_text:
        return []

    components = [m.group(1).strip() for m in _COMPONENT_HEADING_RE.finditer(arch_text)]
    if not components:
        return []

    all_task_text = "\n".join(_read(tf) for tf in _task_files(project_dir))

    return [
        Flag(
            rule="architecture_task_coverage",
            severity="warning",
            message=(
                f"Architecture component '{component}' is not mentioned "
                f"in any task guide"
            ),
        )
        for component in components
        if component not in all_task_text
    ]


# ---------------------------------------------------------------------------
# Invariant 7 — Pre-flight cross-task symbol dependency validity
# ---------------------------------------------------------------------------

def _check_preflight_dependency_order(project_dir: Path) -> list[Flag]:
    """Pre-flight sections of task N must not reference files first created in task M > N."""
    task_files = _task_files(project_dir)

    # Build map: declared new path → earliest task number that creates it
    file_created_in: dict[str, int] = {}
    for tf in task_files:
        n = _task_num(tf.name)
        if n is None:
            continue
        for path in _extract_creates(_read(tf)):
            if path not in file_created_in:
                file_created_in[path] = n

    flags: list[Flag] = []
    for tf in task_files:
        n = _task_num(tf.name)
        if n is None:
            continue
        preflight = _extract_section(_read(tf), r"##\s+\d+\.\s+Pre-flight")
        for path in re.findall(r"`([^`]+\.[^`]+)`", preflight):
            created_in = file_created_in.get(path)
            if created_in is not None and created_in > n:
                flags.append(Flag(
                    rule="preflight_dependency_order",
                    severity="error",
                    message=(
                        f"{tf.name}: pre-flight references '{path}' which "
                        f"is not created until task {created_in}"
                    ),
                ))
    return flags


# ---------------------------------------------------------------------------
# Invariant 8 — Content routing (status vocabulary confined to timeline.md)
# ---------------------------------------------------------------------------

_STATUS_RE = re.compile(
    r"\b(TODO|In Progress|Blocked|BLOCKED|NOT STARTED|NOT_STARTED)\b"
    r"|[✅\U0001f504⏳\U0001f6ab⬜]"
)


def _check_content_routing(project_dir: Path) -> list[Flag]:
    """Status tracking vocabulary must only appear in timeline.md.

    Emoji shortlist covers the five most common status glyphs; the word list
    covers the six tracking terms observed in the analysis. Both are intentionally
    narrow to avoid false positives on e.g. '✅' in a test assertion comment.
    """
    flags: list[Flag] = []
    for doc in sorted(project_dir.glob("*.md")):
        if doc.name == "timeline.md":
            continue
        text = _read(doc)
        for m in _STATUS_RE.finditer(text):
            lineno = text[: m.start()].count("\n") + 1
            flags.append(Flag(
                rule="content_routing",
                severity="warning",
                message=(
                    f"{doc.name}:{lineno}: status term '{m.group(0)}' "
                    f"must be confined to timeline.md"
                ),
                line=lineno,
            ))
    return flags
