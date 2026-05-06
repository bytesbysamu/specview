FROM python:3.11-slim

# Install Node.js 20 (for claude CLI) + curl
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI (Linux-compatible npm package)
RUN npm install -g @anthropic-ai/claude-code

RUN groupadd --system appgroup \
 && useradd --system --gid appgroup --create-home --home-dir /home/appuser appuser

WORKDIR /app

COPY api/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./
COPY data/ /data/spec-doc/

RUN chown -R appuser:appgroup /data/spec-doc/

USER appuser
ENV HOME=/home/appuser

EXPOSE 3101

CMD ["gunicorn", \
     "--bind", "0.0.0.0:3101", \
     "--worker-class", "gthread", \
     "--workers", "1", \
     "--threads", "4", \
     "--timeout", "900", \
     "--preload", \
     "create_app:create_app()"]
