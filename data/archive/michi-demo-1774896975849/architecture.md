# 🏗️ Architecture: Michi Demo

**Purpose**: Long-lived system design document for building Spec Doc using Spec Doc itself.

**References**: Addresses concepts from [Analysis](./analysis.md). See [Epic](./epic.md) for scope and milestones.

---

## Architecture Overview

Spec Doc is built on a fundamental insight: the document IS the interface. Rather than treating AI as a conversational partner hidden behind a chat window, Spec Doc positions the artifact—the specification document—as the primary surface where both human and AI operate. This inverts the traditional AI workflow where users extract value from conversations into documents; instead, value accumulates directly in the document through text operations.

The system follows a separation of concerns that mirrors its philosophy: humans define intent through specs, machines handle execution through text transformations. The browser-based editor becomes a workspace for the artifact being produced, not a portal to an AI chatbot. Every architectural decision reinforces this core loop: open document → express intent → AI transforms → accept/reject → document evolves.

This is a self-hosting architecture. We build Spec Doc by using Spec Doc—the methodology validates itself. The specs in `specs/` folder are both documentation AND the authoritative source of product behavior. Code becomes derived artifact, not primary.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Document as Interface | No chat panel. All AI interaction happens through text operations on the document itself. |
| Specs as Source of Truth | Markdown files are authoritative. Database stores metadata only. Git provides versioning. |
| Instant Feedback Over Perfection | Client-side rendering (marked.js) delivers sub-millisecond preview. 60s rebuild delays are unacceptable. |
| Text Operations Over Conversation | Rewrite, expand, compress, clarify—atomic operations that transform text, not open-ended chat. |
| Loose Coupling | Swap AI providers, rendering engines, or storage backends without touching core editing logic. |

---

## System Boundaries

### What This System Includes

- Browser-based Markdown editor with Monaco
- AI-powered text operations (rewrite, expand, compress, generate)
- Multi-project management with file tree navigation
- Real-time preview with marked.js
- Local persistence via Express API
- Bootstrap workflow (brain dump → structured specs)

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Chat interface | Violates core thesis—chat scatters decisions and loses context |
| Real-time collaboration | Over-engineering for MVP; Git handles async collaboration |
| Custom SSG builds | Client-side rendering chosen for instant feedback |
| GitHub Pages integration | Adds 60s latency; deferred to post-MVP |
| PR review bot | Enforcement layer planned but not core editing experience |
| User authentication | Local-first MVP; auth adds friction before value proven |

---

## Component Design

### Editor Component

**Purpose**: Primary workspace where human and AI collaborate on the document.

**Key Parts**:
- `EditorComponent` — Monaco editor wrapper with Markdown syntax support
- `OperationBarComponent` — AI operation buttons (rewrite, expand, compress, clarify)
- `PreviewComponent` — marked.js renderer for instant visual feedback

**Patterns**: View-mode toggle (editor/split/preview) follows IntelliJ paradigm. Selection-based operations—user selects text, clicks operation, AI transforms that selection.

### AI Service Layer

**Purpose**: Abstract text intelligence operations from specific providers.

**Key Parts**:
- `AiService` — Angular service making HTTP calls to backend
- Express `/api/ai/text` endpoints — Proxy to Claude CLI or remote AI API
- Provider abstraction via `AI_PROVIDER` environment variable

**Patterns**: Backend handles provider selection. Frontend agnostic to whether Claude CLI, Groq, or remote API fulfills requests. Enables local development with CLI, production with API.

### Project Management

**Purpose**: Organize multiple spec documents into coherent product definitions.

**Key Parts**:
- `SidebarComponent` — Project tree navigation
- `ProjectsService` — CRUD operations via Express API
- `NewProjectComponent` — Bootstrap modal for brain dump → spec generation

**Patterns**: Projects stored as folders in `projects/` directory. Each project contains Markdown files mirroring the document hierarchy (analysis, epic, architecture, spec-index).

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | Angular 19 + Monaco Editor | Component architecture matches document-centric design; Monaco provides IDE-quality editing |
| Preview | marked.js | Sub-millisecond rendering; simple; 50KB; no build pipeline needed |
| Backend | Express.js (port 3100) | Lightweight project persistence; proxies AI calls; enables CLI integration |
| AI Runtime | Claude CLI | Local development without API keys; production can switch to remote |
| Persistence | Filesystem (Markdown files) | Specs ARE files; no impedance mismatch; git-friendly |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Client-side rendering over GitHub Pages | Instant feedback (<1ms) vs 60s rebuild delay | No SSR initially; can add later for SEO |
| Monaco over textarea | Professional editing experience; syntax highlighting; multi-cursor | Heavier bundle; overkill for simple notes |
| Express over direct file access | Enables AI proxy, project bootstrapping, future auth | Extra process to run locally |
| Claude CLI over direct API | No API keys for local dev; consistent with Claude Code workflow | Requires Claude CLI installed |
| Filesystem over database | Markdown files ARE the product; git-native; no sync issues | No search index; manual backup |
| Selection-based operations over inline triggers | Clear affordance; explicit user intent; predictable behavior | Requires text selection; no ambient assistance |

---

## Patterns

### Text Operation Pattern

**When to use**: User wants AI to transform selected text.

**How it works**: User selects text → clicks operation button → backend receives text + instruction → AI returns transformed text → diff shown → user accepts/rejects → document updates.

**Example**: User selects a paragraph, clicks "Compress," AI returns concise version, user sees diff, accepts, paragraph replaced.

### Bootstrap Pattern

**When to use**: User starts new product from scratch with unstructured thoughts.

**How it works**: User enters brain dump in modal → AI generates structured spec documents (analysis, epic, architecture, spec-index) → documents created in new project folder → user iterates on generated specs.

**Example**: User pastes "I want to build a todo app with voice input" → system generates four interconnected spec documents → user refines each using text operations.

### Document Hierarchy Pattern

**When to use**: Organizing specs for a product or capability.

**How it works**: Fixed document types with specific responsibilities. Analysis (optional, if problems exist) → Epic (scope, tasks) → Architecture (design decisions) → Implementation (per-task guides). Timeline tracks status. Each doc has ONE job.

**Example**: New feature starts with Epic defining scope, Architecture explaining design choices, then Implementation guides for each task. Status lives only in Timeline, not scattered.

---

## Execution Flow

```
[Bootstrap Phase]
  Brain Dump ──→ AI Generation
                      │
[Editing Phase]       ▼
  Select Text ──→ Choose Operation ──→ AI Transform ──→ Preview Diff
                                                            │
[Persistence]                                               ▼
  Accept ──→ Update Document ──→ Auto-save (1s debounce) ──→ Filesystem
```

Bootstrap and editing are independent flows. Bootstrap creates initial documents; editing refines them. Auto-save ensures work persists without explicit save actions. The 1-second debounce prevents excessive writes during active editing.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design choices
- [Epic](./epic.md) – Scope, MVP definition, and milestones
- [Timeline](./timeline.md) – Status tracking for all capabilities
- [Spec Index](./spec-index.md) – Entry point for all documentation