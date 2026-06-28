# ── Stage 1: Build Angular app ────────────────
FROM node:20-alpine AS build
WORKDIR /app
COPY web-ng/package*.json ./
RUN npm ci --quiet --legacy-peer-deps
COPY web-ng/ .
COPY api/openapi.yaml /api/openapi.yaml
RUN npm run generate:api && npm run build

# ── Stage 2: Serve with nginx ─────────────────
FROM nginx:alpine
COPY --from=build /app/dist/web-ng/browser /usr/share/nginx/html/
# C2/C3: deployed specview is a Core CLIENT — the core-split conf proxies
# /api/auth|billing|email → https://core.oll.am (TLS) and product /api/* → api:3101.
# (Old self-contained monolith conf kept as nginx.conf for reference/rollback.)
COPY nginx.core-split.conf /etc/nginx/conf.d/default.conf
