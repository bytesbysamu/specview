---
name: Always use spec-doc pipeline
description: Never manually write spec docs — always run braindumps through the spec-gen pipeline (GUI or API), never hand-craft the 5 output files
type: feedback
originSessionId: e024faf7-9ea0-4c83-9555-b3f47825503d
---
Never manually write spec docs (spec-index, analysis, epic, architecture, timeline). Write the braindump, then run it through the spec-gen pipeline — either via the GUI or API call. The pipeline produces the structured output.

**Why:** The spec-doc pipeline is the workflow. Hand-writing spec files bypasses the system and produces inconsistent output.
**How to apply:** When a braindump is ready, hand it off to the user to run through their GUI or API. Don't try to generate the 5 spec files inline or by hacking the CLI provider.
