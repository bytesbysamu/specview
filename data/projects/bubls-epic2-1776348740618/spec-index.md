---
sidebar_position: 0
---

# 📋 Spec Route + Chain Primitive

> Port Spec Doc's brain-dump-to-spec pipeline into Bubls as `/spec`, extracting the shared multi-step AI orchestration layer both photoshoot and spec now depend on.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [🎯 Epic](./epic.md) | Scope, tasks, success criteria |
| [🏗️ Architecture](./architecture.md) | Technical design |
| [📅 Timeline](./timeline.md) | Status tracking |

## Overview

Epic 2 is the moment Bubls stops being "an app with an AI feature" and becomes a host for AI features that share a common runtime. Epic 1 hardcoded chain orchestration inside `server/modules/photoshoot/service.py`. That worked for one feature; the second feature would duplicate it. Epic 2 ports Spec Doc's brain-dump-to-executable-spec pipeline into Bubls as a new `/spec` route, and in the process extracts the shared orchestration surface — builder/principles injection, sequential model calls, streaming events, signal capture — into a chain primitive that both features consume.

The visible outcome for users: Bubls gains an onboarding form that captures builder profile and seeds principles, plus a `/spec` tab where pasted brain dumps stream back as analysis → epic → architecture → tasks. The invisible outcome: photoshoot is retrofitted onto the primitive, proving the abstraction survives contact with two structurally different chains (image generation vs. long-form text streaming). That is the proof point the Five-Part Agent methodology essay needs, and the infrastructure Epic 3 (correction loop) will sit on top of.

The port follows the same rules that worked for the Trendfy-to-photoshoot port in Epic 1: copy the working pipeline ~80% as-is, adapt to Bubls's auth, user model, and module structure, ship minimal UX. No editor, no wizard, no migration of existing Spec Doc projects.

## Related Documents

- [Analysis](./analysis.md)
