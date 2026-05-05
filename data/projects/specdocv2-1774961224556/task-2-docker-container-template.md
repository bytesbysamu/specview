# 🛠️ Task 2: Docker Container Template

**Purpose**: Create a pre-configured Docker image with the full Next.js 15 + shadcn/ui stack that serves as the execution environment for Claude Code agents, enabling isolated per-user code generation and live preview.

**Effort**: 2 days

**Dependencies**: Task 1 (Plate Editor) — need editor to trigger container creation

**Parallel With**: Task 3 (Claude Code integration) — can develop agent wrapper while container builds

**Blocks**: Task 4 (Real-time streaming) — containers must exist before we can stream from them

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Dockerfile with Next.js 15 + dependencies pre-installed
- CLAUDE.md with coding patterns and constraints
- Container startup script that runs dev server
- Docker Compose configuration for local development
- Health check endpoint for container readiness

### What's NOT Included
- Container orchestration (Kubernetes/ECS) — that's infrastructure, not template
- Multi-container networking — single container per session for POC
- Persistent storage — containers are ephemeral in POC phase
- Production optimizations — dev mode only for live preview

---

## Prerequisites

Before starting:
- Docker Desktop installed and running
- Node.js 20+ (for testing outside container)
- Understanding of Next.js 15 App Router
- Familiarity with shadcn/ui component installation

---

## Implementation Steps

### Step 1: Create Base Dockerfile

**File**: `docker/Dockerfile`

**Purpose**: Define the container image with all dependencies pre-baked so agent sessions start instantly.

The image should have everything installed at build time. When a user session starts, we copy their generated code into a running container rather than installing dependencies each time.

**Pattern**:
```dockerfile
FROM node:20-alpine

WORKDIR /app

# Install dependencies for native modules
RUN apk add --no-cache libc6-compat

# Create Next.js 15 app with all dependencies
# Pre-install shadcn/ui, Tailwind, Supabase client
COPY package.json package-lock.json ./
RUN npm ci

# Copy base app structure (pages, components, configs)
COPY . .

# Generate Tailwind CSS and shadcn components at build
RUN npx shadcn@latest init -y

EXPOSE 3000

# Health check for orchestrator
HEALTHCHECK --interval=5s --timeout=3s \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/api/health || exit 1

CMD ["npm", "run", "dev"]
```

### Step 2: Create Base Next.js App Structure

**File**: `docker/app/`

**Purpose**: Provide the scaffolding that Claude Code agents will modify. This isn't a blank slate — it's a working app with conventions established.

Structure the app so agents know where to put things:

```
docker/app/
├── src/
│   ├── app/
│   │   ├── layout.tsx      # Root layout with providers
│   │   ├── page.tsx        # Home page (agent modifies)
│   │   └── api/
│   │       └── health/
│   │           └── route.ts # Health check endpoint
│   ├── components/
│   │   └── ui/             # shadcn components live here
│   └── lib/
│       ├── supabase/
│       │   └── client.ts   # Supabase browser client
│       └── utils.ts        # cn() helper
├── tailwind.config.ts
├── components.json         # shadcn config
└── package.json
```

**Pattern** for `package.json`:
```json
{
  "name": "spec-doc-sandbox",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "15.0.0",
    "react": "19.0.0",
    "react-dom": "19.0.0",
    "@supabase/supabase-js": "^2.45.0",
    "@supabase/ssr": "^0.5.0",
    "tailwindcss": "^3.4.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0"
  }
}
```

### Step 3: Create CLAUDE.md for Agent Guidance

**File**: `docker/app/CLAUDE.md`

**Purpose**: This file is read by Claude Code when it runs in the container. It establishes coding patterns and constraints so generated code is consistent.

