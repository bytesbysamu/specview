FROM python:3.11-slim

RUN addgroup --system appgroup \
 && adduser --system --ingroup appgroup appuser

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

# Drop to non-root before the process starts.
USER appuser

EXPOSE 3101

# 2 workers × 4 gthread threads.
# --timeout 900: AI provider calls run up to 15 minutes; gunicorn's default 120
#   silently kills them with no error visible to the caller.
# --preload: AI provider adapter initializes once before workers fork.
CMD ["gunicorn", \
     "--bind", "0.0.0.0:3101", \
     "--worker-class", "gthread", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "900", \
     "--preload", \
     "create_app:create_app()"]
