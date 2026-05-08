# Specview — Open Source Release

## The question to answer first

Should specview be open source? This isn't obvious. Most successful developer tools go one of three ways: (1) fully proprietary SaaS, (2) open source with a hosted SaaS on top ("open core"), or (3) fully open source with no commercial product. Each has different distribution economics.

The case for open source: GitHub stars are social proof. Developers trust tools they can inspect. An open source repo gets indexed by search engines in a way that a landing page alone does not. Community issues become free product research. Contributors occasionally fix bugs you haven't noticed.

The case against: you're essentially publishing the prompt engineering and the chain architecture that makes the product work. A competitor can fork it and host a rival SaaS. Open sourcing also creates a support obligation — people file issues expecting responses. The maintenance burden on a solo project is real.

The case for open-core specifically: open source the infrastructure (Flask API, Angular frontend, Docker setup) while keeping the prompts and chain configuration proprietary. But that's architecturally awkward here — the AI chain is deeply woven into the codebase. A partial open source release that excludes the prompts would be less useful to self-hosters and confusing as a story.

My instinct is that open source with AGPL licensing is the right call for specview at this stage. Here's why.

## Why AGPL makes sense

AGPL (GNU Affero General Public License) requires anyone who modifies and runs the software as a network service to release their modifications under AGPL. In practice, this means: a competitor who forks specview and runs it as a SaaS must open source their fork. Self-hosters who modify it for internal use must share those modifications.

This creates the right asymmetry. Solo developers running their own instance can use it freely. Tinkerers can contribute. But anyone building a commercial product on top of the specview codebase owes the community their improvements. The hosted SaaS (app.specview.io) operated by me is explicitly exempted from AGPL by the copyright holder — which is me.

The alternative is MIT, which is cleaner and more permissive but offers no protection against someone building a funded competitor on the same codebase. Given that the product's moat is prompt quality and chain architecture, I'm not sure I want to give that away for free.

## What the repo needs before a public release

The repo currently works but is not in a state that makes a good first impression to a stranger:

### README.md needs to be written for outsiders

The current CLAUDE.md is a developer guide for me. A public README needs: what is specview, who is it for, what does it produce, a screenshot of the output, prerequisites (Docker, Anthropic CLI key), 5-minute quickstart, architecture overview, and how to contribute.

The "0 human code lines" story should be in the README. It's the most interesting thing about the project and it immediately demonstrates the product's capability. The fact that specview's own specs are in data/projects/ is worth highlighting — a self-referential proof.

### CONTRIBUTING.md

Even if no contributors ever come, this file signals that external contributions are welcome and that there's a process. At minimum it should explain: how to run locally, how to run tests, what kinds of contributions are welcome (bug fixes yes, giant new features no), and how to get a PR reviewed.

### LICENSE

Add the AGPL-3.0-only license file to the repo root. This is a one-line addition but it has legal weight.

### .env.example

The `.env.local` file contains real credentials and is gitignored. There should be a `.env.example` with placeholders for all required environment variables: `ANTHROPIC_API_KEY`, `DATABASE_URL`, `JWT_SECRET`, `STRIPE_SECRET_KEY`, etc. This is the most common friction point for first-time self-hosters.

### Sanitize history

Before making the repo public, check the git history for accidentally committed secrets. A single leaked API key in git history is a security problem even if it's been rotated. Use `git log --all -S "key_pattern"` or a tool like truffleHog to scan. This is non-negotiable before a public push.

### data/projects/ — include or exclude?

The project data directory contains 36+ generated projects. Some of these are specview's own design documents (architecture.md, epic.md for specview itself). Including them is a powerful demo — it shows exactly what the tool produces. But some may contain personal project ideas that shouldn't be public.

The right call: include only the specview-internal projects (phases 1-4, saas, landing, plugin). Gitignore personal/client projects or exclude them from the public repo via `.gitignore` patterns.

## The self-referential story as the launch narrative

The most compelling thing about specview as an open source project is that its own development was planned using the tool. The data/projects/ directory includes:

- Phase 1 bootstrap spec
- Phase 2 thin API spec
- Phase 3 execution spec
- Phase 4 quality spec
- SaaS monetisation spec
- Landing page spec
- Plugin spec

Every architectural decision in the current codebase came from a spec generated by specview. This is a live proof of concept. No other open source project I know of has this property.

The README should surface this directly. "Specview was designed using Specview. Every phase's architecture, timeline, and implementation guide was generated by the tool itself. The data/projects/ directory is the design history of the product."

