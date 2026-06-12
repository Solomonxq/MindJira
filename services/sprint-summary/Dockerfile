FROM python:3.12-slim

WORKDIR /app

# Copy repository into image
COPY . /app

# Create virtualenv and install service + local packages during build
RUN python -m venv /app/.venv \
    && /app/.venv/bin/pip install --upgrade pip setuptools wheel \
    && /app/.venv/bin/pip install --no-cache-dir -e services/sprint-summary -e packages/jira-client -e packages/ai-client

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
CMD ["sh", "-c", "alembic -c services/sprint-summary/alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
