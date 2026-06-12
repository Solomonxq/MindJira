.PHONY: up down frontend-dev lint migrate test

up:
	cd infra && docker-compose up --build -d

down:
	cd infra && docker-compose down

frontend-dev:
	cd frontend && npm install && npm run dev

lint:
	cd frontend && npm run lint

migrate:
	cd services/auth && uv run alembic upgrade head
	cd services/gateway && uv run alembic upgrade head
	cd services/description-enricher && uv run alembic upgrade head
	cd services/sprint-summary && uv run alembic upgrade head
	cd services/test-case-generator && uv run alembic upgrade head

test:
	cd services/auth && uv run pytest
	cd services/description-enricher && uv run pytest
	cd services/gateway && uv run pytest
	cd services/sprint-summary && uv run pytest
	cd services/test-case-generator && uv run pytest
