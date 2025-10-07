# Radiator CLI

Command-line tool for Yandex Tracker integration, task synchronization, and reporting.

## Features

- **Yandex Tracker Integration**: Automatic synchronization of tasks and their history
- **PostgreSQL Database**: Robust relational database with SQLAlchemy ORM
- **Status Change Reports**: Generate comprehensive reports on task status changes
- **Time to Market Reports**: Analyze task completion timelines (TTD/TTM metrics)
- **Google Sheets Integration**: Upload reports to Google Sheets
- **Telegram Bot**: Automated file monitoring and processing
- **Database Migrations**: Alembic-based database schema management
- **Testing**: Comprehensive test suite with pytest

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd radiator
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp env.example .env
# Edit .env with your configuration
```

4. Run database migrations:
```bash
alembic upgrade head
```

5. Run CLI commands:
```bash
# Generate status change report
python -m radiator.commands.generate_status_change_report

# Generate time to market report
python -m radiator.commands.generate_time_to_market_report

# Sync with Tracker
python -m radiator.commands.sync_tracker
```

## Yandex Tracker Integration

The application includes a powerful Yandex Tracker integration system that automatically syncs task data and history:

### Features

- **Automatic Sync**: Cron-based synchronization of tracker data
- **Incremental Updates**: Only syncs new or modified data
- **Parallel Processing**: Fast synchronization with multiple workers
- **History Tracking**: Complete status change history for all tasks
- **Comprehensive Logging**: Detailed logs of all sync operations

### Setup

1. Configure tracker API credentials in `.env`:
```bash
TRACKER_API_TOKEN=your_oauth_token
TRACKER_ORG_ID=your_organization_id
```

2. Create a task list file (`tasks.txt`):
```txt
12345
67890
11111
```

3. Run synchronization:
```bash
# Manual sync
python sync_tracker.py tasks.txt

# Via Makefile
make sync-tracker

# Test the system
make test-tracker-sync
```

4. Set up automatic sync:
```bash
# Linux/macOS
chmod +x setup_cron.sh
./setup_cron.sh

# Windows
bash setup_cron.sh

## Status Change Reports

Generate comprehensive reports on CPO task status changes and author activity:

### Quick Report Generation

```bash
# Generate report with default settings
make generate-status-report

# Or run directly
python -m radiator.commands.generate_status_change_report

# With custom filenames
python -m radiator.commands.generate_status_change_report --csv my_report.csv --table my_table.png
```

### Report Features

- **2-Week Analysis**: Status changes and task counts for last 2 weeks
- **Author Activity**: Per-author breakdown of changes and tasks
- **Dynamic Indicators**: Visual arrows showing trends (▲ ▼ →)
- **Block Analysis**: Discovery vs Delivery task distribution with last change dates
- **Multiple Formats**: CSV export and visual PNG table

### Output Files

Reports are saved to the `reports/` folder:
- `status_change_report_YYYYMMDD_HHMMSS.csv` - Data export
- `status_change_table_YYYYMMDD_HHMMSS.png` - Visual table

See [Status Change Report Guide](docs/guides/STATUS_CHANGE_REPORT_GUIDE.md) for detailed usage instructions.

## Time to Market Reports

Generate comprehensive reports on task completion timelines with TTD/TTM metrics:

### Quick Report Generation

```bash
# Generate report with default settings
make generate-time-to-market-report

# Or run directly
python -m radiator.commands.generate_time_to_market_report

# Group by teams
python -m radiator.commands.generate_time_to_market_report --group-by team
```

### Report Features

- **TTD (Time To Delivery)**: Days from task creation to "Готова к разработке" status
- **TTM (Time To Market)**: Days from task creation to completion (done status)
- **Pause Time Handling**: Automatically excludes time spent in "Приостановлено" status
- **Status Duration Metrics**: Time spent in "Discovery backlog" and "Готова к разработке" statuses (v2.1)
- **Quarterly Analysis**: Tasks grouped by quarters based on target status dates
- **Statistical Metrics**: Mean and 85th percentile calculations
- **Multiple Formats**: CSV export and visual PNG tables

### Output Files

Reports are saved to the `reports/` folder:
- `time_to_market_report_YYYYMMDD_HHMMSS.csv` - Data export
- `time_to_market_table_YYYYMMDD_HHMMSS.png` - Visual table

See [Time to Market Report Guide](docs/guides/TIME_TO_MARKET_REPORT_GUIDE.md) for detailed usage instructions.

For detailed documentation, see [TRACKER_SYNC_README.md](TRACKER_SYNC_README.md).

## Telegram Bot Service

The application includes a Telegram bot for automated file monitoring and processing. The bot is configured to run as a systemd service for automatic startup.

### Service Management

The Telegram bot runs as a systemd user service and can be managed with the following commands:

```bash
# Check service status
systemctl --user status radiator-telegram-bot.service

# Start the service
systemctl --user start radiator-telegram-bot.service

# Stop the service
systemctl --user stop radiator-telegram-bot.service

# Restart the service
systemctl --user restart radiator-telegram-bot.service

# Enable auto-start (runs automatically on login)
systemctl --user enable radiator-telegram-bot.service

# Disable auto-start
systemctl --user disable radiator-telegram-bot.service

# View logs
journalctl --user -u radiator-telegram-bot.service -f
```

### Manual Bot Control

You can also run the bot manually using Makefile commands:

```bash
# Start bot manually
make telegram-bot

# Test bot connection
make telegram-test

# Reset bot state (re-send all files)
make telegram-reset
```

### Service Files

- **Service file**: `~/.config/systemd/user/radiator-telegram-bot.service`
- **Startup script**: `start-telegram-bot.sh`
- **Service is enabled by default** and will start automatically on user login

For detailed service management instructions, see [Telegram Bot Service Guide](docs/guides/TELEGRAM_BOT_SERVICE_GUIDE.md).

## CLI Commands

The application provides several CLI commands for different operations:

- **Status Change Reports**: Generate reports on task status changes
- **Time to Market Reports**: Analyze task completion timelines
- **Tracker Sync**: Synchronize data with Yandex Tracker
- **Search Tasks**: Search and filter tasks from the database

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black .
isort .
```

### Pre-commit Hooks

```bash
pre-commit install
pre-commit run --all-files
```

## Documentation

- [Time to Market Report Guide](docs/guides/TIME_TO_MARKET_REPORT_GUIDE.md) - User guide for TTM/TTD reports
- [TTM/TTD Calculation Details](TTM_TTD_CALCULATION.md) - Technical documentation of calculation algorithms
- [Status Change Report Guide](docs/guides/STATUS_CHANGE_REPORT_GUIDE.md) - User guide for status change reports
- [Tracker Sync Guide](docs/guides/TRACKER_SYNC_README.md) - Yandex Tracker integration guide

## License

This project is licensed under the MIT License.
