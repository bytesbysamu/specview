# 🏗️ RelateAI – Solution Architecture

**Purpose**: Technical design for implementing the [Epic](./epic.md).

---

## Architecture Overview

RelateAI is a relationship improvement platform built as a mobile-first web application with a persistent AI advisor that maintains context across sessions. The system ingests multiple input types (chat exports, free text, images), builds a longitudinal relationship profile, and delivers personalized insights grounded in relationship research frameworks.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Context Accumulation | Every interaction enriches the relationship profile; AI responses improve over time |
| Input Flexibility | Normalize all input methods (chat, text, OCR, structured) into unified context |
| Privacy by Design | Sensitive relationship data encrypted at rest; minimal data retention options |
| Research-Grounded | All AI outputs reference established frameworks (Gottman, attachment theory, NVC) |
| Mobile-First | Primary interaction is phone-based, quick check-ins and advisor chats |

---

## Component Design

### Input Processor

**Purpose**: Normalize diverse inputs into structured context for the AI advisor

**Key Modules**: Chat parser, OCR service, free-text normalizer, structured-form handler

**Patterns**: Adapter pattern for input types; Pipeline for processing stages

### Relationship Profile Engine

**Purpose**: Build and maintain longitudinal understanding of the couple's dynamic

**Key Modules**: Profile store, pattern detector, assessment scorer, context retriever

**Patterns**: Event sourcing for profile changes; RAG for context injection

### The Advisor

**Purpose**: Conversational AI grounded in relationship research and couple-specific context

**Key Modules**: Prompt builder, framework selector, response generator, memory manager

**Patterns**: Chain-of-thought reasoning; few-shot examples from research literature

### Check-In System

**Purpose**: Structured data collection through guided prompts and assessments

**Key Modules**: Prompt scheduler, response collector, partner comparison engine

**Patterns**: State machine for check-in flows; diff visualization for partner responses

---

## Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Frontend | Next.js + PWA | Mobile-first web app with offline check-in capability |
| Backend | Node.js + Express | Simple API layer; most logic in AI prompts |
| Database | Supabase (Postgres) | Auth, profiles, encrypted relationship data |
| AI | Claude API | Long context for relationship history; nuanced emotional reasoning |
| OCR | Tesseract.js / Claude Vision | Screenshot-to-text for chat images |
| Auth | Supabase Auth | Secure couple accounts with partner linking |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Web app over native | Faster iteration; no app store approval for sensitive content |
| Single AI provider (Claude) | Consistency in tone; long context handles relationship history well |
| Profile-as-context over fine-tuning | Simpler; context injection via prompts more maintainable |
| Partner accounts linked, not shared | Each partner has private space; shared insights opt-in |
| Frameworks embedded in system prompts | Ensures research-grounded responses without external lookups |
| Weekly check-ins over daily | Sustainable habit; reduces notification fatigue |

---

## Related Documents

- [Analysis](./analysis.md)
- [Epic](./epic.md)
- [Thesis](./thesis.md)