# 🎯 Epic: babyname

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

The App Store search term "baby names" is evergreen, high-volume, and globally relevant. Every top result is a static database with filters — alphabetical lists that force parents to scroll without any understanding of what they actually want. No competitor uses AI to personalize results. This isn't a crowded market with strong incumbents; it's a stale category waiting for a modern entry. The first AI-powered baby name app defines the category rather than competing in it.

Parents search for 6-9 months before choosing a name, often across 3-5 apps simultaneously. That duration represents subscription lifetime value that no current app captures well, because none of them solve the core problem: translating personal preferences into relevant name suggestions. A preference-driven generation model replaces the browse-and-hope pattern with a "tell me what you want, here's what fits" experience — the same shift that transformed restaurant discovery (Yelp lists → personalized recommendations).

The target customer is any English-speaking expectant parent with an iPhone. Monetization is freemium: free generations to demonstrate value, then a hard paywall for continued use. Apple Small Business Program keeps the platform cut at 15%. The tech stack reuses the existing Ionic + Capacitor boilerplate, and Claude API handles all generation — no ML pipeline, no training data, no cold start problem. Ship in under a week, validate with 200 users.

**Value Proposition**: AI-generated baby names personalized to what parents actually care about — style, culture, meaning — delivered as explained recommendations, not database lookups.

---

## Scope

### What This Epic Covers

- **Preference capture flow** – Structured input for style, origin, meaning, gender, optional letter/sibling constraints
- **AI name generation** – Claude API generates name cards with rationale tied to stated preferences
- **Name card display** – Each result shows name, pronunciation, origin, meaning, popularity context, and why it fits
- **Favorites and sharing** – Save names to a shortlist, share the list with a partner via link
- **Freemium paywall** – Limited free generations, then subscription gate

### What This Epic Does NOT Cover

- ❌ Partner voting/swipe mechanics — Post-MVP collaborative feature; basic sharing covers the need initially
- ❌ Name legality by jurisdiction — Requires per-country legal databases; no demand signal yet
- ❌ Family tree integration — Different product category
- ❌ Name trend forecasting — Requires historical data pipeline; consider post-validation
- ❌ Multilingual UI — English-first per distribution strategy
- ❌ Cultural deep-dive content (articles, history) — Content-heavy engagement feature for post-PMF
- ❌ Preference learning across sessions — Valuable but not required for MVP validation

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Preference Input Flow** | None | — | 2 days | High |
| 2 | **AI Name Generation Engine** | 1 | — | 2 days | High |
| 3 | **Name Card UI + Results Screen** | 2 | 4 | 1 day | High |
| 4 | **Favorites + Partner Sharing** | 1 | 3 | 1 day | High |
| 5 | **Paywall + Subscription** | 3 | — | 1 day | High |

### Task 1: Preference Input Flow

Build the onboarding screen where parents specify what matters to them: name style (classic, modern, unique, nature-inspired, etc.), cultural origin, preferred meaning themes, gender, and optional constraints like starting letter or sibling names to harmonize with. This is the core differentiator — no competitor captures preferences before showing results. The flow should feel like a conversation, not a form. See [Solution Architecture](./architecture.md) for input design.

### Task 2: AI Name Generation Engine

Implement the Claude API integration that takes structured preferences and generates 5-10 name cards per request. Each card includes the name, pronunciation guide, origin, meaning, popularity context (common, rising, rare), and a one-sentence rationale explaining why this name fits the stated preferences. The prompt engineering here is the product — the quality of rationale and cultural accuracy determines whether users trust the results. See [Solution Architecture](./architecture.md) for prompt design and API structure.

### Task 3: Name Card UI + Results Screen

Display generated names as swipeable or scrollable cards with all metadata visible: name, pronunciation, origin, meaning, popularity indicator, and the personalized "why it fits" explanation. Each card needs a save-to-favorites action. The UI should make the rationale prominent — this is what separates the product from every static database. See [Solution Architecture](./architecture.md) for component structure.

### Task 4: Favorites + Partner Sharing

Implement a favorites list where saved names persist locally. Add a share action that generates a read-only link to the shortlist, so partners can review without installing the app. This addresses the partner alignment problem identified in the [Analysis](./analysis.md) — parents currently share names via screenshots and texts. Basic sharing is sufficient for MVP; collaborative editing is out of scope.

### Task 5: Paywall + Subscription

Gate generation behind a usage limit (e.g., 3-5 free generation rounds) with a hard paywall for continued use. Integrate StoreKit for iOS subscription via Apple Small Business Program. Pricing to be validated — initial range is $3.99-$4.99/month or equivalent weekly pricing. The free tier must be generous enough to demonstrate value but limited enough to convert. See [Solution Architecture](./architecture.md) for paywall integration.

---

## Success Criteria

This epic is complete when:

- ✅ A parent can input preferences and receive AI-generated name cards with personalized rationale in under 10 seconds
- ✅ Each name card displays pronunciation, origin, meaning, popularity context, and a "why it fits" explanation
- ✅ Users can save favorites and share a shortlist link with a partner
- ✅ Free-to-paid paywall activates after the defined generation limit
- ✅ App is submitted to App Store with ASO-optimized metadata (keywords: baby names, name generator, unique baby names)
- ✅ 200 users reached for initial validation signal

---

## Non-Goals

- ❌ Replacing baby name databases — The app generates names, it doesn't need to contain every name ever recorded
- ❌ Building a social platform — Partner sharing is a utility feature, not a community
- ❌ Achieving cultural perfection at launch — AI generation covers breadth; accuracy improves with user feedback post-launch
- ❌ Complex onboarding — Preference capture should take under 60 seconds, not be an exhaustive questionnaire
- ❌ Backend infrastructure — Direct API calls from the app where feasible; minimize server-side complexity for MVP

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview