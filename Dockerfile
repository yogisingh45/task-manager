FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install runtime dependencies first so this layer is cached across code changes.
COPY requirements.txt .
# pytest is a dev dependency, so it is filtered out of the runtime image.
RUN grep -vi '^pytest' requirements.txt > runtime-requirements.txt \
    && pip install --no-cache-dir -r runtime-requirements.txt

COPY app.py .
COPY task_manager/ task_manager/

# Run as an unprivileged user.
RUN useradd --system --no-create-home appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import os, urllib.request as u; u.urlopen('http://127.0.0.1:%s/tasks' % os.environ['PORT'])"]

# The in-memory repository is per-process, so use exactly one worker
# (threads provide concurrency; the repository lock makes this safe).
CMD ["sh", "-c", "exec gunicorn --workers 1 --threads 4 --bind 0.0.0.0:${PORT} app:app"]
