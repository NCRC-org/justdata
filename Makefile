.PHONY: help install dev test clean docker-build docker-up docker-down docker-logs lint format

# Default target
help:
	@echo "JustData Development Commands"
	@echo "============================="
	@echo ""
	@echo "Installation:"
	@echo "  install      Install dependencies"
	@echo "  dev          Install development dependencies"
	@echo ""
	@echo "Development:"
	@echo "  run          Run the API server locally"
	@echo "  test         Run tests"
	@echo "  lint         Run linting checks"
	@echo "  format       Format code with black and isort"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build Build Docker images"
	@echo "  docker-up    Start all services"
	@echo "  docker-down  Stop all services"
	@echo "  docker-logs  View service logs"
	@echo ""
	@echo "Database:"
	@echo "  db-init      Initialize database"
	@echo "  db-migrate   Run database migrations"
	@echo ""
	@echo "Utilities:"
	@echo "  clean        Clean up generated files"
	@echo "  logs         View application logs"

# Installation
install:
	pip install -r requirements.txt

dev:
	pip install -r requirements.txt
	pip install -e ".[dev]"

# Development
run:
	python -m justdata.api.main

test:
	pytest tests/ -v --cov=justdata --cov-report=html

lint:
	flake8 justdata/ tests/
	mypy justdata/
	black --check justdata/ tests/
	isort --check-only justdata/ tests/

format:
	black justdata/ tests/
	isort justdata/ tests/

# Docker commands
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Database
db-init:
	python -c "from justdata.core.database.connection import init_database; init_database()"

db-migrate:
	alembic upgrade head

# Utilities
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .pytest_cache/ htmlcov/ .coverage

logs:
	tail -f logs/app.log

# Development server with auto-reload
dev-server:
	uvicorn justdata.api.main:app --reload --host 0.0.0.0 --port 8000

# Run specific application tests
test-branchseeker:
	pytest tests/apps/test_branchseeker/ -v

test-lendsight:
	pytest tests/apps/test_lendsight/ -v

test-bizsight:
	pytest tests/apps/test_bizsight/ -v

# API documentation
docs-serve:
	mkdocs serve

docs-build:
	mkdocs build

# Production deployment
deploy-prod:
	docker build -t justdata:latest .
	docker tag justdata:latest us-docker.pkg.dev/hdma1-242116/justdata-repo/justdata:latest
	docker push us-docker.pkg.dev/hdma1-242116/justdata-repo/justdata:latest

# Health checks
health:
	curl -f http://localhost:8000/health || echo "Service not healthy"

# Database connection test
test-db:
	python -c "from justdata.core.database.connection import test_connections; test_connections()"
