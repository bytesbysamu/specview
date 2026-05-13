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

RUN pip install --no-cache-dir datamodel-code-generator==0.45.0 \
 && python -m datamodel_code_generator \
      --input openapi.yaml \
      --output dtos/models.py \
      --output-model-type pydantic_v2.BaseModel \
      --input-file-type openapi \
      --target-python-version 3.10 \
      --disable-timestamp \
 && pip uninstall -y datamodel-code-generator
COPY plugin/ ./plugin/
COPY data/ /data/spec-doc/

RUN chown -R appuser:appgroup /data/spec-doc/

COPY api/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Pre-create .claude directory with correct ownership so named volumes
# inherit appuser ownership on first mount (Docker copies the image's
# directory ownership into empty named volumes).
RUN mkdir -p /home/appuser/.claude && chown appuser:appgroup /home/appuser/.claude

ARG APP_RELEASE=dev
ENV APP_RELEASE=${APP_RELEASE}

USER appuser
ENV HOME=/home/appuser

EXPOSE 3101

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", \
     "--bind", "0.0.0.0:3101", \
     "--worker-class", "gthread", \
     "--workers", "1", \
     "--threads", "4", \
     "--timeout", "900", \
     "create_app:create_app()"]
