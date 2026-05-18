# Implementation Guide: Side Income Strategy

## Overview
This epic transforms Sam's fragmented five-project portfolio into a single revenue-focused product shipped through a marketplace with built-in discovery. The five tasks execute strictly sequentially: first, free attention by triaging every existing project (Task 1); then lock a revenue target and distribution channel (Task 2); then validate and select one product for that channel (Task 3); then build and submit the MVP to the Chrome Web Store (Task 4); and finally optimize the listing until the first organic paid customer arrives (Task 5). Each task produces a written artifact that constrains the next, ensuring no backtracking or scope creep.

## Shared Pre-flight
- Confirm access to the Chrome Web Store Developer Dashboard and pay the one-time $5 registration fee if not already registered
- Create a Stripe account (or confirm an existing one) with Checkout and Customer Portal enabled
- Verify Docker Compose and Coolify are operational on the existing deployment server
- Ensure Node.js (v18+) and npm are installed locally for TypeScript extension development
- Ensure Python 3.11+ and pip are available locally for the Flask license backend
- Set up a dedicated Git repository for the revenue product (separate from OpenClaw, spec-doc, and sam-plugin)
- Inventory current weekly hours spent on each existing project so triage decisions are grounded in real data
- Bookmark the Chrome Extensions Manifest V3 migration guide for reference during the build phase

---

## Task 1: Portfolio Triage  [Effort: 1 day]

### What
Produce a one-line kill, keep-passive, or keep-active verdict for every existing project (humanize-me, Bubls, Trendfy, and spec-doc) and execute the verdict immediately. This reclaims the full nights-and-weekends attention budget before any new commitment begins.

### Files
- **Create**: `decisions/portfolio-triage.md` — written verdicts for each project with rationale citing the three triage criteria (marketplace distribution, 90-day traction, weekly maintenance cost)
- **Modify**: GitHub repository settings for killed projects — archive the repository and disable issues/wiki

### Steps
1. For each of the four projects, answer three questions in writing: does it have a marketplace-native distribution channel today, has it generated revenue or inbound interest in the last 90 days, and does it consume more than two hours per week to maintain.
2. Assign the verdict for Trendfy as "kill" since its kill date has already passed, and archive the repository on GitHub.
3. Assign humanize-me to "keep-passive" — it stays deployed but receives zero development hours; if it breaks, it gets archived rather than fixed.
4. Assign Bubls to "keep-passive" or "kill" depending on current maintenance burden; if it requires any community-building effort in the Zürich market, kill it.
5. Assign spec-doc to "keep-active as internal tooling" with an explicit note that it carries zero revenue expectation and must not become a dependency of the revenue product.
6. Record all verdicts in `decisions/portfolio-triage.md` with the date and a one-sentence rationale per project.
7. For any project marked "kill," archive the GitHub repository, remove it from any CI/CD pipelines, and tear down deployed infrastructure on Coolify if applicable.

### Verify
- `decisions/portfolio-triage.md` exists and contains exactly four verdicts with no project left in ambiguous status
- Every project marked "kill" has its GitHub repo archived (Settings > Archive this repository)
- No killed project is consuming Coolify resources (check the Coolify dashboard)
- The weekly attention budget freed by triage is documented as available hours for the revenue product

---

## Task 2: Revenue Target & Channel Lock  [Effort: 1 day]

### What
Set a concrete monthly dollar target that filters product categories and effort allocation, then select exactly one marketplace as the distribution channel. These two decisions constrain every subsequent task and prevent scope drift into multi-channel hedging.

### Files
- **Create**: `decisions/revenue-target.md` — the chosen dollar-per-month target with a justification tied to Sam's attention budget and lifestyle goals
- **Create**: `decisions/channel-selection.md` — the chosen marketplace (Chrome Web Store), the five-criteria evaluation against Shopify App Store and MCP registries, and the explicit trade-offs accepted

