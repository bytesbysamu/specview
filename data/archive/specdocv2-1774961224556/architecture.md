# 🏗️ Architecture: Spec Doc POC 2

**Purpose**: Long-lived system design document for spec-to-code execution platform.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

Spec Doc POC 2 is a real-time spec execution platform that bridges the gap between natural language specifications and running code. The core insight is that specifications should be *executable*, not just *readable*. Rather than generating static code that users must manually integrate, the system maintains a live connection between spec blocks and sandboxed Claude Code agents that can create, modify, and run actual applications.

The architecture separates concerns into three layers: a Plate-based editor for authoring and organizing specs, a container orchestration layer that manages isolated execution environments per user, and a real-time communication layer that streams agent output back to the editor. This separation allows the editor to remain responsive while heavy computation happens in containers, and ensures that one user's buggy code cannot affect another user's environment.

The key architectural decision is to treat each spec block as an independent execution unit with its own agent session, rather than building one monolithic "generate entire app" flow. This enables incremental development, targeted regeneration, and clear traceability between specs and their implementations.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Specs as Source of Truth | Generated code is derived; specs persist and can regenerate at any time |
| Isolation by Default | Each user gets a dedicated container; execution cannot cross boundaries |
| Stream Everything | Agent output, file changes, and preview updates flow in real-time to the editor |
| Frontend-First Simplicity | Container template handles backend; users only spec UI components |
| Fail Fast, Fix Targeted | Multi-agent review catches issues early; fixes address only what failed |

---

## System Boundaries

### What This System Includes

- Plate-based rich text editor with custom spec block plugin
- Docker container orchestration for per-user sandboxed execution
- WebSocket bridge between editor and container agents
- Live preview via iframe connected to container's dev server
- Multi-agent pipeline (coder → reviewer → fixer)
- Pre-built container template with Next.js + shadcn + Supabase

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Backend code generation | 80% of prototyping is frontend; backend complexity deferred |
| Custom database schemas | Pre-built Supabase CRUD handles common patterns |
| Deployment pipeline | POC focuses on prototyping, not production hosting |
| Collaborative editing | Single-user per project simplifies container model |
| Version control UI | Files live in container; git integration is future work |

---

## Component Design

### Editor Layer

**Purpose**: Provides the authoring experience where users write and organize specs.

**Key Parts**:
- `SpecBlockPlugin` — Custom Plate plugin defining spec block type with implement button, status indicator, and output panel
- `ImplementationPanel` — Displays streaming agent output, file list, and error states
- `PreviewPanel` — Iframe pointing to container's dev server URL with hot reload
- `AgentConnector` — WebSocket client managing connection to user's container

**Patterns**: Plugin architecture (Plate's extension model), Observer pattern for real-time updates

### Container Orchestration

**Purpose**: Manages isolated execution environments where Claude Code agents run.

**Key Parts**:
- `ContainerManager` — Creates, starts, stops, and destroys user containers
- `ContainerTemplate` — Pre-built image with Next.js stack, CLAUDE.md, and running dev server
- `AgentBridge` — WebSocket server inside container that receives specs and streams output

**Patterns**: Factory pattern for container creation, Template pattern for standardized environments

### Agent Pipeline

**Purpose**: Executes specs through a multi-agent review process to ensure quality without human oversight.

**Key Parts**:
- `CoderAgent` — Primary agent that implements the spec using Claude Code
- `ReviewerAgent` — Fresh session that validates implementation against original spec
- `FixerAgent` — Addresses only the specific issues identified by reviewer
- `PipelineOrchestrator` — Manages agent sequence and iteration limits

**Patterns**: Chain of Responsibility for agent handoff, Circuit Breaker for iteration limits (max 3)

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Editor | Plate (MIT) | Free, shadcn-based, extensible plugin system, rich text + blocks |
| Frontend Framework | React + shadcn/ui | Consistent with Plate, rapid UI development |
| Container Runtime | Docker | Industry standard isolation, easy VPS deployment |
| Agent Execution | Claude Code CLI | Real file operations via `--dangerously-skip-permissions` |
| Real-time Comms | WebSocket | Bidirectional streaming for agent output |
| Container Template | Next.js 15 + Tailwind + Supabase | Modern stack that covers most prototyping needs |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| One container per user | Complete isolation; simple mental model | Higher resource usage than shared pools |
| Claude Code CLI over API | Real file/command execution, not just text generation | Requires container sandboxing, slower startup |
| Frontend-only generation | Reduces complexity, covers 80% of use cases | Users needing custom backends must wait |
| Plate free tier first | Validate concept before €299 investment | May lack polish; upgrade path exists |
| Block-level execution | Incremental changes, clear traceability | More complex than "generate all" approach |
| Max 3 review iterations | Prevents infinite loops, forces spec clarity | Some edge cases may not fully resolve |

---

## Patterns

### Spec Block Execution

**When to use**: User clicks "Implement" on any spec block.

**How it works**: The spec text is extracted, sent via WebSocket to the user's container, where Claude Code executes it with full file system access. Output streams back in real-time. On completion, the file list updates and preview iframe refreshes.

**Example**: User writes "Create a pricing table component with three tiers: Free, Pro, Enterprise. Use shadcn Card components." Clicking implement sends this to the container, Claude Code creates `components/pricing-table.tsx`, and the preview shows the rendered component.

### Multi-Agent Review

**When to use**: After coder agent completes implementation.

**How it works**: A fresh Claude Code session (reviewer) receives the original spec and generated files. It evaluates whether the implementation matches the spec. If issues are found, a fixer agent receives only the failure notes and makes targeted corrections. This repeats up to 3 times or until review passes.

**Example**: Coder generates a pricing table but forgets the Enterprise tier. Reviewer flags "missing Enterprise tier per spec." Fixer adds the missing tier. Reviewer passes on second iteration.

### Container Lifecycle

**When to use**: User opens a project or remains idle for extended periods.

**How it works**: Containers are created on-demand when a user opens their project. The template image is pre-pulled, so startup is fast. Containers persist while the user is active but are stopped after idle timeout to conserve resources. Data persists in mounted volumes.

**Example**: User opens Spec Doc, container spins up in ~5 seconds with dev server already running. User closes browser, container stops after 30 minutes idle. User returns next day, container resumes with all files intact.

---

## Execution Flow

```
[User Action]
  Write Spec ──→ Click Implement
                      │
[Editor Layer]        ▼
  Extract Spec ──→ Send via WebSocket
                      │
[Container]           ▼
  CoderAgent ──→ Execute with Claude Code
       │              │
       │         [generates files]
       ▼              │
  ReviewerAgent ◄─────┘
       │
  [pass?]──yes──→ Update UI, Refresh Preview
       │
      no
       ▼
  FixerAgent ──→ [iteration < 3?]──yes──→ ReviewerAgent
       │
      no (max reached)
       ▼
  Return partial result with warnings
```

The coder and reviewer agents run sequentially because the reviewer needs coder's output. However, multiple spec blocks could execute in parallel across different users since containers are isolated. Within a single spec block, the pipeline is strictly sequential to maintain coherence.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview