.PHONY: help install bootstrap seed run test lint pipeline foundation frontend-build frontend-dev docker clean

help:  ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install:  ## Install Python deps into .venv
	uv sync --group dev

bootstrap:  ## Make workspace packages importable
	uv run python scripts/bootstrap.py

seed:  ## Load deterministic demo data
	uv run python scripts/seed_demo_data.py

run:  ## Run all backend services locally (SQLite + in-memory infra)
	uv run python scripts/run_local.py

test:  ## Run the full test suite
	uv run pytest

lint:  ## Lint Python sources
	uv run ruff check shared services scripts tests

pipeline:  ## Verify the crawl->index->rank->search pipeline end to end
	uv run python scripts/verify_pipeline.py

foundation:  ## Verify imports, migrations, and app wiring
	uv run python scripts/validate_foundation.py

frontend-build:  ## Type-check and build the frontend
	cd frontend && npm install && npm run build

frontend-dev:  ## Run the frontend dev server
	cd frontend && npm run dev

docker:  ## Build and start the full stack with Docker Compose
	docker compose up --build

clean:  ## Remove local databases and build artifacts
	rm -f nexus.db
	rm -rf frontend/dist
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
