---
sidebar_position: 0
---

# 📋 Text Chains — LoRA for Text

> Extend Bubls' /text page with multi-step chain operations that inject stored context files at each step, turning single-shot rewrites into domain-aware pipelines.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [🔍 Analysis](./analysis.md) | Constraints, dependencies, resolved decisions |
| [🎯 Epic](./epic.md) | Scope, tasks, success criteria |
| [🏗️ Architecture](./architecture.md) | Technical design |
| [📅 Timeline](./timeline.md) | Status tracking |

## Overview

Text Chains adds a second row of buttons to the existing /text page. Where the current five modes (Humanize, Expand, Compress, Clarify, Formalize) each make a single Claude call through the chain adapter, chain-mode buttons run multi-step pipelines — each step feeding its output into the next, with repo-stored context files injected at specified stages. The user sees the same textarea-in / text-out surface; the difference is depth and quality of output.

The analogy is LoRA for text: just as LoRA injects small adapter weights into a base image model to customize output without retraining, context blocks (principles, builder profile, references, rubrics) inject domain knowledge into a base Claude call to customize text output without prompt engineering. The user taps one button. Three to five Claude calls happen behind the scenes. The output is qualitatively different from a single-shot rewrite.

Three chain operations ship in this epic: **Deep Humanize** (3-pass, ported from humanize-me's PASS_1/PASS_2/PASS_3 prompts), **Braindump → Docs** (multi-file generation with `===FILE:===` markers, ported from spec-doc's generate-spec pipeline), and **Rewrite + Review** (rewrite → rubric-score → fix cycle). All three flow through the existing chain adapter — no direct provider imports. Context blocks live in-repo as markdown, loaded through a manifest-driven loader with an adapter-shaped mock mode. The frontend extends `OperationBarComponent` with a second button row and a tabbed output area for multi-file results.

## Key Architecture Decisions

- **STEP_HANDLERS dispatch map** — no if/elif in the runner loop; adding an operation = one function + one dict entry
- **Observer pattern** — `chainCompleted` event emitted on every run; analytics subscribes without coupling
- **Null-object feature guard** — chain buttons render locked (not hidden) when `text_chains` disabled; tap shows upgrade toast
- **Module-boundary structural tests** — grep-based tests enforce that only the loader reads `server/context/` and only the runner reads `chain/definitions/`
- **Blueprint registration** — chain endpoint registered in `ENABLED_MODULES`, same pattern as existing feature modules

## Related Documents

- [Analysis](./analysis.md)
- [Epic](./epic.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

