---
name: always use plugin agents and skills
description: User wants every task routed through the plugin system — agents and skills, not direct Claude responses
type: feedback
---

Always use the plugin (agents/skills) for every request. Do not implement code directly — dispatch to the appropriate specialist agent or invoke a skill.

**Why:** Sam doesn't use the CLI directly. The plugin IS the interface. Every prompt Sam gives should be routed through the plugin — skills or agents. This validates the product and enforces conventions automatically.

**How to apply:**
- Code changes → dispatch to spec-backend, chain-agent, spec-frontend, or chain-developer agent
- Build/test checks → invoke /dev-build, /dev-test skills
- Reviews → invoke /dev-review skill
- Spec generation → invoke /spec-pipeline skill
- Guide generation → invoke /impl-guide skill
- Guide execution → invoke /exec-guide skill
- Never write code or run bash implementation commands directly in the main conversation
- Always use the Agent tool or Skill tool as the first action
