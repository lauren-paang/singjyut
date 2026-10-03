FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run as an unprivileged user; only the cache directory needs to be writable.
RUN useradd --create-home --uid 1000 app \
    && mkdir -p data/lyrics_cache data/tts_cache \
    && chown -R app:app data
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/api/health' % os.environ.get('PORT', '8000'), timeout=4)" || exit 1

# Via sh so $PORT (set by Render and similar hosts) is honoured; exec keeps
# uvicorn as PID 1 so it receives SIGTERM directly.
CMD ["sh", "-c", "exec uvicorn server:app --host 0.0.0.0 --port \"$PORT\""]
