FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python \
        fastapi "uvicorn[standard]" "pydantic[email]" pydantic-settings \
        sqlalchemy asyncpg alembic httpx structlog slowapi \
        "passlib[bcrypt]" "bcrypt==4.0.1" "python-jose[cryptography]" \
        python-multipart "redis>=5.0.0" pytest pytest-asyncio

FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
COPY . /app
EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]