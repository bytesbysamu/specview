**1. Key Themes**

- **Live event discovery as a missing layer** — concerts, theater, comedy, and other ticketed events are a distinct category from restaurants/attractions and deserve first-class treatment, not a buried sub-filter.
- **Context of capture matters** — "I was driving" signals the input was voice-dictated mid-task. The product needs to handle fragmented, low-effort input gracefully.
- **Intent vs. inventory** — the user is expressing what they want included; the system must decide whether that means a data-source expansion, a UI surface, or a recommendation weighting change.
- **Hands-free / eyes-free use case** — driving implies the brainstorm tool itself may need to function in voice-first contexts.
- **Implicit personalization** — "please include" hints the user has tastes the system isn't yet capturing (live performance over static venues).

**2. Hidden Connections**

- The driving context and the request for events are linked: people often plan weekend outings while commuting. Voice-first event discovery is a real, underserved moment.
- Events differ from places in a structural way most apps ignore — they have a *time dimension*. Adding events forces the product to become time-aware, which then unlocks reminders, conflict detection, and itinerary building.
- "Please include" framing suggests the user sees this tool as configurable/curatable. That's a different mental model than passive recommendation — it implies a settings or preferences surface.
- Concerts and theater are social goods — almost never solo. Adding them implicitly pulls group coordination into scope.

**3. Open Questions**

- **What event sources should we integrate?**
  - Ticketmaster + Live Nation API
  - Bandsintown + Songkick (artist-followed model)
  - Eventbrite + local venue scraping for indie coverage
  - **Recommended:** Bandsintown + Songkick — taste-graph data beats raw inventory for relevance, and indie coverage matters more than catalog completeness.

- **How do events surface relative to places?**
  - Separate "Events" tab
  - Unified feed with event cards interleaved
  - Time-filtered: events appear when user picks a date
  - **Recommended:** Time-filtered — events without a date context are noise; gating on date intent makes them feel earned.

- **How do we handle the voice/driving input modality?**
  - Auto-detect driving via motion API and switch to voice-only UI
  - Always-available push-to-talk button
  - Treat voice as just another input, no special mode
  - **Recommended:** Push-to-talk button — auto-detect is creepy and unreliable; explicit invocation respects the user.

- **Should we charge for ticket purchase or stay discovery-only?**
  - Pure discovery, deep-link to ticketing partner
  - Affiliate revenue on tickets
  - In-app checkout
  - **Recommended:** Affiliate deep-links — captures revenue without owning the support nightmare of refunds and seat maps.

- **How do we handle taste — does the user input genres, or do we infer?**
  - Explicit genre/artist onboarding
  - Infer from Spotify/Apple Music connection
  - Learn from in-app behavior over time
  - **Recommended:** Spotify/Apple Music connection — zero friction, immediate relevance, and the data is already curated.

- **What does "include" mean here — system-wide default or this-session preference?**
  - Persistent preference saved to profile
  - Session-only adjustment
  - Ask the user inline to clarify
  - **Recommended:** Persistent preference — the phrasing "please include" reads as a standing rule, not a one-off.

**4. Ideas to Explore**

- Build a **"weekend ahead" voice briefing** — Sunday evening, the app reads out the top 3 events matching taste + calendar availability for the coming week.
- Add a **CarPlay/Android Auto integration** specifically for event discovery while commuting — "What's happening Friday?" as a single voice command.
- Treat **artist follows as the primary input** instead of categories — let users say "tell me when Phoebe Bridgers tours within 100 miles" and skip filtering entirely.
- Layer in **friend-of-friend signal**: "3 people you know are going to this" makes events convert at 5x the rate of cold listings.
- Build a **conflict-aware itinerary planner**: if a user adds a Saturday concert, the dinner recommendations auto-shift to nearby pre-show options with appropriate timing.
- Experiment with **"surprise me" mode** — single-tap voice command that books a full Saturday night (dinner + show + nightcap) within a budget. Pure agentic execution.
- Test whether **theater and concerts should be split** — theatergoers and concertgoers behave differently (planning horizon, group size, repeat rate). Treating them as one bucket may dilute relevance.