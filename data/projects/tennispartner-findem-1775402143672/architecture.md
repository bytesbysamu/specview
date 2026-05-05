# 🏗️ Architecture: TennisPartner FindEm

**Purpose**: Long-lived system design document for a tennis partner matching application.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

TennisPartner FindEm is a mobile-first application that connects tennis players looking for practice partners, match opponents, or doubles teammates. The core insight is that tennis, unlike team sports, requires explicit coordination to play—you cannot practice alone, and finding compatible partners is surprisingly difficult.

The system operates as a matching platform with three key flows: profile creation (skill level, availability, location), discovery (finding compatible players nearby), and connection (messaging and scheduling). We prioritize low-friction onboarding over comprehensive profiling, recognizing that players will refine their preferences through actual matches rather than extensive questionnaires.

The architecture separates the matching algorithm from the social features, allowing us to iterate on match quality independently from communication features. This modularity means we can start with simple proximity-based matching and evolve toward skill-balanced recommendations without rebuilding the entire system.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Mobile-First | All interactions designed for one-handed phone use at the court |
| Low Friction | Play within 3 taps from opening the app |
| Trust Through Transparency | Show mutual connections, match history, reliability scores |
| Location-Centric | Everything anchored to courts, not abstract distances |

---

## System Boundaries

### What This System Includes

- Player profile management (skill, availability, preferences)
- Court-based discovery and search
- In-app messaging between matched players
- Match scheduling with calendar integration
- Basic reputation system (showed up / didn't show up)

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Court booking/reservations | Complex integrations with each facility; use existing systems |
| Payment processing | No monetization in MVP; adds legal complexity |
| Video analysis/coaching | Different product category; stay focused on connection |
| League/tournament management | Requires admin tools and complex scheduling; future capability |

---

## Component Design

### Player Service

**Purpose**: Manages player identity, preferences, and availability

**Key Parts**:
- `PlayerProfile` — Core identity with skill self-assessment (NTRP rating), play style preferences
- `AvailabilityManager` — Recurring and one-time availability windows
- `PreferenceEngine` — Match criteria (skill range, distance, play type)

**Patterns**: Event sourcing for profile changes enables "undo" and audit trail

### Discovery Service

**Purpose**: Finds compatible players based on location, skill, and availability overlap

**Key Parts**:
- `CourtRegistry` — Known tennis courts with metadata (surface, lights, public/private)
- `MatchFinder` — Core algorithm matching players by compatibility score
- `ProximityIndex` — Geospatial indexing for efficient nearby searches

**Patterns**: Read-optimized projections; eventual consistency acceptable for discovery

### Connection Service

**Purpose**: Facilitates communication and scheduling between matched players

**Key Parts**:
- `ConversationManager` — Threaded messaging between player pairs
- `MatchScheduler` — Proposed times, confirmations, reminders
- `ReliabilityTracker` — Did they show up? Tracks no-shows and cancellations

**Patterns**: Optimistic UI updates with background sync for responsive feel

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | React Native | Single codebase for iOS/Android; large talent pool |
| Backend | Node.js + Express | Fast iteration; JavaScript across stack reduces context switching |
| Data | PostgreSQL + PostGIS | Mature, reliable; PostGIS for geospatial queries on court locations |
| Real-time | Socket.io | Simple WebSocket abstraction for messaging |
| Auth | Firebase Auth | Proven mobile auth with social login; reduces security surface |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Self-reported skill levels | Lower friction than verified ratings; players know their level | Risk of skill misrepresentation; mitigate with post-match feedback |
| Court-centric discovery | Players think in terms of "where to play" not "who is nearby" | Requires maintaining court database; start with user-submitted courts |
| Mutual opt-in messaging | Reduces spam and unwanted contact | Slower connection flow; worth it for trust |
| No algorithmic feed | Show all nearby matches transparently | May feel overwhelming; paginate and filter instead of rank |

---

## Patterns

### Availability Overlap Detection

**When to use**: When showing potential matches or suggesting times

**How it works**: Compare recurring availability patterns (e.g., "weekday evenings") with one-time blocks. Find intersection windows of minimum 90 minutes (time for a match).

**Example**: Player A available Tuesday/Thursday 6-9pm. Player B available Tuesday 5-8pm. System shows Tuesday 6-8pm as potential match window.

### Progressive Profile Enrichment

**When to use**: Onboarding and ongoing profile improvement

**How it works**: Start with minimal required fields (name, skill estimate, one availability window). Prompt for additional details contextually—ask about preferred court surface after first match, not during signup.

**Example**: After confirming a match at a clay court, prompt: "How do you feel about clay courts?" to enrich preferences naturally.

### Reliability Scoring

**When to use**: Displaying player trustworthiness; sorting match results

**How it works**: Track confirmed matches, cancellations (with timing), and no-shows. Recent behavior weighted more heavily. Score decays toward neutral over time if inactive.

**Example**: Player with 8 confirmed matches, 1 cancellation (24h+ notice), 0 no-shows shows as "Reliable" badge.

---

## Execution Flow

```
[Onboarding]
  Sign Up ──→ Basic Profile ──→ Set Availability
                                      │
[Discovery]                           ▼
  Open App ──→ See Nearby Players ──→ View Profile
                                           │
[Connection]                               ▼
  Request Match ──→ Mutual Accept ──→ Message/Schedule
                                              │
[Post-Match]                                  ▼
  Confirm Played ──→ Rate Experience ──→ Update Reliability
```

Onboarding and Discovery can happen in parallel once basic profile exists. Connection requires mutual consent before messaging unlocks. Post-match feedback is optional but incentivized (unlock features, improve match quality).

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview