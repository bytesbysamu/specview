---
name: RevenueCat iOS SubscriptionPeriod fix
description: iOS 18.4+ causes SubscriptionPeriod ambiguity in RevenueCat — must keep purchases-capacitor updated and iOS target >= 16.0
type: feedback
---

When building iOS with Xcode 16.3+ / iOS 18.4+, RevenueCat's `SubscriptionPeriod` collides with StoreKit 2's native type. Build fails with "'SubscriptionPeriod' is ambiguous for type lookup in this context" in PurchasesHybridCommon.

**Why:** Apple introduced a `SubscriptionPeriod` typealias in StoreKit starting iOS 18.4. Older RevenueCat versions use unqualified `SubscriptionPeriod` references.

**How to apply:** Always keep `@revenuecat/purchases-capacitor` at latest (13.0.0+ for Cap 7, 9.2.2+ for Cap 6). iOS deployment target must be >= 16.0. After upgrading, run `pod update PurchasesHybridCommon --repo-update` if Podfile.lock is stale. This applies to both bubls and ionstarter repos.
