# SpecDocV2 — Braindump

## What it is

SpecDocV2 is an AI-powered spec document editor built on Plate (a Slate-based rich text framework for Next.js). The core concept: a document editor where "spec blocks" are executable — you write a spec in a block, trigger an AI agent, and the agent implements what the spec describes. It's a bridge between product specs and code execution, with the document as the interface.

Two repos:
- `/Users/sam/Projects/2026/specdocv2/` — Next.js app (mostly bootstrapped, minimal AGENTS.md/CLAUDE.md, appears to be the primary target)
- `/Users/sam/Projects/2026/specdocv2-plate-demo/` — A working Plate playground template with AI features wired up, used as proof-of-concept

## Problem it solves

The current spec-doc workflow (braindump → analysis → epic → architecture → tasks) generates markdown files that sit in a folder. Getting from those files to running code requires manually context-switching between the spec and the implementation environment. SpecDocV2 puts the spec document and the execution interface in the same surface — write a spec block, click execute, watch an agent implement it. The document is the product.

Validated use case from the plate-demo work: transforming wardrobai spec markdown files into Plate documents with executable spec blocks. One-click: brain dump → spec document → agent execution.

## Stack

- **Framework**: Next.js (16 in plate-demo, current version in specdocv2)
- **Editor**: Plate (rich text, based on Slate) with shadcn/ui
- **AI**: Currently Groq API with `llama-3.3-70b-versatile` (plate-demo uses this); target for specdocv2 is connecting spec blocks to Claude Code running in a Docker sandbox
- **Agent runtime**: Claude Code (CLI provider, via `~/.claude` mount, `CHAIN_PROVIDER=cli`) — not SDK with API key
- **Build tool**: bun
- **Tooling**: Biome for lint/format

## Current state

**plate-demo (working POC):**
- All AI features operational: native Plate AI (Cmd+J), AI Block with 12 operations (Humanize, Formal, Expand, Compress, Clarify, Improve, Fix, Summarize, Explain, Emojify, Ask, Rewrite), copilot autocomplete
- 4 API endpoints working: `/api/ai/command`, `/api/ai/ask`, `/api/ai/copilot`, `/api/ai/text`
- AI Block has Accept/Reject with keyboard shortcuts, diff preview, state machine (spec → implementing → review → done/failed)
- Integration notes: `AI_GATEWAY_API_KEY` needs to be replaced with Claude Code sandbox connection; `UPLOADTHING_TOKEN` needs to be replaced with own backend

**specdocv2 (the actual target):**
- Next.js bootstrapped
- AGENTS.md only says "this is not the Next.js you know" — minimal guidance written
- Appears to be early stage; plate-demo is where the real work happened

**Integration vision (from `.claude/docs/plans/`):**
- Task 1 (done): Plate editor with spec blocks
- Task 2: Docker container template
- Task 3: WebSocket connection → Claude Code sandbox → agent execution from spec blocks
- Task 4: Multi-agent review loop
- Task 5: Live preview integration + file upload backend

The wardrobai → Plate transform plan shows the intended flow: read epic/architecture/task-*.md files from spec-doc project → generate Plate JSON document → load in editor → execute spec blocks sequentially.

## Key decisions made

- **Spec blocks are the primitive**: Each block is self-contained and actionable — purpose, what to build, key patterns, file paths, verification steps. Stack decisions stay in CLAUDE.md, not spec blocks.
- **Claude Code CLI provider always**: Never SDK with API key. Always `CHAIN_PROVIDER=cli` + `~/.claude` mount.
- **Groq for AI text operations** (fast, free tier) for editor-native AI (Cmd+J, autocomplete). Claude Code for actual spec execution.
- **bun over npm/npx**: Build tool standardized across plate-demo.
- **Verification sequence is mandatory**: `bun install → bun run build → bun run typecheck → bun run lint:fix` — never run build and typecheck in parallel.
- **No git operations without explicit ask**: AGENTS.md is strict on this.
- **Skills system**: plate-demo has a full `.agents/skills/` directory (ce-work, ce-plan, ce-review, ce-compound, frontend-design, react, tdd, dev-browser, etc.) — this is the agent skill harness for working in this codebase.

## Open questions

- Is specdocv2 meant to replace plate-demo or build on top of it? The relationship between the two repos is unclear from docs alone.
- What's the WebSocket protocol for connecting Plate spec blocks to Claude Code? (Task 3 is the key unresolved piece)
- File upload backend: what replaces UploadThing? Is there a planned storage layer?
- How does the spec-doc pipeline (spec-pipeline skill in specview) interact with the Plate editor? Is specdocv2 the viewer for specview-generated docs?
- Should the document format (Plate JSON) be the canonical spec format, or does it sit alongside existing markdown spec docs?

## Next steps

1. Clarify the relationship between specdocv2 and plate-demo — merge, fork, or parallel tracks?
2. Task 2: Design Docker container template for Claude Code sandbox
3. Task 3: WebSocket server that receives spec block content → spawns Claude Code CLI → streams output back to editor
4. Wire real Claude Code execution replacing the Groq text operations for spec block execution
5. Build the wardrobai-style transform (markdown spec files → Plate JSON) as a reusable import tool
6. Task 5: Replace UploadThing with own backend storage for document assets
