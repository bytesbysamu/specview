# 🎯 Epic: Spec Doc MVP

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Chat-based AI interfaces force users into a copy-paste loop that destroys productivity. Every LLM interaction becomes a manual transfer operation: write prompt, copy response, paste into document, edit, repeat. This friction compounds—a 10-page spec might require 50+ copy-paste cycles. The chat paradigm treats AI as a conversation partner when users need it as a writing tool.

Spec Doc eliminates this friction by making AI operations native to the document editing experience. Users work directly in their artifact (the spec), applying AI as text operations rather than conducting separate conversations. This is the IDE model applied to documentation: the workspace IS the output.

The market is anyone who writes structured documents with AI assistance—product managers, technical writers, architects, consultants. The immediate beachhead is developers who already understand that specs drive better code output from AI coding tools.

**Value Proposition**: Write better specs faster by applying AI as text operations, not chat conversations.

---

## Scope

### What This Epic Covers

- **Document editing workspace** – Monaco-based markdown editor with live preview
- **AI text operations** – Rewrite, expand, compress, clarify as direct document transforms
- **Project persistence** – Save/load project folders with multiple markdown files
- **Bootstrap flow** – Generate initial spec structure from brain dump input

### What This Epic Does NOT Cover

- ❌ User authentication — Self-hosted MVP, no multi-tenancy
- ❌ GitHub integration — Manual export for now
- ❌ Vector DB / RAG — Future enhancement after core editing validated
- ❌ Collaboration — Single-user editing only
- ❌ Code generation — Specs only, coding tools consume exported markdown

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Document Editor Core** | None | — | 3 days | High |
| 2 | **AI Text Operations** | 1 | 3 | 2 days | High |
| 3 | **Project Persistence** | 1 | 2 | 2 days | High |
| 4 | **Bootstrap Flow** | 2, 3 | — | 2 days | High |

### Task 1: Document Editor Core

Build the primary workspace using Monaco editor with markdown syntax highlighting and split-view preview using marked.js. This establishes the foundation—users can open, edit, and preview markdown files. No AI yet, just a functional editor.

### Task 2: AI Text Operations

Implement the operation bar with rewrite, expand, compress, and clarify buttons. Each operation sends selected text (or full document) to Claude API and streams the response back into the editor. This transforms the editor from passive to AI-native.

### Task 3: Project Persistence

Create Express API for saving/loading project folders. Each project is a directory of markdown files. Implement sidebar navigation for switching between files and projects. Auto-save with debounce to prevent data loss.

### Task 4: Bootstrap Flow

Build modal that accepts brain dump text and generates initial spec structure (analysis.md, epic.md, architecture.md). This demonstrates the end-to-end value: messy input → structured specs via AI, then refined through text operations.

---

## Success Criteria

This epic is complete when:

- ✅ User can edit markdown with live preview in browser
- ✅ User can apply AI operations (rewrite, expand, compress, clarify) to selected text
- ✅ Projects persist across browser sessions
- ✅ Brain dump input generates structured spec documents
- ✅ Single user can write a complete product spec without copy-pasting from chat

---

## Non-Goals

- ❌ Perfect document generation — AI assists, humans refine
- ❌ Replacing code editors — Specs only, export to other tools
- ❌ Enterprise features — Validate core loop before scaling

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview