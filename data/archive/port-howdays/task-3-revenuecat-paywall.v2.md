# Task 3: RevenueCat Service + Paywall Modal — Execution Plan

**Status**: In Progress
**Effort**: 2 days
**Dependencies**: Task 1 (Capacitor Base Service) — already landed

---

## Plan

### Step 1: Install RevenueCat + Add Environment Config
- `npm install @revenuecat/purchases-capacitor`
- Add `RC_API_KEY` placeholder and `MOCK_PAYMENTS` flag to both environment files
- Add `@revenuecat/purchases-capacitor` to ACL banned list

### Step 2: Payments Model + Mock Data
- `src/app/shared/payments/payments.model.ts` — PurchaseResult, PaywallConfig, tier definitions
- `src/app/shared/payments/payments.mock.ts` — Mock offerings, entitlements for dev/test

### Step 3: RevenueCatService
- `src/app/shared/payments/revenuecat.service.ts` — Extends CapacitorBaseService
  - `initialize()` — configure SDK with API key and user ID
  - `getOfferings()` — returns available packages
  - `purchase(package)` — triggers native IAP flow
  - `getEntitlements()` / `checkEntitlement(id)` — returns active entitlements as signal
  - `customerInfoUpdate$` — observable for real-time entitlement changes
  - `restorePurchases()` — restore flow
  - Mock mode on web or when `MOCK_PAYMENTS=true`
- `src/app/shared/payments/revenuecat.service.spec.ts` — Tests

### Step 4: PaywallModalComponent
- `src/app/shared/payments/paywall-modal.component.ts` — Standalone, OnPush, signals
  - Pro features list, price, CTA button
  - Purchase flow with loading state
  - Error handling via ErrorParserService
  - `data-test` selectors throughout
  - Dismiss on success with entitlement update
- `src/app/shared/payments/paywall-modal.component.spec.ts` — Tests

### Step 5: FeatureGateGuard
- `src/app/shared/payments/feature-gate.guard.ts` — Functional route guard
  - Checks `RevenueCatService.checkEntitlement('pro')`
  - Opens paywall modal when not entitled (null object pattern)
- `src/app/shared/payments/feature-gate.guard.spec.ts` — Tests

### Step 6: Wire Into Existing Feature Gates
- Text page: chain buttons + voice mic check entitlements via RevenueCatService
- Keep `enabled_features` as server-side fallback
- Initialize RevenueCat on app start (after auth) in AppComponent

### Step 7: Barrel Export + Index
- `src/app/shared/payments/index.ts` — Public API

---

## Files Created

| File | Purpose |
|------|---------|
| `src/app/shared/payments/payments.model.ts` | Types, tier config |
| `src/app/shared/payments/payments.mock.ts` | Mock offerings/entitlements |
| `src/app/shared/payments/revenuecat.service.ts` | RevenueCat adapter |
| `src/app/shared/payments/revenuecat.service.spec.ts` | Service tests |
| `src/app/shared/payments/paywall-modal.component.ts` | Paywall UI |
| `src/app/shared/payments/paywall-modal.component.spec.ts` | Component tests |
| `src/app/shared/payments/feature-gate.guard.ts` | Route guard |
| `src/app/shared/payments/feature-gate.guard.spec.ts` | Guard tests |
| `src/app/shared/payments/index.ts` | Barrel export |

## Files Modified

| File | Change |
|------|--------|
| `src/environments/environment.ts` | Add RC_API_KEY, MOCK_PAYMENTS |
| `src/environments/environment.prod.ts` | Add RC_API_KEY, MOCK_PAYMENTS |
| `src/app/app.component.ts` | Initialize RevenueCat on app start |
| `src/app/pages/text/text.page.ts` | Wire entitlement checks for chain/voice |
| `scripts/architecture-acl-check.mjs` | Ban `@revenuecat/purchases-capacitor` |
| `package.json` | Add dependency |

---

## Actual Results

**Status**: Complete
**Commit**: `8b12f04` feat(payments): add RevenueCat service, paywall modal, and feature gate

### Test Results

| Suite | Count | Status |
|-------|-------|--------|
| RevenueCatService (mock mode) | 7 | PASS |
| RevenueCatService (entitlement state transitions) | 5 | PASS |
| RevenueCatService (observables) | 3 | PASS |
| PaywallModalComponent | 10 | PASS |
| featureGateGuard | 6 | PASS |
| **Total** | **31** | **ALL PASS** |

### Deviations

| Deviation | Reason |
|-----------|--------|
| Native mode SDK tests replaced with state-transition tests | RevenueCat Capacitor plugin throws "Web not supported" in headless browser before jasmine spies can intercept. Tests verify the adapter logic (entitlement signal updates, purchase result mapping, cancel detection) which IS testable. Real SDK round-trip validated on iOS simulator. |
| `@capacitor-community/sqlite` installed as side-effect | Pre-existing missing dependency blocking all test runs. Not part of Task 3 scope but required to unblock CI. |
| `textChainsEnabled` and `voiceProLocked` changed from writable signals to computed signals | Required for proper entitlement gating. One existing test (`freeUser_micLocked_proBadgeShown`) updated to not call `.set()` on a computed. |

### Architecture Notes

- `RevenueCatService` is the single point of contact with the RevenueCat SDK (ACL enforced via `architecture-acl-check.mjs`)
- Pages consume `RevenueCatService.isPro()` signal, never import the plugin
- Mock mode (`environment.useMocks.payments`) returns fixture data for web/dev
- `FeatureGateGuard` can be applied to any route via `canActivate: [featureGateGuard]`
- Text page's `showUpgradeToast()` now opens the paywall modal instead of `window.alert()`
