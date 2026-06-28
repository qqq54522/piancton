.PHONY: check backend-check frontend-check docker-build docker-up docker-up-search docker-down

BACKEND_PYTHON := $(shell if [ -x backend/.venv/bin/python ]; then echo ./.venv/bin/python; else echo python3; fi)
BACKEND_RUFF := $(shell if [ -x backend/.venv/bin/ruff ]; then echo ./.venv/bin/ruff; else echo ruff; fi)
BACKEND_PYRIGHT := $(shell if [ -x backend/.venv/bin/pyright ]; then echo ./.venv/bin/pyright; else echo pyright; fi)

check: backend-check frontend-check

backend-check:
	cd backend && $(BACKEND_PYTHON) -m pytest tests -q
	cd backend && $(BACKEND_RUFF) check app tests scripts
	cd backend && $(BACKEND_PYRIGHT)

frontend-check:
	cd client && npm run typecheck
	cd client && npm test -- --run
	cd client && npm run build

docker-build:
	docker compose build

docker-up:
	docker compose up --build -d

docker-up-search:
	docker compose --profile search up --build -d

docker-down:
	docker compose down
