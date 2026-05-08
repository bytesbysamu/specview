# Claude Code Guide – Braindump

## What It Is

A Docusaurus-based course site teaching Claude Code (Anthropic's terminal AI coding tool), built using Claude Code itself. The self-referential hook is the point: the course was created in a single session on 2026-01-24 using Claude Opus 4.5, demonstrating every technique it teaches. Hosted as a static doc site with a coral-themed landing page and interactive terminal demos.

## Problem It Solves

Claude Code is more than a chatbot with file access — it has specific tools, patterns, and mental models that dramatically change effectiveness. Most users don't know about parallel tool execution, sub-agents, `ultrathink` triggers, CLAUDE.md conventions, or how to break tasks by size. This course packages that knowledge in a structured, browsable reference.

## Content Structure

Five core modules: (1) Basics — installation, session management, CLAUDE.md, built-in slash commands; (2) Tools and Capabilities — Read/Write/Edit/Bash/Glob/Grep/WebSearch/Task agents, tool selection heuristics; (3) Best Practices — specificity, context, incremental iteration, task-size-matched prompt patterns; (4) Tips and Tricks — hidden superpowers (image/PDF/notebook reading, background tasks, web search, smart git commits/PRs); (5) Prompts Reference — copy-paste prompt library organized by task type. Supporting reference docs: Cheat Sheet, CLAUDE.md Templates (5 stack presets), Custom Slash Commands collection, Meta-Story.

## Current State

Site is built and the terminal demo plan (PLAN-terminal-demos.md) is marked complete. Navigation cleanup done (3 items: Brand | Course | GitHub, coral styling). `SimpleTerminalDemo` component created with typewriter/click-to-play animation. Eleven demos added across four docs (basics, tools, best practices, tips). Site builds without errors. Live API (`TryItLive` component) calls `https://api.bytesbysamu.cloud/api/ai/text/generate` — the Speedback/Springular backend — for real Claude responses. Two open follow-up items: mobile navbar testing and accessibility improvements (aria-live, keyboard nav, focus management).

## Key Decisions

- **Docusaurus** — static site, sidebar-driven nav, MDX support for embedding React components
- **SimpleTerminalDemo** vs **TryItLive** — pre-scripted demos (no API) for reliability; live demos for real interaction, backed by the existing Springular backend
- **Built-by-Claude framing** — the meta-story (Claude Code building a Claude Code course) is the primary credibility signal and marketing hook
- **Coral/orange theme** — matches the broader 2026 product aesthetic; carried through navbar, gradients, terminal styling
- **CLAUDE.md Templates** as reference content — practical, immediately usable, covers Flask+Angular, Next.js, Python CLI, React Native, and a minimal starter

## Open Questions

- Distribution plan: where does this site live and how does it get traffic?
- Relationship to the broader product portfolio — is this a standalone product, a lead-gen asset, or documentation for a paid course?
- Whether to extract shared terminal styles into a single CSS file (currently duplicated between landing page and component module)
- Accessibility improvements are listed as follow-up but unscheduled

## Next Steps

1. Manual mobile testing of navbar and terminal demos
2. Accessibility pass: `tabIndex`, `aria-live`, focus management on demo components
3. Decide distribution channel and deploy target
4. Optional: CSS consolidation for terminal styles
5. Optional: upgrade logo from emoji (🎓) to custom SVG
