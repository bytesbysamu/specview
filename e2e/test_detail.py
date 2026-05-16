"""Wire all project-detail feature files to pytest via pytest-bdd scenarios().

Each call to scenarios() registers all scenarios from the named feature file
as individual pytest test functions in this module. Step definitions are
loaded via conftest.py's pytest_plugins list.
"""
from pytest_bdd import scenarios

# PD-02: Reader panel opens when a project is selected
# PD-15: Files appear in canonical order in the sidebar
# PD-16: Markdown renders with formatting; XSS script tags are stripped
scenarios("detail-reader.feature")

# PD-03: Clicking a sidebar filename loads that file in the reader
# PD-04: Sidebar status row displays current connection state
# PD-05: Per-file dot indicators appear during generation (@SKIP_MOCK)
scenarios("detail-sidebar.feature")

# PD-01: Full spec-gen pipeline lifecycle — start, poll, complete (@SKIP_MOCK)
# PD-06: Generate Specs button trigger and loading state (@SKIP_MOCK)
# PD-07: Generate Guide button trigger (@SKIP_MOCK)
scenarios("detail-specgen.feature")

# PD-08: AI text operation chips visible and toggleable (@SKIP_MOCK)
# PD-09: Style preset chips render and can be selected (@SKIP_MOCK)
scenarios("detail-ai-ops.feature")

# PD-10: AI result panel shows diff view (@SKIP_MOCK)
# PD-11: Apply, Copy, and Dismiss toolbar actions (@SKIP_MOCK)
# PD-12: Undo/redo stack after applying a result (@SKIP_MOCK)
scenarios("detail-results.feature")

# PD-13: Brainstorm follow-up input accepts text and submits (@SKIP_MOCK)
# PD-14: Generate Specs can be triggered from brainstorm output (@SKIP_MOCK)
scenarios("detail-brainstorm.feature")
