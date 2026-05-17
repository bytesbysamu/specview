# Unified Landing + App Page

## 1. Key Themes

Progressive disclosure as architecture. The page is not three things smashed together — it is one experience that reveals depth based on who you are and what you do. Anonymous visitor sees the pitch. Curious visitor pastes text and gets a live demo. Logged-in user sees their projects. The page upgrades itself based on engagement and auth state.

The playground IS the onboarding funnel. There is no try it free button that takes you somewhere else. The demo is right there. You paste, you see results, you are hooked. The conversion event is not a click — it is the moment they see their own text transformed.

Zero-navigation product design. Killing routes is a philosophical stance: the product is simple enough that it does not need a sitemap. One URL, one mental model. This is anti-SaaS in the best way — closer to a tool than a platform.

The braindump as seed content. The first braindump is not throwaway — it becomes the users first real project. The playground output persists. There is no start over moment after signup. Continuity from anonymous to authenticated.

Collapsing the marketing/product boundary. The landing page does not describe the product — it IS the product. Every pixel is both marketing and functionality. This kills the handoff problem where landing pages overpromise and apps underdeliver.

## 2. Hidden Connections

The playground solves the cold-start problem twice. For the visitor: they see real output before committing. For the product: you get their first braindump before they even sign up, so their account is not empty on day one. The demo IS the onboarding.

Auth state becomes a UI variable, not a routing decision. Instead of redirecting / to /app after login, you just conditionally render more sections. This means the login moment is seamless — the page grows, it does not teleport you.

One route = one shareable URL. If someone shares / and the recipient lands on it, they get the full experience. No broken links to /app that redirect to /login. The viral loop is cleaner because the entry point is always the same.

The braindump format connects the pitch to the product. The landing page copy can literally be a braindump that was processed by the tool.

## 3. Open Questions

How does the page handle the transition from anonymous playground to authenticated app — does the playground output persist through signup?
- Option A: Store playground state in localStorage, rehydrate after auth redirect
- Option B: Create a temporary session/token server-side, associate playground output with it, merge into user account on signup
- Option C: Use a modal/inline signup that does not navigate away, so state is never lost
- Recommended: Option C — inline signup without navigation.

What is the scroll architecture — is this a long single-scroll page, or sections that swap/animate in place?
- Option A: Long scroll — hero/pitch at top, playground in middle, project list below
- Option B: Sticky sections that transform — the hero collapses into a header, playground expands to fill the viewport
- Option C: Tab-like zones within the same route, no actual scrolling between major sections
- Recommended: Option B — sticky sections that transform.

For returning logged-in users, do they still see the landing/pitch section or does it collapse?
- Option A: Always show the pitch
- Option B: Collapse it to a minimal header/logo bar for authenticated users
- Option C: Let users toggle it
- Recommended: Option B — collapse for authenticated users.

What happens if the playground demo generates something really good and the user is not logged in — what is the save/capture moment?
- Option A: Prompt signup immediately when output is generated
- Option B: Let them copy/download the output freely, prompt signup for persistence
- Option C: Auto-save to a shareable URL, require signup for editing
- Recommended: Option A — prompt signup at the moment of peak value.

## 4. Ideas to Explore

Build the page as a state machine with three states: visitor, engaged, authenticated. Each state renders a superset of the previous one. The transitions are: paste text to engaged, sign in to authenticated. No routing logic, just state.

Make the landing page copy itself a live braindump example. The hero section shows raw text on the left and the processed output on the right — and it is the actual tool running, not a screenshot.

Implement ghost projects — anonymous playground outputs that persist in the browser. If someone uses the playground three times before signing up, they see all three outputs. On signup, all ghost projects migrate to their account.

Add a subtle page evolution animation when someone logs in. The pitch section slides up and compresses, the playground transforms into the input area, and the project list fades in below. The page literally morphs from marketing to product.

Create app-v2 as a new template that imports components from both the existing landing page and app templates. Do not rewrite — compose.

Use URL hash fragments for deep-linking within the single page. /#playground scrolls/focuses the playground. /#projects jumps to the project list. One route, but still addressable sections.

A/B test the unified page against the current separate routes. Measure: time-to-first-braindump, signup conversion rate, bounce rate.

Consider a spectator mode where the playground shows a rotating feed of anonymized public braindumps being processed in real time. Visitors see the tool working for other people before they try it themselves. Social proof baked into the product, not bolted on as testimonials.