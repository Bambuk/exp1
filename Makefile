.PHONY: help install dev test lint format clean docker-build docker-run deploy migrate migrate-create migrate-status migrate-history migrate-downgrade migrate-reset db-init test-db-create test-db-drop test-db-reset test-env update-status-history update-status-history-cpo update-status-history-dev update-status-history-qa update-status-history-custom generate-status-report generate-status-report-teams generate-status-report-all sync-and-report

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
	@echo '  sync-cpo*          - Sync CPO tasks (last 6 months, force, custom limit)'
	@echo ''
	@echo 'Tracker Test Commands:'
	@echo '  test-tracker*      - Run tracker tests (all, unit, integration, crud, api)'
	@echo '  test-tracker-coverage - Run tracker tests with coverage report'
	@echo ''
	@echo 'Status History Commands:'
	@echo '  update-status-history* - Update status history for tasks'
	@echo '  update-status-history-cpo - Update CPO queue status history (last 14 days)'
	@echo '  update-status-history-dev - Update DEV queue status history (last 7 days)'
	@echo '  update-status-history-qa - Update QA queue status history (last 30 days)'
	@echo '  generate-status-report - Generate CPO tasks status change report (last 2 weeks)'
	@echo '  sync-and-report - Complete CPO workflow: sync tasks + generate report'

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
	python3 -c "import asyncio; from radiator.core.database import init_db; asyncio.run(init_db())"

# Test database management commands
test-db-create:  ## Create test database
	@echo "Creating test database 'radiator_test'..."
	python3 scripts/database/create_test_db.py

test-db-drop:  ## Drop test database
	@echo "Dropping test database 'radiator_test'..."
	python3 scripts/database/create_test_db.py --drop

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
	@python3 scripts/sync/sync_tracker.py

sync-tracker-active:
	@echo "Syncing active tracker tasks..."
	@python3 scripts/sync/sync_tracker.py --sync-mode active

sync-tracker-recent:
	@echo "Syncing recent tracker tasks (last 7 days)..."
	@python3 scripts/sync/sync_tracker.py --days 7

sync-tracker-filter:
	@echo "Syncing tracker tasks with custom filters..."
	@python3 scripts/sync/sync_tracker.py --sync-mode filter --status "In Progress" --limit 50


sync-tracker-debug:
	@echo "Syncing tracker data with debug..."
	@python3 scripts/sync/sync_tracker.py --debug

sync-tracker-force:
	@echo "Force full sync of tracker data..."
	@python3 scripts/sync/sync_tracker.py --force-full-sync

# CPO sync commands
sync-cpo:  ## Sync CPO tasks for last 6 months
	@echo "Syncing CPO tasks for last 6 months..."
	@python3 scripts/sync/sync_cpo_tasks.py

sync-cpo-force:  ## Force full sync of CPO tasks
	@echo "Force full sync of CPO tasks..."
	@python3 -m radiator.commands.sync_tracker --filter "key:CPO-*" --limit 1000 --force-full-sync

sync-cpo-limit:  ## Sync CPO tasks with custom limit
	@echo "Usage: make sync-cpo-limit LIMIT=<number>"
	@echo "Example: make sync-cpo-limit LIMIT=500"
	@if [ -n "$(LIMIT)" ]; then \
		python3 -m radiator.commands.sync_tracker --filter "key:CPO-*" --limit $(LIMIT) --force-full-sync; \
	else \
		echo "Please specify LIMIT parameter"; \
		exit 1; \
	fi


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

# Status history update commands
update-status-history:  ## Update status history for tasks (default: CPO queue, last 14 days)
	@echo "Updating status history for CPO queue (last 14 days)..."
	@python3 radiator/commands/update_status_history.py --queue CPO --days 14

update-status-history-cpo:  ## Update CPO queue status history (last 14 days)
	@echo "Updating status history for CPO queue (last 14 days)..."
	@python3 radiator/commands/update_status_history.py --queue CPO --days 14

update-status-history-dev:  ## Update DEV queue status history (last 7 days)
	@echo "Updating status history for DEV queue (last 7 days)..."
	@python3 radiator/commands/update_status_history.py --queue DEV --days 7

update-status-history-qa:  ## Update QA queue status history (last 30 days)
	@echo "Updating status history for QA queue (last 30 days)..."
	@python3 radiator/commands/update_status_history.py --queue QA --days 30

