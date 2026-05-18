---
name: Revert unnecessary backend changes before declaring done
description: When root cause turns out to be config, revert speculative code changes before moving on
type: feedback
---

When debugging a problem that turns out to be a config/environment issue (not a code bug), revert all speculative code changes (retry logic, model upgrades, timeout tweaks, workflow refactors) before closing out. Only keep changes that fix a real bug.

**Why:** In the specview session, rate limit errors were caused by CHAIN_PROVIDER=claude + expired OAuth token. But multiple API changes were made chasing the symptom (model upgrades, retry logic, WorkflowRuntime in thread, combined prompts) — all unnecessary. The only real bug fixed was frontend error propagation (err?.message instead of hardcoded string).

**How to apply:** Before finishing a debugging session, ask: "did any code change actually fix the root cause, or was it a config fix?" If config, revert the code. Keep only changes that address a real, confirmed bug.
