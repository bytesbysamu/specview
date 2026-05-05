---
sidebar_position: 2
---

# 🎯 Bubls App Store Launch – Epic

**Purpose**: Define scope and tasks for shipping Bubls from TestFlight to a monetized App Store product.

**Source Analysis**: See [Analysis](./analysis.md) for the six problems this epic addresses.

---

## Business Value

Bubls has three AI features, 161 backend tests, a landing page with tracking, and a TestFlight build — everything except the ability to make money and reach users organically. StealthGPT proves the market at $195K MRR charging $15/mo for text humanization alone. Bubls bundles three features (text rewriting, AI photoshoot, curated picks) at $4.99/mo, a 67% discount with 3x the surface area. The margin math works: Claude API costs per rewrite are ~$0.003, so even the $4.99 Pro tier runs at 91%+ gross margin at moderate usage.

The second lever is voice input. Every text rewriter on the market takes text in and gives text back — same modality, same workflow, same positioning. Voice-to-rewrite ("talk to your phone, get a polished email") is a new behavior category. It collapses three steps (think → type → rewrite) into two (speak → done). No competitor does this as a single flow. This is the feature that earns the App Store feature slot and the press coverage, not "another text humanizer."

**Value proposition**: Ship the minimum delta to go from "working TestFlight build" to "monetized App Store product with a differentiated input modality." Revenue starts day one. Voice earns the positioning. Share sheets close the viral loop.

---

## Scope

### What This Epic Covers

- Stripe subscription backend (webhook, customer creation, subscription state in Neon)
- Paywall UI with feature guard (Pro features → upgrade page, never 404)
- Server-side usage metering (free: 10/day single-shot only; Pro: unlimited + chain modes)
- Voice input on the Text page (microphone → on-device transcription → textarea, "speak then rewrite" flow)
- Native share sheet on text output, photoshoot results, and picks detail
- App Store submission (screenshots, metadata, privacy labels, review compliance)

### What This Epic Does NOT Cover

- ❌ Push notifications (post-launch engagement feature)
- ❌ Analytics dashboard UI (tracking data is collected; dashboard is a separate capability)
- ❌ Offline mode or multi-device sync
- ❌ Apple In-App Purchase / StoreKit 2 (Stripe web checkout first; IAP if Apple mandates)
- ❌ A/B testing pricing tiers
- ❌ Automated refund handling
- ❌ Voice input on Photoshoot or Picks (Text page only for v1)
- ❌ New AI modes or chain operations
- ❌ Backend infrastructure changes beyond subscription + usage tables

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Stripe subscription backend** | None | — | 2 days | Critical |
| 2 | **Paywall UI + feature guard** | 1 | 3 | 1.5 days | Critical |
| 3 | **Usage metering enforcement** | 1 | 2 | 1.5 days | Critical |
| 4 | **Voice input on Text page** | None | 1, 5 | 2 days | High |
| 5 | **Share sheet integration** | None | 1, 4 | 1 day | High |
| 6 | **App Store submission** | 2, 3, 4, 5 | — | 1.5 days | High |

### Task Details

#### Task 1: Stripe subscription backend

Wire Stripe into the Flask backend. Alembic migration adds `subscriptions` table (`id`, `user_id FK`, `stripe_customer_id`, `stripe_subscription_id`, `plan` enum free/pro, `status` enum active/cancelled/past_due, `current_period_end`, `created_at`, `updated_at`). SQLModel for the subscription entity. Three endpoints: `POST /api/billing/create-checkout-session` (creates Stripe Checkout session with `success_url` and `cancel_url`), `POST /api/billing/webhook` (handles `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted` — signature verified via `stripe.Webhook.construct_event`), `GET /api/billing/status` (returns current plan + period end for the authenticated user). Stripe customer created lazily on first checkout — linked to `superapp_users` via email. Environment variables: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRO_MONTHLY_PRICE_ID`, `STRIPE_PRO_ANNUAL_PRICE_ID`. No raw SQL — all through SQLModel. Tests mock the Stripe SDK, verify webhook signature validation rejects tampered payloads, and confirm subscription state transitions (free → pro → cancelled → free).

#### Task 2: Paywall UI + feature guard

Add `SubscriptionService` adapter in `src/app/services/subscription.service.ts` — calls `GET /api/billing/status`, exposes `plan: Signal<'free' | 'pro'>` and `isPro: Signal<boolean>`. `UpgradeComponent` standalone page at `src/app/pages/upgrade/` — shows pricing table (Free vs Pro comparison), CTA opens Stripe Checkout via `POST /api/billing/create-checkout-session` returned URL. Feature guard `proGuard` checks `isPro()` — if false, navigates to `/upgrade` with a return URL. Guard applied to chain mode buttons (Deep Humanize, Brain Dump → Docs, Rewrite + Review) and voice input. Single-shot modes remain free. Guard shows the upgrade page with the specific feature name that triggered it ("Unlock Deep Humanize with Pro"). Success URL from Stripe redirects back to the app via deep link (`bubls://billing/success`), which triggers a `subscription.service.refresh()`. Add `data-test` selectors on every interactive element. TestBed spec covers: free user taps chain mode → sees upgrade page; pro user taps chain mode → proceeds; upgrade CTA opens checkout URL.

#### Task 3: Usage metering enforcement

