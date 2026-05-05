# 🛠️ Task 5: Deploy & CI/CD

**Purpose**: Configure Docker Compose deployment to Coolify with Traefik reverse proxy and automated GitHub Actions pipeline for continuous deployment.

**Effort**: 0.5 days

**Dependencies**: Tasks 1-4 (all services must be buildable)

**Parallel With**: —

**Blocks**: Production launch

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Docker Compose configuration for all services
- Traefik reverse proxy with SSL termination
- GitHub Actions CI/CD pipeline
- Coolify deployment configuration
- Subdomain routing (app., api., docs.)

### What's NOT Included
- Kubernetes/orchestration — overkill for MVP scale
- Blue-green deployments — add after validating traffic patterns
- Custom domain email — use external service (Resend, etc.)

---

## Prerequisites

Before starting:
- Coolify instance running and accessible
- Domain (trendfy.me) DNS pointing to Coolify server
- GitHub repository with push access
- Docker installed locally for testing

---

## Implementation Steps

### Step 1: Create Docker Compose Configuration

**File**: `docker-compose.yml`

**Purpose**: Define all services and their relationships for production deployment

```yaml
version: '3.8'

services:
  traefik:
    image: traefik:v3.0
    command:
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.letsencrypt.acme.email=${ACME_EMAIL}"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - letsencrypt:/letsencrypt
    networks:
      - web

  frontend:
    build: ./frontend
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=Host(`app.trendfy.me`)"
      - "traefik.http.routers.frontend.entrypoints=websecure"
      - "traefik.http.routers.frontend.tls.certresolver=letsencrypt"
    networks:
      - web
    depends_on:
      - api

  api:
    build: ./backend
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REPLICATE_API_TOKEN=${REPLICATE_API_TOKEN}
      - STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY}
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`api.trendfy.me`)"
      - "traefik.http.routers.api.entrypoints=websecure"
      - "traefik.http.routers.api.tls.certresolver=letsencrypt"
    networks:
      - web
      - internal

  landing:
    build: ./landing
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.landing.rule=Host(`trendfy.me`)"
      - "traefik.http.routers.landing.entrypoints=websecure"
      - "traefik.http.routers.landing.tls.certresolver=letsencrypt"
    networks:
      - web

volumes:
  letsencrypt:

networks:
  web:
    external: true
  internal:
```

### Step 2: Create Service Dockerfiles

**File**: `frontend/Dockerfile`

**Purpose**: Production build for Next.js frontend

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

**File**: `backend/Dockerfile`

**Purpose**: Production build for FastAPI backend

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Step 3: Configure GitHub Actions Pipeline

**File**: `.github/workflows/deploy.yml`

**Purpose**: Automated deployment on push to main branch

```yaml
name: Deploy to Coolify

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Deploy to Coolify
        run: |
          curl -X POST \
            -H "Authorization: Bearer ${{ secrets.COOLIFY_TOKEN }}" \
            -H "Content-Type: application/json" \
            "${{ secrets.COOLIFY_WEBHOOK_URL }}"
```

### Step 4: Configure Coolify

**Purpose**: Set up the deployment target in Coolify dashboard

1. **Create new project** in Coolify dashboard
2. **Add environment** (production)
3. **Connect GitHub repository** via OAuth
4. **Configure build settings**:
   - Build pack: Docker Compose
   - Docker Compose file: `docker-compose.yml`
5. **Set environment variables**:
   ```
   ACME_EMAIL=admin@trendfy.me
   DATABASE_URL=postgresql://...
   REPLICATE_API_TOKEN=r8_...
   STRIPE_SECRET_KEY=sk_live_...
   ```
6. **Generate webhook URL** and add to GitHub secrets

### Step 5: Configure DNS Records

**Purpose**: Point subdomains to Coolify server

Add these DNS records in your domain registrar:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | @ | `<COOLIFY_IP>` | 300 |
| A | app | `<COOLIFY_IP>` | 300 |
| A | api | `<COOLIFY_IP>` | 300 |
| A | docs | `<COOLIFY_IP>` | 300 |

### Step 6: Add HTTP to HTTPS Redirect

**File**: `docker-compose.yml` (update traefik service)

**Purpose**: Force all traffic to HTTPS

Add to traefik labels:

```yaml
traefik:
  # ... existing config ...
  labels:
    - "traefik.http.routers.http-catchall.rule=hostregexp(`{host:.+}`)"
    - "traefik.http.routers.http-catchall.entrypoints=web"
    - "traefik.http.routers.http-catchall.middlewares=redirect-to-https"
    - "traefik.http.middlewares.redirect-to-https.redirectscheme.scheme=https"
```

---

## Verification

Test locally before deploying:

```bash
# Create external network
docker network create web

# Test compose configuration
docker compose config

# Build all services
docker compose build

# Start stack locally (without SSL)
docker compose up -d

# Check all services are running
docker compose ps
```

**Expected Result**: All services show as "running" with correct port mappings.

Test production deployment:

```bash
# Push to trigger deployment
git push origin main

# Wait for Coolify webhook to complete (~2-3 min)

# Verify SSL certificates
curl -I https://trendfy.me
curl -I https://app.trendfy.me
curl -I https://api.trendfy.me
```

**Expected Result**: All endpoints return `HTTP/2 200` with valid SSL certificates.

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| SSL cert not issued | DNS not propagated | Wait 5-10 min, verify with `dig` |
| 502 Bad Gateway | Service not running | Check `docker compose logs <service>` |
| Webhook not triggering | Token expired | Regenerate in Coolify |

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 5 done
2. Verify all services accessible via production URLs
3. Run smoke tests against production endpoints

---

## Related Documents

- [Architecture](./architecture.md) – Subdomain structure rationale
- [Epic](./epic.md) – Task scope and success criteria
- [Timeline](./timeline.md) – Status tracking