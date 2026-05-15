# Unified Landing + App Page

## 1. Key Themes

Progressive disclosure as architecture. The page isn't three things smashed together — it's one experience that reveals depth based on who you are and what you do. Anonymous visitor sees the pitch. Curious visitor pastes text and gets a live demo. Logged-in user sees their projects. The page upgrades itself based on engagement and auth state.

The playground IS the onboarding funnel. There's no "try it free" button that takes you somewhere else. The demo is right there. You paste, you see results, you're hooked. The conversion event isn't a click — it's the moment they see their own text transformed.

Zero-navigation product design. Killing routes is a philosophical stance: the product is simple enough that it doesn't need a sitemap. One URL, one mental model. This is anti-SaaS in the best way — closer to a tool than a platform.

The braindump as seed content. The first braindump isn't throwaway — it becomes the user's first real project. The playground output persists. There's no "start over" moment after signup. Continuity from anonymous to authenticated.

Collapsing the marketing/product boundary. The landing page doesn't describe the product — it IS the product. Every pixel is both marketing and functionality. This kills the handoff problem where landing pages overpromise and apps underdeliver.

## 2. Hidden Connections

The playground solves the cold-start problem twice. For the visitor: they see real output before committing. For the product: you get their first braindump before they even sign up, so their account isn't empty on day one. The demo IS the onboarding.

Auth state becomes a UI variable, not a routing decision. Instead of redirecting / → /app after login, you just conditionally render more sections. This means the login moment is seamless — the page grows, it doesn't teleport you. This is the same pattern Notion uses but taken further.

One route = one shareable URL. If someone shares / and the recipient lands on it, they get the full experience. No broken links to /app that redirect to /login. The viral loop is cleaner because the entry point is always the same.

The braindump format connects the pitch to the product. The landing page copy can literally be a braindump that was processed by the tool. "Here's what this page looked like as raw text → here's what the tool produced." The medium is the message.

## 3. Open Questions

How does the page handle the transition from anonymous playground to authenticated app — does the playground output persist through signup?
- Option A: Store playground state in localStorage, rehydrate after auth redirect
- Option B: Create a temporary session/token server-side, associate playground output with it, merge into user account on signup
- Option C: Use a modal/inline signup that doesn't navigate away, so state is never lost
- Recommended: Option C — inline signup without navigation. It preserves the "one page" philosophy and avoids the complexity of state persistence across redirects. The user never leaves, so nothing is lost.

What's the scroll architecture — is this a long single-scroll page, or sections that swap/animate in place?
- Option A: Long scroll — hero/pitch at top, playground in middle, project list below
- Option B: Sticky sections that transform — the hero collapses into a header, playground expands to fill the viewport
- Option C: Tab-like zones within the same route, no actual scrolling between major sections
- Recommended: Option B — sticky sections that transform. Long scroll buries the app below the fold for returning users. Tabs feel like hidden routes. Transforming sections let the page feel alive and adapt to intent.

For returning logged-in users, do they still see the landing/pitch section or does it collapse?
- Option A: Always show the pitch — it reinforces the brand on every visit
- Option B: Collapse it to a minimal header/logo bar for authenticated users
- Option C: Let users toggle it — collapsed by default, expandable
- Recommended: Option B — collapse for authenticated users. Returning users don't need to be sold. Respecting their time by defaulting to the tool builds trust and makes the product feel fast.

How do you handle SEO and social previews when the page is dynamically assembled?
- Option A: Server-render the landing page content statically, hydrate the playground/app client-side
- Option B: Use meta tags optimized for the landing page version, ignore the app state for crawlers
- Option C: Implement dynamic OG tags based on query params (e.g., /?ref=share gets different previews)
- Recommended: Option A — server-render the pitch, client-hydrate the rest. Crawlers get the landing page. Users get the full experience. Best of both worlds without complexity.

What happens if the playground demo generates something really good and the user isn't logged in — what's the save/capture moment?
- Option A: Prompt signup immediately when output is generated — "Sign up to save this"
- Option B: Let them copy/download the output freely, prompt signup for persistence and history
- Option C: Auto-save to a shareable URL (like a gist), require signup for editing/continuing
- Recommended: Option A — prompt signup at the moment of peak value. They just saw their braindump transformed. That's the highest-intent moment. Don't let it cool off.

## 4. Ideas to Explore

Build the page as a state machine with three states: visitor, engaged, authenticated. Each state renders a superset of the previous one. The transitions are: paste text → engaged, sign in → authenticated. No routing logic, just state.

Make the landing page copy itself a live braindump example. The hero section shows raw text on the left and the processed output on the right — and it's the actual tool running, not a screenshot. Visitors see the product working before they even scroll.

Implement "ghost projects" — anonymous playground outputs that persist in the browser. If someone uses the playground three times before signing up, they see all three outputs. On signup, all ghost projects migrate to their account. This rewards exploration.

Add a subtle "page evolution" animation when someone logs in. The pitch section slides up and compresses, the playground transforms into the input area, and the project list fades in below. The page literally morphs from marketing to product. Make the transition feel intentional, not jarring.

Create app-v2 as a new template that imports components from both the existing landing page and app templates. Don't rewrite — compose. The landing hero component, the playground component, and the project list component should all be importable. The unified page is just a new layout that arranges them.

Use URL hash fragments for deep-linking within the single page. /#playground scrolls/focuses the playground. /#projects jumps to the project list. One route, but still addressable sections. This gives you shareability without route fragmentation.

A/B test the unified page against the current separate routes. Measure: time-to-first-braindump, signup conversion rate, bounce rate. The hypothesis is that removing friction (no navigation to playground) increases activation. Prove it.

Consider a "spectator mode" where the playground shows a rotating feed of anonymized public braindumps being processed in real time. Visitors see the tool working for other people before they try it themselves. Social proof baked into the product, not bolted on as testimonials.
