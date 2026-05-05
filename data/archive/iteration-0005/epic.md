# 🎯 Epic: Spec Doc

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

The entire history of developer tools is: give people a proper workspace for the artifact they're producing. For code, we have IDEs. For design, we have Figma. For specs, papers, documentation — we're still in the chat dark ages, copy-pasting thousands of times between AI chat and our actual documents.

Spec Doc creates the IDE for specification-driven development. Instead of chatting with AI and copying outputs, users write directly in a document-first interface where AI transforms text in place. Specs become the source of truth. AI agents read specs, generate plans, modify code. Humans edit specs, review intent, approve outcomes.

The market opportunity is anyone who writes with AI assistance: technical founders, product managers, technical writers, developers building AI products. The differentiation is MD-native + AI-native + git-native + enforcement layer. No one has all four.

**Value Proposition**: One good prompt + referenced spec docs should be enough.

---

## Scope

### What This Epic Covers

- Document-first browser UI with Monaco editor — no chat, direct text manipulation
- AI text operations (rewrite, expand, compress, clarify, generate) — the primitives
- Markdown preview with live rendering — see what you're building
- Spec bootstrap from brain dump — go from idea to structured docs
- Git-native workflow — specs versioned as source code

### What This Epic Does NOT Cover

- ❌ Team collaboration — Single user MVP first
- ❌ Cloud sync — Local-first, files on disk
- ❌ Custom templates — Built-in templates only
- ❌ Full code generation — Specs to agents, not specs to code
- ❌ Chat interface — Document-first means no chat

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Document-First Editor** | None | — | 3 days | High |
| 2 | **AI Text Operations** | 1 | 5 | 2 days | High |
| 3 | **Spec Bootstrap** | 2 | — | 2 days | High |
| 4 | **Agent Integration** | 3 | — | 2 days | High |
| 5 | **Git Integration** | 1 | 2 | 1 day | Medium |

### Task 1: Document-First Editor

Browser-based Markdown editor using Monaco. Split view with live preview via marked.js. No chat interface — users write directly in the document. This is the foundation everything else builds on.

### Task 2: AI Text Operations

Implement the five primitives: rewrite, expand, compress, clarify, generate. Select text, choose operation, AI transforms in place. Uses Claude CLI or remote API. These operations replace chat interaction.

### Task 3: Spec Bootstrap

Take a brain dump and generate structured spec documents: analysis.md, epic.md, architecture.md, timeline.md, spec-index.md. Goes from unstructured idea to capability folder in minutes.

### Task 4: Agent Integration

Connect specs to Claude Code. "Implement" button sends spec context to agent. Stream output back to UI. Tasks from timeline become executable. Specs become actionable, not just readable.

### Task 5: Git Integration

Save specs to git repository. Export to GitHub. Specs versioned alongside code. MD files as source code.

---

## Success Criteria

This epic is complete when:

- ✅ User can write specs faster than chatting with AI
- ✅ Brain dump → structured capability folder in under 3 minutes
- ✅ AI operations work without leaving the document
- ✅ Specs can be sent to Claude Code for implementation
- ✅ Users stop copy-pasting from chat

---

## Non-Goals

- ❌ Replacing VS Code — We're for specs, not code
- ❌ Building another Notion — No databases, no blocks, just Markdown
- ❌ Chat-based AI — Document-first is the entire point
- ❌ Enterprise features — Single user, local first

---

## Related Documents

- [🔍 Analysis](./analysis.md) – Problems driving this epic
- [🏗️ Architecture](./architecture.md) – System design
- [📅 Timeline](./timeline.md) – Status tracking
- [📋 Spec Index](./spec-index.md) – Document overview
