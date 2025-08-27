# Radiator API

FastAPI-based REST API for the Radiator project.

## Features

- FastAPI framework
- PostgreSQL database with SQLAlchemy ORM
- Alembic database migrations
- JWT authentication
- User management
- Item management
- Docker support
- Comprehensive testing

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
pip install -e ".[dev]"
```

3. Set up environment variables:
```bash
cp env.example .env
# Edit .env with your database credentials
```

4. Run database migrations:
```bash
# Using PowerShell script (Windows)
.\migrate.ps1 upgrade

# Or directly with Alembic
alembic upgrade head
```

5. Start the development server:
```bash
uvicorn radiator.main:app --reload
```

## Database Migrations

This project uses Alembic for database migrations. The initial migration has been created based on the existing database schema.

### Migration Commands

#### Using PowerShell Script (Windows)
```powershell
# Show current status
.\migrate.ps1 status

# Show migration history
.\migrate.ps1 history

# Create new migration
.\migrate.ps1 create "Description of changes"

# Apply migrations
.\migrate.ps1 upgrade

# Rollback one migration
.\migrate.ps1 downgrade

# Reset all migrations
.\migrate.ps1 reset
```

#### Using Alembic Directly
```bash
# Show current status
alembic current

# Show migration history
alembic history

# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Reset all migrations
alembic downgrade base
```

### Migration Files

- **Initial Migration**: `99e284f2522b_initial_migration_based_on_existing_.py`
  - Creates `users` and `items` tables
  - Sets up indexes and foreign key relationships
  - Removes old tables from previous schema

For detailed migration documentation, see [MIGRATIONS_README.md](MIGRATIONS_README.md).

## API Documentation

Once the server is running, you can access:

- **Interactive API docs**: http://localhost:8000/docs
- **ReDoc documentation**: http://localhost:8000/redoc
- **OpenAPI schema**: http://localhost:8000/openapi.json

## Development

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=radiator --cov-report=html
```

### Code Quality

```bash
# Format code
black radiator/ tests/
isort radiator/ tests/

# Lint code
flake8 radiator/ tests/
mypy radiator/
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

## Docker

### Build and Run

```bash
# Build image
docker build -t radiator-api .

# Run with Docker Compose
docker-compose up -d

# Stop services
docker-compose down
```

## Project Structure

```
radiator/
├── alembic/                 # Database migrations
│   ├── versions/           # Migration files
│   ├── env.py             # Alembic environment
│   └── script.py.mako     # Migration template
├── radiator/               # Main application code
│   ├── api/               # API endpoints
│   ├── core/              # Core functionality
│   ├── crud/              # Database operations
│   ├── models/            # Database models
│   └── schemas/           # Pydantic schemas
├── tests/                  # Test suite
├── migrate.ps1            # PowerShell migration helper
├── MIGRATIONS_README.md   # Migration documentation
└── README.md              # This file
```

## Environment Variables

Key environment variables (see `env.example` for full list):

- `DATABASE_URL`: Async PostgreSQL connection string
- `DATABASE_URL_SYNC`: Sync PostgreSQL connection string
- `SECRET_KEY`: JWT secret key
- `DEBUG`: Enable debug mode

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

[Add your license here]
