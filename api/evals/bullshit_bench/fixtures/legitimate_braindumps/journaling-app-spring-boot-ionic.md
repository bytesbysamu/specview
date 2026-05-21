# howDays — Braindump

## What it is

howDays is a personal journaling mobile app built with Ionic + Angular + SQLite (local-first), backed by a Spring Boot API. The app lets users log mood scores and journal entries, then receive AI-generated prompts tailored to their mood. The backend is a standard Spring Boot + Postgres stack ("Springular1") designed for Docker deployment.

## Problem it solves

Generic journaling apps serve static prompts. howDays uses mood context and journal entry content to generate dynamic, personalized reflection prompts — support-focused for low mood, insight/growth-focused for high mood. The AI layer sits behind a Spring Boot intermediary so the frontend never holds AI credentials.

## Current state

- Frontend (angular-sqlite-starter v2.1.3, Oct 2024): functional Ionic/Angular app with local SQLite storage, dark-mode theming, live updates, splash screen, Ionic 8, Capacitor 6. The task/journal scaffold is in place.
- Backend integration plan (API_INTEGRATION_PLAN.md): fully specced — AIApiService, PromptsService, PromptFlowService — with fallback to static prompts when AI is unavailable. Architecture is written; implementation is in progress.
- Spring Boot backend (springular1): the standard Springular boilerplate is present with JWT auth, Stripe, SendGrid, Google OAuth wired. Production deployment guide exists — Docker Compose + nginx + Postgres + Coolify-style deployment. CI/CD with GitHub Actions (compile, checkstyle, unit tests, build, Docker Compose, Coolify deploy toggle).
- AI backend (BACKEND_REQUIREMENTS.md): fully specced Spring Boot service — PromptController with /api/health, /api/prompts/generate, /api/prompts/generate-batch. Multi-provider AI abstraction (OpenAI, Ollama). Not yet implemented — the spec exists as a planning document.

## Key decisions already made

- Ionic + Angular + SQLite (local-first): entries live on device, backend is for AI prompts only, not primary storage.
- Spring Boot as AI proxy: abstracts AI providers, handles rate limiting, keeps keys server-side.
- Multi-provider abstraction: AIProvider interface supports OpenAI and Ollama interchangeably.
- Fallback strategy: if AI is unavailable, static mood-based prompts serve instead — app never breaks.
- Springular1 as the backend base: reuses established boilerplate with JWT, Stripe, Google OAuth already wired.
- Docker + Coolify for deployment: same pattern as other projects in Sam's portfolio.

## Open questions

- Which AI provider to use for production (OpenAI vs Ollama — cost vs control tradeoff)?
- Is the Spring Boot AI service a separate microservice or merged into springular1?
- Caching strategy for AI prompts (reduce API cost on repeated mood/context combos)?
- Whether to expose user history to the AI for prompt personalization over time.
- Monetization model — free tier with limited AI prompts, paid for unlimited?

## Next steps

1. Implement the Spring Boot AI service endpoints (Phase 1: health + single prompt generation + basic OpenAI integration).
2. Test end-to-end: Angular app → Spring Boot → AI provider → prompt returned.
3. Wire the AI toggle UI in the Angular app (user can disable AI, falls back to static).
4. Implement batch prompt generation (Phase 2).
5. Add prompt caching to reduce AI costs.
6. Production deploy: Docker Compose with prod env vars, Coolify webhook.
