---
sidebar_position: 3
---

# 🏗️ LinkedIn Profile Rewrite – Solution Architecture

**Purpose**: Content structure, messaging framework, and positioning design for the LinkedIn rewrite.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

This is a content architecture, not a software architecture. The "system" is the LinkedIn profile as a conversion surface — headline and about section are the two components, each with distinct constraints (character limits, truncation behavior, rendering differences across platforms). The design goal is a messaging framework that makes every word load-bearing: identity, proof, method, invitation.

The content follows a narrative arc structure: **Credibility** (where I come from) → **Capability** (what I built) → **Invitation** (where to see it). This mirrors how a stranger processes a profile: "Can I trust this person?" → "What do they actually do?" → "Should I engage?"

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Front-load the signal | Headline must survive 120-char mobile truncation. The identity ("AI builder") and the hook ("brain dumps → shipped products") must appear before the cut. |
| Proof over adjectives | "18 epics in 42 hours" does more work than "passionate AI innovator." Every claim is backed by a number or a named product. |
| One live product > many MVPs | Naming only Humaniz.me (live, revenue, production) is stronger than listing four pre-validation projects. Credibility comes from shipped, not started. |
| Accessible arc, technical proof | The story (Java → AI → methodology) is readable by anyone. The numbers (42 hours, 18 epics, $5–25/mo) earn respect from technical readers. Both audiences served simultaneously. |
| Pure indie positioning | No employer mention in headline or about. The audience doesn't need employment context to evaluate builder credibility. Experience section handles that separately. |

---

## Component Design

### Task 1: Headline Variants

**Purpose**: Establish identity and hook in ≤220 characters, mobile-safe at 120.

**Structure**: `[Identity] | [Method/Hook] | [Named System]`

**Constraints**:
- 220-character hard limit (LinkedIn desktop)
- 120-character soft limit (LinkedIn mobile truncation)
- No emojis (builder aesthetic, not LinkedIn-bro)
- Keywords that matter: AI, builder, shipping, methodology/system

**Content framework**:
```
Layer 1 (chars 1–50):   Identity     → "AI builder"
Layer 2 (chars 51–120): Hook         → "shipping products from brain dumps"
Layer 3 (chars 121–220): Named system → "Building the Five-Part Agent"
```

Mobile users see layers 1–2. Desktop users see all three. The message degrades gracefully.

**Example variants**:
```
A: "AI builder — shipping products from brain dumps → Five-Part Agent"
B: "AI builder | Brain dump → shipped product in hours | Five-Part Agent"
C: "Building the Five-Part Agent — AI methodology that ships 18 epics in 42 hours"
```

Variant evaluation criteria: (1) Does the identity land before char 50? (2) Does the hook survive mobile truncation at 120? (3) Does the named system appear? (4) Is there a number or proof point?

### Task 2: About Section Arc

**Purpose**: Tell the complete story in 3 paragraphs, ≤2,600 characters.

**Structure**:

```
Paragraph 1: THE ARC (credibility)
├── 10 years Java/Angular — enterprise engineering
├── Pivot to AI — building with Claude, not just coding
└── Realization: methodology > tools

Paragraph 2: THE METHOD (capability)
├── Named: Spec Doc / Five-Part Agent
├── Quantified: 18 epics, 42 hours, brain dump → shipped
├── Proof: Humaniz.me — live in production, $5-25/mo
└── How it works: brain dump → specs → code → product

Paragraph 3: THE THESIS (worldview)
├── Same code, many products
├── The moat is positioning, not technology
└── Ship the car, not the engine
```

**Character budget**:
- Paragraph 1: ~700 chars (credibility setup)
- Paragraph 2: ~1,100 chars (the meat — method + proof)
- Paragraph 3: ~500 chars (thesis + transition to CTA)
- CTA block: ~300 chars (links + invitation)
- Total: ~2,600 chars

### Task 3: CTA Block

**Purpose**: Convert interest into action — visit the product, read the methodology.

**Components**:
- `link-product` — Humaniz.me landing page URL
- `link-methodology` — THE post (methodology write-up URL)

**Tone**: Invitation, not pitch. "See it live" energy. No "let's connect" / "open to opportunities" / "DM me" LinkedIn defaults.

**Structure**:
```
[One-line bridge from thesis to action]
🔗 See it live: humaniz.me
📖 Read how it works: [methodology post URL]
```

Note: Emoji usage limited to link markers only — functional, not decorative. If emoji-free is preferred, use plain text markers or line breaks.

### Task 4: Constraint Review

**Purpose**: Validate all copy against hard constraints before publishing.

**Checklist**:
- [ ] Headline ≤ 220 characters
- [ ] Headline core message survives 120-char mobile truncation
- [ ] About section ≤ 2,600 characters
- [ ] No employer/company name mentioned
- [ ] Only Humaniz.me named as product (no Trendfy, no pre-validation projects)
- [ ] Numbers present: 18 epics, 42 hours, pricing tiers
- [ ] Five-Part Agent or Spec Doc named
- [ ] Links are valid and destinations are current
- [ ] Passes 10-second stranger test
- [ ] No recruiter-bait language ("passionate," "innovative," "results-driven")

---

## Execution Flow

```
[Phase 1: Draft]
   Task 1 (headline) ──┐
   Task 2 (about)    ──┤ parallel
                        │
[Phase 2: Polish]       ▼
   Task 3 (CTA) ────→ Task 4 (review)
                           │
[Phase 3: Ship]            ▼
                      Task 5 (publish)
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Employer mention | Omit entirely | Target audience (builders, users) doesn't need employment context. Including it creates "side project?" framing that undermines credibility. Experience section handles employment separately. |
| Products to name | Humaniz.me only | One live product with revenue > a list of MVPs. Credibility comes from shipped and earning, not started. |
| Methodology naming | "Five-Part Agent" in headline, "Spec Doc" in body | Five-Part Agent is the hook (curiosity-inducing, named system). Spec Doc is the explanation (what it actually is). Both serve different functions. |
| Tone | Accessible + numbers | Adjective-free positioning. Let "18 epics in 42 hours" do the work that "passionate innovator" tries and fails to do. |
| CTA style | Invitation, not pitch | "See it live" converts better than "let's connect" for the target audience. Builders respect show-don't-tell. |
| Emoji usage | Minimal (link markers only) | Builder aesthetic. Emoji-heavy profiles signal LinkedIn-bro, not serious builder. Functional use only. |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)

