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
COPY nginx.conf /etc/nginx/conf.d/default.conf
