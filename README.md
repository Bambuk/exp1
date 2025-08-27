# Radiator API

FastAPI-based REST API with PostgreSQL database, authentication, and Yandex Tracker integration.

## Features

- **FastAPI Framework**: Modern, fast web framework for building APIs
- **PostgreSQL Database**: Robust relational database with SQLAlchemy ORM
- **Authentication**: JWT-based authentication system
- **User Management**: User registration, login, and profile management
- **Item Management**: CRUD operations for items with user ownership
- **Yandex Tracker Integration**: Automatic synchronization of tasks and their history
- **Database Migrations**: Alembic-based database schema management
- **Testing**: Comprehensive test suite with pytest
- **Docker Support**: Containerized deployment with docker-compose

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL
- Docker (optional)

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

5. Start the application:
```bash
python run.py
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
.\setup_cron.ps1
```

For detailed documentation, see [TRACKER_SYNC_README.md](TRACKER_SYNC_README.md).

## API Documentation

Once the application is running, you can access:

- **API Documentation**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

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

## Docker Deployment

```bash
docker-compose up -d
```

## License

This project is licensed under the MIT License.
