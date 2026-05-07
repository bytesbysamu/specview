## Key Themes

**1. The Boundary Is the Architecture**
The entire v2 argument rests on one line: *"If changing what a rewrite does requires touching Python, the architecture has a leak."* This isn't a refactor — it's a declarative claim about where intelligence is allowed to live. Python is infrastructure. The plugin is product. That boundary, once held, is self-reinforcing: every new capability defaults to a skill, not a route.

**2. Skills Are Agents, Not Wrappers**
The "max plugin use" test reframes what a skill *is*. A skill isn't a named prompt — it's a scoped agent with file access, convention awareness, and the ability to orchestrate sub-agents. The distinction matters because it changes what you build toward: not a prompt library, but a capability layer that gets smarter as the plugin gets richer.

**3. Execution Model as First-Class Contract**
Burying `sync` vs `async` in `skill.json` — not in routes, not in frontend logic — is a significant design commitment. The API becomes self-describing. The frontend derives behavior from the skill registry, not from hardcoded branching. This is the foundation for a genuinely extensible system where new skills don't require frontend changes to integrate.

**4. Migration Is the Product**
The phased benchmark gates (95%, N=10, per-track) aren't operational overhead — they're the mechanism by which the team builds *trust in the new architecture*. The benchmark runner isn't a test suite; it's a confidence machine. That's a product artifact, not an engineering artifact.

**5. Brainstorm as UX Philosophy**
Renaming `lint-braindump` to `brainstorm` isn't cosmetic. It signals a shift in the product's posture: from passive validator to active collaborator. The questions + recommendations + rewritten braindump output structure is a prototype for a broader interaction model — what it looks like when the product thinks *with* the user instead of *at* them.

---

## Hidden Connections

**The max-plugin-use test is a policy, not a heuristic.**
Right now it reads like a design smell detector. But "if swapping this for a plain prompt produces worse output, the skill is using the plugin" is precise enough to be enforced. It should be in the skill review checklist, in PR templates, and eventually as a benchmark category. It's the architectural invariant equivalent of the "zero AI strings in Python" test — one for the plugin layer, one for the API layer.

**The `X-Job-Id` header on sync responses creates a hidden replay surface.**
Every sync job writes a transient record to `.jobs/<job_id>/run.log`. That means every text operation — every rewrite, every brainstorm, every review — leaves a forensic trail. You can replay any job with a new skill version. That's a regression testing primitive hiding inside an observability decision. The benchmark runner could consume this corpus instead of synthetic inputs.

**The brainstorm skill's output schema is a frontend contract disguised as an AI output.**
`questions`, `recommendations`, `rewritten_braindump` — this JSON structure will be parsed by the frontend. If the skill evolves (adds a `confidence` field, restructures `options`), the frontend breaks silently unless the schema is declared and validated. The skill output contract needs the same rigor as the stdout protocol. This is the one place where "domain logic in the skill" creates a tight coupling back to Python/frontend that the architecture doesn't yet account for.

**Track A (sync) and Track B (async) aren't just parallel — they're a dependency graph disguised as a schedule.**
Track A proves the generic route, `skill.json` schema, and skill authoring pattern. Track B *depends* on all of that being proven. The apparent parallelism hides a sequencing risk: if Track A reveals a flaw in the `execution_model` branching logic, Track B work may need to be unwound. The tracks aren't independent — they share the route layer.

**`brainstorm` → `spec-pipeline` is a natural funnel that doesn't yet exist as a designed flow.**
The brainstorm skill produces a `rewritten_braindump` explicitly described as "ready to feed `spec-pipeline`." That's a handoff. But the current architecture treats them as separate invocations. The product implication is that accepting the rewritten braindump *should* trigger `spec-pipeline` — a guided, two-step project creation flow. That flow isn't documented anywhere and will be assembled ad hoc by the frontend unless someone designs it intentionally now.

---

## Open Questions

**1. Who owns the skill output schema, and what breaks when it changes?**
`skill.json` declares `execution_model`. Does it also declare the output schema? If the `brainstorm` skill adds a new top-level key, does the frontend break? Does Python validate the output shape before returning it? The stdout protocol is CI-enforced — why isn't the JSON output contract?

**2. What does "95% pass" mean for a rewrite skill?**
For async pipeline skills, pass/fail is structural: did the expected files appear in the right shape? For sync text skills, the output is prose or semi-structured text. What's the evaluator? Human review of N=10 is not a repeatable benchmark. If the answer is "LLM-as-judge," that needs to be a decision, not an assumption.

