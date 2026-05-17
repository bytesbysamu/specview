---
sidebar_position: 2
---

# 🏗️ Architecture Rethink – Solution Architecture

**Purpose**: Define the new clean architecture where ClawBoi is the automation layer and products are simple frontends.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

The new architecture has two clear layers:

1. **ClawBoi** = The Automation Layer (intelligence, memory, notifications)
2. **Products** = Simple Apps (UI, payments, auth)

This replaces Constellation's original vision of building automation capabilities in Java/Spring Boot.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| **DRY** | Don't rebuild what ClawBoi already does |
| **Simplicity** | Products are just UI + payments |
| **Native AI** | Use Claude's capabilities directly, not abstractions |
| **Memory-First** | ClawBoi remembers context, products don't need to |

---

## New Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  ClawBoi = The Automation Layer                              │
│                                                              │
│  • Opportunity finding (Reddit, HN, Twitter)                 │
│  • Content drafting and analysis                             │
│  • Memory/tracking (diary, bubls, sessions)                  │
│  • Multi-channel (Telegram, WhatsApp)                        │
│  • Scheduling via cron + hooks                               │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ Telegram / API
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Products = Simple, focused apps                             │
│                                                              │
│  • Humaniz.me (Flask API + Next.js + Stripe)                │
│  • Future products: same pattern                             │
│  • No automation logic - ClawBoi handles that               │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Design

### ClawBoi (OpenClaw)

**Purpose**: Serve as the central automation and intelligence layer.

**Capabilities**:
- `WebFetch` — Retrieve data from any URL
- `Bash` — Execute commands, API calls, scripts
- `Memory` — Track conversations, people, events
- `Telegram` — Receive commands, send notifications
- `Claude` — Native AI reasoning, no abstraction needed

**Location**: VPS at `/data/.openclaw/`

### Products (Constellation Remnants)

**Purpose**: Simple frontends that handle UI, auth, and payments.

**Components**:
- `Flask API` — Minimal product logic (~150 lines)
- `Next.js Frontend` — User interface
- `Stripe` — Payment processing
- `Supabase` — Authentication

**Location**: Product-specific repos (e.g., `humanize-me/`)

---

## Execution Flow

```
[User Interaction]
   │
   ├──► Product (Humaniz.me)
   │       │
   │       └──► Flask API ──► Claude ──► Response
   │
   └──► ClawBoi (Telegram)
           │
           ├──► Opportunity Scan ──► Analysis ──► Briefing
           │
           ├──► Content Draft ──► Review ──► Post
           │
           └──► Memory Update ──► Diary Entry
```

**Key Insight**: Products handle synchronous user requests. ClawBoi handles asynchronous automation and intelligence.

---

## Integration Patterns

### Pattern 1: Telegram Briefings

ClawBoi sends daily briefings to Sam via Telegram.

**Flow**:
1. Cron triggers ClawBoi skill
2. ClawBoi fetches opportunities (Reddit, HN, etc.)
3. ClawBoi analyzes and ranks
4. ClawBoi sends summary via Telegram
5. Sam reviews and responds with actions

### Pattern 2: Memory-Assisted Engagement

ClawBoi remembers past engagements to improve future responses.

**Flow**:
1. Sam asks ClawBoi to draft a response
2. ClawBoi checks memory for past interactions
3. ClawBoi drafts response with context
4. Sam reviews, edits, posts manually

### Pattern 3: Product Notifications

ClawBoi monitors product metrics and alerts on anomalies.

**Flow**:
1. ClawBoi periodically checks product dashboards
2. If anomaly detected, sends Telegram alert
3. Sam investigates and takes action

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Delete LangChain4j | Claude's native API is simpler and more capable |
| Delete Jobs system | ClawBoi handles scheduling via cron + hooks |
| Delete Reddit adapters | ClawBoi's WebFetch + Bash handles any API |
| Keep Flask API | Product-specific logic needs to live somewhere |
| Keep Stripe/Supabase | Products need auth and payments |

---

## What Gets Deleted from Constellation

| Component | Reason for Deletion |
|-----------|-------------------|
| LangChain4j multi-provider | Claude used directly |
| Jobs/background processing | ClawBoi cron + hooks |
| Reddit/platform adapters | ClawBoi WebFetch + Bash |
| Intelligence layer | ClawBoi native capability |
| Report generation | ClawBoi + Claude |

---

## What Remains in Constellation

| Component | Reason to Keep |
|-----------|---------------|
| Flask API | Product-specific humanization logic |
| Next.js frontend | User interface |
| Stripe integration | Payment processing |
| Supabase auth | User authentication |
| Deployment configs | Docker, Coolify |

---

## Success Criteria

### Architectural

- ✅ Clear separation: ClawBoi = automation, Products = UI
- ✅ No duplicate capabilities between systems
- ✅ Simple integration patterns documented

### Operational

- ✅ ClawBoi handles all intelligence tasks
- ✅ Products remain simple and focused
- ✅ Telegram serves as primary interaction channel

---

## Related Documents

- [Epic](./epic.md) — Scope and business context
- [ClawMemory Architecture](../clawmemory/architecture.md) — Dashboard for memory data
