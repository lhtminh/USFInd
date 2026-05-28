COMPOSE := docker compose -f docker/docker-compose.yml

ifeq ($(OS),Windows_NT)
	PY := .venv/Scripts/python.exe
else
	PY := .venv/bin/python
endif

.PHONY: up down logs reset run test fmt seed benchmark

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

reset:
	$(COMPOSE) down -v
	$(COMPOSE) up -d

run:
	$(PY) -m streamlit run app/streamlit_app.py

test:
	$(PY) -m pytest

fmt:
	$(PY) -m black .
	$(PY) -m ruff check --fix .

seed:
	$(PY) -m scripts.seed_data

benchmark:
	$(PY) -m scripts.benchmark
