# Skill Map — chain-agent-plugin

Master index of all skills. 7 skills total: 4 dev-tools + 1 spec-pipeline + 1 impl-guide + 1 exec-guide.

**Plugin:** chain-agent-plugin v0.1.0

---

## Workflow Diagram

```
          Braindump / Spec update
                  |
       +----------v-----------+
       | spec-pipeline        |  (Orchestrator — braindump -> full spec set)
       | /spec-pipeline <id>  |
       +----------+-----------+
                  |
         bootstrap-project API
                  |
         (analysis -> epic -> architecture -> timeline)
```

```
     Code change / PR review
            |
   +--------v--------+
   | dev-review      |  (Fan-out — parallel review across 3 agents)
   | /dev-review     |
   +--+---+---+------+
      |   |   |
chain  flask  angular
agent  back   front
```

---

## Dev-Tools Skills (4)

| Skill | Command | Description | Allowed Tools |
|-------|---------|-------------|---------------|
| **dev-build** | `/dev-build` | pytest collect (backend) or ng build (frontend) | Bash, Read, Glob, Grep |
| **dev-test** | `/dev-test` | Run pytest or ng test, scoped to nearest module | Bash, Read, Glob, Grep |
| **dev-migrate** | `/dev-migrate <desc>` | Alembic scaffold + review gate + apply + verify | Bash, Read, Glob, Grep, Write, Edit |
| **dev-review** | `/dev-review` | 3-agent parallel review (chain + backend + frontend) | Bash, Read, Glob, Grep, Agent, AskUserQuestion |

---

## Spec Skills (2)

| Skill | Command | Description | Allowed Tools |
|-------|---------|-------------|---------------|
| **spec-pipeline** | `/spec-pipeline <id>` | Braindump → full spec set via bootstrap API | Bash, Read, Glob, Grep, WebFetch, AskUserQuestion |
| **impl-guide** | `/impl-guide <id>` | epic + architecture → single high-level guide, no code, fast | Bash, Read, Glob, Grep, Write |
| **exec-guide** | `/exec-guide <id> [task-N]` | Execute tasks from implementation-guide.md via specialist agents | Agent, Read, Glob, Grep, Bash |

---

## Domain Agents (4)

Invoked by dev-review and consulted during development.

| Agent | Focus | References |
|-------|-------|------------|
| **chain-agent** | Chain adapter, providers, prompt engineering, workflow steps | chain-conventions, flask-conventions |
| **spec-backend** | Flask blueprints, SQLModel models, Alembic migrations, services | flask-conventions, chain-conventions |
| **spec-frontend** | Angular signals, service pattern, templates, polling | angular-conventions |
| **chain-developer** | Cross-layer features, full-stack coordination | all three references |

---

## Quick Reference

```bash
# Dev tools
/dev-build                    # Build check (backend or frontend)
/dev-test                     # Run tests (module-scoped)
/dev-migrate add_tags_column  # Alembic migration scaffold + apply
/dev-review                   # 3-agent code review

# Spec pipeline
/spec-pipeline my-project     # braindump -> analysis -> epic -> arch -> timeline

# Implementation guide (high-level, no code)
/impl-guide my-project        # epic + architecture -> implementation-guide.md

# Execute the plan
/exec-guide my-project        # run all tasks in implementation-guide.md
/exec-guide my-project task-2 # run only Task 2
```
