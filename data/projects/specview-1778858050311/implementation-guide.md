# Implementation Guide: SpecView — Launch-Ready Product Definition

## Overview
This epic delivers the messaging and explanation layer needed to launch SpecView on Sunday 2026-05-18. It sequences five tasks: first lock down product positioning and a one-liner (Task 1), then validate SpecView's own dogfood spec set as a credible demo artifact (Task 2), build the static first-visit explanation surface that converts strangers into users (Task 3), walk through end-to-end new-user onboarding to eliminate dead ends (Task 4), and finally prepare channel-specific launch distribution copy (Task 5). No new services, endpoints, or infrastructure are introduced — this is composition and content work on top of the existing Flask API, Angular SPA, and static landing page.

## Shared Pre-flight
- Confirm the Flask API is running on port 3101 and the Angular SPA is serving on port 4201
- Confirm the static landing page in `landing/` is served via nginx:alpine and accessible at the root URL
- Identify the dogfood project directory under `data/projects/` that contains SpecView's own spec set (analysis, epic, architecture, timeline)
- Verify the `quality/` module is importable and `lint_task_guide()` runs without errors on an existing project
- Ensure at least two user accounts exist (primary and test) with valid credentials for onboarding testing
- Confirm the Docker Compose to Coolify deployment pipeline is functional and a content-only redeploy completes in under five minutes
- Have access to the target launch channels (Twitter/X account, Product Hunt draft, direct-share URL) so distribution copy can be validated against real character limits and field constraints

---

## Task 1: Define Product Positioning and One-Liner  [Effort: 0.5 days]

### What
Establish the single-sentence product description, a two-sentence pitch, and the positioning angle that all downstream tasks depend on. This is the launch blocker — without a crisp one-liner, the landing page, showcase, and distribution copy have no foundation.

### Files
- **Create**: `landing/copy/positioning.md` — canonical one-liner, two-sentence pitch, target audience definition, and positioning angle (productivity tool for solo devs who use AI tools)
- **Modify**: `landing/index.html` — embed the finalized one-liner into the hero section heading and the two-sentence pitch into the subheading area

### Steps
1. Review the analysis document's problem statement and the epic's business value section to extract the core value proposition: brain dumps become linked spec sets, documentation becomes a byproduct of thinking.
2. Draft three candidate one-liners that each take a different angle — productivity tool, AI writing tool, and structured-context layer — and select the one that best fits the target audience of solo devs and indie hackers already using AI tools.
3. Write the two-sentence pitch that expands the one-liner with the specific transformation (paste brain dump, get analysis-epic-architecture-timeline) and the credibility hook (SpecView documented itself).
4. Define the target audience explicitly: solo founders and indie hackers who use AI tools and understand that structured context improves AI output.
5. Record all positioning decisions in `landing/copy/positioning.md` as the canonical source of truth for Tasks 3 and 5.
6. Update the hero section of `landing/index.html` with the finalized one-liner and pitch so the landing page reflects the positioning immediately.

### Verify
- `landing/copy/positioning.md` exists and contains a one-liner under 15 words, a two-sentence pitch, and an explicit target audience statement
- The one-liner appears in the hero heading of `landing/index.html` when viewed in a browser
- Reading the one-liner cold, without any other context, communicates what SpecView does within five seconds

---

## Task 2: Validate Dogfood Spec Set (SpecView Documenting Itself)  [Effort: 1 day]

### What
Run SpecView's own spec set through the coherence linter and fix all violations so the dogfood project can serve as the product demo. If the linter cannot pass SpecView's own output, either the specs or the linter need fixing — both outcomes improve the product before launch.

### Files
- **Modify**: `data/projects/specview-1778858050311/analysis.md` — fix any cross-reference issues, remove placeholder content, ensure the document reads as a coherent narrative
- **Modify**: `data/projects/specview-1778858050311/epic.md` — ensure all task references resolve, success criteria are concrete, and no content-routing violations exist (no status words that belong in timeline, no code blocks that belong in implementation guides)
- **Modify**: `data/projects/specview-1778858050311/architecture.md` — verify all cross-document links resolve, design decisions are justified, and integration points reference real components
- **Modify**: `data/projects/specview-1778858050311/timeline.md` — confirm status entries are current, dates are accurate for the Sunday launch, and the document passes linting
- **Modify**: `quality/` module linting functions — if the linter rejects valid spec patterns found in the dogfood set, fix the linter rules rather than working around them in the specs

