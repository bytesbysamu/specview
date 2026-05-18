---
name: Braindump input template — 3 sections, no implementation details
description: The standard braindump format fed into spec-doc's generate-spec endpoint; three sections (What / Why now / What's missing), explicitly no endpoints, no file paths, no component names
type: reference
originSessionId: ddd9becd-d854-4163-892e-00f6ecd0b63d
---
The braindump input form in Bubls/spec-doc uses this exact template:

```
# [Name]

## What
[What you want to build. 2-3 sentences. No endpoints, no file paths, no component names.]

## Why now
[Why this and not something else. Evidence, not vibes. Numbers if you have them.]

## What's missing
[What needs to be true before this ships. Decisions unmade, dependencies, blockers.]
```

The template enforces business-level input, not implementation detail. The pipeline (generate-spec) is responsible for turning this into Analysis → Epic → Architecture → Timeline. The braindump should be under ~150 lines.
