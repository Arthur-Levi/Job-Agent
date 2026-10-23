SHELL := /bin/bash
BACKEND_BIN ?= backend/.venv/bin
BIN := $(abspath $(BACKEND_BIN))

.DEFAULT_GOAL := help
.PHONY: help up down db-reset backend-install migrate seed backend-dev backend-lint backend-typecheck backend-test frontend-install frontend-dev frontend-lint frontend-build frontend-test check

help: ## Lista os comandos
	@grep -hE '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-20s %s\n", $$1, $$2}'

up: ## Sobe o PostgreSQL local (docker compose)
	docker compose up -d

down: ## Para os containers (mantém os dados)
	docker compose down

db-reset: ## DESTRÓI os dados locais do PostgreSQL e recria (exige CONFIRM=yes)
	@test "$(CONFIRM)" = "yes" || { echo "Isto apaga o volume do banco. Rode: make db-reset CONFIRM=yes"; exit 1; }
	docker compose down -v
	docker compose up -d

backend-install: ## Cria backend/.venv e instala o backend (com dependências de dev)
	python3.12 -m venv backend/.venv
	backend/.venv/bin/python -m pip install --upgrade pip
	backend/.venv/bin/pip install -e "backend[dev]"

migrate: ## Aplica as migrations (alembic upgrade head) no DATABASE_URL
	cd backend && $(BIN)/alembic upgrade head

seed: ## Dados de DESENVOLVIMENTO (só com APP_ENV=development; idempotente)
	cd backend && $(BIN)/python -m app.devtools.seed

backend-dev: ## API com reload em http://localhost:8000
	cd backend && $(BIN)/uvicorn app.main:create_app --factory --reload

backend-lint: ## ruff (lint + formato)
	cd backend && $(BIN)/ruff check . && $(BIN)/ruff format --check .

backend-typecheck: ## mypy (strict)
	cd backend && $(BIN)/mypy

backend-test: ## pytest com as variáveis do .env (TEST_DATABASE_URL habilita os testes de banco)
	@test -f .env || { echo "Crie o .env: cp .env.example .env"; exit 1; }
	set -a; . ./.env; set +a; cd backend && $(BIN)/pytest

frontend-install: ## npm ci
	cd frontend && npm ci

frontend-dev: ## Vite em http://localhost:5173
	cd frontend && npm run dev

frontend-lint: ## eslint
	cd frontend && npm run lint

frontend-build: ## tsc + vite build
	cd frontend && npm run build

frontend-test: ## vitest
	cd frontend && npm test

check: backend-lint backend-typecheck backend-test frontend-lint frontend-build frontend-test ## Todos os gates de qualidade
