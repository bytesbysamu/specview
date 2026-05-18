---
name: Spec-doc pipeline
description: How to run spec-gen end-to-end — call spec-doc server, parse output, write files, push to sidebar. Always atomic.
type: reference
originSessionId: bceb2169-d048-4238-ac89-4934b0936057
---
## Spec-gen workflow (atomic — always do ALL steps)

When user says "run spec doc", "generate epic", or "spec gen" on a braindump:

### Step 1: Start spec-doc server (if not running)
```bash
cd /projects/2026/spec-doc && node server.js &
```
Server runs on `localhost:3100`. AI provider: `cli` (uses `claude -p`).

### Step 2: Call generate-spec endpoint
```js
// Node.js — no jq/python available in container
const body = JSON.stringify({ input: braindumpContent });
POST http://localhost:3100/api/ai/text/generate-spec
// Returns: { text: "===FILE: ...===\n...", latencyMs: N }
```

### Step 3: Parse ===FILE: markers and write to projects/
```js
const fileRegex = /===FILE:\s*(.+?)===\n([\s\S]*?)(?=\n===FILE:|\n===END===|$)/g;
// Write each file to /workspace/projects/{name}/
// Also write project.json: { "name": "...", "createdAt": "YYYY-MM-DD" }
```

### Step 4: Push to spec-doc sidebar (ALWAYS — never skip)
```js
POST http://localhost:3100/api/projects
{ name: "Project Name", files: [{ filename: "spec-index.md", content: "..." }, ...] }
// Returns 201 with project ID
```

**5 output files**: spec-index.md, analysis.md, epic.md, architecture.md, timeline.md

**Key**: No Python in this container. Use Node.js for all HTTP calls and file parsing. Spec-doc lives at `/projects/2026/spec-doc/`.

**How to apply:** Every spec-gen MUST end with the sidebar push. The user expects to see results in the spec-doc UI immediately. This is one atomic operation, not two separate steps.
