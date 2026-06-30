"""Import-guard regression test for the boot path's hard dependencies.

``modules.runtime.chain.providers.gateway`` does an unconditional top-level
``import requests`` (the oll-model HTTP boundary). ``requests`` used to be
supplied only *transitively* by ``stripe``/``resend``; once those were dropped
from requirements, nothing declared it directly — so the package imported fine
in any env that happened to still have ``requests`` lying around, but a clean
deploy would crash-loop the moment Flask imported the gateway at boot.

This test imports the providers package the same way app boot does, so a future
transitive-dep removal fails loudly here in CI instead of silently in prod.
"""
from __future__ import annotations


def test_providers_package_imports():
    """Importing the providers package must not raise (pulls in gateway →
    requests). A missing transitive dep would surface as ImportError here."""
    import modules.runtime.chain.providers  # noqa: F401

    assert True