Server-side rate limiting per user per day for free-tier users. Alembic migration adds `usage_counters` table (`id`, `user_id FK`, `feature` varchar, `date` date, `count` int, unique constraint on `user_id + feature + date`). On every `POST /api/text/rewrite` and `POST /api/text/generate`, middleware checks: if user is free and today's count ≥ 10, return 429 with `{"error": "daily_limit_reached", "limit": 10, "resets_at": "ISO timestamp"}`. If user is pro, no limit. Increment counter atomically via `INSERT ... ON CONFLICT (user_id, feature, date) DO UPDATE SET count = count + 1`. Chain endpoints (`/api/text/rewrite` with chain modes) check `plan == 'pro'` and return 403 if free. Client-side: `UsageMeterComponent` in the Text page header shows "7/10 remaining" for free users, hidden for pro. When limit hit, the 429 response triggers the paywall overlay with "Upgrade to Pro for unlimited rewrites." Tests: mock 10 calls → 11th returns 429; pro user → no limit; counter resets at midnight UTC.

#### Task 4: Voice input on Text page

Add microphone button to the Text page textarea. Tap to start recording — button pulses with a ring animation, waveform visualizer shows amplitude. Tap again (or 30s timeout) to stop. On-device transcription via `@capacitor-community/speech-recognition` plugin — no API cost, works offline, supports 60+ languages. Transcribed text fills the textarea (appends if text exists, replaces if empty — configurable via a toggle). User then taps any rewrite mode as normal. The "speak then rewrite" flow: mic → transcribe → textarea populated → user taps Humanize → polished output. Permission request on first tap with rationale ("Bubls uses your microphone to transcribe speech into text for rewriting"). If permission denied, mic button shows a tooltip explaining how to enable in Settings. Add `VoiceInputService` adapter wrapping the Capacitor plugin — mock mode returns fixture transcription for tests. Feature-gated as Pro (free users see the mic button grayed out with "Pro" badge). Haptic feedback on start/stop. `prefers-reduced-motion` disables the pulse animation. TestBed spec covers: tap mic → permission granted → recording state → stop → textarea filled; permission denied → tooltip shown; free user → pro badge shown.

#### Task 5: Share sheet integration

Add native share sheet via `@capacitor/share` plugin to three surfaces. **Text page**: "Share" button appears below output after any rewrite/generate completes. Shares the output text with subject line "Rewritten with Bubls". **Photoshoot page**: share button on each result in the contact sheet. Shares the image file with subject "AI Photo by Bubls". **Picks detail page**: share pill next to the existing save pill. Shares the pick URL + title. `ShareService` adapter wrapping `Share.share()` — mock mode logs share intent for tests. Each share event writes to `superapp_generations.shared_at` (nullable timestamp column, Alembic migration) for tracking share rate. Share buttons use `data-test` selectors. TestBed spec covers: output present → share button visible; tap share → `Share.share()` called with correct payload; no output → share button hidden.

#### Task 6: App Store submission

Package Bubls for App Store review. **Screenshots**: capture 6.7" (iPhone 15 Pro Max), 6.1" (iPhone 15), and 5.5" (iPhone 8 Plus) screenshots for all three features + onboarding, in both light and dark mode. Use Fastlane `snapshot` if possible, manual capture otherwise. **Metadata**: app name "Bubls — AI Writer & Photos", subtitle "Rewrite, Generate, Create", keywords (text up to 100 chars: "AI writer, text humanizer, AI photos, rewrite, voice to text"), description (feature highlights, privacy-first positioning, pricing). **Privacy labels**: data collected (email for account, usage data for analytics, photos for AI generation), data not linked to identity (analytics), data linked to identity (email, photos). **Review guidelines compliance audit**: check for private API usage, ensure Stripe Checkout doesn't violate IAP rules (link to Apple's reader app exception or small-business exemption if applicable), verify all AI-generated content is clearly labeled, ensure camera/microphone permission strings are descriptive. **App Review Information**: demo account credentials, notes explaining AI features. **Build**: increment to v1.3.0 build 1, archive via `xcodebuild`, upload via `xcrun altool` or Transporter. Privacy policy hosted at `humaniz.me/bubls/privacy` (static page).

---

## Success Criteria

- ✅ Free user hits 10 rewrites → 11th request returns 429 → paywall appears → taps "Upgrade" → Stripe Checkout opens → completes payment → returns to app as Pro → chain modes unlocked, no daily limit
- ✅ Pro user speaks into mic → transcription fills textarea → taps Humanize → polished output → taps Share → native share sheet opens with text
- ✅ Stripe webhook processes `customer.subscription.deleted` → user downgraded to free → chain modes re-gated → daily limit re-enforced
- ✅ App Store submission accepted on first attempt (no rejections for missing metadata, privacy issues, or IAP violations)
- ✅ Landing page TestFlight link updated to App Store link post-approval
- ✅ Day-7 verdict endpoint reports ≥5% return rate among first 50 organic installs
- ✅ All 161+ existing backend tests continue passing; new tests bring total to 185+

---

## Non-Goals

- ❌ Optimizing pricing (ship $4.99/mo and $39.99/yr; A/B test after 200 users)
- ❌ Family sharing or promo codes (manual via Stripe dashboard)
- ❌ Stripe billing portal for self-service cancellation (link to Stripe customer portal URL; no custom UI)
- ❌ Voice input on Photoshoot or Picks pages
- ❌ Real-time transcription streaming (batch transcription on stop is sufficient for v1)
- ❌ Localization (English only for initial App Store listing)

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

