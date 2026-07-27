.PHONY: help install dev test lint format docker-up docker-down clean

help:
	@echo "Jarvis Development Commands:"
	@echo "  make install     Install dependencies"
	@echo "  make dev         Install dependencies in editable dev mode"
	@echo "  make test        Run all unit and integration tests"
	@echo "  make lint        Check code quality with ruff and mypy"
	@echo "  make format      Format code with black and ruff"
	@echo "  make docker-up   Start infrastructure services in Docker"
	@echo "  make docker-down Stop infrastructure services"
	@echo "  make clean       Clean build artifacts"

install:
	pip install -e .

dev:
	pip install -e ".[dev,api,database]"

test:
	pytest tests/

lint:
	ruff check src/ tests/
	mypy src/

format:
	black src/ tests/
	ruff check --fix src/ tests/

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
