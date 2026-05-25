SHELL := /bin/bash

PROFILE ?= local
COMPOSE := docker compose --profile $(PROFILE)

ifeq ($(PROFILE),deployed)
APP_SERVICE := app-prod
BACKEND_SERVICE := backend-prod
SITE_SERVICE := site-prod
else
APP_SERVICE := app
BACKEND_SERVICE := backend
SITE_SERVICE := site
endif

.PHONY: help env up up-foreground down restart rebuild ps logs logs-app logs-backend logs-site logs-db smoke lint lint-app lint-site lint-backend format format-backend test test-backend test-ui hooks-install hooks-run

help: ## Show available commands
	@grep -E '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "%-18s %s\n", $$1, $$2}'

env: ## Create per-service .env files from their examples if missing
	@test -f app/.env || cp app/.env.example app/.env
	@test -f backend/.env || cp backend/.env.example backend/.env
	@test -f site/.env || cp site/.env.example site/.env

up: ## Start the current compose profile in the background
	$(COMPOSE) up --build -d

up-foreground: ## Start the current compose profile attached to the terminal
	$(COMPOSE) up --build

down: ## Stop the current compose profile
	$(COMPOSE) down --remove-orphans

restart: down up ## Restart the current compose profile

rebuild: ## Force-recreate the current compose profile
	$(COMPOSE) up --build -d --force-recreate

ps: ## Show compose service status
	$(COMPOSE) ps

logs: ## Tail all container logs for the current profile
	$(COMPOSE) logs -f $(SITE_SERVICE) $(APP_SERVICE) $(BACKEND_SERVICE) db

logs-app: ## Tail app logs for the current profile
	$(COMPOSE) logs -f $(APP_SERVICE)

logs-backend: ## Tail backend logs for the current profile
	$(COMPOSE) logs -f $(BACKEND_SERVICE)

logs-site: ## Tail site logs for the current profile
	$(COMPOSE) logs -f $(SITE_SERVICE)

logs-db: ## Tail database logs for the current profile
	$(COMPOSE) logs -f db

smoke: ## Run the root smoke test against the current profile
	./scripts/smoke-test.sh $(PROFILE)

lint: lint-backend lint-app lint-site ## Run repo lint checks

lint-app: ## Run app linting
	cd app && npm run lint

lint-site: ## Run site linting
	cd site && npm run lint

lint-backend: ## Run backend linting
	cd backend && uv run ruff check .

format: format-backend ## Run repo formatting commands

format-backend: ## Format backend Python code
	cd backend && uv run ruff format .

test: test-backend ## Run the default automated test suite

test-backend: ## Run backend unit tests
	cd backend && uv run python -m pytest

test-ui: ## Run app Playwright UI tests
	cd app && npm run test:ui

hooks-install: ## Install the shared pre-commit hooks using backend's uv environment
	cd backend && uv run pre-commit install --config ../.pre-commit-config.yaml

hooks-run: ## Run all pre-commit hooks across the repo
	cd backend && uv run pre-commit run --all-files --config ../.pre-commit-config.yaml
