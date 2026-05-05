---
sidebar_position: 0
---

# 📋 Bubls App Store Launch

> Ship Bubls from TestFlight to a monetized App Store product with voice input as the positioning wedge.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [🎯 Epic](./epic.md) | Scope, tasks, success criteria |
| [🏗️ Architecture](./architecture.md) | Technical design |
| [📅 Timeline](./timeline.md) | Status tracking |

## Overview

Bubls v1.2.0 is live on TestFlight with three AI features (Text, Photoshoot, Picks), 161 backend tests passing, 7 LoRA models, and a landing page with waitlist tracking wired end-to-end. What it lacks is the delta between "internal test build" and "monetized product in the App Store": payment infrastructure, usage enforcement, a differentiating input modality, content sharing, and App Store submission compliance.

This capability closes that gap in six tasks. Stripe subscriptions gate chain modes and remove the daily cap for Pro users ($4.99/mo or $39.99/yr). Server-side usage metering enforces the free tier at 10 single-shot rewrites per day — the backend already has feature gating and a generations table, so this extends existing infrastructure rather than building from scratch. Voice input ships as the positioning wedge: "talk to your phone, get a polished email" is a behavior category no text-rewriting competitor occupies. Capacitor Share plugin gives every output surface (text results, photoshoot images, saved picks) a native share sheet. App Store submission packages the whole thing with screenshots, metadata, privacy labels, and review-guidelines compliance.

The business case is straightforward: StealthGPT validates $195K MRR at the same price point. Bubls undercuts on price ($4.99 vs $15/mo), bundles three features where competitors sell one, and adds voice as the hook that earns the App Store feature slot. Revenue starts flowing the day the listing goes live.

## Related Documents

- [Analysis](./analysis.md)
- [Bubls UX Revamp Epic](../bubls-ux-revamp-1776370239783/epic.md)
- [Spec Route + Chain Primitive Epic](../bubls-epic2-1776348740618/epic.md)

