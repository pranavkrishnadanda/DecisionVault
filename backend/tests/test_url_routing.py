"""
Tests for URL routing and health endpoints.

Verifies that:
- Root URL configuration includes all module URLs
- Health check endpoint returns 200 OK
- Each module has its base endpoint configured
"""

import pytest
from django.urls import resolve, reverse


class TestHealthEndpoint:
    """Test the health check endpoint."""

    def test_health_endpoint_exists(self):
        """
        Health endpoint should be resolvable.

        This endpoint is critical for:
        - Load balancer health checks
        - Kubernetes readiness probes
        - Monitoring systems
        """
        url = reverse("api:health")
        assert url == "/api/v1/health/"

    def test_health_endpoint_returns_200(self, client):
        """
        Health endpoint should return HTTP 200.

        Response should be JSON with status information.
        """
        response = client.get("/api/v1/health/")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/json"

    def test_health_endpoint_returns_request_id_header(self, client):
        response = client.get("/api/v1/health/")

        assert response.status_code == 200
        assert "X-Request-ID" in response
        assert response["X-Request-ID"]

    def test_health_endpoint_returns_status_ok(self, client):
        """
        Health endpoint should return status: ok.
        """
        response = client.get("/api/v1/health/")
        data = response.json()
        assert data["status"] == "ok"

    def test_health_endpoint_has_version(self, client):
        """
        Health endpoint should include version information.
        """
        response = client.get("/api/v1/health/")
        data = response.json()
        assert "version" in data


class TestModuleURLs:
    """Test that each module has URL configuration."""

    def test_api_urls_included(self):
        """
        API URLs should be included in root URLconf.
        """
        # Verify /api/v1/ prefix resolves
        match = resolve("/api/v1/health/")
        assert match.url_name == "health"

    def test_ingestion_base_endpoint_exists(self):
        """
        Ingestion module should have a base endpoint.

        This will be used for data ingestion operations.
        """
        # Endpoint should be defined (will fail until implemented)
        url = reverse("ingestion:ingestion-base")
        assert url == "/api/ingestion/"

    def test_verification_base_endpoint_exists(self):
        """
        Verification module should have a base endpoint.

        This will be used for verification workflows.
        """
        url = reverse("verification:verification-base")
        assert url == "/api/verification/"

    def test_workers_base_endpoint_exists(self):
        """
        Workers module should have a base endpoint.

        This will be used for worker status and job management.
        """
        url = reverse("workers:workers-base")
        assert url == "/api/workers/"


class TestURLNamespaces:
    """Test URL namespace configuration."""

    def test_api_namespace_exists(self):
        """
        API URLs should be namespaced under 'api'.
        """
        from django.urls import get_resolver

        resolver = get_resolver()

        # Drill down to find api namespace
        api_patterns = None
        for pattern in resolver.url_patterns:
            if hasattr(pattern, "namespace") and pattern.namespace == "api":
                api_patterns = pattern
                break

        assert api_patterns is not None, "API namespace not found in URL patterns"
