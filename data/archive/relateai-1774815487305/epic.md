# Epic: RelateAI

**Purpose**: Capability-definition document that validates this product.

**Source**: Addresses issues in [Analysis](./analysis.md).

---

## Business Value

Couples spend $200+/hour on therapy sessions that happen once a week—if they can get an appointment at all. Meanwhile, the actual relationship friction happens in the daily moments: the text that came across wrong, the conversation that escalated, the thing you want to say but don't know how. RelateAI captures this daily window, offering relationship guidance at the moment it's needed rather than three weeks later on a therapist's couch.

The relationship wellness market is underserved by technology. Dating apps have captured "finding someone" ($5B+ market), but "keeping someone" remains analog—books, podcasts, expensive professionals. RelateAI positions as the first AI-native relationship companion that learns your specific dynamic over time, not a chatbot dispensing generic advice.

**Value Proposition**: On-demand relationship guidance grounded in your actual communication patterns and relationship context, available when you need it—not when you can book an appointment.

---

## Scope

### What This Epic Covers

- **The Advisor** – AI conversation interface for relationship guidance, situation analysis, and communication coaching
- **Flexible Input** – Multiple ways to bring relationship context into the system (paste, describe, upload)
- **Relationship Context** – Onboarding flow that establishes the AI's understanding of the couple
- **Persistent Memory** – The AI remembers past conversations and builds understanding over time

### What This Epic Does NOT Cover

- ❌ Partner pairing / two-user accounts — V2 feature requiring auth complexity
- ❌ Relationship Dashboard with health scores — Requires pattern data we won't have at launch
- ❌ Guided Check-Ins — Needs notification infrastructure and habit loops
- ❌ WhatsApp/platform integrations — Start with manual input, validate before building integrations
- ❌ OCR/screenshot parsing — Nice-to-have, not essential for core value delivery

---

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Relationship Context Onboarding** | None | 2 | 2 days | High |
| 2 | **Multi-Input Conversation Interface** | None | 1 | 2 days | High |
| 3 | **Advisor AI with Memory** | 1, 2 | — | 3 days | High |
| 4 | **Session Persistence & History** | 3 | — | 1 day | High |

### Task Details

#### Task 1: Relationship Context Onboarding

Build a structured onboarding flow that captures relationship basics: how long together, living situation, communication style preferences, and what they're hoping to improve. This context seeds the AI's understanding and makes advice specific rather than generic.

#### Task 2: Multi-Input Conversation Interface

Create an input system that accepts: pasted chat text, free-form situation descriptions, and conversation-from-memory narratives. The UI should make it obvious these are all valid ways to bring context to the AI. No parsing magic needed—the AI handles interpretation.

#### Task 3: Advisor AI with Memory

Implement the core Advisor experience: a conversational AI grounded in relationship research (Gottman principles, attachment theory, NVC patterns) that maintains context across the session and references the user's relationship profile. This is the product's primary value delivery mechanism.

#### Task 4: Session Persistence & History

Store conversation sessions so users can return to past advice, and so the AI can reference "last time we talked about X." This transforms the product from a stateless tool into a relationship companion that learns.

---

## Success Criteria

This epic is complete when:

- ✅ A new user can complete onboarding in under 3 minutes and receive personalized first advice
- ✅ Users can paste a chat excerpt and receive analysis specific to their relationship context
- ✅ Users can describe a situation in plain text and receive actionable coaching
- ✅ The AI references past conversations and relationship context in its responses
- ✅ Users return to the app after their first session (retention signal)

---

## Non-Goals

Explicitly NOT doing:

- ❌ Real-time chat integration — Manual input validates demand before we build complexity
- ❌ Quantified relationship metrics — Scores require data we don't have yet; start qualitative
- ❌ Couple accounts — Single-user MVP; partner features after validation
- ❌ Mobile app — Web-first; mobile after product-market fit
- ❌ Therapist matching/referrals — Stay in our lane; we're a companion, not a clinical tool

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Architecture](./architecture.md) – System design
- [Thesis](./thesis.md) – Product vision