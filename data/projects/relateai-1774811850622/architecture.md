Here's the architecture document:

# 🏗️ RelateAI – Solution Architecture

## Architecture Overview

RelateAI is a relationship improvement platform built as a progressive web application with AI at its core. The system processes multiple input types (text, images, structured data), maintains persistent relationship context, and delivers personalized insights through both on-demand conversations and proactive notifications.

The architecture follows a document-centric approach where the relationship profile serves as the evolving source of truth. Every interaction—whether a chat analysis, check-in response, or advisor conversation—contributes to and draws from this accumulated understanding.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Advisor   │  │  Dashboard  │  │  Check-Ins  │              │
│  │   (Chat)    │  │  (Metrics)  │  │  (Forms)    │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         └────────────────┼────────────────┘                      │
│                          ▼                                       │
│              ┌───────────────────────┐                          │
│              │    Input Processor    │                          │
│              │  (Text/Image/Upload)  │                          │
│              └───────────┬───────────┘                          │
└──────────────────────────┼──────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                        API Layer                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Ingest API │  │ Advisor API │  │ Profile API │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         └────────────────┼────────────────┘                      │
│                          ▼                                       │
│              ┌───────────────────────┐                          │
│              │   Context Assembler   │                          │
│              │  (Profile + History)  │                          │
│              └───────────┬───────────┘                          │
└──────────────────────────┼──────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                        AI Layer                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   Claude API                             │    │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐           │    │
│  │  │  Parser   │  │  Advisor  │  │  Analyzer │           │    │
│  │  │  Prompts  │  │  Prompts  │  │  Prompts  │           │    │
│  │  └───────────┘  └───────────┘  └───────────┘           │    │
│  └─────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Data Layer                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Supabase   │  │   Partner   │  │  Check-In   │              │
│  │   Auth      │  │  Profiles   │  │  History    │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│  ┌─────────────┐  ┌─────────────┐                               │
│  │ Conversation│  │   Health    │                               │
│  │   Archive   │  │   Scores    │                               │
│  └─────────────┘  └─────────────┘                               │
└──────────────────────────────────────────────────────────────────┘
```

---

## Design Principles

| Principle | Description | Implementation |
|-----------|-------------|----------------|
| **Context is King** | AI quality depends on accumulated relationship understanding | Every interaction enriches the relationship profile; context assembler pulls relevant history for each request |
| **Input Flexibility** | Users communicate naturally, system adapts | Unified input processor handles text, images, uploads, and structured forms—all normalized before AI processing |
| **Privacy by Design** | Relationship data is deeply personal | End-to-end encryption for stored conversations; no raw chat data in logs; user-controlled data retention |
| **Progressive Depth** | Start simple, grow sophisticated | Onboarding captures basics; depth builds through organic use; features unlock as context accumulates |
| **Async-First** | Partners have different schedules | Check-ins work independently; comparison views only show when both complete; no real-time pressure |
| **Research-Grounded** | Advice backed by relationship science | Prompts incorporate Gottman principles, attachment theory, NVC; system explains reasoning, not just conclusions |

---

## Component Design

### Input Processor

**Purpose**: Normalize diverse input types into structured text for AI consumption.

**Files**:
- `input-processor.service.ts` — Routing and orchestration
- `chat-parser.util.ts` — WhatsApp/iMessage/generic chat extraction
- `ocr.service.ts` — Image-to-text for screenshot uploads
- `situation-form.component.ts` — Guided situation description UI

**Patterns**:
- Strategy pattern for input type handling
- Each parser returns normalized format: participants, messages with timestamps, metadata
- Free text passes through with minimal processing
- OCR uses Claude's vision capability directly

---

### The Advisor

**Purpose**: Always-available AI conversation grounded in relationship context and research.

**Files**:
- `advisor.component.ts` — Chat interface with streaming responses
- `advisor.service.ts` — Conversation management, context injection
- `advisor-prompts.ts` — System prompts with relationship frameworks
- `conversation-memory.service.ts` — Session and long-term memory handling

**Patterns**:
- Streaming responses for natural conversation feel
- Context window managed by relevance scoring
- System prompt layers: base framework → couple profile → recent history → current conversation
- Conversation summaries stored for long-term memory

---

### Relationship Profile

**Purpose**: The evolving source of truth about the couple's dynamic.

**Files**:
- `profile.service.ts` — CRUD and profile enrichment
- `onboarding-flow.component.ts` — Initial profile creation
- `assessment.service.ts` — Attachment style, love language questionnaires
- `profile-updater.service.ts` — Background enrichment from interactions

**Patterns**:
- Profile as living document, not static form
- AI extracts implicit information from conversations
- Explicit assessments (attachment style) combined with inferred patterns
- Versioned history for tracking relationship evolution

---

### Check-In System

**Purpose**: Structured pulse-checks that track relationship health over time.

**Files**:
- `checkin-scheduler.service.ts` — Weekly/monthly cadence management
- `checkin-form.component.ts` — Partner-independent response UI
- `checkin-comparison.component.ts` — Side-by-side view when both complete
- `checkin-prompts.ts` — Question banks for different check-in types

**Patterns**:
- Push notifications for check-in reminders
- Responses stored independently until both partners complete
- Comparison view highlights alignment and gaps
- Trends tracked across check-in history

---

### Dashboard

**Purpose**: Visual representation of relationship health across dimensions.

**Files**:
- `dashboard.component.ts` — Main metrics view
- `health-score.service.ts` — Score calculation from multiple signals
- `dimension-card.component.ts` — Individual metric display
- `trend-chart.component.ts` — Historical visualization

**Patterns**:
- Scores derived from: check-in responses, conversation analysis, advisor interactions
- Dimensions: Communication, Conflict Resolution, Emotional Connection, Appreciation, Growth
- No raw scores without context—always paired with insights
- Trends more important than absolute numbers

---

### Partner Linking

**Purpose**: Connect two users as a couple with appropriate data sharing.

**Files**:
- `partner-invite.service.ts` — Invite code generation and redemption
- `couple.service.ts` — Shared vs. individual data management
- `permissions.service.ts` — What each partner can see

**Patterns**:
- Invite via unique code (not email lookup for privacy)
- Some data shared (check-in comparisons), some private (individual advisor chats)
- Either partner can unlink; data handling clearly communicated
- Works fully as single-user app; partner linking optional

---

## Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend** | Angular 19 | Consistent with existing stack; strong typing for complex forms; good mobile PWA support |
| **UI Components** | Angular Material | Accessible, well-documented; conversation UI needs minimal customization |
| **State** | Signals + Services | Angular's native reactivity; simpler than NgRx for this scope |
| **Backend** | Express.js | Minimal surface area; handles API routing, auth middleware, AI orchestration |
| **AI** | Claude API | Best reasoning for nuanced relationship advice; vision capability for OCR; streaming support |
| **Auth** | Supabase Auth | Magic links for easy signup; row-level security for partner data isolation |
| **Database** | Supabase (Postgres) | Relational model fits couple/profile/check-in relationships; JSONB for flexible profile data |
| **Storage** | Supabase Storage | Encrypted file storage for uploaded screenshots and chat exports |
| **Notifications** | OneSignal | Push notifications for check-in reminders; cross-platform support |
| **Hosting** | Coolify | Consistent with existing infrastructure; Docker-based deployment |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Single AI provider (Claude)** | Relationship advice requires nuanced reasoning; Claude excels at empathy and context handling; vision capability eliminates need for separate OCR service |
| **No real-time chat sync** | Partners rarely message simultaneously; polling or manual refresh sufficient; reduces complexity and cost |
| **Profile as JSONB, not normalized tables** | Relationship profiles are schema-flexible; new attributes added through AI inference; migrations would be constant |
| **Check-ins independent, not collaborative** | Avoids coordination overhead; partners answer honestly without seeing other's response; comparison is the insight |
| **Advisor conversations ephemeral by default** | Reduces storage; privacy-friendly; only explicit "save insight" persists to profile |
| **PWA, not native app** | Faster iteration; lower distribution friction; push notifications via service worker sufficient for MVP |
| **Streaming responses everywhere** | Relationship conversations feel more natural with gradual responses; reduces perceived latency |
| **No couples therapist replacement claims** | Positioned as communication improvement tool; clear disclaimers; suggests professional help for serious issues |
| **Partner linking optional** | Full value as individual user; partner features are enhancement, not requirement; respects relationship asymmetry |
| **Dimension scores, not single "health" number** | Relationships are multidimensional; single score oversimplifies; dimension breakdown enables targeted improvement |