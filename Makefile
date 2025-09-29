.PHONY: help install dev test lint format clean docker-build docker-run deploy migrate migrate-create migrate-status migrate-history migrate-downgrade migrate-reset db-init test-db-create test-db-drop test-db-reset test-env generate-status-report generate-status-report-teams generate-status-report-all sync-and-report generate-time-to-market-report generate-time-to-market-report-teams generate-time-to-market-report-all

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
	@echo '  sync-tracker       - Sync tracker tasks with custom filter and optional skip-history'
	@echo '  sync-tracker-*     - Various sync modes (active, recent, filter, file)'
	@echo '  sync-cpo*          - Sync CPO tasks (last 6 months, force, custom limit)'
	@echo ''
	@echo 'Tracker Test Commands:'
	@echo '  test-tracker*      - Run tracker tests (all, unit, integration, crud, api)'
	@echo '  test-tracker-coverage - Run tracker tests with coverage report'
	@echo ''
	@echo 'Status History Commands:'
	@echo '  generate-status-report - Generate CPO tasks status change report (last 2 weeks)'
	@echo '  sync-and-report - Complete CPO workflow: sync tasks + generate report'
	@echo ''
	@echo 'Time To Market Commands:'
	@echo '  generate-time-to-market-report - Generate TTD/TTM report by authors'
	@echo '  generate-time-to-market-report-teams - Generate TTD/TTM report by teams'
	@echo '  generate-time-to-market-report-all - Generate both author and team TTD/TTM reports'
	@echo ''
	@echo 'Google Sheets Commands:'
	@echo '  google-sheets-monitor - Start Google Sheets CSV uploader monitoring'

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

sync-tracker-active:
	@echo "Syncing active tracker tasks..."
	@python3 scripts/sync/sync_tracker.py --sync-mode active

sync-tracker-recent:
	@echo "Syncing recent tracker tasks (last 7 days)..."
	@python3 scripts/sync/sync_tracker.py --days 7

sync-tracker-filter:
	@echo "Syncing tracker tasks with custom filters..."
	@python3 scripts/sync/sync_tracker.py --sync-mode filter --status "In Progress" --limit 50

sync-tracker:  ## Sync tracker tasks with custom filter and optional skip-history
	@echo "Usage: make sync-tracker FILTER='<filter_string>' [SKIP_HISTORY=true]"
	@echo "Example: make sync-tracker FILTER='Queue: CPO Status: In Progress'"
	@echo "Example: make sync-tracker FILTER='key:CPO-*' SKIP_HISTORY=true"
	@if [ -n "$(FILTER)" ]; then \
		if [ "$(SKIP_HISTORY)" = "true" ]; then \
			python3 -m radiator.commands.sync_tracker --filter "$(FILTER)" --skip-history; \
		else \
			python3 -m radiator.commands.sync_tracker --filter "$(FILTER)"; \
		fi; \
	else \
		echo "Please specify FILTER parameter"; \
		echo "Example: make sync-tracker FILTER='Queue: CPO'"; \
		exit 1; \
	fi


sync-tracker-debug:
	@echo "Syncing tracker data with debug..."
	@python3 scripts/sync/sync_tracker.py --debug


# CPO sync commands
sync-cpo:  ## Sync CPO tasks for last 6 months
	@echo "Syncing CPO tasks for last 6 months..."
	@python3 scripts/sync/sync_cpo_tasks.py


sync-cpo-limit:  ## Sync CPO tasks with custom limit
	@echo "Usage: make sync-cpo-limit LIMIT=<number>"
	@echo "Example: make sync-cpo-limit LIMIT=500"
	@if [ -n "$(LIMIT)" ]; then \
		python3 -m radiator.commands.sync_tracker --filter "key:CPO-*" --limit $(LIMIT); \
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

# Google Sheets CSV Uploader commands
google-sheets-monitor: ## Start Google Sheets CSV uploader monitoring
	@echo "Starting Google Sheets CSV uploader monitoring..."
	@python3 scripts/google_sheets_csv_uploader.py --monitor

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
	@. venv/bin/activate && python -m radiator.commands.sync_tracker --filter "Queue: CPO Status: changed(date: today()-14d .. today())" || echo "⚠️ Sync completed with warnings"
	@echo ""
	@echo "Step 2/2: Generating status change report..."
	@. venv/bin/activate && python -m radiator.commands.generate_status_change_report
	@echo ""
	@echo "✅ Complete CPO workflow finished successfully!"

# Time To Market Report Commands
generate-time-to-market-report:  ## Generate Time To Delivery and Time To Market report by authors
	@echo "📊 Generating Time To Market report by authors..."
	@. venv/bin/activate && python -m radiator.commands.generate_time_to_market_report --group-by author --report-type both
	@echo ""
	@echo "✅ Time To Market report by authors generated successfully!"

generate-time-to-market-report-teams:  ## Generate Time To Delivery and Time To Market report by teams
	@echo "📊 Generating Time To Market report by teams..."
	@. venv/bin/activate && python -m radiator.commands.generate_time_to_market_report --group-by team --report-type both
	@echo ""
	@echo "✅ Time To Market report by teams generated successfully!"

generate-time-to-market-report-all:  ## Generate both author and team Time To Market reports
	@echo "📊 Generating Time To Market reports for both authors and teams..."
	@echo ""
	@echo "Step 1/2: Generating report by authors..."
	@. venv/bin/activate && python -m radiator.commands.generate_time_to_market_report --group-by author --report-type both
	@echo ""
	@echo "Step 2/2: Generating report by teams..."
	@. venv/bin/activate && python -m radiator.commands.generate_time_to_market_report --group-by team --report-type both
	@echo ""
	@echo "✅ Both Time To Market reports generated successfully!"