**3. What is the failure mode when a skill misbehaves in production?**
Python can catch exit codes and malformed stdout. It can't detect a skill that exits 0, emits valid JSON, and produces subtly wrong output — a rewrite that drops a paragraph, a brainstorm that hallucinates constraints. The observability infrastructure captures *what happened*, not *whether it was right*. Is there a plan for surfacing quality degradation at runtime, not just in benchmarks?

**4. Sub-agent invocation is unbounded — what's the blast radius?**
Skills can invoke chain-agent, spec-backend, spec-frontend as sub-tasks. Nothing in the current design limits recursion depth, compute time, or concurrent sub-agent spawns per skill. A single `brainstorm` invocation could fan out into multiple agent calls. Is there a timeout hierarchy? A cost ceiling? A circuit breaker?

**5. How do prompt changes get reviewed?**
SKILL.md is a plain text file in git. A change to the system prompt in `brainstorm/SKILL.md` is a product change with user-facing consequences — equivalent to changing a core algorithm. But it looks like a docs edit. Does it require benchmark re-run before merge? Is there a review process distinct from regular code review? Without one, the architecture's cleanliness is undermined by its own permissiveness.

**6. What's the rollback plan if a skill fails in production after passing its benchmark gate?**
The migration strategy is phased forward — benchmarks gate advancement. But there's no documented path backward. If `brainstorm` passes its smoke test, ships, and starts producing bad output on real user inputs (out-of-distribution from the N=10 corpus), what happens? Does traffic revert to the old Python route? Is the old route still alive? For how long?

---

## Ideas to Explore

**1. Enforce "zero AI strings in Python" in CI, not just in convention.**
A grep-based linter that fails the build if any Python file in `api/modules/ai/` contains strings over N characters that look like natural language instructions. Make the architectural invariant mechanical. It costs an afternoon and eliminates an entire class of drift.

**2. Declare skill output schemas in `skill.json` and validate them in Python before returning.**
Add an `output_schema` field (JSON Schema) to `skill.json`. Python validates the agent's stdout result against it before writing the response. If the schema fails, it's a skill error, not a Python bug. This closes the silent contract-break loop between skill evolution and frontend parsing.

**3. Build the brainstorm → spec-pipeline handoff as a designed flow, not a frontend hack.**
Define a `next_skill` field or a `suggested_action` in the brainstorm output. The frontend uses it to surface "Run spec pipeline with this braindump?" as a CTA after the user accepts the rewrite. Design the two-step flow now, before the frontend assembles it ad hoc. This is where the product differentiates — guided AI collaboration, not just API calls.

**4. Make the benchmark runner consume real job logs, not synthetic inputs.**
Every sync job already writes to `.jobs/<job_id>/run.log`. Build the benchmark runner to optionally consume this corpus — replay real user inputs against a new skill version and diff the outputs. The N=10 corpus grows automatically as the product is used. The benchmark improves without manual curation.

**5. Build a skill diff tool for prompt change review.**
When SKILL.md changes in a PR, automatically run the benchmark suite against both the old and new version and post the diff to the PR. Makes prompt changes as reviewable as code changes. Enforces the same rigor without requiring a new process — it's just a CI step.

**6. Add a trace ID that propagates through sub-agent invocations.**
When a skill spawns a sub-agent (chain-agent, spec-backend), pass the parent job ID as an environment variable. Sub-agent logs reference it. Now you have a call graph for any multi-agent invocation — essential for debugging `brainstorm` or `spec-pipeline` failures that involve nested agents. Without this, production failures in multi-agent skills are opaque.

**7. Design a "skill inspector" for developer experience.**
`GET /api/skills/{name}/inspect` returns what the skill actually receives at spawn time: the resolved `--add-dir` contents, the `skill.json` config, the effective prompt structure. Developers authoring skills currently have no way to see what the agent sees without running a live job. This removes the "why is the skill doing that?" friction entirely.

**8. Treat `execution_model` as the seed of a capability matrix, not just a binary flag.**
`sync` and `async` are two points on a spectrum. Future skills might need streaming output, interactive mid-run pauses (e.g., "answer these questions before I continue"), or multi-turn loops. Adding a third value to `execution_model` later will require route changes. Design the branching logic in the generic route to be extensible now — a handler registry keyed on `execution_model` value — so new models are additive, not breaking.