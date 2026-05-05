# 🏗️ Architecture: Spec Doc

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

## System Boundaries

### What This System Includes

- Browser-based Markdown editor with Monaco
- AI text operations (rewrite, expand, compress, clarify, generate)
- Spec bootstrap from brain dump to structured documents
- Project persistence to local filesystem
- Git export for versioning specs

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Chat interface | Document-first is the entire product thesis |
| Cloud sync | Local-first approach; files on disk |
| Database | Filesystem IS the database; MD files are source of truth |
| Code generation | Specs flow to agents (Claude Code), not direct codegen |
| Team collaboration | Single user MVP; collaboration is future scope |
| IDE features | We're for specs, not code editing |

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
| Sequential doc generation | Each doc can reference previous | Slower than parallel |

---

## Patterns

### Document Generation Pipeline

**When to use**: Bootstrap flow when creating new capability folder

**How it works**:
1. Analysis generated first (problems)
2. Epic generated second (can reference analysis)
3. Architecture generated third (can reference epic)
4. Implementation guides generated per task (can reference architecture + epic)
5. Template docs (timeline, spec-index) generated from epic data

**Example**: `bootstrap()` in NewProjectComponent sequences AI calls and extracts task data from Epic output to generate implementation guides.

### Selection-Based Operations

**When to use**: Any text transformation in the editor

**How it works**:
1. User selects text in Monaco editor
2. Operation bar appears with available operations
3. User clicks operation (e.g., "Expand")
4. Selected text sent to AI service with operation instruction
5. Response replaces selection in editor

**Example**: Select "Add user auth" → Click Expand → AI returns detailed auth requirements that replace the selection.

### File-Based Persistence

**When to use**: Saving projects and specs

**How it works**:
1. Projects saved as folder structure in `projects/` directory
2. Each spec is a separate `.md` file
3. Changes debounced and auto-saved
4. No server-side state; filesystem is the database

**Example**: `ProjectsService.save()` writes files directly to disk via Express API.

---

## Execution Flow

```
[Task 1: Editor]
  Document-first UI
       │
       ├──────────────────┐
       ▼                  ▼
[Task 2: AI Ops]    [Task 5: Git]
  Text operations     Versioning
       │
       ▼
[Task 3: Bootstrap]
  Brain dump → Specs
       │
       ▼
[Task 4: Agent Integration]
  Specs → Claude Code
```

Tasks 1 is foundation. Tasks 2 and 5 can run in parallel after 1. Task 3 depends on 2. Task 4 depends on 3.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview
