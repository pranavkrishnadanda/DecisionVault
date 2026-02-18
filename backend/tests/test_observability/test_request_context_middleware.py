"""Request context middleware tests for Phase 3.0."""

from django.http import JsonResponse
from django.test import RequestFactory


def test_middleware_generates_request_id_header():
    from core.middleware import RequestContextMiddleware

    factory = RequestFactory()
    request = factory.get("/api/v1/health/")

    middleware = RequestContextMiddleware(lambda req: JsonResponse({"ok": True}))
    response = middleware(request)

    assert "X-Request-ID" in response
    assert response["X-Request-ID"]


def test_middleware_propagates_incoming_request_id_header():
    from core.middleware import RequestContextMiddleware

    factory = RequestFactory()
    request = factory.get("/api/v1/health/", HTTP_X_REQUEST_ID="req-incoming-123")

    middleware = RequestContextMiddleware(lambda req: JsonResponse({"ok": True}))
    response = middleware(request)

    assert response["X-Request-ID"] == "req-incoming-123"