### Steps
1. Run the existing linter from the `quality/` module against the full dogfood project at `data/projects/specview-1778858050311/` and capture all violations.
2. Categorize violations into spec-content issues (fixable by editing the spec files) and linter-rule issues (false positives or overly strict rules that reject valid patterns).
3. Fix spec-content issues first: resolve broken cross-references between analysis, epic, architecture, and timeline documents; remove any placeholder text; ensure each document stays within its content-routing lane.
4. Fix linter-rule issues second: adjust rules in the `quality/` module that produce false positives on well-formed spec content, ensuring the fixes are general improvements and not dogfood-specific special cases.
5. Re-run the linter and confirm zero critical violations across all four spec documents.
6. Read through the full spec set end-to-end as a narrative — analysis identifies problems, epic scopes the response, architecture designs the solution, timeline tracks delivery — and verify the story is coherent to a stranger.

### Verify
- The coherence linter produces zero critical violations when run against `data/projects/specview-1778858050311/`
- All cross-reference links between the four spec documents resolve to real sections
- The spec set reads coherently when navigated in order: analysis, then epic, then architecture, then timeline
- No content-routing violations exist — status words appear only in timeline, code references appear only where appropriate

---

## Task 3: Build First-Visit Explanation Surface  [Effort: 1 day]

### What
Transform the existing static landing page into a 30-second explanation path that takes a stranger from "what is this?" to "let me try it." The surface includes the positioning one-liner, a visual walkthrough of the brain-dump-to-spec transformation, a read-only showcase of SpecView's own specs as proof of quality, and a single call-to-action routing to signup.

### Files
- **Modify**: `landing/index.html` — add the visual walkthrough section showing the brain-dump-to-spec-set transformation, embed the pre-rendered dogfood showcase content, add the call-to-action linking to the Angular SPA signup route, and add OG meta tags for link preview cards
- **Create**: `landing/assets/showcase/` — directory containing pre-rendered static versions of SpecView's own spec set (analysis, epic, architecture, timeline) exported as HTML fragments for embedding in the landing page
- **Modify**: `landing/` nginx or Docker configuration if static asset paths need updating to serve the showcase directory

### Steps
1. Export SpecView's validated dogfood spec set from Task 2 as static HTML fragments suitable for embedding, placing them in `landing/assets/showcase/`.
2. Design the landing page flow as three sections: hero with the one-liner and pitch from Task 1, a walkthrough section that visually shows the transformation from a messy brain dump input to a structured four-document spec set output, and a showcase section that embeds the actual dogfood specs as proof.
3. Add the walkthrough section to `landing/index.html` below the hero, using inline styles consistent with the existing page design — no CSS framework, no JavaScript, no build toolchain.
4. Add the showcase section that presents the four dogfood spec documents as navigable tabs or expandable panels using minimal inline CSS and, if needed for tab switching, a small inline script.
5. Add the call-to-action button that links directly to the Angular SPA's signup route, positioned after the showcase section so visitors see proof before being asked to commit.
6. Add OG meta tags to the landing page head: `og:title` with the one-liner, `og:description` with the two-sentence pitch, and `og:image` pointing to a representative screenshot or logo asset.
7. Test the full page load in a browser with JavaScript disabled to confirm the explanation surface works without any dynamic dependencies — the showcase content is static, the walkthrough is static, only the CTA link requires navigation.

### Verify
- The landing page loads in under two seconds on a cold visit with no API calls visible in the network tab
- A stranger reading top to bottom encounters the one-liner, the walkthrough, the showcase specs, and the signup CTA in that order
- Sharing the landing page URL on Twitter/X or in a messaging app shows a correct link preview card with the product title and description from the OG meta tags
- The signup CTA links to the correct Angular SPA route and the link works when clicked

---

## Task 4: End-to-End New-User Onboarding Walkthrough  [Effort: 0.5 days]

### What
Walk through the complete second-account flow — signup, first project creation, first brain dump paste, first spec generation — and eliminate every dead end, confusing empty state, or UX friction point. The Angular SPA's zero-project state must act as the onboarding path without a separate tutorial system.

