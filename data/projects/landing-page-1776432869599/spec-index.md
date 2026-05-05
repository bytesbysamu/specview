---
sidebar_position: 0
---

# 📋 Bubls Landing Page

> Distribution prerequisite — a single-page destination so every post, tweet, and share has a URL.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [🎯 Epic](./epic.md) | Scope, tasks, success criteria |
| [🏗️ Architecture](./architecture.md) | Technical design |
| [📅 Timeline](./timeline.md) | Status tracking |

## Overview

Bubls is live on TestFlight but has no public web presence. Every distribution experiment — Reddit posts, Twitter threads, DMs, QR codes — needs a URL to land on. Without one, traffic has nowhere to go and there's no way to capture interest from people who aren't ready to install yet.

This capability ships a single static HTML page: hero section with a one-liner, three feature screenshots from the TestFlight build (photoshoot result, text rewrite, onboarding), a TestFlight link, and an email capture form backed by a Neon Postgres table. Hosted on the existing Trendfy VPS via Coolify. No framework, no build step, no CMS — one HTML file, one Flask endpoint, deployed in a day.

The landing page is not a marketing site. It's the minimum viable destination: enough to make a link worth clicking, enough to capture emails from people who want to follow along, enough to get the TestFlight link in front of anyone who lands on the page.

## Related Documents

- [Analysis](./analysis.md)

