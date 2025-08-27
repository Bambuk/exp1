.PHONY: help install dev test lint format clean docker-build docker-run deploy migrate migrate-create migrate-status migrate-history migrate-downgrade migrate-reset db-init

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install:  ## Install dependencies
	pip install -e ".[dev]"
	pre-commit install

dev:  ## Run development server
	uvicorn radiator.main:app --reload --host 0.0.0.0 --port 8000

test:  ## Run tests
	pytest tests/ -v --cov=radiator --cov-report=html

test-unit:  ## Run unit tests only
	pytest tests/ -v -m unit --cov=radiator --cov-report=html

test-integration:  ## Run integration tests only
	pytest tests/ -v -m integration --cov=radiator --cov-report=html

lint:  ## Run linting
	flake8 radiator/ tests/
	mypy radiator/

format:  ## Format code
	black radiator/ tests/
	isort radiator/ tests/

check-format:  ## Check code formatting
	black --check radiator/ tests/
	isort --check-only radiator/ tests/

clean:  ## Clean up generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .mypy_cache/

docker-build:  ## Build Docker image
	docker build -t radiator-api .

docker-run:  ## Run with Docker Compose
	docker-compose up -d

docker-stop:  ## Stop Docker Compose
	docker-compose down

docker-logs:  ## Show Docker logs
	docker-compose logs -f

deploy:  ## Deploy to Ubuntu server
	@echo "Make sure you have access to the server and run:"
	@echo "bash deploy/deploy.sh"

migrate:  ## Run database migrations
	alembic upgrade head

migrate-create:  ## Create new migration
	@read -p "Enter migration message: " message; \
	alembic revision --autogenerate -m "$$message"

migrate-status:  ## Show migration status
	alembic current

migrate-history:  ## Show migration history
	alembic history

migrate-downgrade:  ## Downgrade one migration
	alembic downgrade -1

migrate-reset:  ## Reset to base (remove all migrations)
	alembic downgrade base

db-init:  ## Initialize database
	python -c "import asyncio; from radiator.core.database import init_db; asyncio.run(init_db())"

pre-commit-run:  ## Run pre-commit hooks on all files
	pre-commit run --all-files

# Tracker sync commands
sync-tracker:
	@echo "Syncing tracker data..."
	@python sync_tracker.py tasks.txt

sync-tracker-debug:
	@echo "Syncing tracker data with debug..."
	@python sync_tracker.py tasks.txt --debug

sync-tracker-force:
	@echo "Force full sync of tracker data..."
	@python sync_tracker.py tasks.txt --force-full-sync

test-tracker-sync:
	@echo "Testing tracker sync system..."
	@python test_tracker_sync.py
