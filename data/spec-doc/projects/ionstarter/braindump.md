# ionstarter — Braindump

## What it is

ionstarter is a commercial Ionic starter kit sold as a product at ionstarter.dev. It provides a pre-built Angular + Ionic + Capacitor scaffold with SQLite local storage so developers can ship mobile apps faster. It is Sam's primary reusable app template — the same scaffold underlies Bubls, howDays, and the super app. The product includes documentation at docs.ionstarter.dev.

## Problem it solves

Starting an Ionic + Angular + Capacitor app from scratch requires wiring SQLite, themes, live updates, splash screen, Capacitor plugins, and build pipelines — all before writing a single line of product code. ionstarter collapses this into a single installable template. The value prop is time-to-first-feature, not time-to-hello-world.

## Current state

- Version 2.1.3 (released October 2024). Stable and released.
- Stack: Angular + Ionic Framework 8 + Capacitor 6 + SQLite (jeep-sqlite).
- Features shipped: live updates (Appflow or self-hosted), splash screen, dark mode via ion-palette-dark class, SQLite local persistence, Ionic 8 component set.
- Bug fixes in recent versions: null check in core, task query disable-on-delete race condition, SQLite upgrade statement excluded on web.
- Breaking change at v2.0.0: Capacitor 6 migration.
- No AI integration in the starter itself — that's left to the consuming project.
- Documentation site exists (Docusaurus-based, separate repo under springular1/docs/).
- CI/CD is not described in the starter's own docs — the consuming project handles that.

## Key decisions already made

- Angular + Ionic + Capacitor (not React Native, not Flutter): consistent with Sam's skillset and preferred stack across all projects.
- SQLite local-first: data lives on device; backend integration is the consuming project's responsibility.
- jeep-sqlite as the Capacitor SQLite plugin: well-maintained, handles web fallback.
- Ionic 8: latest Ionic major version at time of last release.
- Capacitor 6: current major at time of last release.
- Live updates via Ionic's Appflow-compatible mechanism — allows OTA updates without App Store review.
- Versioned via commit-and-tag-version with conventional commits.

## Open questions

- Is ionstarter actively maintained as a commercial product, or has it become internal tooling?
- Does the starter need to be updated to Capacitor 7/8 (used in Bubls and the super app)?
- Should ionstarter incorporate auth scaffolding (magic link, Supabase) given that every consuming project needs it?
- Is there a roadmap for a React version or is Angular the permanent bet?
- How does the documentation site get deployed and kept in sync with releases?

## Next steps

- Evaluate Capacitor 6 → 8 upgrade path (Bubls already runs Capacitor 8; ionstarter is behind).
- Consider adding shared auth scaffolding (magic link pattern) as a starter feature.
- Sync documentation site with v2.1.3 release notes.
- Assess whether a new major version is warranted to align with the super app shell's conventions (signals, OnPush, standalone components).
