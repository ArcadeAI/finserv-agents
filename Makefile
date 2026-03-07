.PHONY: setup db seed materialize dev deploy clean install help

help:
	@echo ""
	@echo "  FinServ Agents"
	@echo "  ──────────────────────────────────"
	@echo "  make install      Install dependencies"
	@echo "  make setup        DB + schema + seed + materialize to Redis"
	@echo "  make materialize  Materialize Postgres views into Redis cache"
	@echo "  make dev          Start Next.js dev server"
	@echo "  make deploy       Deploy MCP server to Arcade Cloud"
	@echo "  make clean        Tear down Docker volumes"
	@echo ""

install:
	npm install
	cd database && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

setup: db seed materialize
	@echo ""
	@echo "  Done. Run 'make dev' to start the app."
	@echo ""

db:
	docker compose up -d
	@echo "Waiting for PostgreSQL to start..."
	@sleep 5
	docker exec -i loanops-pg psql -U postgres -d loanops < database/schema.sql

seed:
	cd database && .venv/bin/python seed_data.py

materialize:
	cd database && .venv/bin/python materialize.py

dev:
	cd web && npm run dev

deploy:
	cd tools && uv sync && arcade deploy -e src/redis_mcp/server.py

clean:
	docker compose down -v
