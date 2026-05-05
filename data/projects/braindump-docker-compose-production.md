# spec-doc — Docker Compose Production Stack

> **MERGED** into `braindump-saas-operations.md` on 2026-04-26 (one consolidated dump per bucket).
>
> Original kept for git history; do not generate a spec from this file.

---

> **Priority**: P5 — partly redundant with Epic 6 (Coolify Traefik handles SSL + routing).
> **Effort**: ~1 day for the nginx + certbot pieces if Coolify is replaced.
> **Blocks**: nothing — only relevant if you outgrow Coolify.
> **Depends on**: nothing.
> **Siblings**: Epic 6 (`api/docs/epic-6-devex-cicd/`) ships Coolify-deploy stack — read first;
>               most of this brain dump is now redundant.
> **Status**: Revisit when a concrete non-Coolify deploy target appears (e.g., self-hosted VPS).

## What

Define a production `docker-compose.yml` at the repo root that runs the full spec-doc stack: nginx reverse proxy, Flask API, and Angular static files. Same pattern as Trendfy and humanize-me. Replaces the current ad-hoc container startup with a reproducible, restartable, SSL-aware service definition.

The current production setup is unclear — the container runs Flask directly on port 3101 with no reverse proxy, no SSL termination, and no restart policy. A server reboot orphans the process.

### 1. docker-compose.yml (root)

```yaml
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    restart: unless-stopped
    environment:
      - SPEC_DOC_DIR=/data/projects
      - CORS_ORIGINS=https://spec-doc.yourdomain.com
    volumes:
      - projects_data:/data/projects
    expose:
      - "3101"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3101/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:1.27-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro
      - certbot_data:/var/www/certbot
    depends_on:
      api:
        condition: service_healthy

volumes:
  projects_data:
  certbot_data:
```

### 2. nginx/nginx.conf

```nginx
upstream flask_api {
    server api:3101;
    keepalive 32;
}

server {
    listen 80;
    server_name spec-doc.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name spec-doc.yourdomain.com;

    ssl_certificate     /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;

    # API routes — long timeout for AI calls
    location /api/ {
        proxy_pass         http://flask_api;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
    }

    # Angular SPA — served by Flask catch-all
    location / {
        proxy_pass         http://flask_api;
        proxy_read_timeout 60s;
    }
}
```

`proxy_read_timeout 3600s` on `/api/` is the nginx analog of the CLI subprocess timeout — keeps the channel open for the worst-case bootstrap. Once the bootstrap becomes async (202+polling), this can drop to 30s.

### 3. Dockerfile — gunicorn, not flask dev server

```dockerfile
FROM python:3.11-slim
WORKDIR /app

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY api/ .
COPY web/dist/spec-doc/browser/ ./web/

ENV PYTHONUNBUFFERED=1
EXPOSE 3101

CMD ["gunicorn", \
     "--bind", "0.0.0.0:3101", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "3600", \
     "--worker-class", "gthread", \
     "create_app:create_app()"]
```

`gthread` worker class: 2 workers × 4 threads = 8 concurrent requests. Background threads (generate-task, bootstrap-async) are not affected by gunicorn's worker model because they're daemon threads within the worker process.

### 4. Volume strategy — projects on host, not in image

```yaml
volumes:
  - projects_data:/data/projects
```

`SPEC_DOC_DIR=/data/projects` points Flask at the Docker volume. Projects survive image rebuilds. Local dev still uses `SPEC_DOC_DIR=/Users/sam/Projects/2026/spec-doc` from `.env`.

### 5. Makefile targets (root-level)

```makefile
# Makefile (root)
up:
    docker compose up -d

down:
    docker compose down

logs:
    docker compose logs -f api

deploy: build up
    @echo "Deployed"

build:
    docker compose build --no-cache
```

### 6. SSL certificates — certbot (manual first run)

```bash
# One-time setup on the server
docker run --rm -v certbot_data:/var/www/certbot certbot/certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  -d spec-doc.yourdomain.com --email admin@yourdomain.com --agree-tos
```

Renewal via cron: `0 0 1 * * docker compose run --rm certbot renew`

## Why now

The production container runs flask dev server directly on 3101 with no supervisor. A crash or reboot takes the service down until someone SSHes in. `unless-stopped` restart policy + gunicorn fixes both. nginx terminates SSL and protects Flask from direct internet exposure. The volume mount ensures projects survive deploys.

This is the same stack shape as humanize-me and Trendfy — proven in production.

## What's missing

One decision: **domain name**. The nginx config has `spec-doc.yourdomain.com` as a placeholder. Before the Dockerfile and compose file can be fully deployed, the domain must be set and the cert provisioned. Internal use only = skip nginx/SSL and just map `3101:3101`.

## Explicitly out of scope

- Redis / PostgreSQL — in-process state is sufficient for spec-doc's single-user model
- Container registry (ECR, GHCR) — build on the server from source; image is not portable
- Horizontal scaling / load balancing — single VPS is the deployment target
- Coolify / Dokku — Docker Compose directly gives more control for this stack
