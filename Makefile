.PHONY: help install dev test clean docker-build docker-up docker-down docker-logs lint format deploy-all deploy-main deploy-branchsight deploy-lendsight deploy-branchmapper

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
	@echo ""
	@echo "Cloud Run Deployment:"
	@echo "  deploy-all          Deploy all configured services"
	@echo "  deploy-main         Deploy BranchSight, BranchMapper, and LendSight"
	@echo "  deploy-branchsight Deploy BranchSight only"
	@echo "  deploy-branchmapper Deploy BranchMapper only"
	@echo "  deploy-lendsight    Deploy LendSight only"

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
test-branchsight:
	pytest tests/apps/test_branchsight/ -v

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

# Deploy all services to Cloud Run
deploy-all:
	bash scripts/deploy-all.sh all

# Deploy the three main services (BranchSight, BranchMapper, LendSight)
deploy-main:
	bash scripts/deploy-all.sh branchsight branchmapper lendsight

# Deploy individual services to Cloud Run
deploy-branchsight:
	bash scripts/deploy-all.sh branchsight

deploy-lendsight:
	bash scripts/deploy-all.sh lendsight

deploy-branchmapper:
	bash scripts/deploy-all.sh branchmapper

# Additional services (optional)
deploy-bizsight:
	bash scripts/deploy-all.sh bizsight

deploy-mergermeter:
	bash scripts/deploy-all.sh mergermeter

# Health checks
health:
	curl -f http://localhost:8000/health || echo "Service not healthy"

# Database connection test
test-db:
	python -c "from justdata.core.database.connection import test_connections; test_connections()"
