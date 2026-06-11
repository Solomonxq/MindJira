FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY . /app

RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python \
        -e services/description-enricher \
        -e packages/ai-client \
        -e packages/jira-client

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
