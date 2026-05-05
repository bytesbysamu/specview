# Architecture: RelateAI

**Purpose**: Long-lived system design document.

**References**: Addresses issues in [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

RelateAI is architected as a **context-accumulating AI companion** rather than a stateless analysis tool. The central insight is that relationship advice quality scales directly with historical context—generic tips help no one, but advice grounded in six months of understood patterns becomes genuinely useful. This drives every architectural decision.

The system operates on three layers: an **input normalization layer** that converts diverse sources (WhatsApp exports, screenshots, free text, structured questionnaires) into a unified conversation/context format; a **relationship context engine** that maintains and evolves understanding of each couple's dynamic over time; and a **interaction layer** that surfaces insights through the Advisor, Dashboard, and Check-in interfaces.

The key architectural bet is treating the AI not as a feature but as the core—the relationship context engine IS the product. Everything else (parsing, UI, notifications) exists to feed context in and surface insights out.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Context is king | Every feature must either add context or use context. No standalone utilities. |
| Privacy by architecture | Raw conversations processed and summarized, not stored verbatim. Users own their data. |
| Input flexibility | Never force a single input method. Relationships happen across many channels. |
| Grounded, not generic | All AI outputs reference specific patterns from the couple's history. |
| Progressive understanding | System improves with time. First-day experience differs from six-month experience. |
| Couples, not individuals | Data model treats the relationship as the primary entity, not either partner. |

---

## Component Design

### Input Normalization Layer

**Purpose**: Convert any input format into structured context the AI can reason over.

**Components**:
- `ConversationParser` — Handles WhatsApp export format, detects speakers, extracts timestamps
- `OCRProcessor` — Extracts text from screenshot uploads via vision model
- `FreeTextNormalizer` — Structures narrative descriptions into conversation-like events
- `StructuredInputCollector` — Manages questionnaires, check-ins, and guided prompts

**Patterns**: Adapter pattern for input sources. Each adapter produces a `ContextEvent` regardless of source. This lets us add new input types (Instagram DMs, voice memos) without touching downstream logic.

*Consider*: OCR quality varies wildly. The system should ask for clarification when confidence is low rather than silently misinterpreting.

### Relationship Context Engine

**Purpose**: Maintain evolving understanding of each couple's patterns, history, and dynamics.

**Components**:
- `RelationshipProfile` — Long-lived document capturing attachment styles, communication patterns, recurring themes, conflict triggers
- `ContextAccumulator` — Processes new inputs and updates the profile incrementally
- `PatternDetector` — Identifies recurring dynamics (pursuer-distancer, criticism-defensiveness cycles, etc.)
- `InsightGenerator` — Produces observations grounded in Gottman research and attachment theory

**Patterns**: Event sourcing for context accumulation. Every input is an event that modifies the relationship profile. This preserves the ability to "replay" understanding and explain how the system reached its conclusions.

*Consider*: The profile must be human-readable. Users should be able to see what the AI "knows" about them. This builds trust and catches misunderstandings.

### Interaction Layer

**Purpose**: Surface insights through multiple interaction modes.

**Components**:
- `Advisor` — Conversational interface grounded in relationship context
- `Dashboard` — Visual health scores and trend lines across dimensions
- `CheckInOrchestrator` — Manages cadence and content of guided check-ins
- `ComparisonEngine` — When both partners answer independently, surfaces alignment/gaps

**Patterns**: The Advisor uses retrieval-augmented generation, pulling relevant context from the RelationshipProfile before responding. Dashboard scores derive from pattern analysis, not arbitrary metrics.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | React Native or Flutter | Cross-platform mobile required. Relationship management happens on phones. |
| Backend | Node.js/Express or Python/FastAPI | API simplicity over performance. AI calls dominate latency anyway. |
| Data | PostgreSQL + Vector Store | Structured data for profiles, vectors for semantic search over conversation history. |
| AI | Claude API (primary) | Best at nuanced relationship reasoning. Streaming for Advisor responsiveness. |
| OCR | Claude Vision or Google Vision | Vision model handles screenshot extraction without separate OCR service. |
| Auth | Supabase Auth | Handles couple linking (two users, one relationship) without custom auth logic. |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Summarize conversations, don't store verbatim | Privacy-first. Users more comfortable knowing raw texts aren't retained. | Lose ability to re-analyze with improved models. Mitigate with optional "vault" feature. |
| Relationship as primary entity | Enables partner comparison, shared context, couples features. | More complex data model. Single-user onboarding must still work. |
| No real-time chat integration | Avoid permission complexity and platform dependency. | Users must manually input. Mitigate with easy paste/upload flows. |
| Claude over fine-tuned model | Relationship advice requires reasoning, not pattern matching. General capability beats domain fine-tuning here. | Higher per-query cost. Mitigate with context caching. |
| Check-ins over passive monitoring | Active participation builds engagement. Passive feels surveillance-y. | Requires user effort. Mitigate with quick, low-friction prompts. |
| Dimension scores derived, not self-reported | Users are bad at rating their own communication quality. AI assessment more consistent. | Users may disagree with scores. Mitigate with explainability. |

---

## Execution Flow

```
[Input Phase]
  Upload/Paste ──→ Parse/Normalize
                        │
[Context Phase]         ▼
  RelationshipProfile ←── Accumulate Context
         │
         ▼
[Insight Phase]
  Pattern Detection ──→ Advisor/Dashboard/Check-in
```

**Blocking relationships**: Parsing must complete before context accumulation. Profile must exist before pattern detection. All input types flow through the same accumulation pipeline.

**Parallel opportunities**: Multiple input sources can be processed simultaneously. Dashboard computation and Advisor availability are independent. Check-in prompts can be generated while conversation parsing runs.

**Critical path**: New user → First input → Initial profile → First Advisor interaction. This path must be under 30 seconds or users churn.

---

## Data Model (Conceptual)

```
Relationship
  │
  ├── Partner A (User)
  ├── Partner B (User, optional initially)
  │
  ├── RelationshipProfile (evolving document)
  │     ├── AttachmentStyles
  │     ├── CommunicationPatterns
  │     ├── RecurringThemes
  │     └── ConflictTriggers
  │
  ├── ContextEvents (append-only)
  │     ├── ConversationSummaries
  │     ├── SituationDescriptions
  │     └── CheckInResponses
  │
  └── DimensionScores (computed)
        ├── CommunicationQuality
        ├── ConflictResolution
        └── EmotionalConnection
```

*Consider*: Partner B joining later must feel seamless. The relationship already has context from Partner A—Partner B adds their perspective, not starts fresh.

---

## Privacy Architecture

| Data Type | Storage | Retention | User Control |
|-----------|---------|-----------|--------------|
| Raw conversations | Processed, not stored | Immediate deletion after summarization | Can enable "vault" for optional retention |
| Conversation summaries | Encrypted at rest | Until user deletion | Full export, selective deletion |
| Profile data | Encrypted at rest | Account lifetime | View, edit, delete any section |
| Check-in responses | Encrypted at rest | Account lifetime | Full history access |

**Partner visibility**: Each partner controls what the other can see. Default is shared check-in results, private conversation uploads.

---

## Scaling Considerations

**Early stage**: Monolithic backend, single AI provider. Optimize for iteration speed.

**Growth stage**: Separate context engine as service. Add AI provider redundancy. Introduce caching for repeated profile retrievals.

**Not premature**: Don't build multi-model routing, real-time sync, or enterprise features until demand exists.

---

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| AI gives harmful relationship advice | Ground all advice in established research. Include disclaimers. Detect crisis language and refer to professionals. |
| Partner surveillance/abuse potential | No location tracking. No stealth features. Both partners notified when either accesses shared data. |
| Context accumulation errors | Users can view and edit what the AI "believes" about them. Incorrect patterns can be flagged. |
| Single point of failure (Claude) | Abstract AI provider. Test with Claude, prepare Gemini fallback. |

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and business context
- [Thesis](./thesis.md) – Vision