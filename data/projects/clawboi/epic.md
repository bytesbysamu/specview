---
sidebar_position: 1
---

# 🎯 Architecture Rethink – Epic

**Purpose**: Define the DRY consolidation of automation capabilities between ClawBoi and Constellation.

**Context**: Now that ClawBoi (OpenClaw) exists as a functioning automation layer, Constellation contains duplicate capabilities that should be eliminated.

---

## Business Value

ClawBoi already provides automation capabilities that Constellation was building from scratch:

| Capability | Constellation Built | ClawBoi Already Has |
|------------|--------------------|--------------------|
| Fetch data | Jobs + adapters | WebFetch + Bash |
| Analyze text | LangChain4j | Claude (native) |
| Score/rank | Custom logic | Claude reasoning |
| Generate reports | Report service | Claude + memory |
| Notifications | Not built | Telegram (working) |
| Remember context | Not built | Memory system |

**The Arbitrage**: ClawBoi uses Claude's native capabilities. No need for custom abstractions, job systems, or multi-provider LLM layers when Claude handles it directly.

**Value Proposition**: By eliminating duplicate automation code from Constellation, we reduce maintenance burden, simplify the architecture, and let each system do what it does best.

---

## Scope

### What This Epic Covers

- Identifying which Constellation components to delete
- Defining the new clean architecture
- Establishing integration patterns between ClawBoi and products
- Documenting what remains in Constellation (product-specific)

### What This Epic Does NOT Cover

- ❌ Building new ClawBoi features (separate epic)
- ❌ Migrating existing Constellation data
- ❌ Changing Humaniz.me product functionality
- ❌ New product launches

---

## Tasks

**Note**: Task status is tracked in timeline, not here.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Document deletion list** | None | — | 2 hours | High |
| 2 | **Define kept components** | 1 | — | 1 hour | High |
| 3 | **Design integration pattern** | 2 | — | 2 hours | High |
| 4 | **Update Constellation docs** | 3 | — | 1 hour | Medium |

### Task Details

#### Task 1: Document Deletion List

Identify all Constellation components that duplicate ClawBoi functionality.

**Components to Delete**:
- LangChain4j multi-provider abstraction
- Jobs/background processing system
- Reddit/platform adapters
- Intelligence layer (Fetch → Analyze → Report)
- Report generation services

#### Task 2: Define Kept Components

Document what remains in Constellation for product-specific needs.

**Components to Keep**:
- Humaniz.me Flask API (~150 lines)
- Next.js frontend
- Stripe payments integration
- Supabase authentication

#### Task 3: Design Integration Pattern

Define how ClawBoi serves as the automation layer for products.

**Pattern**: Products are simple frontends with payments. ClawBoi handles all automation, intelligence, and notifications via Telegram/WhatsApp.

#### Task 4: Update Constellation Docs

Update Constellation strategy docs to reflect the new architecture.

---

## Success Criteria

- ✅ Clear list of deleted vs kept components documented
- ✅ New architecture diagram created
- ✅ Integration pattern defined and documented
- ✅ Constellation docs updated to reflect changes
- ✅ No duplicate automation capabilities between systems

---

## Non-Goals

- ❌ Immediate code deletion (documentation first)
- ❌ Breaking existing Humaniz.me functionality
- ❌ Building new automation features
- ❌ Changing ClawBoi's architecture

---

## Related Documents

- [Architecture](./architecture.md) — System design for the new architecture
- [ClawMemory Epic](../clawmemory/epic.md) — Dashboard for ClawBoi memory data
