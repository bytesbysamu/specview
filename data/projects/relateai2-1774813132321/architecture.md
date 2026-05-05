# 🏗️ RelateAI2 – Solution Architecture

**Purpose**: Technical design for implementing the [Epic](./epic.md).

---

## Architecture Overview

RelateAI2 is a relationship companion platform built around a persistent AI advisor that accumulates context over time. The system ingests diverse input types (chat exports, free-form text, check-ins), processes them through specialized parsers, and feeds them into a context-aware AI layer that maintains couple-specific memory. The architecture prioritizes data privacy, flexible input handling, and longitudinal relationship insights.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Context accumulation | Every interaction enriches the AI's understanding of the couple |
| Input flexibility | Multiple parsers normalize diverse inputs to a common format |
| Privacy by design | End-to-end encryption, no raw chat storage, only derived insights |
| Research-grounded | AI responses anchored in Gottman, attachment theory, NVC frameworks |
| Progressive disclosure | Start simple, reveal depth as users engage more |

---

## Component Design

### Input Processing Layer

**Purpose**: Normalize diverse input types into structured relationship data

**Key Components**: Chat parser, OCR service, free-text analyzer, check-in collector

**Patterns**: Strategy pattern for input type handling, adapter pattern for platform-specific parsing

### Relationship Context Engine

**Purpose**: Maintain and query the accumulated understanding of each couple

**Key Components**: Context store, pattern detector, timeline builder

**Patterns**: Event sourcing for relationship history, CQRS for read/write separation

### The Advisor (AI Layer)

**Purpose**: Provide personalized, research-grounded relationship guidance

**Key Components**: Prompt orchestrator, memory retriever, response generator

**Patterns**: RAG for context injection, chain-of-thought for nuanced responses

### Check-In System

**Purpose**: Structured periodic relationship assessment

**Key Components**: Pulse surveys, comparison engine, trend analyzer

**Patterns**: Observer pattern for partner response pairing

---

## Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Frontend | React Native / Expo | Cross-platform mobile, intimate form factor |
| Backend | Node.js / Express | Fast iteration, TypeScript shared with frontend |
| AI | Claude API | Strong reasoning, long context, safety alignment |
| Database | PostgreSQL + pgvector | Relational structure + vector embeddings for semantic search |
| Auth | Supabase Auth | Couples pairing, secure partner linking |
| Storage | Encrypted blob storage | Chat exports processed then purged |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Mobile-first | Relationships happen on phones; desktop is secondary |
| No raw chat storage | Privacy-critical; store only extracted patterns and insights |
| Single AI advisor persona | Consistency builds trust; feels like "your" therapist |
| Couple-linked accounts | Enables partner comparison features while respecting individual privacy |
| Async-first check-ins | Partners answer independently before seeing comparison |
| Attachment style as core model | Research-backed framework that explains most relationship dynamics |

---

## Related Documents

- [Analysis](./analysis.md)
- [Epic](./epic.md)
- [Thesis](./thesis.md)