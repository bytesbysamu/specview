## Session 1 — Origin Story

Specview started from Springular boilerplate's Docusaurus docs — the docs were more useful than the code. Organized pages (analysis, epic, architecture, implementation guides) made projects understandable. Evolution: Constellation (Jan 2026, 18 docs, over-engineered) → Spec Doc (Mar 2026, Monaco editor, brain dump → AI-generated docs) → Specview (May 2026, newspaper UI making specs readable/browsable/shareable). Core: paste messy thinking, get structured documentation in 45 seconds. "The best documentation you ever read was for a boilerplate. Specview generates that quality for every project, from a brain dump, in 45 seconds."

## Session 2 — Analysis

Key Themes:

    Documentation was always the product, not code — Specview bets docs are the highest-leverage artifact but nobody writes them because it's painful
    Core transaction: brain dump → structured output. Selling people their own ideas in usable form
    Reader experience is the moat — generation is commodity; the newspaper UI making specs shareable turns a tool into a destination
    Self-referential PMF: using Specview to build/describe Specview is the strongest demo
    Evolution shows subtraction — each iteration stripped complexity, kept methodology

Hidden Connections:

    Boilerplates and newspapers both organize overwhelming material into scannable structure
    45-second promise is really a trust claim — AI can structure your thinking without losing meaning; speed just lowers risk to try
    Sam's second account reveals viral loop — product sells through use, not explanation
    Documentation-first is actually decision-first development — specs are crystallized decisions before code

Open Questions (with recommendations):

    Buyer: Solo builders for launch (fastest decision cycle, no procurement) → expand to teams later
    Retention: Living docs (specs evolve with project) create habitual use → build "update this spec" flow post-launch
    Newspaper UI's real job: sharing/virality mechanism — specs look good enough to send, nobody shares raw markdown
    Launch story: Lead with origin ("best docs were for a boilerplate") → pivot to output (45-second claim)
    "Can't describe it" problem: Landing page should BE a Specview document — medium is the message

Ideas:

    Landing page as actual Specview-generated document — visitors experience product before signup
    CTA: "Paste Your Brain Dump" not "Sign Up" — first use IS the explanation
    Publish Constellation → Spec Doc → Specview evolution as first public collection
    "Specview-generated" badge on shared specs — every share becomes an ad
    Target boilerplate/template creators (the exact inspiring use case)
    "Sam test": before launching features, fresh-account test for self-explanatory UX
    Live 45-second timer on landing page — show real generation, don't just claim it
    Post-launch: spec diffs showing how project documentation evolves over time

## Session 3 — Sunday Launch Priorities

Core Insight: Product IS Marketing. Specview's marketing problem and product are identical. Describing it is inferior to experiencing it. Stop writing about it — show it.

Sam's Second Account Insight: Conversion moment is the first read, not signup. Launch funnel: someone sees a Specview doc → wonders what made it → clicks through → pastes their own thinking → feels it. Only Step 1 needs engineering for Sunday. Public URLs for specs aren't nice-to-have — they're the entire growth engine.

PMF Sequence:

    Weeks 1-2: Solo builder acquisition via shared spec links + badge
    Weeks 3-4: Living docs retention — "this spec changed, regenerate" is the habit loop
    Month 2+: Team expansion happens organically through shared living specs

Launch Narrative (three sentences): "The best documentation I ever read was for a $29 boilerplate. So I built a tool that generates docs like that from a brain dump — in 45 seconds. This post was outlined by the product." Origin → output → self-reference.

Live Timer: Real generation, real clock. Honesty (38s or 52s) beats fake consistency. Turns utility into experience people screen-record. Implementation: simple Date.now() delta, 30-minute build.

Spec Diffs (post-launch): Version control for project thinking — nothing exists for decisions like Git exists for code. Architectural decision now: store every generation with timestamps, never overwrite.

Sunday Punch List (priority order):

    Public shareable URLs — #1 blocker for viral loop
    Landing page as Specview document with origin hook + 45s claim + "Paste Your Brain Dump" CTA (~2hrs)
    Live timer on generation (~30min)
    "Specview-generated" badge on shared specs (~1hr)
    Launch tweet/post — write after landing page exists

Everything else (outreach, diffs, teams, living docs) is post-Sunday. Ship the viral loop, not the feature set.
