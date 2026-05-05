# Task 4: Wire RevenueCat into CocoaPods

## Goal

Verify the RevenueCat native plugin is correctly wired end-to-end: Podfile (Task 1) has it, service imports from the right package, ACL check blocks page-level imports.

## Current State

- `RevenuecatPurchasesCapacitor` already in Podfile from Task 1.
- `src/app/shared/payments/revenuecat.service.ts` imports from `@revenuecat/purchases-capacitor` — correct.
- `scripts/architecture-acl-check.mjs` BANNED list already includes `@revenuecat/purchases-capacitor` (line 26).
- No changes needed to ACL — already configured.

## Changes

1. **Verify** `revenuecat.service.ts` imports match the CocoaPods pod name (`RevenuecatPurchasesCapacitor` maps to `@revenuecat/purchases-capacitor`). Already correct.
2. **Verify** ACL check already bans `@revenuecat/purchases-capacitor` from pages/features. Already in BANNED array.
3. **No code changes required** — this is a verification-only task. The commit documents that the native wiring is complete.

## Verification

- `npm run test:acl` passes (or exits 0 with known violations for StatusBar/Haptics, which are unrelated).
- `npx ng build --configuration=production` passes.

## Commit

```
feat(payments): verify RevenueCat native wiring via CocoaPods
```

NOTE: This task produces an empty commit (documentation-only) since all wiring was completed in Tasks 1 and the existing service.
