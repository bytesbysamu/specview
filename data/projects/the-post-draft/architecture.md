---
sidebar_position: 3
---

# 🏗️ The Post Thread – Solution Architecture

**Purpose**: Technical design for the thread's structure, content strategy, and proof system.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

This isn't a code architecture — it's a content architecture. The thread is a 10-unit narrative system where each tweet has one job, one emotional beat, and one proof point. The architecture defines the structure (what goes where), the proof system (how claims are backed), the tone constraints (what language is allowed), and the cross-post adaptation layer (Twitter → LinkedIn).

The thread follows a five-act structure compressed into 10 tweets: Hook (1) → Failure Arc (2-3) → System Arc (4-5) → Pattern Payload (6-7) → Proof + CTA (8-10). This mirrors classic storytelling structure but optimized for the Twitter scroll — each tweet must work as a standalone insight while also pulling the reader into the next one.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Every claim has a receipt | No tweet contains a qualitative claim ("powerful", "game-changing") without a quantitative anchor from the fact sheet |
| War story, not tutorial | First person past tense ("I built", "I failed"), never second person imperative ("you should", "try this") |
| Name the pattern, don't explain the tool | The thread sells the methodology (Five-Part Agent), not the product (Spec Doc). The product is proof, not payload |
| Compression over completeness | Each tweet is ≤280 chars. If a point can't be compressed, it gets cut — not split across tweets |
| One primary CTA | Landing page is primary. TestFlight is secondary ("and if you want to touch it..."). Never split attention equally |

---

## Component Design

### Task 1: Proof Point Extraction

**Purpose**: Build a reference table mapping every usable number to its thread position

**Components**:
- `docs/the-post-numbers.md` — source fact sheet (read-only, do not modify)
- Proof reference table (working artifact, not persisted) — maps each number to a tweet slot

**Patterns**: Anti-Corruption Layer — the fact sheet is the external source; the proof table is the internal domain model. Thread drafting never reads the fact sheet directly, only the proof table. This prevents the draft from drifting toward numbers that are interesting but don't serve the arc.

**Proof table structure**:

| Number | Context | Tweet Slot | Usage |
|--------|---------|------------|-------|
| 175 | Total commits | 1 (Hook) | Scale of autonomous output |
| 18 | Epics generated | 1 (Hook) | Breadth of specification |
| 42 | Hours elapsed | 1 (Hook) | Speed of execution |
| 18 | Failed projects before system | 2-3 (Failure) | Cost of not having a system |
| 3 | Paragraphs of braindump input | 6-7 (Pattern) | Simplicity of input |

### Task 2: Pattern Name Crystallization

**Purpose**: Lock the name that the thread introduces to the world

**Components**:
- Name evaluation matrix (working artifact)
- One-line definition (persisted in the thread itself)

**Evaluation criteria**:
1. **Curiosity test**: Does "Five-Part Agent" make a technical founder ask "what are the five parts?" Yes — numbers in names create information gaps.
2. **Claim test**: Is "Five-Part Agent" already used by LangChain, CrewAI, AutoGen, or any major agent framework? Search required.
3. **Fit test**: Does "Five-Part Agent" + a one-line definition fit in a single tweet (≤280 chars)? "The Five-Part Agent: braindump → analysis → epic → architecture → implementation. Each doc feeds the next. The last one writes the code." = 158 chars. Passes.

**Alternatives ranked**:
- "Five-Part Agent" — strong (numbered, novel, curiosity-inducing)
- "The Five-Part Loop" — weaker (loops imply repetition, this is a pipeline)
- "Spec-to-Ship Pipeline" — descriptive but generic (sounds like CI/CD)
- "Document-First Agent" — accurate but boring (no information gap)

### Task 3: Thread Draft

**Purpose**: Produce the 10-tweet narrative

