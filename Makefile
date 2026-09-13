.PHONY: setup migrate seed dev test build verify verify-release run-prod

setup:
	uv sync --all-groups
	npm --prefix web ci
	@test -f .env || uv run python -m scripts.bootstrap_env

migrate:
	uv run alembic upgrade head

seed:
	uv run python -m app.db.seed

dev:
	@sh -c 'trap "kill 0" EXIT INT TERM; uv run uvicorn app.main:app --reload --port 8000 & npm --prefix web run dev'

test:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy app
	uv run pytest --cov=app --cov-report=term-missing
	npm --prefix web run lint
	npm --prefix web run test

build:
	npm --prefix web run build

verify:
	uv run python scripts/verify_all.py

verify-release:
	uv run python scripts/verify_release.py

run-prod: build
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
