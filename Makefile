.DEFAULT_GOAL := help
VENV := .venv
PY   := $(VENV)/bin/python
PIP  := $(VENV)/bin/pip

.PHONY: help venv install lint format typecheck test test-fast security migrate \
        seed admin up down logs shell clean images check

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
	 awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

venv: ## Create the virtualenv
	python3 -m venv $(VENV)
	$(PIP) install --quiet --upgrade pip pip-tools

install: venv ## Install all dev dependencies (hash-verified)
	$(PIP) install --require-hashes -r requirements/dev.txt
	$(PIP) install -e . --no-deps

lock: ## Recompile pinned requirements from the .in files
	$(VENV)/bin/pip-compile --generate-hashes --strip-extras --allow-unsafe -o requirements/base.txt requirements/base.in
	$(VENV)/bin/pip-compile --generate-hashes --strip-extras --allow-unsafe -o requirements/dev.txt  requirements/dev.in

lint: ## Ruff lint (S608 catches f-string SQL)
	$(VENV)/bin/ruff check src tests scripts
	$(VENV)/bin/ruff format --check src tests scripts

format: ## Auto-format
	$(VENV)/bin/ruff check --fix src tests scripts
	$(VENV)/bin/ruff format src tests scripts

typecheck: ## mypy (strict on models/services/security/config)
	$(VENV)/bin/mypy src/itsc

test: ## Full suite with coverage gate
	$(VENV)/bin/pytest --cov --cov-fail-under=90

test-fast: ## Suite without the coverage gate, parallel
	$(VENV)/bin/pytest -n auto -q

security: ## Dependency CVEs + static security analysis
	$(VENV)/bin/pip-audit -r requirements/base.txt
	$(VENV)/bin/bandit -q -r src/itsc

check: lint typecheck test security ## Everything CI runs

migrate: ## Apply migrations
	FLASK_APP=itsc:create_app $(VENV)/bin/flask db upgrade

revision: ## Generate a migration:  make revision M="add x"
	FLASK_APP=itsc:create_app $(VENV)/bin/flask db migrate -m "$(M)"

admin: ## Create an admin user (prompts for the password)
	FLASK_APP=itsc:create_app $(VENV)/bin/flask itsc create-admin

seed: ## Seed demo content (clearly labelled as samples)
	FLASK_APP=itsc:create_app $(VENV)/bin/flask itsc seed-demo

images: ## Regenerate optimised image derivatives
	python3 scripts/optimize_images.py --apply

up: ## Start the full stack
	docker compose up -d --build

down: ## Stop the stack
	docker compose down

logs: ## Tail application logs
	docker compose logs -f web

clean: ## Remove caches and build artefacts
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage build dist *.egg-info
