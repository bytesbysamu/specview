# 🎯 Epic: Spec Doc POC 2

**Purpose**: Build a spec-driven development editor where structured text blocks execute against real Claude Code agents in sandboxed containers.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Non-technical founders and freelancers can describe what they want in structured spec blocks and get working React code without writing any themselves. The gap between "idea" and "prototype" shrinks from days to minutes. This captures users who can't use Claude Code directly because they lack the technical context to guide it.

The market is validated: Claude Code works. The barrier is access and structure. By providing pre-configured containers with opinionated stacks and multi-agent review, we remove the setup friction and quality variance that makes raw AI coding tools unusable for non-developers.

**Value Proposition**: Write specs, get working React apps—no coding required.

---

## Scope

### What This Epic Covers

- **Plate-based editor** with custom spec block type (implement button, status indicators)
- **Docker container orchestration** with pre-built Next.js + shadcn template
- **Claude Code execution** via `--dangerously-skip-permissions` in sandboxed containers
- **Multi-agent review** (coder → reviewer, max 3 iterations)
- **Live preview** via iframe to container's dev server

### What This Epic Does NOT Cover

- ❌ Backend code generation — Pre-built Supabase CRUD covers 80% of needs
- ❌ Plate Plus purchase — Validate with free Plate first
- ❌ Production deployment — POC targets local preview only
- ❌ User authentication — Manual container assignment for POC
- ❌ Billing/subscriptions — Free during validation

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Plate editor with spec blocks** | None | — | 3 days | High |
| 2 | **Docker container template** | None | 1 | 2 days | High |
| 3 | **Agent execution pipeline** | 1, 2 | — | 3 days | High |
| 4 | **Multi-agent review loop** | 3 | — | 2 days | High |
| 5 | **Live preview integration** | 2, 3 | — | 1 day | High |

### Task 1: Plate Editor with Spec Blocks

Set up Plate editor with a custom "spec block" node type. Each spec block has: editable rich text area for the spec content, "Implement" button, status indicator (idle/running/complete/failed), and expandable output panel. Slash command `/spec` creates new spec blocks.

### Task 2: Docker Container Template

Build the pre-configured Docker image: Next.js 15 + shadcn/ui + Tailwind + Supabase client. Include CLAUDE.md with coding patterns and constraints. Container runs `npm run dev` on startup, exposing port 3000 for preview. Design for one container per user session.

### Task 3: Agent Execution Pipeline

Connect spec blocks to containers via WebSocket. When user clicks "Implement", send spec text to container, spawn Claude Code with `--dangerously-skip-permissions`, stream stdout/stderr back to editor, parse and display generated file list. Handle timeouts and errors gracefully.

### Task 4: Multi-Agent Review Loop

After coder agent completes, spawn reviewer agent in fresh session. Reviewer compares implementation against original spec, outputs pass/fail with specific issues. On fail, fixer agent addresses only failed criteria. Cap at 3 total iterations. Surface final status to user.

### Task 5: Live Preview Integration

Embed iframe pointing to container's dev server (port 3000). Auto-refresh on file changes. Show loading state during implementation. Handle container not-ready states. Preview panel sits alongside editor in split view.

---

## Success Criteria

This epic is complete when:

- ✅ User can write a spec block describing a React component
- ✅ Clicking "Implement" generates working code in the container
- ✅ Reviewer agent catches obvious spec violations and triggers fixes
- ✅ Live preview shows the running component within 60 seconds
- ✅ Non-technical tester can create a simple landing page without help

---

## Non-Goals

- ❌ Mobile responsiveness — Desktop-first for POC
- ❌ Collaborative editing — Single-user sessions only
- ❌ Version control integration — File persistence within container is sufficient
- ❌ Custom container stacks — One opinionated template for now

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking