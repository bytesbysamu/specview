# 6month-plan — Braindump

## What it is

A structured learning and portfolio project built around a real enterprise codebase: ELA, a multi-tenant financial advisory platform for Swiss banks (built by K&W Software AG). The 6month-plan project is a Next.js app that hosts documentation, lessons, and learnings extracted from deep codebase exploration sessions. The goal is skills acceleration — understanding production-grade Spring Boot, Angular, testing, and design patterns through analysis of a 32-module, 4-server, 38-frontend-subproject enterprise system.

## Problem it solves

Sam needed a structured way to extract and retain knowledge from working inside a complex enterprise codebase. Rather than passive observation, the approach is active documentation: explore a system thoroughly, write up architectural decisions, patterns, and testing strategies, then reference those learnings when building his own projects. The 6month-plan repo is the artifact of that process.

## Current state

- Three lessons written (as of April 2026):
  - Lesson 01 (2026-03-31): Spring Boot architecture deep dive — 32-module structure, onion architecture per module, ArchUnit enforcement, Flyway orchestration, Keycloak/IAM dual-token auth, MapStruct, QueryDSL, Caffeine caching, Hibernate Envers, async task framework, OpenAPI-first design.
  - Lesson 02 (2026-04-01 + 04-07): Testing strategy — Mockito patterns, @SpringBootTest with modular configs, H2 in-memory (MODE=Oracle), approval tests, shallow-render vs TestBed, Cypress + Cucumber BDD with API-based login, page objects, MockWebServer for external services.
  - Lesson 03 (2026-04-15): Design patterns — 30 GoF/Spring/DDD patterns with concrete code examples from the ELA codebase. Builder, Factory, Strategy, Template Method, Observer, Adapter, Decorator, Facade, Proxy, Composite, Bridge, Registry, Null Object, Chain of Responsibility, Aggregate Root, Value Object, Domain Events, Bounded Context, Anti-Corruption Layer.
- The Next.js app itself is a viewer/documentation surface — the CLAUDE.md defers to AGENTS.md for agent behavior, and AGENTS.md references Next.js breaking changes in node_modules/next/dist/docs.
- No tests in the Next.js app; no CI/CD described for the documentation site itself.

## Key decisions already made

- Document learnings by exploration, not by theory — every pattern has a named class or file from the real codebase.
- Organize by lesson, not by topic — each lesson is a complete session artifact.
- 28 development rules extracted from ELA as a canonical reference (Rule 17: no "should" in test names; Rule 18: arrange/act/assert; Rule 19: page objects with data-test selectors; Rule 24: never run the server yourself; Rule 28: never commit).
- Next.js as the documentation platform — not a production app, just a viewer.
- The learnings directly inform the super app architecture (bounded contexts, constructor injection via inject(), signals, data-test selectors, no field injection, explicit caching).

## Open questions

- What are Lessons 04-N? The 6-month plan implies ongoing learning; only 3 lessons exist.
- Is there a target completion date or a specific set of topics to cover?
- Should the learnings be integrated into spec-doc as a reference library, or kept standalone?
- Does the Next.js viewer need any real features (search, navigation, linking) or is it just markdown rendering?

## Next steps

- Write Lesson 04+ (likely: advanced frontend patterns, CI/CD patterns, or multi-tenancy strategies).
- Cross-reference learnings with active projects — especially the super app architecture doc which explicitly cites ELA patterns.
- Consider migrating or linking key architectural decisions into spec-doc for reuse across project architectures.