This narrative works particularly well on HN, where people care about authenticity and technical depth. It also serves as documentation of the product's capabilities — the generated specs are better demos than any screenshot.

## Docs site

A GitHub-hosted docs site (GitHub Pages or a simple README-linked directory) covers:

- Quickstart (5 minutes, Docker Compose)
- Environment variables reference
- Architecture overview (the chain, the skill system, how providers work)
- How to add a new skill
- API reference (link to openapi.yaml)
- FAQ: why AGPL? why CLI-only in Docker? why signals over RxJS?

The docs don't need to be elaborate. A single well-organized `docs/` directory in the repo root with a few markdown files is enough. Don't build a dedicated docs site (Docusaurus, GitBook, etc.) until there's evidence that people are actually using the project.

## GitHub-specific setup

- **Topics/tags**: `spec-generator`, `ai-tools`, `flask`, `angular`, `docker`, `claude`, `self-hosted`, `developer-tools`
- **About description**: "Self-hosted AI spec generator. Paste a braindump, get analysis + epic + architecture + timeline + implementation guide."
- **Social preview image**: Screenshot of the five-document output with specview branding
- **GitHub Actions**: CI already exists (or needs to be set up) to run `pytest` on PRs. This is the minimum gate for community contributions.
- **Issues templates**: Bug report template, feature request template. Both should ask for the specview version and CHAIN_PROVIDER setting.

## What an open source release does for distribution

A public repo changes the SEO profile of the project significantly. GitHub is indexed by search engines and has domain authority. When someone searches "AI spec generator self-hosted", a GitHub repo with good README copy will rank where a landing page alone might not.

Stars are social proof. A repo that reaches 100 stars gets listed in GitHub trending. 500 stars gets it referenced in newsletters. 1000+ stars is a distribution event in itself. This is speculative, but the flywheel is real for developer tools.

Issues and discussions become a feedback channel that operates asynchronously. Someone who finds a bug at 2am can file an issue without needing to email. This is lower friction than any other feedback mechanism.

The fork graph is also a distribution signal. When developers fork a project to deploy their own instance, GitHub shows that as public activity.

## Risks and mitigations

**Prompt engineering gets copied**: Anyone can read the chain prompts and replicate them. Mitigation: the prompts are designed for a specific skill-based execution model. The system as a whole (skill runner + chain adapter + Flask API + Angular frontend) is a substantial build even if the prompts are copied. The moat is the complete system, not any single prompt.

**Support burden**: Public issues require responses. Mitigation: set clear expectations in CONTRIBUTING.md that this is a solo-maintained project, issues get triaged weekly, and not all issues will be fixed. A "good first issue" label on small bugs invites community help without creating an obligation.

**AGPL misunderstood**: Developers sometimes panic when they see AGPL. Mitigation: add a clear FAQ section to the README: "If you're self-hosting for your own use, you can use and modify specview freely. AGPL only requires sharing modifications if you run it as a network service for others."

**Security**: Running specview requires an Anthropic API key, a database, and a JWT secret. Make sure the Docker setup doesn't accidentally expose these. The docker-compose.yml should use env files, not hardcoded values, in the public repo.

## Timing

An open source release should happen after the SaaS launch, not before. The sequence is:
1. Wire Stripe, enforce usage limits, harden reliability (Phase 4 + saas-monetisation)
2. Do the SaaS launch (Show HN, Reddit)
3. After the SaaS launch, do an open source release as a follow-up event

This gives the SaaS its own moment. If the open source release happens first, the Show HN for the SaaS competes with "it's already free on GitHub." The narrative is cleaner if the SaaS launch is about the product and the OSS release is about the architecture and self-hosting.

## Open questions

Which specific projects from data/projects/ should be included in the public repo? All specview-internal ones? Only phases 1-4? Everything non-personal?

Should the CLAUDE.md (which reveals a lot about the development workflow, agent routing, and skill system) be included in the public repo? It's interesting to developers but also exposes all the conventions and constraints of how the project is built.

Should the plugin/ directory be included? The Claude Code plugin system is genuinely novel. Sharing it openly could seed a community of people building similar plugins for their own projects. But it requires a working Claude Code setup to use, which limits the audience.

Is there a universe where specview becomes a community-maintained project with multiple contributors? Or is it fundamentally a solo tool that I'm open-sourcing for distribution, not for collaboration? The answer shapes how much effort to put into onboarding contributors vs. just making it easy to self-host.
