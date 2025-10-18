.PHONY: help install dev test lint format clean deploy migrate migrate-create migrate-status migrate-history migrate-downgrade migrate-reset db-init test-db-create test-db-drop test-db-reset test-env generate-status-report generate-status-report-teams sync-and-report generate-time-to-market-report generate-time-to-market-report-teams generate-time-to-market-report-long generate-time-to-market-report-teams-long db-snapshot db-snapshot-prod db-snapshot-test db-restore db-list-snapshots

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ''
	@echo 'Database Commands:'
	@echo '  db-init*           - Initialize main database'
	@echo '  test-db-*          - Manage test database (create, drop, reset)'
	@echo '  db-snapshot*       - Create database snapshots (both, prod-only, test-only)'
	@echo '  db-restore         - Restore database from snapshot (interactive)'
	@echo '  db-list-snapshots  - List all available snapshots'
	@echo ''
	@echo 'Tracker Sync Commands:'
	@echo '  sync-tracker       - Sync tracker tasks with custom filter, optional skip-history and limit'
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
	@echo '  generate-time-to-market-report - Generate TTD/TTM report by authors (wide format)'
	@echo '  generate-time-to-market-report-teams - Generate TTD/TTM report by teams (wide format)'
	@echo '  generate-time-to-market-report-long - Generate TTD/TTM report by authors (long format)'
	@echo '  generate-time-to-market-report-teams-long - Generate TTD/TTM report by teams (long format)'
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

migrate-reset-base:  ## Reset to base (remove all migrations)
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
	@if [ -n "$(FILTER)" ]; then \
		if [ "$(SKIP_HISTORY)" = "true" ]; then \
			if [ -n "$(LIMIT)" ]; then \
				. venv/bin/activate && python -m radiator.commands.sync_tracker --filter "$(FILTER)" --skip-history --limit $(LIMIT); \
			else \
				. venv/bin/activate && python -m radiator.commands.sync_tracker --filter "$(FILTER)" --skip-history; \
			fi; \
		else \
			if [ -n "$(LIMIT)" ]; then \
				. venv/bin/activate && python -m radiator.commands.sync_tracker --filter "$(FILTER)" --limit $(LIMIT); \
			else \
				. venv/bin/activate && python -m radiator.commands.sync_tracker --filter "$(FILTER)"; \
			fi; \
		fi; \
	else \
		echo "Usage: make sync-tracker FILTER='<filter_string>' [SKIP_HISTORY=true] [LIMIT=N]"; \
		echo "Example: make sync-tracker FILTER='Queue: CPO Status: In Progress' LIMIT=50"; \
		echo "Example: make sync-tracker FILTER='key:CPO-*' SKIP_HISTORY=true LIMIT=100"; \
		echo "Please specify FILTER parameter"; \
		exit 1; \
	fi

sync-tracker-by-keys:  ## Sync tracker tasks by keys from file in batches
	@if [ -n "$(FILE)" ]; then \
		. venv/bin/activate && python scripts/sync_by_keys.py --file "$(FILE)" $(EXTRA_ARGS); \
	else \
		echo "Usage: make sync-tracker-by-keys FILE=path/to/keys.txt [EXTRA_ARGS='--batch-size 200']"; \
		echo "Example: make sync-tracker-by-keys FILE=data/input/my_keys.txt"; \
		echo "Example: make sync-tracker-by-keys FILE=data/input/my_keys.txt EXTRA_ARGS='--batch-size 100 --skip-history'"; \
		echo "Please specify FILE parameter"; \
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

telegram-service-status: ## Check Telegram bot systemd service status
	@echo "Checking Telegram bot service status..."
	@systemctl --user status radiator-telegram-bot.service

telegram-service-start: ## Start Telegram bot systemd service
	@echo "Starting Telegram bot service..."
	@systemctl --user start radiator-telegram-bot.service
	@echo "✅ Telegram bot service started!"

telegram-service-stop: ## Stop Telegram bot systemd service
	@echo "Stopping Telegram bot service..."
	@systemctl --user stop radiator-telegram-bot.service
	@echo "✅ Telegram bot service stopped!"

telegram-service-restart: ## Restart Telegram bot systemd service
	@echo "Restarting Telegram bot service..."
	@systemctl --user restart radiator-telegram-bot.service
	@echo "✅ Telegram bot service restarted!"

telegram-service-logs: ## View Telegram bot service logs
	@echo "Viewing Telegram bot service logs (press Ctrl+C to exit)..."
	@journalctl --user -u radiator-telegram-bot.service -f

# Google Sheets CSV Uploader commands
google-sheets-monitor: ## Start Google Sheets CSV uploader monitoring
	@echo "Starting Google Sheets CSV uploader monitoring..."
	@python3 scripts/google_sheets_csv_uploader.py --monitor

