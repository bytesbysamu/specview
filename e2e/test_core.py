"""Wire the five core feature files to pytest via pytest-bdd scenarios().

These cover brainstorm, bootstrap pipeline, billing gate, epic guide, and
pro-subscription checks.
"""
from pytest_bdd import scenarios

scenarios("brainstorm.feature")
scenarios("bootstrap-pipeline.feature")
scenarios("billing-gate.feature")
scenarios("epic-guide.feature")
scenarios("pro-check.feature")
