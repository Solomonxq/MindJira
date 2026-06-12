# MindJira

AI-powered assistant for Jira.

## Architecture

- `services/` — FastAPI microservices
  - `auth` — authentication & users
  - `gateway` — API gateway, jobs, webhooks
  - `description-enricher` — AI description generation
  - `sprint-summary` — sprint reports & health checks
  - `test-case-generator` — AI test case generation
- `packages/` — shared libraries
  - `ai-client` — LLM client
  - `jira-client` — Jira REST client
- `frontend/` — React dashboard
- `infra/` — Docker Compose infrastructure

## Quick Start

```bash
# Copy environment variables
cp .env.example .env

# Start infrastructure and services
cd infra && docker-compose up --build

# Start frontend (dev)
cd frontend && npm install && npm run dev
```

Open http://localhost for the UI.
