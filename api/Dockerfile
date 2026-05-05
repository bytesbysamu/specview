FROM python:3.11-slim

RUN addgroup --system appgroup \
 && adduser --system --ingroup appgroup appuser

WORKDIR /app

COPY api/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./
COPY data/ /data/spec-doc/

USER appuser

EXPOSE 3101

CMD ["gunicorn", \
     "--bind", "0.0.0.0:3101", \
     "--worker-class", "gthread", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "900", \
     "--preload", \
     "create_app:create_app()"]
