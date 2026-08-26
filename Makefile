# =============================================================================
# dsv-parser — standalone parser for DSV swim-meet interchange files.
#
# One self-contained Makefile covering the whole target surface (install / lint /
# format / typecheck / test / test-it / audit), so the same commands drive the
# project locally and in CI.
#
# The `api` extra is installed by `make install`: the HTTP surface is optional
# for a library consumer, but the test suite covers it, so the dev environment
# always has it.
# =============================================================================

SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help
PACKAGE := dsv_parser
IMAGE := dsv-parser
PORT ?= 8000
COMPOSE_DEV := -f docker-compose.yaml -f docker-compose.dev.yaml

.PHONY: help install dev serve build image up up-dev down restart logs ps sh \
        test test-it lint format format-check typecheck audit spec clean

help:           ## Show this help.
	@awk 'BEGIN {FS=":.*##"} /^[a-zA-Z0-9_.-]+:.*##/ \
	  {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install:        ## Install / refresh dependencies (uv sync, with the api extra).
	uv sync --extra api
dev:            ## Print the CLI help, listing every subcommand.
	uv run python -m $(PACKAGE) --help
serve:          ## Run the FastAPI service with auto-reload on $(PORT).
	uv run uvicorn dsv_parser.api:app --host 0.0.0.0 --port $(PORT) --reload
spec:           ## Print the element table this parser implements.
	uv run python -m $(PACKAGE) spec
build:          ## Build the sdist and the wheel into dist/ — what the release publishes.
	rm -rf dist
	uv build
image:          ## Build the runtime container image.
	docker build -t $(IMAGE):local .

# --- container stack -------------------------------------------------------
# `up` runs the production image; `up-dev` layers the reload overlay on top.
up:             ## Build and start the stack in the background.
	docker compose up -d --build
up-dev:         ## Start the stack with sources mounted and uvicorn --reload.
	docker compose $(COMPOSE_DEV) up -d --build
down:           ## Stop and remove the stack.
	docker compose $(COMPOSE_DEV) down --remove-orphans
restart:        ## Recreate the stack from a fresh build.
	$(MAKE) down && $(MAKE) up
logs:           ## Follow the service logs.
	docker compose logs -f dsv-parser
ps:             ## Show the stack's containers and health.
	docker compose ps
sh:             ## Open a shell in the running container.
	docker compose exec dsv-parser sh

test:           ## Unit tests only — fast, offline, no coverage gate.
	uv run pytest -m "not integration" --no-cov
test-it:        ## Full test gate: unit + integration tests and the coverage threshold.
	uv run pytest
lint:           ## Ruff check.
	uv run ruff check .
format:         ## Ruff: sort imports (I) + format in place.
	uv run ruff check --select I --fix .
	uv run ruff format .
format-check:   ## Verify import order (I) + formatting without writing.
	uv run ruff check --select I .
	uv run ruff format --check .
typecheck:      ## mypy static type check.
	uv run mypy $(PACKAGE)
audit:          ## pip-audit.
	uv run pip-audit
clean:          ## Remove caches, build output and the virtualenv.
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov dist .venv
