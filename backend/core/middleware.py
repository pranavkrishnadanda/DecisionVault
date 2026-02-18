"""Middleware for request-scoped tracing context."""

from __future__ import annotations

import uuid

from core.observability import reset_context, set_request_id


class RequestContextMiddleware:
    """Attach request id to context and response headers."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.META.get("HTTP_X_REQUEST_ID") or str(uuid.uuid4())
        token = set_request_id(request_id)
        request.request_id = request_id

        try:
            response = self.get_response(request)
        finally:
            reset_context(token)

        response["X-Request-ID"] = request_id
        return response
