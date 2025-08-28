.PHONY: help install dev test lint format clean docker-build docker-run deploy migrate migrate-create migrate-status migrate-history migrate-downgrade migrate-reset db-init test-db-create test-db-drop test-db-reset test-env

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ''
	@echo 'Database Commands:'
	@echo '  db-init*           - Initialize main database'
	@echo '  test-db-*          - Manage test database (create, drop, reset)'
	@echo ''
	@echo 'Tracker Sync Commands:'
	@echo '  sync-tracker*      - Sync recent tracker tasks'
	@echo '  sync-tracker-*     - Various sync modes (active, recent, filter, file)'
	@echo ''
	@echo 'Tracker Test Commands:'
	@echo '  test-tracker*      - Run tracker tests (all, unit, integration, crud, api)'
	@echo '  test-tracker-coverage - Run tracker tests with coverage report'

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

db-init:  ## Initialize main database
	python -c "import asyncio; from radiator.core.database import init_db; asyncio.run(init_db())"

# Test database management commands
test-db-create:  ## Create test database
	@echo "Creating test database 'radiator_test'..."
	python create_test_db.py

test-db-drop:  ## Drop test database
	@echo "Dropping test database 'radiator_test'..."
	python create_test_db.py --drop

test-db-reset: test-db-drop test-db-create  ## Reset test database (drop and recreate)
	@echo "Test database reset complete."

test-env:  ## Verify test environment configuration
	@echo "Verifying test environment..."
	@echo "ENVIRONMENT: $$(python -c "from radiator.core.config import settings; print(settings.ENVIRONMENT)")"
	@echo "Test Database URL: $$(python -c "from radiator.core.config import settings; print(settings.test_database_url)")"
	@echo "Is Test Environment: $$(python -c "from radiator.core.config import settings; print(settings.is_test_environment)")"

pre-commit-run:  ## Run pre-commit hooks on all files
	pre-commit run --all-files

# Tracker sync commands
sync-tracker:
	@echo "Syncing recent tracker tasks..."
	@python sync_tracker.py

sync-tracker-active:
	@echo "Syncing active tracker tasks..."
	@python sync_tracker.py --sync-mode active

sync-tracker-recent:
	@echo "Syncing recent tracker tasks (last 7 days)..."
	@python sync_tracker.py --days 7

sync-tracker-filter:
	@echo "Syncing tracker tasks with custom filters..."
	@python sync_tracker.py --sync-mode filter --status "In Progress" --limit 50

sync-tracker-file:
	@echo "Syncing tracker tasks from file (legacy mode)..."
	@python sync_tracker.py --sync-mode file --file-path tasks.txt

sync-tracker-debug:
	@echo "Syncing tracker data with debug..."
	@python sync_tracker.py --debug

sync-tracker-force:
	@echo "Force full sync of tracker data..."
	@python sync_tracker.py --force-full-sync

test-tracker-sync:
	@echo "Testing tracker sync system..."
	@python test_tracker_sync.py

# Tracker test commands
test-tracker:  ## Run all tracker-related tests
	@echo "Running all tracker tests..."
	pytest tests/test_tracker_sync.py tests/test_tracker_crud.py tests/test_tracker_api.py -v

test-tracker-unit:  ## Run tracker unit tests only
	@echo "Running tracker unit tests..."
	pytest tests/test_tracker_crud.py tests/test_tracker_api.py -v

test-tracker-integration:  ## Run tracker integration tests only
	@echo "Running tracker integration tests..."
	pytest tests/test_tracker_sync.py -v

test-tracker-crud:  ## Run tracker CRUD tests only
	@echo "Running tracker CRUD tests..."
	pytest tests/test_tracker_crud.py -v

test-tracker-api:  ## Run tracker API tests only
	@echo "Running tracker API tests..."
	pytest tests/test_tracker_api.py -v

test-tracker-coverage:  ## Run tracker tests with coverage report
	@echo "Running tracker tests with coverage..."
	pytest tests/test_tracker_sync.py tests/test_tracker_crud.py tests/test_tracker_api.py -v --cov=radiator.crud.tracker --cov=radiator.services.tracker_service --cov=radiator.commands.sync_tracker --cov-report=html

test-tracker-simple:  ## Run simple tracker tests (basic functionality)
	@echo "Running simple tracker tests..."
	pytest tests/test_tracker_simple.py -v
