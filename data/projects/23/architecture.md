# 🏗️ Solution Architecture: prepper

## Architecture Overview

This is a **knowledge architecture**, not a software system. The deliverable is a structured research document that maps the political landscape of prepper movements across four countries, with the US and UK as primary research targets and Switzerland and Germany as comparative anchors. The architecture defines how information is organized, how research threads connect, and what analytical framework binds the findings into a coherent, referenceable whole.

The key structural insight is that prepper movements are not monolithic — they fragment along political, legal, and cultural axes that differ dramatically between countries. A flat country-by-country dump would miss the cross-cutting patterns that make comparison valuable. Instead, the architecture uses a **matrix model**: countries form one axis, and analytical dimensions (government integration, legal environment, partisan identity, media framing, cultural legitimacy) form the other. Each cell in the matrix holds a focused finding, and the synthesis layer identifies which axis drives the most divergence.

The research components are sequenced to build on each other: landscape mapping (US and UK in parallel) feeds into a legal-policy layer, which feeds into the comparative framework, which produces the synthesis. This mirrors the epic's dependency graph and ensures no comparative claim is made before both sides of the comparison are documented.

## Design Principles

| Principle | Application |
|-----------|-------------|
| Evidence-anchored claims | Every political characterization names at least one organization, public figure, legal statute, or documented event — no unsourced generalizations |
| Segment-first, not ideology-first | Map who the actors are before characterizing what they believe — avoids forcing movements into pre-existing ideological boxes |
| Legal environment as structural driver | Treat firearms law, land-use regulation, and emergency-planning policy as **causes** of cultural divergence, not just background context |
| Swiss/German as baseline, not subject | DACH-region knowledge is assumed; it provides the comparative frame, not a research target requiring equal depth |
| Consolidated output over scattered notes | One document with internal navigation, not a folder of disconnected research fragments |

## Component Design

### Political Segment Maps (US and UK)

**Purpose**: Establish the actor landscape before attempting comparison. Each map identifies 3–5 distinct political groupings within that country's prepper movement, characterized by their relationship to government, partisan alignment, and self-stated motivations.

The US map must capture the full spectrum: right-libertarian/militia-adjacent, left/mutual-aid, religious-eschatological, civic-preparedness, and apolitical-practical segments. The UK map operates under fundamentally different constraints (no armed citizenry as default, stronger government emergency-planning tradition) and likely surfaces different segment boundaries — possibly Brexit-anxiety, green-collapse, and government-skeptic clusters rather than US-style partisan splits.

### Legal and Policy Framework Layer

**Purpose**: Explain **why** prepper culture takes different shapes in different countries by documenting the regulatory environment that constrains or enables specific behaviors. This is the causal layer — without it, cultural differences appear arbitrary rather than structurally determined.

Key regulatory domains: firearms access, off-grid habitation legality, food/fuel stockpiling limits, radio communication licensing, and government civil-defense integration programs. The Swiss Zivilschutz model and German BBK (Bundesamt für Bevölkerungsschutz) serve as the high-integration benchmark against which US and UK policies are measured.

### Comparative Framework Matrix

**Purpose**: Transform parallel country research into structured cross-comparison. The matrix uses five analytical axes applied uniformly across all four countries, enabling pattern recognition that sequential country profiles would obscure.

The five axes — government integration, legal permissiveness, partisan identity, media perception, and cultural legitimacy — were chosen because they capture the political dimensions specifically (as opposed to practical-skills or gear-culture dimensions that are out of scope). Each axis produces a spectrum, not a binary, allowing nuanced positioning.

### Synthesis Layer

**Purpose**: Distill the matrix into actionable insight — what is genuinely different about Anglophone prepper politics versus DACH-region prepper culture, and what structural factors (legal, historical, institutional) drive those differences. This is the layer that makes the research referenceable rather than merely comprehensive.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Research format | Single consolidated markdown document | Referenceable, searchable, version-controllable; avoids scattered-notes failure mode |
| Analytical framework | 5-axis comparative matrix | Forces uniform coverage across countries; reveals gaps; enables cross-cutting pattern identification |
| Evidence standard | Named examples per claim | Prevents drift into unsourced generalization; makes claims verifiable and updatable |
| Source priority | Government publications, named organizations, legislative texts, established journalism | Avoids forum-culture anecdotes that skew toward extreme segments |
| Comparison baseline | Swiss/German models (assumed knowledge) | Leverages existing understanding; avoids redundant research on familiar territory |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Matrix model over sequential country profiles | Cross-cutting patterns are the research value; sequential profiles bury comparison in reader effort | Harder to read as a narrative; requires the reader to hold multiple countries in mind simultaneously |
| Five axes, not three or seven | Captures political dimensions comprehensively without diluting focus into cultural or practical axes that are out of scope | Excludes interesting non-political dimensions (community structure, skills culture, economic class) |
| Post-2000 temporal boundary | Modern prepper politics are shaped by 9/11, 2008 financial crisis, and COVID — earlier history is genealogy, not current landscape | Misses Cold War origins that explain some current attitudes; acceptable because the gap is acknowledged, not hidden |
| UK treated as distinct research track, not US variant | UK legal environment (near-total firearms restriction, Cabinet Office emergency frameworks) creates fundamentally different movement dynamics | Requires independent research effort rather than adapting US findings; justified because the differences are structural, not superficial |
| Exclude sovereign-citizen and QAnon-adjacent movements from primary focus | These movements have prepper-adjacent behaviors but are defined by conspiracy epistemology rather than preparedness motivation | Risks missing overlap zones where political extremism and prepper practice genuinely merge; mitigated by noting them as context without deep-diving |
| Single document output, not multi-file knowledge base | Prevents the scattered-notes failure mode; forces prioritization; stays referenceable as one artifact | Document may grow long; mitigated by strong internal heading structure and the matrix format enabling selective reading |

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking