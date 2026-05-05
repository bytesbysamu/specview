# Architecture: Spec Doc

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

Spec Doc is a browser-based application with a thin backend. The frontend is the product — a Monaco-powered Markdown editor with AI operations. The backend exists only to proxy AI calls and persist files. There is no database; the filesystem is the database. Markdown files are the source of truth.

The key insight is that document-first means the document IS the interface. Users don't chat with AI and copy results. They select text, invoke operations, and AI transforms the document in place. This inverts the typical AI UX where chat is primary and documents are secondary.

The architecture enables a simple flow: User edits → AI transforms → Document updates → Git commits. Specs flow downstream to Claude Code for implementation. The CLAUDE.md becomes the configuration. Markdown becomes the programming language.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Document-first | No chat interface. All interaction through the document. |
| MD-native | Markdown is the format. Files on disk. Git-versioned. |
| AI-native | AI operations are primitives, not features. |
| Local-first | No cloud dependency. Files live on user's machine. |
| Thin backend | Frontend is the product. Backend is just a proxy. |

---

## Component Design

### Editor Component

**Purpose**: Primary interface for document editing.

**Key Parts**:
- `EditorComponent` — Monaco editor wrapper with markdown language
- `PreviewComponent` — marked.js renderer for live preview
- `OperationBarComponent` — AI operation buttons (rewrite, expand, etc.)

**Patterns**: Split view like VS Code. Selection-based operations.

### AI Service

**Purpose**: Bridge to AI capabilities.

**Key Parts**:
- `AiService` — HTTP client for AI operations
- `server.js` — Express proxy to Claude CLI or remote API

**Patterns**: Streaming responses. Provider abstraction (CLI vs remote).

### Bootstrap System

**Purpose**: Generate structured specs from brain dump.

**Key Parts**:
- `NewProjectComponent` — Modal for brain dump input
- `buildAnalysisPrompt()`, `buildEpicPrompt()`, `buildArchitecturePrompt()` — Prompt templates

**Patterns**: Sequential generation. Template-based prompts.

### Project Management

**Purpose**: Organize and persist spec projects.

**Key Parts**:
- `ProjectsService` — CRUD for projects
- `SidebarComponent` — Project tree navigation
- `projects/` folder — Persisted projects on disk

**Patterns**: File-based persistence. No database.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | Angular 19 | Component architecture, TypeScript, familiar |
| Editor | Monaco Editor | Same as VS Code, excellent MD support |
| Preview | marked.js | Fast, standards-compliant MD rendering |
| Backend | Express.js | Minimal, just for proxying |
| AI | Claude CLI | Local-first, no API keys for dev |
| Persistence | Filesystem | Markdown files, git-friendly |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| No database | Files are source of truth, git-versioned | No search, no relations |
| No chat interface | Document-first is the product | Different mental model |
| Monaco over CodeMirror | VS Code familiarity, better API | Larger bundle |
| Claude CLI default | No API key setup for local dev | Requires Claude CLI installed |
| Angular over React | Team familiarity, enterprise patterns | Larger community in React |

---

## Execution Flow

```
[Task 1: Editor]
  Document-first UI
       │
       ▼
[Task 2: AI Ops]
  Text operations
       │
       ▼
[Task 3: Bootstrap]
  Brain dump → Specs
       │
       ▼
[Task 4: Agent Integration]
  Specs → Claude Code
       │
       ▼
[Task 5: Git]
  Versioned specs
```

Tasks 1-2 are foundation. Task 3 builds on operations. Task 4 connects to implementation. Task 5 enables workflow.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview
