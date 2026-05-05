---
sidebar_position: 0
---

# 📋 Distribution Experiment — 100 Strangers

> Ship the product to strangers, measure if anyone comes back.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [🎯 Epic](./epic.md) | Scope, tasks, success criteria |
| [🏗️ Architecture](./architecture.md) | Technical design |
| [📅 Timeline](./timeline.md) | Status tracking |

## Overview

Bubls is shipped — 6 epics, 3 AI features, TestFlight live, pipeline shipping features in hours. The only remaining unknown is whether strangers want what exists. Every day spent improving without testing demand repeats the v1 pattern: great backend, no users.

This capability runs one controlled experiment. One channel (Reddit), one post, one week. The funnel is: impression → landing page → TestFlight signup → app open → day-7 return. The only metric that matters is unprompted return by day 7. Greater than 5% return rate is signal to continue. Zero returns is signal to kill or pivot. There is no ambiguity after day 7.

The technical surface is small: a landing page that funnels to TestFlight, event tracking in Neon Postgres to measure each funnel stage, and a query to read the verdict. Everything else — the post, the channel selection, the analysis — is manual and intentional. This is a demand experiment, not a growth system.

## Related Documents

- [Analysis](./analysis.md)

