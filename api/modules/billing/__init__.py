"""billing — Stripe Checkout / webhook / Customer Portal adapter.

Sole writer of Subscription state and User.plan ('free' | 'pro').
The webhook signature-verifies every event before any handler runs;
no in-app code path may set User.plan to 'pro'.
"""