**Pattern**:
```markdown
# Sandbox Environment

You are running inside a Spec Doc sandbox container.

## Stack
- Next.js 15 (App Router)
- React 19
- Tailwind CSS
- shadcn/ui components
- Supabase client (configure via env vars)

## Constraints
- Components go in `src/components/`
- Pages go in `src/app/`
- Use shadcn/ui for all UI elements
- Max 80 lines per component
- No external API calls without user approval

## Patterns

### Adding a shadcn component
```bash
npx shadcn@latest add button
```

### Creating a new page
File: `src/app/[route]/page.tsx`

### Using Supabase
```typescript
import { createClient } from '@/lib/supabase/client'
const supabase = createClient()
```

## What NOT to do
- Don't modify package.json
- Don't install new dependencies
- Don't create files outside src/
- Don't use `use server` (no server actions in sandbox)
```

### Step 4: Create Health Check Endpoint

**File**: `docker/app/src/app/api/health/route.ts`

**Purpose**: Allow the orchestrator to verify the container is ready before routing traffic to it.

**Pattern**:
```typescript
import { NextResponse } from 'next/server'

export async function GET() {
  return NextResponse.json({ 
    status: 'healthy',
    timestamp: Date.now()
  })
}
```

### Step 5: Create Docker Compose for Local Development

**File**: `docker/docker-compose.yml`

**Purpose**: Enable local testing of the container setup before integrating with the main app.

**Pattern**:
```yaml
version: '3.8'

services:
  sandbox:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    volumes:
      # Mount for live code injection during development
      - ./app/src:/app/src:delegated
    environment:
      - NODE_ENV=development
      - NEXT_PUBLIC_SUPABASE_URL=${SUPABASE_URL}
      - NEXT_PUBLIC_SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:3000/api/health"]
      interval: 5s
      timeout: 3s
      retries: 3
```

### Step 6: Create Container Management Utilities

**File**: `server/container-manager.ts`

**Purpose**: Provide functions the main server uses to create/destroy containers per user session.

**Pattern**:
```typescript
import { exec } from 'child_process'
import { promisify } from 'util'

const execAsync = promisify(exec)

interface ContainerInfo {
  id: string
  port: number
  status: 'starting' | 'ready' | 'error'
}

const containers = new Map<string, ContainerInfo>()

export async function createContainer(sessionId: string): Promise<ContainerInfo> {
  const port = await findAvailablePort()
  
  const { stdout } = await execAsync(
    `docker run -d -p ${port}:3000 --name sandbox-${sessionId} spec-doc-sandbox`
  )
  
  const containerId = stdout.trim()
  const info: ContainerInfo = { id: containerId, port, status: 'starting' }
  containers.set(sessionId, info)
  
  // Wait for health check
  await waitForHealthy(port)
  info.status = 'ready'
  
  return info
}

export async function destroyContainer(sessionId: string): Promise<void> {
  const info = containers.get(sessionId)
  if (!info) return
  
  await execAsync(`docker rm -f ${info.id}`)
  containers.delete(sessionId)
}

async function waitForHealthy(port: number, maxAttempts = 30): Promise<void> {
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const res = await fetch(`http://localhost:${port}/api/health`)
      if (res.ok) return
    } catch {}
    await new Promise(r => setTimeout(r, 1000))
  }
  throw new Error('Container failed to become healthy')
}
```

---

## Verification

How to verify this implementation works:

```bash
# Build the image
cd docker
docker build -t spec-doc-sandbox .

# Run a test container
docker run -d -p 3000:3000 --name test-sandbox spec-doc-sandbox

# Wait for startup (10-15 seconds for Next.js dev server)
sleep 15

# Check health endpoint
curl http://localhost:3000/api/health
# Expected: {"status":"healthy","timestamp":...}

# Check the app loads
curl -I http://localhost:3000
# Expected: HTTP/1.1 200 OK

# Cleanup
docker rm -f test-sandbox
```

**Expected Result**: 
- Container builds without errors (~2-3 min first build, cached after)
- Health endpoint returns 200 within 20 seconds of container start
- Next.js dev server accessible on mapped port
- Hot reload works when files are volume-mounted

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 2 done
2. Proceed to Task 3 (Claude Code integration) — wire up agent execution inside containers
3. Test container creation from the Plate editor sidebar

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale for container isolation
- [Epic](./epic.md) – Task scope and success criteria
- [Timeline](./timeline.md) – Status tracking