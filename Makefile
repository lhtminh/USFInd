COMPOSE := docker compose -f docker/docker-compose.yml

ifeq ($(OS),Windows_NT)
	PY := .venv/Scripts/python.exe
else
	PY := .venv/bin/python
endif

.PHONY: up down logs reset api web test fmt seed benchmark

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

reset:
	$(COMPOSE) down -v
	$(COMPOSE) up -d

api:
	$(PY) -m uvicorn api.main:app --reload --port 8000

web:
	cd web && npm run dev

test:
	$(PY) -m pytest

fmt:
	$(PY) -m black .
	$(PY) -m ruff check --fix .

seed:
	$(PY) -m scripts.seed_data

benchmark:
	$(PY) -m scripts.benchmark
