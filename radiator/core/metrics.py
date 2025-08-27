"""Prometheus metrics for monitoring."""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time

# Request metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"]
)

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
USER_COUNT = Gauge(
    "users_total",
    "Total number of users"
)

# Custom metrics
CUSTOM_EVENTS = Counter(
    "custom_events_total",
    "Total number of custom events",
    ["event_type"]
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Record metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        return response


def get_metrics():
    """Get Prometheus metrics."""
    return generate_latest()


def update_user_count(count: int):
    """Update user count metric."""
    USER_COUNT.set(count)


def increment_custom_event(event_type: str):
    """Increment custom event counter."""
    CUSTOM_EVENTS.labels(event_type=event_type).inc()


def update_db_connection_count(count: int):
    """Update database connection count metric."""
    DB_CONNECTION_GAUGE.set(count)
