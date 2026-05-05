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
> **Reprioritized**: Agent Integration moved up to exit terminal workflow faster.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Document-First Editor** | None | — | 2 days | High |
| 4 | **Agent Integration** | 1 | — | 2 days | High |
| 2 | **AI Text Operations** | 4 | 5 | 2 days | Medium |
| 3 | **Spec Bootstrap** | 2 | — | 2 days | Medium |
| 5 | **Git Integration** | 4 | 2 | 1 day | Low |

### Task 1: Document-First Editor (Lite)

Browser-based Markdown editor using Monaco. Split view with live preview via marked.js. No chat interface — users write directly in the document. Lite version: editor + preview only, no operation bar yet. Foundation for agent integration.

### Task 4: Agent Integration

Connect specs to Claude Code. "Implement" button sends spec context to agent. Stream output back to UI. Tasks from timeline become executable. **This is the exit point from terminal-based Claude Code interaction.**

### Task 2: AI Text Operations

Implement the five primitives: rewrite, expand, compress, clarify, generate. Select text, choose operation, AI transforms in place. Uses Claude CLI or remote API. These operations replace chat interaction.

### Task 3: Spec Bootstrap

Take a brain dump and generate structured spec documents: analysis.md, epic.md, architecture.md, timeline.md, spec-index.md. Goes from unstructured idea to capability folder in minutes.

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

## Future Tasks (Post-MVP)

> These tasks extend the core pipeline after MVP tasks 1-5 are complete.

| # | Task | Dependencies | Effort | Priority |
|---|------|--------------|--------|----------|
| 6 | **Validation Command** | 3 | 1 day | Medium |
| 7 | **Doc Update Suggestions** | 4 | 2 days | Medium |
| 8 | **Claude Rules Generator** | 3 | 1 day | Low |
| 9 | **Doc Drift Detection** | 4, 7 | 2 days | Low |
| 10 | **Spec Search** | 3 | 1 day | Low |
| 11 | **Generate Next Task Button** | 3 | 1 day | High |

### Task 6: Validation Command

`/validate` command that checks generated specs against quality rubric. Outputs report showing which criteria pass/fail. Ensures generated docs meet constellation quality standards.

### Task 7: Doc Update Suggestions

After implementation completes, analyze what was built vs what was specified. Suggest updates to timeline (mark done), architecture (add patterns discovered), epic (scope changes). Human approves suggestions.

### Task 8: Claude Rules Generator

Auto-generate `.claude/rules/spec-awareness.md` for each project. Embeds spec references so Claude Code automatically reads specs before implementing. Bridges Spec Doc to Claude Code workflow.

### Task 9: Doc Drift Detection

Periodic comparison of specs vs actual implementation. Detect when code diverges from spec. Suggest spec updates or flag implementation gaps. Keeps specs and code in sync over time.

### Task 10: Spec Search

Natural language search across all spec files in a project. Index markdown content, allow queries like "how do we handle authentication?", return relevant excerpts with file/line references. Makes large spec surfaces navigable.

### Task 11: Generate Next Task Button

Add a per-project **"+ Generate Next Task"** sidebar action. Given a project whose `epic.md` has more task rows than on-disk `task-N-*.md` files, one click finds the first un-generated task in the epic table and produces its implementation guide using the same pipeline as bootstrap — builder + principles + codebase injection into `buildImplementationGuidePrompt`. Writes `task-N-{slug}.md` alongside existing task files, auto-selects the new file in the editor, and shows progress in the existing output panel. Key refactor: extract `buildImplementationGuidePrompt` and `extractTasksFromEpic` out of `NewProjectComponent` into a new `ImplementationGuideService` so the bootstrap path and the new button share one source of truth (no more ~180 lines of duplicated template). Enables incremental task addition without re-bootstrapping the whole project, which currently overwrites hand-edited specs. Edge cases: no active project, no ungenerated tasks (toast), double-dash task filenames (`task-3--` vs `task-3-`).

---

## Related Documents

- [🔍 Analysis](./analysis.md) – Problems driving this epic
- [🏗️ Architecture](./architecture.md) – System design
- [📅 Timeline](./timeline.md) – Status tracking
- [📋 Spec Index](./spec-index.md) – Document overview
