The architecture document is ready. Here's what it covers:

**6 sections, all design decisions traced to references.md or principles.md:**

| Section | Key Content |
|---------|-------------|
| **Architecture Overview** | Port not rewrite. Filesystem-backed REST API. Chain module deferred — zero Phase 1 consumers. |
| **Design Principles** | 5 principles: port don't invent, contract compatibility, ship the car, module registry as extension point, filesystem is the database |
| **System Boundaries** | 5 included (app factory, project CRUD, context files, walker, integration verification), 7 excluded with trigger conditions |
| **Component Design** | 4 components, each with named consumers from the epic. Walker placed in `core/` because it has two named consumers (project list + Phase 2 scan). Context files use flat I/O, not manifest loader (analysis identified these as separate concerns). |
| **Design Decisions** | 6 decisions with trade-offs: chain deferral, env var naming (`CHAIN_PROVIDER` canonical / `AI_PROVIDER` alias), flat files vs manifest, integration verification as explicit task, backend coexistence strategy |
| **Execution Flow** | Task 1 → Tasks 2+3 parallel → Task 4 gate. Phase 2 adds modules without modifying Phase 1 code. |

No code blocks. No status words. Cross-references to Analysis and Epic are bidirectional. Would you like to grant write permission, or should I output the full markdown?