**Components**:
- 10 tweet drafts, each tagged with: slot number, arc position, proof point used, character count
- Thread continuity markers (each tweet's last line creates pull into the next)

**Arc mapping**:

```
Tweet 1:  HOOK        — Numbers that stop the scroll
Tweet 2:  FAILURE     — The 18 failed projects (pattern of failure)
Tweet 3:  FAILURE     — Why chat-based AI dev breaks at scale
Tweet 4:  SYSTEM      — The shift: stop chatting, start specifying
Tweet 5:  SYSTEM      — Braindump → specs → code (the pipeline)
Tweet 6:  PATTERN     — Name drop: Five-Part Agent
Tweet 7:  PATTERN     — The five parts, one line each
Tweet 8:  PROOF       — Product 1 shipped, time from braindump
Tweet 9:  PROOF       — Product 2 shipped, commit receipts
Tweet 10: CTA         — Landing page + TestFlight + one sentence
```

**Tone constraints** (enforced in Task 5):
- ✅ "I failed 18 times before this worked"
- ✅ "175 commits. Zero typed by hand."
- ❌ "We're thrilled to introduce..."
- ❌ "Here's how you can build your own..."
- ❌ "The future of AI development is..."
- ❌ "Like and retweet if you agree"

### Task 4: CTA + Proof Anchoring

**Purpose**: Final verification that every claim has a receipt and the CTA is sharp

**Components**:
- Claim-to-proof audit (every qualitative statement cross-referenced against proof table)
- CTA tweet final copy

**CTA structure**:
```
Primary:   Landing page URL (what it is, what they get)
Secondary: TestFlight (for people who want to touch it)
Tertiary:  None. Two actions max.
```

### Task 5: Tone + Compression Edit

**Purpose**: Strip tutorial language, compress to 280-char limit, ensure narrative flow

**Kill list** (phrases that get cut on sight):
- "I'm excited to share" / "I'm humbled"
- "Here's how" / "Here's what I learned"
- "Game-changing" / "Revolutionary" / "Powerful"
- "In this thread" / "Thread 🧵" (let the content speak)
- "Let me explain" / "Let me break it down"
- Any sentence that starts with "You"

### Task 6: LinkedIn Cross-Post

**Purpose**: Reformat for LinkedIn's single-post format

**Adaptation rules**:
- Collapse 10 tweets into continuous narrative with line breaks
- Remove thread numbering
- Add one-line intro: slightly more context for LinkedIn's less-technical audience
- Keep same arc, same tone, same proof points
- Max 3,000 characters (LinkedIn's limit for non-article posts)
- No hashtags (they look desperate on LinkedIn)

---

## Execution Flow

```
[Phase 1: Research]
   Task 1 (proof points) ──→ Task 2 (name)
                                │
[Phase 2: Draft]                ▼
                    Task 3 (10-tweet draft)
                         │          │
[Phase 3: Polish]        ▼          ▼
                    Task 4 (CTA)  Task 5 (tone)
                         │          │
[Phase 4: Adapt]         ▼          ▼
                    Task 6 (LinkedIn reformat)
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Thread length | Exactly 10 tweets | Long enough to tell the full arc, short enough that people finish. 10 is the upper bound of Twitter thread engagement before drop-off accelerates |
| Pattern name position | Tweets 6-7 (middle) | Hook pulls them in, failure arc creates empathy, THEN you name the thing. Naming it in tweet 1 loses the story |
| CTA position | Tweet 10 only | Scattered CTAs dilute urgency. One CTA at the end, after proof, converts better than three CTAs throughout |
| No images/screenshots | Text only | Images slow the scroll on mobile. The numbers ARE the visual. If the thread works, a follow-up tweet with a screenshot can be added later — not in the thread itself |
| War story over tutorial | First person past tense | Technical founders trust founders who show scars, not teachers who show slides. "I failed 18 times" > "5 steps to build an AI agent" |
| LinkedIn as cross-post, not native | Reformatted, not rewritten | One canonical artifact (Twitter thread). LinkedIn gets the same content in a different container. Writing LinkedIn-native content is a separate capability, out of scope |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)