google-sheets-process-pivots: ## Process CSV files with pivot upload markers
	@echo "Processing CSV files with pivot upload markers..."
	@python3 scripts/google_sheets_csv_uploader.py --process-pivot-markers

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
	@. venv/bin/activate && python -m radiator.commands.sync_tracker --filter "Queue: CPO Updated: >=today()-14d" || echo "⚠️ Sync completed with warnings"
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

generate-time-to-market-report-long:  ## Generate Time To Delivery and Time To Market report by authors (long format)
	@echo "📊 Generating Time To Market report by authors (long format)..."
	@. venv/bin/activate && python -m radiator.commands.generate_time_to_market_report --group-by author --report-type both --csv-format long
	@echo ""
	@echo "✅ Time To Market report by authors (long format) generated successfully!"

generate-time-to-market-report-teams-long:  ## Generate Time To Delivery and Time To Market report by teams (long format)
	@echo "📊 Generating Time To Market report by teams (long format)..."
	@. venv/bin/activate && python -m radiator.commands.generate_time_to_market_report --group-by team --report-type both --csv-format long
	@echo ""
	@echo "✅ Time To Market report by teams (long format) generated successfully!"

# Database snapshot and restore commands
db-snapshot:  ## Create snapshot of both production and test databases
	@echo "📸 Creating snapshot of both databases..."
	@mkdir -p .snapshots
	@TIMESTAMP=$$(date +%Y-%m-%d_%H-%M-%S); \
	SNAPSHOT_DIR=".snapshots/snapshot_$$TIMESTAMP"; \
	mkdir -p "$$SNAPSHOT_DIR"; \
	set -a; [ -f env.local ] && . ./env.local || . ./.env; set +a; \
	DB_URL="$$DATABASE_URL_SYNC"; \
	DB_HOST=$$(echo $$DB_URL | sed -n 's|.*@\([^:]*\):.*|\1|p'); \
	DB_PORT=$$(echo $$DB_URL | sed -n 's|.*:\([0-9]*\)/.*|\1|p'); \
	DB_USER=$$(echo $$DB_URL | sed -n 's|.*//\([^:]*\):.*|\1|p'); \
	DB_PASS=$$(echo $$DB_URL | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p'); \
	DB_NAME=$$(echo $$DB_URL | sed -n 's|.*/\([^?]*\).*|\1|p'); \
	echo "📦 Dumping $$DB_NAME..."; \
	PGPASSWORD=$$DB_PASS pg_dump -h $$DB_HOST -p $$DB_PORT -U $$DB_USER -d $$DB_NAME -F c -f "$$SNAPSHOT_DIR/$$DB_NAME.dump"; \
	echo "📦 Dumping radiator_test..."; \
	PGPASSWORD=$$DB_PASS pg_dump -h $$DB_HOST -p $$DB_PORT -U $$DB_USER -d radiator_test -F c -f "$$SNAPSHOT_DIR/radiator_test.dump" || echo "⚠️  radiator_test not found, skipping"; \
	echo "🗜️  Creating archive..."; \
	tar -czf ".snapshots/snapshot_$$TIMESTAMP.tar.gz" -C .snapshots "snapshot_$$TIMESTAMP"; \
	rm -rf "$$SNAPSHOT_DIR"; \
	echo "✅ Snapshot created: .snapshots/snapshot_$$TIMESTAMP.tar.gz"

db-snapshot-prod:  ## Create snapshot of production database only
	@echo "📸 Creating snapshot of production database..."
	@mkdir -p .snapshots
	@TIMESTAMP=$$(date +%Y-%m-%d_%H-%M-%S); \
	SNAPSHOT_DIR=".snapshots/snapshot_$$TIMESTAMP"; \
	mkdir -p "$$SNAPSHOT_DIR"; \
	set -a; [ -f env.local ] && . ./env.local || . ./.env; set +a; \
	DB_URL="$$DATABASE_URL_SYNC"; \
	DB_HOST=$$(echo $$DB_URL | sed -n 's|.*@\([^:]*\):.*|\1|p'); \
	DB_PORT=$$(echo $$DB_URL | sed -n 's|.*:\([0-9]*\)/.*|\1|p'); \
	DB_USER=$$(echo $$DB_URL | sed -n 's|.*//\([^:]*\):.*|\1|p'); \
	DB_PASS=$$(echo $$DB_URL | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p'); \
	DB_NAME=$$(echo $$DB_URL | sed -n 's|.*/\([^?]*\).*|\1|p'); \
	echo "📦 Dumping $$DB_NAME..."; \
	PGPASSWORD=$$DB_PASS pg_dump -h $$DB_HOST -p $$DB_PORT -U $$DB_USER -d $$DB_NAME -F c -f "$$SNAPSHOT_DIR/$$DB_NAME.dump"; \
	echo "🗜️  Creating archive..."; \
	tar -czf ".snapshots/snapshot_$$TIMESTAMP.tar.gz" -C .snapshots "snapshot_$$TIMESTAMP"; \
	rm -rf "$$SNAPSHOT_DIR"; \
	echo "✅ Snapshot created: .snapshots/snapshot_$$TIMESTAMP.tar.gz"

db-snapshot-test:  ## Create snapshot of test database only
	@echo "📸 Creating snapshot of test database..."
	@mkdir -p .snapshots
	@TIMESTAMP=$$(date +%Y-%m-%d_%H-%M-%S); \
	SNAPSHOT_DIR=".snapshots/snapshot_$$TIMESTAMP"; \
	mkdir -p "$$SNAPSHOT_DIR"; \
	set -a; [ -f env.local ] && . ./env.local || . ./.env; set +a; \
	DB_URL="$$DATABASE_URL_SYNC"; \
	DB_HOST=$$(echo $$DB_URL | sed -n 's|.*@\([^:]*\):.*|\1|p'); \
	DB_PORT=$$(echo $$DB_URL | sed -n 's|.*:\([0-9]*\)/.*|\1|p'); \
	DB_USER=$$(echo $$DB_URL | sed -n 's|.*//\([^:]*\):.*|\1|p'); \
	DB_PASS=$$(echo $$DB_URL | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p'); \
	echo "📦 Dumping radiator_test..."; \
	PGPASSWORD=$$DB_PASS pg_dump -h $$DB_HOST -p $$DB_PORT -U $$DB_USER -d radiator_test -F c -f "$$SNAPSHOT_DIR/radiator_test.dump"; \
	echo "🗜️  Creating archive..."; \
	tar -czf ".snapshots/snapshot_$$TIMESTAMP.tar.gz" -C .snapshots "snapshot_$$TIMESTAMP"; \
	rm -rf "$$SNAPSHOT_DIR"; \
	echo "✅ Snapshot created: .snapshots/snapshot_$$TIMESTAMP.tar.gz"

db-restore:  ## Restore database from snapshot (interactive selection)
	@echo "🔄 Available snapshots:"
	@ls -1t .snapshots/*.tar.gz 2>/dev/null | nl || echo "No snapshots found"
	@read -p "Enter snapshot number: " NUM; \
	SNAPSHOT=$$(ls -1t .snapshots/*.tar.gz | sed -n "$${NUM}p"); \
	if [ -z "$$SNAPSHOT" ]; then echo "❌ Invalid selection"; exit 1; fi; \
	echo "📦 Extracting $$SNAPSHOT..."; \
	TEMP_DIR=$$(mktemp -d); \
	tar -xzf "$$SNAPSHOT" -C "$$TEMP_DIR"; \
	SNAPSHOT_NAME=$$(basename "$$SNAPSHOT" .tar.gz); \
	set -a; [ -f env.local ] && . ./env.local || . ./.env; set +a; \
	DB_URL="$$DATABASE_URL_SYNC"; \
	DB_HOST=$$(echo $$DB_URL | sed -n 's|.*@\([^:]*\):.*|\1|p'); \
	DB_PORT=$$(echo $$DB_URL | sed -n 's|.*:\([0-9]*\)/.*|\1|p'); \
	DB_USER=$$(echo $$DB_URL | sed -n 's|.*//\([^:]*\):.*|\1|p'); \
	DB_PASS=$$(echo $$DB_URL | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p'); \
	DB_NAME=$$(echo $$DB_URL | sed -n 's|.*/\([^?]*\).*|\1|p'); \
	if [ -f "$$TEMP_DIR/$$SNAPSHOT_NAME/$$DB_NAME.dump" ]; then \
		echo "🔄 Restoring $$DB_NAME..."; \
		PGPASSWORD=$$DB_PASS pg_restore -h $$DB_HOST -p $$DB_PORT -U $$DB_USER -d $$DB_NAME -c "$$TEMP_DIR/$$SNAPSHOT_NAME/$$DB_NAME.dump" 2>/dev/null || true; \
	fi; \
	if [ -f "$$TEMP_DIR/$$SNAPSHOT_NAME/radiator_test.dump" ]; then \
		echo "🔄 Restoring radiator_test..."; \
		PGPASSWORD=$$DB_PASS pg_restore -h $$DB_HOST -p $$DB_PORT -U $$DB_USER -d radiator_test -c "$$TEMP_DIR/$$SNAPSHOT_NAME/radiator_test.dump" 2>/dev/null || true; \
	fi; \
	rm -rf "$$TEMP_DIR"; \
	echo "✅ Restore complete"

db-list-snapshots:  ## List all available snapshots
	@echo "📸 Available snapshots:"
	@ls -lht .snapshots/*.tar.gz 2>/dev/null | awk '{print $$9, "(" $$5 ")", $$6, $$7, $$8}' || echo "No snapshots found"
