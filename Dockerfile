FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production \
    HOST=0.0.0.0 \
    PORT=3000 \
    COOKIE_SECURE=true \
    TRUST_PROXY=false \
    UVICORN_RELOAD=0 \
    DATABASE_PATH=/app/backend/data/planner.db

WORKDIR /app/backend
COPY backend/requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 planner \
    && useradd --uid 10001 --gid planner --no-create-home --home-dir /tmp planner \
    && mkdir -p /app/backend/data \
    && chown -R planner:planner /app/backend/data

COPY --chown=planner:planner backend/app ./app
COPY --chown=planner:planner backend/index.py ./index.py
COPY --chown=planner:planner frontend /app/frontend
USER planner
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '3000') + '/healthz', timeout=3).close()"
CMD ["python", "-m", "app"]