The file write needs your permission. Once you approve it, the document will be saved to `projects/chain-primitive-port-from-bubls-agent-runtime-to-spec-doc-api-1776977083541/architecture.md`.

Here's a summary of the key decisions the architecture document makes:

**Layer structure** — `run_chain()` sits above the adapter, not beside it. Routes call the runner; the runner calls `chain_adapter.stream()`; the adapter dispatches to providers. The existing `featureModules_mustNotImportProvidersDirectly` structural test passes unchanged.

**`ChainEvent` is Pydantic, not a dataclass** — `model_dump_json()` is needed for SSE serialization in the route. This is the only reason to prefer Pydantic here; it aligns with the existing DTO layer.

**Context stays in the route** — `run_chain()` receives a flat `inputs` dict. No `context_loader` dependency inside the runner, so unit tests need only `CHAIN_PROVIDER=mock` and a plain dict — no filesystem fixtures.

**No batch endpoint** — the batch `generate-spec` endpoint doesn't exist in the current `routes.py`, so there's no legacy code path to preserve or deprecate during a soak window. The stream endpoint is the primary path.

**`test_pipelinedFeatures_useRunChain`** — new structural test that greps route files for `chain_adapter.generate`/`chain_adapter.stream` call sites. More than one per handler = chain-by-copy-paste = violation. Added now because this epic creates the violation class for the first time.

**Port bubls's shape verbatim** — `$`-prefixed input resolution, frozen dataclasses, generator-based `run_chain()`. Every deviation from the reference shape is made explicit in commit bodies.