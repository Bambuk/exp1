.PHONY: help install dev test lint format clean deploy migrate migrate-create migrate-status migrate-history migrate-downgrade migrate-reset db-init test-db-create test-db-drop test-db-reset test-env generate-status-report generate-status-report-teams sync-and-report generate-time-to-market-report generate-time-to-market-report-teams

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

lint:  ## Run linting
	flake8 radiator/ tests/
	mypy radiator/

format:  ## Format code
	black radiator/ tests/
	isort radiator/ tests/

clean:  ## Clean up generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .mypy_cache/

deploy:  ## Deploy to Ubuntu server
	@echo "Make sure you have access to the server and run:"
	@echo "bash deploy/deploy.sh"

migrate:  ## Run database migrations
	python3 scripts/database/migrate_db.py --env development

migrate-test:  ## Run database migrations for test environment
	python3 scripts/database/migrate_db.py --env test

migrate-check:  ## Check database tables without running migrations
	python3 scripts/database/migrate_db.py --env development --check-only

migrate-reset:  ## Reset database completely (WARNING: destroys all data)
	python3 scripts/database/reset_db.py --env development --recreate --force

migrate-reset-test:  ## Reset test database completely
	python3 scripts/database/reset_db.py --env test --recreate --force

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

# Tracker sync commands

sync-tracker:  ## Sync tracker tasks with custom filter and optional skip-history
	@echo "Usage: make sync-tracker FILTER='<filter_string>' [SKIP_HISTORY=true]"
	@echo "Example: make sync-tracker FILTER='Queue: CPO Status: In Progress'"
	@echo "Example: make sync-tracker FILTER='key:CPO-*' SKIP_HISTORY=true"
	@if [ -n "$(FILTER)" ]; then \
		if [ "$(SKIP_HISTORY)" = "true" ]; then \
			. venv/bin/activate && python -m radiator.commands.sync_tracker --filter "$(FILTER)" --skip-history; \
		else \
			. venv/bin/activate && python -m radiator.commands.sync_tracker --filter "$(FILTER)"; \
		fi; \
	else \
		echo "Please specify FILTER parameter"; \
		echo "Example: make sync-tracker FILTER='Queue: CPO'"; \
		exit 1; \
	fi



# Tracker test commands
test-tracker:  ## Run all tracker-related tests
	@echo "Running all tracker tests..."
	pytest tests/test_tracker_sync.py tests/test_tracker_crud.py tests/test_tracker_api.py -v

# Telegram Bot commands
telegram-bot: ## Start Telegram bot for reports monitoring
	@echo "Starting Telegram bot..."
	@. venv/bin/activate && python -m radiator.telegram_bot.main

telegram-test: ## Test Telegram bot connection
	@echo "Testing Telegram bot connection..."
	@. venv/bin/activate && python -m radiator.telegram_bot.main --test

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
	@. venv/bin/activate && python -m radiator.telegram_bot.main --reset

telegram-get-chat-id: ## Get Chat ID from Telegram bot
	@echo "Getting Chat ID from Telegram bot..."
	@python3 scripts/get_chat_id.py

# Google Sheets CSV Uploader commands
google-sheets-monitor: ## Start Google Sheets CSV uploader monitoring
	@echo "Starting Google Sheets CSV uploader monitoring..."
	@python3 scripts/google_sheets_csv_uploader.py --monitor

# Status change report commands
generate-status-report:  ## Generate CPO tasks status change report by authors (last 2 weeks)
	@echo "Generating CPO tasks status change report by authors for last 2 weeks..."
	@. venv/bin/activate && python -m radiator.commands.generate_status_change_report --group-by author

generate-status-report-teams:  ## Generate CPO tasks status change report by teams (last 2 weeks)
	@echo "Generating CPO tasks status change report by teams for last 2 weeks..."
	@. venv/bin/activate && python -m radiator.commands.generate_status_change_report --group-by team

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
