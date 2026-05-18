---
name: Sam — user profile
description: Who Sam is, his active projects, tech stack, working style, and key preferences
type: user
originSessionId: 8a0ac2aa-6c05-45e1-b7cf-be16c6f8af0d
---
Sam Bedassa Alemu (sbedassa67@gmail.com, GitHub: bytesbysamu) is a solo technical founder based in Zürich, Switzerland (Europe/Zurich). He builds AI-powered products fast using a documentation-first methodology he created called Spec Doc.

**Active projects (verified from Projects folder, May 2026):**
- **humaniz.me** — AI text humanizer. LIVE IN PRODUCTION. Flask + Next.js 15 + Supabase + Stripe. Fully shipped. Current revenue target.
- **Trendfy** (trendfy.me) — AI fashion photoshoot. Co-founder: Isabella (50/50, 4-year vest/1-year cliff). Pipeline: Claude Vision → remove-bg → IDM-VTON → ESRGAN/CodeFormer. Flux LoRA v3a (rank 16, all layers, 2000 steps). May 1 kill date passed — status unknown.
- **Bubls** — Ionic/Angular/Capacitor cross-platform mobile app, Zürich event discovery. Relationship check-in planned as /checkin route inside Bubls.
- **Constellation** — Sam's internal product factory platform, powers humaniz.me. Docusaurus docs, Claude Code slash commands.
- **Spec Doc** — documentation-first methodology: markdown → Claude Code in Docker → Bun WebSocket (port 3002) → Plate editor.

**Tech stack:**
- Frontend (web): Next.js 15 + TypeScript + Tailwind + shadcn/ui + @supabase/ssr
- Frontend (mobile): Angular + Ionic + Capacitor
- Backend: Flask (~150 lines thin layer); Supabase via Flask only
- AI: Claude API + Replicate (IDM-VTON $0.025/run, Flux LoRA, ESRGAN)
- Deploy: Docker Compose → Nginx → Coolify → Traefik, GitHub Actions

**CLAUDE.md rules:** named exports, one component per file, files <200 lines, one file at a time with build verification.

**Working style:** brain dump → AI structures → ship. Pushes back on over-engineering. Frontend with mock data first, then Flask to match the UI's API contract.

**Key preference:** When fixing his writing, correct only a few errors at a time — he wants to learn gradually, not have everything fixed at once.
