.DEFAULT_GOAL := help

.PHONY: help install setup setup-indices db seed materialize demo-reset db-flush dev deploy validate clean

help:
	@echo ""
	@echo "  FinServ Agents"
	@echo "  ──────────────────────────────────"
	@echo "  make install      Install dependencies"
	@echo "  make setup        DB + schema + seed + clean demo materialization"
	@echo "  make setup-indices Ensure RedisVL schema files and indices exist"
	@echo "  make materialize  Refresh live data and clear demo workflow state"
	@echo "  make demo-reset   Clear only shift notes and activity stream state"
	@echo "  make db-flush     Drop FinServ RediSearch indices, then flush Redis Cloud DB"
	@echo "  make dev          Start Next.js dev server"
	@echo "  make deploy       Sync Arcade secrets and deploy the MCP toolkit"
	@echo "  make validate     Run local Python compile, web lint, and web build validation"
	@echo "  make clean        Tear down local PostgreSQL volumes"
	@echo ""

install:
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env from .env.example"; fi
	npm install
	uv sync --locked

setup: db seed materialize
	@echo ""
	@echo "  Done. Run 'make dev' to start the app."
	@echo ""

setup-indices:
	uv run python database/setup_indices.py

db:
	docker compose up -d postgres
	@echo "Waiting for PostgreSQL to start..."
	@until docker exec loanops-pg pg_isready -U postgres -d loanops >/dev/null 2>&1; do sleep 1; done
	docker exec -i loanops-pg psql -U postgres -d loanops < database/schema.sql

seed:
	uv run python database/seed_data.py

materialize:
	uv run python database/materialize.py

demo-reset:
	uv run python database/demo_reset.py

db-flush:
	uv run python database/db_flush.py

dev:
	cd web && npm run dev

validate:
	npm run validate

deploy:
	uv run python scripts/sync_arcade_secrets.py
	cd tools && uv sync --locked
	cd tools && printf 'n\n' | uv run arcade deploy -e src/redis_mcp/server.py --secrets skip

clean:
	docker compose down -v
