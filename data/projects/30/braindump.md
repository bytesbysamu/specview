# SaaS Phase 4: SDK Provider + Onboarding

> **Priority**: P3 — post-launch optimization. Not needed for first users, needed for sustainable unit economics.
> **Effort**: ~2 days.
> **Blocks**: nothing.
> **Depends on**: Phase 1 (auth pages exist), Phase 2 (billing works), first paying customer or proven refresh-token unreliability.

## What this is

Two things that happen after launch: switch production from Claude Max CLI to API key billing when per-user cost tracking justifies per-token pricing, and build the onboarding flow that converts landing page visitors into activated users.

---

## Current State (fact-checked 2026-05-12)

**SDK provider — already built:**
- `api/modules/runtime/chain/providers/claude.py` — complete Anthropic SDK provider with `create_message()`, `stream_message()`, error handling for RateLimitError, APIConnectionError, APIError
- `api/modules/runtime/chain/adapter.py` — provider resolution: if `ANTHROPIC_API_KEY` is set, auto-resolves to SDK provider. If not, falls back to CLI.
- Cost accumulator in adapter.py — per-model pricing (Haiku $0.80/$3.00, Sonnet $3.00/$15.00, Opus $15.00/$75.00), thread-safe `_USAGE` dict
- `GET /api/ai/stats` — returns cumulative calls, token counts, cost_usd, provider name
- Startup gate in `create_app.py` — warns (doesn't crash) when `APP_ENV=production` and `CHAIN_PROVIDER` is not `claude`

**What's missing:**
- Production not using SDK — currently on CLI provider with Claude Max (P0 decision: can't afford API key billing pre-revenue)
- No per-step model routing — all steps use the same model (currently claude-opus-4-6). Analysis could use Haiku (5x cheaper), only architecture needs Opus.
- Startup gate warns but doesn't block — should hard-fail in production mode without `ANTHROPIC_API_KEY`
- No onboarding flow — landing CTA doesn't connect to signup, no first-run experience

---

## Task 1 — SDK Provider as Production Default

> **Effort**: 0.5 days
> **Trigger**: first paying customer, OR Claude Max refresh token proves unreliable.

### When to switch

This is a configuration change, not a code change. The adapter already supports it:

```bash
# In Coolify env vars or .env:
ANTHROPIC_API_KEY=sk-ant-api03-...
# CHAIN_PROVIDER auto-resolves to "claude" (SDK) when ANTHROPIC_API_KEY is set
```

### Per-step model routing

Update bootstrap workflow to use cheaper models where quality doesn't matter:

```python
# analysis step: short prompts, classification work → Haiku (~5x cheaper)
AICall(name="analysis", model="claude-haiku-4-5", max_tokens=4096)

# epic step: structured output, moderate quality → Sonnet
AICall(name="epic", model="claude-sonnet-4-5", max_tokens=8192)

# architecture step: highest quality needed → Opus
AICall(name="architecture", model="claude-opus-4-6", max_tokens=16384)
```

This saves ~60-80% on bootstrap cost compared to running Opus for all 3 steps.

### Startup gate

Harden the existing warning to a hard failure:

```python
# create_app.py
def _enforce_production_startup_gate():
    if os.environ.get("APP_ENV") != "production":
        return
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "Production mode requires ANTHROPIC_API_KEY. "
            "Set CHAIN_PROVIDER=mock to override (tests only)."
        )
```

### Cost monitoring

The `/api/ai/stats` endpoint already returns cumulative cost. Add a daily cost alert:
- If `cost_usd > $10` in a single day, log a WARNING
- Track per-user cost attribution by joining usage counter with token counts (requires correlating chain calls with the user who initiated them)

---

## Task 2 — Landing → Signup Connection

> **Effort**: 0.5 days

The landing page at `landing/index.html` has CTA buttons that don't connect to the app.

### Changes

1. Landing "Get Started" CTA → `https://app.specview.io/signup` (or however the Angular app is routed)
2. Angular needs a `/signup` route that shows the registration form (from Phase 1)
3. After successful registration → redirect to the main app view
4. After successful login → redirect to the main app view

### Angular routing

Currently the app is a single-component SPA with hash-based view switching. Adding proper routes:

```typescript
// Minimal routing for auth pages
const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'signup', component: SignupComponent },
  { path: '', component: AppComponent, canActivate: [authGuard] },
];
```

Or keep the current single-component approach and use signals to toggle between login/signup/app views. Decision depends on how much routing overhead is acceptable.

---

## Task 3 — First-Run Experience

> **Effort**: 1 day

When a new user signs up and lands in the app for the first time, they see an empty project list. They need guidance.

### Approach

1. **Detect first-run**: User has 0 projects → show onboarding state
2. **Sample project**: Auto-create a project called "My First Spec" with a pre-written braindump that demonstrates the tool
3. **Guided prompt**: Banner or modal: "Paste your braindump → Click Generate → See your specs"
4. **Free tier messaging**: "You have 3 free spec generations per day. Upgrade to Pro for unlimited."

### Alternative: skip the first-run and just make the empty state good

Instead of a guided tour, make the empty state actionable:
- Big "Create your first project" button
- Example braindump text as placeholder in the editor
- Status bar says "Ready — paste a braindump to get started"

This is simpler and less presumptuous. Recommended for v1.

---

## Files to Change

| File | Change |
|------|--------|
| `api/create_app.py` | Harden startup gate to hard-fail without ANTHROPIC_API_KEY |
| `api/modules/ai/workflows/` | Per-step model routing (Haiku/Sonnet/Opus) |
| `landing/index.html` | CTA links to app signup |
| `web-ng/src/app/` | Signup route/view, first-run empty state |
| `.env` | `ANTHROPIC_API_KEY` when switching to SDK |

## Success Criteria

- [ ] Production runs on SDK provider with `ANTHROPIC_API_KEY` (when switched)
- [ ] Bootstrap pipeline costs ~60% less via per-step model routing
- [ ] Landing page CTA navigates to signup
- [ ] New user sees actionable empty state, not a blank page
- [ ] Free tier limit is clearly communicated before the user hits it
