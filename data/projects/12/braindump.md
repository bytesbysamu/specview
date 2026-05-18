# Braindump: financing-plugin

## What it is

A Claude Code plugin for WinCredit 3 — a Swiss bank mortgage/financing platform. Extends the `superpowers` plugin with WinCredit-specific convention enforcement, domain agents, dev-tools skills, and ADO (Azure DevOps) integration. The plugin is a configuration and prompt artifact, not a runtime application: markdown files, YAML frontmatter, a Node.js SessionStart hook, and a JSON MCP server config. Ported structurally from `txs-momo` (a .NET/MoMo reference plugin) with every body rewritten for Java 21 + Spring Boot 3 + Gradle + Angular 20 + Flyway + MapStruct.

Target codebase: three independent git roots — `financing-backend` (`/dev/financing2/financing-backend`), `financing-frontend-desk` (`/dev/financing/financing-frontend-desk`), `financing-frontend-admin` (`/dev/financing/financing-frontend-admin`).

## The problem it solves

The financing team has no AI-assisted dev workflow and no ArchUnit-equivalent convention gate. Hexagonal adapter layering, MapStruct categories, jspecify nullability, Flyway naming, "no `@Data`/no field injection" — all enforced only at PR review. When reviewers are busy, violations land in master. The plugin makes Claude Code the enforcement layer: `dev-review` (7 parallel agents) runs the same convention checks on every PR, `feature-pipeline` produces ADO artifacts in the same shape every time, and agents replace "remember to check X" with "the agent already checked X." The plugin extends `superpowers` for cognitive work (brainstorming, writing-plans, executing-plans, TDD, systematic-debugging) and contributes only WinCredit-specific glue.

## Current state

Plugin is extracted and live at `/Users/sam/Projects/financing-plugin-extracted/`. Full spec documentation (analysis, epic, architecture, task-1, task-2) is in `docs/`. The plugin shell is authored: plugin.json, .mcp.json (ADO org basenetch), four reference files (`module-context.md`, `spring-conventions.md`, `angular-conventions.md`, `flyway-conventions.md`), `hooks/session-start.mjs` (the module-context detector across three git roots), three domain agents (`fin-backend`, `fin-frontend`, `fin-test-developer`), and a SKILL_MAP. Skills are scaffolded in `skills/` but individual SKILL.md files may still need authoring per tasks 3–4.

## Key decisions made

- **Plugin extends, never duplicates `superpowers`** — brainstorming, writing-plans, executing-plans, TDD, systematic-debugging live upstream. The plugin is zero re-implementation of those.
- **References are source of truth** — convention text lives once in `references/*.md`. Agents and `dev-review` read from there; skills do not re-state rules inline. A rule change is a one-file edit.
- **Three domain agents in v1** — `fin-backend`, `fin-frontend`, `fin-test-developer` (RED-phase only, explicit handoff to `superpowers:test-driven-development` for GREEN/REFACTOR). `fin-integration` and `fin-ui-reviewer` deferred.
- **Module-context detection via SessionStart hook** — Node.js ESM, no dependencies, cross-platform. Walks up to `.git`, matches against known-roots table, then resolves Gradle module (via `settings.gradle` parse) or Angular feature (via `angular.json` + feature folder). Fallback: "ask the user" — never silent wrong guess.
- **H2-boot binary gate in `dev-migration`** — Spring Boot context loads on H2 with new migration applied = pass. No schema-diff comparison in v1.
- **`dev-test` detection strategy** — Gradle source set (test vs. integrationTest) + Spring profile (`@ActiveProfiles("h2")`). One strategy, picked and shipped; not all candidates.
- **ADO MCP server pinned to `basenetch`** — single concrete config, no multi-org abstraction. One org, no abstraction of one case.
- **No auto-complete in `feature-review`** — PR opens; merge stays manual until reviewers trust the gate.
- **Frontend-admin deferred** — module-context detection is wired for three roots but no admin-specific conventions or pilot until a real admin ticket arrives.
- **Skills and agent body in German, frontmatter in English** — per principles.md localization rule.

## Open questions

- **Cross-plugin invocation pattern** — `feature-pipeline` calling `superpowers/brainstorming` etc. needs to be verified end-to-end before scaling skill count (Task 4's explicit gate). If the invocation breaks, the entire feature-lifecycle layer is dead.
- **NgModule vs standalone detection** — `fin-frontend` acknowledges both (~188 legacy NgModule, ~13 and growing standalone). Does scaffolding default to standalone, NgModule, or detect-from-feature-folder? Currently documents both but the scaffold path isn't pinned.
- **`dev-review` 7-agent fan-out** — the three domain agents plus four `superpowers`-supplied generic reviewers. The four generic reviewer identities need to be named concretely before Task 3 ships `dev-review`.
- **Pilot ticket selection** — Task 5 requires one real backend ticket and one real frontend-desk ticket. No tickets have been selected yet.

## Next steps

- Task 3: Author the four dev-tools skills (`dev-build`, `dev-test`, `dev-migration`, `dev-review`). Can be authored in parallel with agents since they're independent files.
- Task 4: Author the five feature-lifecycle skills (`feature-pipeline`, `feature-requirement`, `feature-prd`, `feature-review`, `bug-fix`). Verify cross-plugin superpowers invocation end-to-end before scaling.
- Task 5: Identify one real backend and one real frontend-desk ticket. Run full ticket-to-PR loop. Tune references and agents from findings — do not add new skills based on pilot gaps (those become follow-up epics).
- Install plugin into the WinCredit-3 workspace: `plugin install financing-plugin` (requires `superpowers` already installed).
- Bump version in `plugin.json` and `SKILL_MAP.md` after each feature change.