update-status-history-custom:  ## Update status history with custom parameters
	@echo "Usage: make update-status-history-custom QUEUE=<queue> DAYS=<days> LIMIT=<limit>"
	@echo "Example: make update-status-history-custom QUEUE=SUPPORT DAYS=7 LIMIT=500"
	@if [ -n "$(QUEUE)" ] && [ -n "$(DAYS)" ]; then \
		python3 radiator/commands/update_status_history.py --queue $(QUEUE) --days $(DAYS) --limit $(LIMIT:-1000); \
	else \
		echo "Please specify QUEUE and DAYS parameters"; \
		exit 1; \
	fi

# Telegram Bot commands
telegram-bot: ## Start Telegram bot for reports monitoring
	@echo "Starting Telegram bot..."
	@python3 -m radiator.telegram_bot.main

telegram-test: ## Test Telegram bot connection
	@echo "Testing Telegram bot connection..."
	@python3 -m radiator.telegram_bot.main --test

telegram-config: ## Show Telegram bot configuration
	@echo "Telegram bot configuration:"
	@python3 -m radiator.telegram_bot.main --config

telegram-reset: ## Reset Telegram bot file monitoring state
	@echo "Resetting Telegram bot file monitoring state..."
	@echo ""
	@echo "⚠️  WHEN TO USE telegram-reset:"
	@echo "   • When you want to re-send ALL existing files in reports/ folder"
	@echo "   • After manually cleaning up old reports and want to re-sync"
	@echo "   • For testing purposes to verify bot functionality"
	@echo ""
	@echo "❌ WHEN NOT TO USE telegram-reset:"
	@echo "   • For normal operation - bot automatically detects new files"
	@echo "   • After generating new reports - bot will find them automatically"
	@echo "   • Just to restart the bot - use telegram-bot instead"
	@echo ""
	@echo "💡 NORMAL WORKFLOW:"
	@echo "   1. make telegram-bot          # Start bot (it remembers sent files)"
	@echo "   2. Generate new report       # Bot automatically finds and sends it"
	@echo "   3. No need to reset anything!"
	@echo ""
	@python3 -m radiator.telegram_bot.main --reset

telegram-cleanup: ## Clean up old files from Telegram bot state
	@echo "Cleaning up old files from Telegram bot state..."
	@python3 -m radiator.telegram_bot.main --cleanup

telegram-get-chat-id: ## Get Chat ID from Telegram bot
	@echo "Getting Chat ID from Telegram bot..."
	@python3 scripts/get_chat_id.py

telegram-simple-chat-id: ## Get Chat ID using simple method
	@echo "Getting Chat ID using simple method..."
	@python3 scripts/simple_chat_id.py

# Status change report commands
generate-status-report:  ## Generate CPO tasks status change report by authors (last 2 weeks)
	@echo "Generating CPO tasks status change report by authors for last 2 weeks..."
	@python3 -m radiator.commands.generate_status_change_report --group-by author

generate-status-report-teams:  ## Generate CPO tasks status change report by teams (last 2 weeks)
	@echo "Generating CPO tasks status change report by teams for last 2 weeks..."
	@python3 -m radiator.commands.generate_status_change_report --group-by team

generate-status-report-all:  ## Generate both author and team reports (last 2 weeks)
	@echo "Generating CPO tasks status change reports for last 2 weeks..."
	@echo "Generating report by authors..."
	@python3 -m radiator.commands.generate_status_change_report --group-by author
	@echo ""
	@echo "Generating report by teams..."
	@python3 -m radiator.commands.generate_status_change_report --group-by team
	@echo ""
	@echo "✅ Both reports generated successfully!"

sync-and-report:  ## Sync CPO tasks and generate status report (complete workflow)
	@echo "🔄 Starting complete CPO workflow: sync + report generation..."
	@echo ""
	@echo "Step 1/2: Syncing CPO tasks (last 14 days)..."
	@. venv/bin/activate && python -m radiator.commands.sync_tracker --filter "Queue: CPO Status: changed(date: today()-14d .. today())"
	@echo ""
	@echo "Step 2/2: Generating status change report..."
	@. venv/bin/activate && python radiator/commands/generate_status_change_report.py
	@echo ""
	@echo "✅ Complete CPO workflow finished successfully!"