### Files
- **Modify**: `web-ng/src/app/` components responsible for the dashboard or project list view — update the empty-state design to present a focused "name your project and paste your brain dump" prompt instead of an empty list with a buried "Create Project" button
- **Modify**: `web-ng/src/app/` components responsible for project creation — ensure the flow from project naming to brain dump input to spec generation is linear with no branching choices or dead ends for a first-time user
- **Modify**: `web-ng/src/app/` components responsible for displaying generated specs — confirm that after generation completes, the user lands on a view showing all four spec documents with clear navigation between them

### Steps
1. Log out of all sessions and create a fresh account using the test-account signup flow to experience the exact path a new user will follow from the landing page CTA.
2. After signup and first login, observe the dashboard empty state — document whether the current UI presents a clear next action or drops the user into a blank screen with no guidance.
3. Modify the dashboard empty-state component to replace the default empty-project-list view with a focused onboarding prompt that says what to do next: name a project and paste a brain dump.
4. Walk through the project creation flow: name the project, paste a sample brain dump, trigger spec generation, and wait for results. Document every point where the user might be confused, stalled, or unsure what to do next.
5. Fix each friction point found in step 4 — unclear button labels, missing loading indicators during generation, confusing navigation after specs are generated, or any error states that show raw technical messages instead of helpful guidance.
6. After generation completes, verify that the user lands on a spec view showing all four documents (analysis, epic, architecture, timeline) with working navigation between them and no broken or empty sections.
7. Repeat the full flow one more time from signup to generated specs to confirm all fixes hold and the path is smooth end-to-end.

### Verify
- A fresh account can complete signup, project creation, brain dump paste, and spec generation without encountering any error screens, dead ends, or ambiguous empty states
- The dashboard empty state for a user with zero projects presents a clear, focused call to action rather than an empty list
- Spec generation completes and displays all four document types with working inter-document navigation
- The entire flow from signup to viewing generated specs takes under three minutes, excluding AI generation wait time

---

## Task 5: Write Launch Distribution Copy and Select Channels  [Effort: 0.5 days]

### What
Prepare channel-specific launch messages for Twitter/X, Product Hunt, and direct URL sharing, each tailored to the channel's format constraints. This is static content work — no scheduling tools, no automated posting. Sam posts manually on launch day Sunday 2026-05-18.

### Files
- **Create**: `landing/copy/launch-distribution.md` — all launch copy variants organized by channel: Twitter/X thread (280-character limit per tweet), Product Hunt listing (tagline, description, first comment), and direct-share message for DMs and community posts
- **Modify**: `landing/index.html` — verify OG meta tags from Task 3 render correct link previews for each distribution channel, adjust if any channel's preview parser handles tags differently

### Steps
1. Write the Twitter/X launch thread: an opening tweet that contains the one-liner and the URL, followed by two to three reply tweets that expand the pitch — what the product does, the dogfood proof point (SpecView documented itself), and a call to try it.
2. Write the Product Hunt listing: a tagline under 60 characters, a description under 260 characters that explains the brain-dump-to-spec-set transformation, and a first-comment maker post that tells the origin story and invites feedback.
3. Write the direct-share message: a two to three sentence version suitable for pasting into Slack channels, Discord servers, Indie Hackers forums, and DMs — longer than a tweet, shorter than a blog post.
4. Validate every copy variant against its channel's character and formatting constraints — tweet length limits, Product Hunt field limits, and OG meta tag rendering for link previews.
5. Test the landing page URL in Twitter's card validator and any available OG preview tool to confirm the link preview card shows the correct title, description, and image across sharing contexts.
6. Compile all finalized copy into `landing/copy/launch-distribution.md` organized by channel with clear section headers so Sam can copy-paste directly on launch day.

### Verify
- `landing/copy/launch-distribution.md` contains complete, copy-paste-ready text for all three channels: Twitter/X thread, Product Hunt listing, and direct-share message
- The Twitter/X opening tweet is under 280 characters including the URL
- The Product Hunt tagline is under 60 characters and the description is under 260 characters
- Sharing the landing page URL generates a correct link preview card with the product one-liner and description visible