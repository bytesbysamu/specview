---
sidebar_position: 0
---

# Chain Output Fix -- Brain Dump Returns Score JSON Instead of Specs

> Fix three chained bugs in the Bubls braindump-to-docs pipeline: generate step produces conversational text instead of file markers, review step scores empty input, and the user sees quality JSON instead of spec files.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [Analysis](./analysis.md) | Root cause of all three bugs, constraints, resolved decisions |
| [Epic](./epic.md) | Scope, tasks, success criteria |
| [Architecture](./architecture.md) | Technical design for prompt fix + runner guard |
| [Timeline](./timeline.md) | Status tracking |

## Overview

The Bubls GUI Brain Dump button triggers a 3-step chain: lint, generate, review. Three bugs interact to produce broken output. First, the generate step (Step 2) sometimes produces conversational prose ("Alright, here's what I'm seeing...") instead of structured `===FILE:===` markers because the `braindump-to-docs.md` context prompt lacks the explicit 5-file template that makes spec-doc's generate-spec endpoint reliable. Second, when the generate step fails to produce file markers, the review step (Step 3) scores empty or malformed input and returns an all-zeros quality JSON blob. Third, the outputKey sidecar fix from the Chain Runner Fix epic correctly sidecars the review score to `meta`, but when the generate step itself fails, `current_text` after Step 2 is conversational junk -- so the final output is still wrong even with correct sidecar behavior.

The fix is two-pronged: (1) port the 5-file template from spec-doc's `server.js` into Bubls' `braindump-to-docs.md` prompt so the generate step reliably produces file markers, and (2) add a file-marker guard in the chain runner so that when a `multi-file` chain's generate step produces no `===FILE:===` markers, the runner surfaces a clear error instead of silently forwarding unparseable text to the review step.

## Key Decisions

- **Prompt fix is primary** -- the 5-file template from spec-doc is proven to produce reliable file-marker output; porting it closes the quality gap
- **Runner guard is defense-in-depth** -- even with a good prompt, LLMs can regress; the guard catches failures before they cascade to review
- **System prompt vs user message** -- investigate whether the CLI provider is treating the context block as a user message instead of a system message, which would explain the conversational tone
- **Separate from template port** -- this epic fixes the chain behavior; the template port epic handles the content of the prompt

## Related Documents

- [Analysis](./analysis.md) -- root cause walkthrough
- [Epic](./epic.md) -- scope and tasks
- [Architecture](./architecture.md) -- technical design
- [Timeline](./timeline.md) -- status tracking
- [Chain Runner Fix](../chain-runner-fix-1776426025036/spec-index.md) -- parent fix for outputKey sidecar (prerequisite, already shipped)
- [Port Spec-Doc Template](../port-specdoc-template/spec-index.md) -- companion epic for prompt content

===END===
