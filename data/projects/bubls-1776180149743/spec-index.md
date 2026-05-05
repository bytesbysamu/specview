---
sidebar_position: 0
---

# 📋 Bubls — AI-Curated Weekend Event Discovery

> 5 AI-picked events, delivered every Thursday — so you stop scrolling and start going out.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [🎯 Epic](./epic.md) | Scope, tasks, success criteria |
| [🏗️ Architecture](./architecture.md) | Technical design |
| [📅 Timeline](./timeline.md) | Status tracking |

## Overview

Bubls is a weekly event discovery service that answers one question: "What should I do this weekend?" Subscribers sign up with their city (Zürich for v1) and up to 3 interests. Every Thursday at 6pm, they receive 5 AI-curated event picks via email and on a personal dashboard. No browsing, no searching, no app to install. Just 5 things worth doing, picked by Claude based on your preferences.

Event discovery has been broken for over a decade. Eventbrite shows 400 results. Google scatters you across 6 sites. Instagram stories disappear. The winning companies — Fever ($1.8B), Partiful (500K MAU), Luma — all sidestepped aggregation entirely. Nobody has cracked the "just tell me what's good" problem for general-purpose local events. Bubls bets that AI curation plus weekly push delivery is the missing piece: match the natural "what are we doing this weekend?" cadence instead of forcing a daily-use app on a once-a-week behavior.

The product is deliberately minimal. Two surfaces (email + dashboard), two database tables (subscribers + picks), zero user accounts, zero search functionality. A Python worker pulls events from Ticketmaster and Eventbrite APIs every Thursday, sends them through Claude for ranking and summarization, and pushes the results out via Resend. The entire system is designed to be built and launched in under a week, validating demand before investing in infrastructure. The bet: if 200 people in Zürich look forward to the Thursday email, something real is happening.

## Related Documents

- [Analysis](./analysis.md)