### Steps
1. Define the revenue target by choosing a specific dollar amount per month (the architecture recommends a range where 100-300 paying users at $5-$15/month hits the goal). Write down why that number was chosen and what product categories it eliminates.
2. Evaluate Chrome Web Store, Shopify App Store, and MCP server registries against five criteria: review cycle speed, willingness-to-pay ceiling, competition density, discovery mechanism, and stack alignment.
3. Select Chrome Web Store as the primary channel based on fastest feedback loop (1-3 day review), lowest review friction, and keyword-driven discovery that does not require audience building.
4. Document the explicit trade-offs accepted: lower WTP ceiling ($5-$15 versus Shopify's $20-$99), giving up MCP's superior stack alignment, and no first-mover advantage in the MCP ecosystem.
5. Write the gate condition: do not expand to a second channel until the first product reaches $500/month sustained for two consecutive months.
6. Save both documents and confirm that the revenue target and channel selection are consistent with each other (the target must be achievable at the channel's WTP ceiling with a realistic number of paying users).

### Verify
- `decisions/revenue-target.md` states a single number, not a range, and explains how many paying users at what price point would reach it
- `decisions/channel-selection.md` names exactly one marketplace with a written rationale referencing all five evaluation criteria
- The documents are internally consistent — the revenue target is achievable within Chrome Web Store's $5-$15/month WTP range
- No mention of "Plan B" or secondary channels exists in either document

---

## Task 3: Product Selection & Validation  [Effort: 2 days]

### What
Identify two to three candidate Chrome extensions, validate demand for each using marketplace data, and commit to exactly one product. Validation happens entirely through research — no code is written in this task. The selection framework prioritizes distribution feasibility over technical ambition.

### Files
- **Create**: `decisions/product-candidates.md` — the 2-3 candidates with scores on four dimensions (search demand, competitor gap, build complexity, retention mechanics)
- **Create**: `decisions/product-selection.md` — the winning product with its validation evidence, the rejected alternatives, and a one-paragraph product brief describing the free tier, paid tier, and price point
- **Create**: `decisions/competitor-analysis.md` — for the winning product, a breakdown of the top 3-5 existing extensions including install counts, star ratings, last update dates, and specific quality gaps Sam can exploit

### Steps
1. Search the Chrome Web Store for productivity and developer-tool categories, noting autocomplete suggestions that indicate active search demand. Identify 2-3 niches where people are searching but existing extensions have obvious quality problems.
2. For each candidate niche, count the installs and review velocity of the top 3-5 existing extensions. A good signal is competitors with high installs but low ratings (below 4.0 stars) or abandoned update schedules (no update in 6+ months).
3. Score each candidate on four dimensions in priority order: search demand signal, competitor gap, build complexity relative to the 5-day attention budget, and retention mechanics that drive weekly usage.
4. Reject any candidate that requires Sam to create content, build an audience, or do outbound sales. Reject any candidate whose MVP requires a feature backend, persistent storage, or ongoing data pipelines.
5. Select the highest-scoring candidate and write a product brief: one sentence describing what the extension does, what the free tier includes, what the paid tier unlocks, and the target price point between $5 and $15 per month.
6. For the selected product, document the top 3-5 competitors in detail — their install counts, star ratings, last update dates, and the specific quality gaps (bad UX, missing features, stale maintenance) that create the opening.

### Verify
- `decisions/product-candidates.md` lists exactly 2-3 candidates with quantified scores, not vague assessments
- `decisions/product-selection.md` names one winner with marketplace evidence (install counts, review counts, competitor gaps) backing the choice
- The selected product's MVP can plausibly ship in 5 focused days using TypeScript and Manifest V3 with no backend features
- `decisions/competitor-analysis.md` names real extensions with real install counts and identifies at least one exploitable quality gap

---

## Task 4: MVP Build & Marketplace Submission  [Effort: 5 days]

### What
Build the minimum shippable version of the selected Chrome extension, wire up a Stripe-backed license verification backend, and submit the extension to the Chrome Web Store. The extension works entirely client-side for core functionality; the only backend call is license checking.

### Files
- **Create**: `extension/manifest.json` — Chrome Manifest V3 configuration with permissions, content scripts, popup, and service worker declarations
- **Create**: `extension/src/popup.ts` — popup UI entry point using vanilla TypeScript or Preact; renders the extension's primary interface
- **Create**: `extension/src/content.ts` — content script that executes the extension's core functionality on target web pages
- **Create**: `extension/src/background.ts` — service worker handling license state caching, message passing between popup and content script, and alarm-based usage tracking for the free tier gate
- **Create**: `extension/src/license.ts` — module that calls the Flask backend to verify license status and caches the result locally
- **Create**: `extension/src/styles.css` — minimal stylesheet for the popup and any injected UI elements
- **Create**: `extension/webpack.config.js` — build configuration targeting Manifest V3 output structure
- **Create**: `extension/package.json` — project manifest with TypeScript, webpack, and Preact (or no framework) as dependencies
- **Create**: `extension/tsconfig.json` — TypeScript configuration targeting ES2020 with Chrome extension type definitions
- **Create**: `backend/app.py` — Flask application with two routes: one for Stripe webhook handling and one for license verification
- **Create**: `backend/requirements.txt` — Python dependencies (Flask, Stripe, gunicorn)
- **Create**: `backend/Dockerfile` — container definition for the Flask license server using a slim Python base image
- **Create**: `docker-compose.yml` — service definition for the license backend, deployable via Coolify
- **Create**: `store-assets/description.txt` — Chrome Web Store listing description with keyword-leading title, value proposition first sentence, and feature bullet points
- **Create**: `store-assets/screenshots/` — directory for 3-5 annotated screenshots showing the extension in action on real web pages

### Steps
1. Initialize the extension project by creating `extension/package.json` with TypeScript, webpack, and any lightweight UI framework as dev dependencies. Run npm install to generate the lockfile.
2. Write `extension/manifest.json` declaring Manifest V3, the minimum required permissions, the service worker entry point at `background.ts`, content script matches, and the popup HTML reference.
3. Implement the core extension functionality in `extension/src/content.ts` — this is the client-side logic that delivers the product's primary value. Keep it self-contained with no backend dependency for the free tier.
4. Build the popup interface in `extension/src/popup.ts` showing the extension's controls, current usage count against the free tier limit, and an upgrade prompt that links to Stripe Checkout for users who hit the gate.
5. Implement the service worker in `extension/src/background.ts` to manage message passing between the popup and content script, cache license state using chrome.storage.local, and track usage counts via chrome.alarms for the freemium gate.
6. Create `extension/src/license.ts` with a single exported function that calls the Flask backend's verification endpoint, caches the response for 24 hours in chrome.storage.local, and gracefully degrades to free-tier behavior if the backend is unreachable.
7. Configure webpack in `extension/webpack.config.js` to produce the Manifest V3 output structure: separate bundles for background, content, and popup entry points, with the output directory set to `extension/dist`.
8. Build the Flask license backend in `backend/app.py` with two routes: a POST endpoint for Stripe webhooks that records subscription status keyed by a license identifier, and a GET endpoint that returns the current license status for a given key. Use an in-process dictionary or SQLite for storage at this scale.
9. Write `backend/Dockerfile` using a slim Python base image, install dependencies from `backend/requirements.txt`, and set the entrypoint to gunicorn with a single worker.
10. Create `docker-compose.yml` defining the license backend service with appropriate port mapping and environment variables for the Stripe secret key and webhook signing secret.
11. Deploy the license backend to Coolify using the existing Docker Compose deployment pattern and verify the health endpoint responds.
12. Build the extension with npm run build, load the `extension/dist` directory as an unpacked extension in Chrome, and manually test the core functionality, the free tier usage gate, the upgrade flow through Stripe Checkout, and license verification after payment.
13. Prepare store assets: write the listing description in `store-assets/description.txt` with the primary search keyword in the first three words of the title, and capture 3-5 annotated screenshots demonstrating the extension on real web pages.
14. Submit the extension to the Chrome Web Store via the Developer Dashboard, uploading the zipped `extension/dist` directory and the store assets. Select the category and tags based on where high-install competitors are listed.

### Verify
- Running `npm run build` in the `extension/` directory produces a `dist/` folder containing a valid Manifest V3 extension with no TypeScript or webpack errors
- Loading the unpacked extension in Chrome and exercising the core feature works without errors in the browser console
- The free tier usage gate triggers after the configured number of uses and displays the upgrade prompt
- The Flask license backend responds to a GET request on the verification endpoint and correctly reflects subscription status after a Stripe webhook test event
- The extension is submitted to the Chrome Web Store and the Developer Dashboard shows a status of "Pending Review" or "Published"

---

## Task 5: First Paid Customer  [Effort: 3 days]

### What
Optimize the Chrome Web Store listing for organic discovery, implement an in-extension review prompt, and monitor installs until at least one user converts to a paid subscription through marketplace discovery alone — no cold outreach, no paid ads.

### Files
- **Modify**: `store-assets/description.txt` — refine keywords, rewrite the first sentence if install-to-detail-view ratio is low, and add or reorder feature bullet points based on competitor listing patterns
- **Modify**: `extension/src/popup.ts` — add a non-intrusive review prompt that appears after the user's third successful use of the core feature, linking to the Chrome Web Store review page
- **Modify**: `extension/src/background.ts` — add a counter in chrome.storage.local tracking successful actions to trigger the review prompt at the right moment
- **Modify**: `store-assets/screenshots/` — replace or re-annotate screenshots if the original set does not clearly communicate the value proposition within the first two images

### Steps
1. After the extension is published, check the Chrome Web Store Developer Dashboard daily for impression counts, install counts, and the detail-view-to-install conversion rate. If impressions are low, the title keywords are wrong; if impressions are high but installs are low, the listing description or screenshots need revision.
2. Compare the listing's title, description, and screenshot style against the top 3 competitors identified in the competitor analysis. Rewrite the listing description in `store-assets/description.txt` to match or exceed the clarity and keyword density of the best-performing competitor listing.
3. Update `extension/src/background.ts` to increment a persistent counter each time the user completes a successful core action, storing the count in chrome.storage.local.
4. Update `extension/src/popup.ts` to check the action counter on each popup open and display a polite, dismissible review prompt after the third successful action. The prompt should link directly to the extension's Chrome Web Store review page and never appear again after dismissal.
5. Rebuild and resubmit the extension with the review prompt changes. Upload revised store assets if the description or screenshots changed.
6. Monitor the Stripe Dashboard for the first subscription event. Do not engage in any outbound marketing, cold outreach, or paid advertising — the goal is to prove that the marketplace's organic discovery is sufficient to convert a stranger into a paying customer.
7. When the first paid subscription appears in Stripe, record the date, the acquisition path (Chrome Web Store search keyword if available from dashboard analytics), and the time elapsed since listing publication.

### Verify
- The Chrome Web Store Developer Dashboard shows a non-zero install count from organic search impressions
- The review prompt appears exactly once after the third successful user action and does not reappear after dismissal
- The Stripe Dashboard shows at least one active subscription with a payment method on file, originating from a user Sam did not contact directly
- The date of first paid customer and days-since-launch are recorded for retrospective analysis