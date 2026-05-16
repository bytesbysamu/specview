"""Wire all SaaS feature files to pytest via pytest-bdd scenarios().

Each call to scenarios() registers all scenarios from the named feature file
as individual pytest test functions in this module. Step definitions are
loaded via conftest.py's pytest_plugins list.
"""
from pytest_bdd import scenarios

# SA-01, SA-02, SA-04, SA-13: Authentication flows and full-page routes
scenarios("saas-auth.feature")

# SA-06: Project ownership isolation (user B cannot access user A's project)
scenarios("saas-isolation.feature")

# SA-08, SA-09, SA-10, SA-11: Billing UI — usage meter, rate-limit redirect, upgrade button
scenarios("saas-billing.feature")

# SA-12, SA-20, SA-21: Upgrade page state per plan and checkout redirect
scenarios("saas-upgrade.feature")
