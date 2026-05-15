"""Wire all overview feature files to pytest via pytest-bdd scenarios().

Each call to scenarios() registers all scenarios from the named feature file
as individual pytest test functions in this module. Step definitions are
loaded via conftest.py's pytest_plugins list.
"""
from pytest_bdd import scenarios

# OV-01: Authentication Gate
scenarios("overview-auth.feature")

# OV-02 + OV-06: Masthead Banner and Update Notification
scenarios("overview-masthead.feature")

# OV-03: Section Tab Navigation
scenarios("overview-navigation.feature")

# OV-04 + OV-05: Generation Status Bar
scenarios("overview-status-bar.feature")

# OV-07: Search and Filter Bar
scenarios("overview-search.feature")

# OV-08 + OV-09: Project Grid and Card Rendering
scenarios("overview-grid.feature")

# OV-10 + OV-11: Background Polling Lifecycle
scenarios("overview-polling.feature")

# OV-13: Create Project Modal
scenarios("overview-create.feature")

# OV-12: Dark Mode Toggle and Persistence
scenarios("overview-dark-mode.feature")
