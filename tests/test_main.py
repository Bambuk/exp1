"""Tests for main application."""

import pytest
from fastapi.testclient import TestClient


class TestMainApp:
    """Test main application endpoints."""

    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data
        assert "redoc" in data

    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data

    def test_docs_endpoint(self, client: TestClient):
        """Test docs endpoint."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_endpoint(self, client: TestClient):
        """Test redoc endpoint."""
        response = client.get("/redoc")
        assert response.status_code == 200

    def test_openapi_json(self, client: TestClient):
        """Test OpenAPI JSON endpoint."""
        response = client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data
