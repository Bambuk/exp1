"""Metrics for CLI application monitoring."""

from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Database metrics
DB_CONNECTION_GAUGE = Gauge(
    "database_connections_active",
    "Number of active database connections"
)

DB_QUERY_DURATION = Histogram(
    "database_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"]
)

# Business metrics
TASK_COUNT = Gauge(
    "tasks_total",
    "Total number of tasks"
)

# Custom metrics
CUSTOM_EVENTS = Counter(
    "custom_events_total",
    "Total number of custom events",
    ["event_type"]
)

# CLI operation metrics
CLI_OPERATION_DURATION = Histogram(
    "cli_operation_duration_seconds",
    "CLI operation duration in seconds",
    ["operation"]
)

CLI_OPERATION_COUNT = Counter(
    "cli_operations_total",
    "Total number of CLI operations",
    ["operation", "status"]
)


def get_metrics():
    """Get Prometheus metrics."""
    return generate_latest()


def update_task_count(count: int):
    """Update task count metric."""
    TASK_COUNT.set(count)


def increment_custom_event(event_type: str):
    """Increment custom event counter."""
    CUSTOM_EVENTS.labels(event_type=event_type).inc()


def update_db_connection_count(count: int):
    """Update database connection count metric."""
    DB_CONNECTION_GAUGE.set(count)


def record_cli_operation(operation: str, duration: float, status: str = "success"):
    """Record CLI operation metrics."""
    CLI_OPERATION_DURATION.labels(operation=operation).observe(duration)
    CLI_OPERATION_COUNT.labels(operation=operation, status=status).inc()
