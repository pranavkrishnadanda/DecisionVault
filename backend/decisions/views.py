"""
DRF ViewSets for DecisionVault.
"""

import datetime as dt
import uuid

from django.db.models import Q
from django.http import StreamingHttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import (
    NotFound,
    ValidationError,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models import (
    WEBHOOK_EVENT_DECISION_CREATED,
    WEBHOOK_EVENT_DECISION_RETRY_REQUESTED,
    WEBHOOK_EVENT_DECISION_SUBMITTED,
    OrganizationRole,
)
from api.services.webhook_dispatcher import dispatch_event_to_webhooks
from core.permissions import (
    get_user_membership_or_raise,
    require_decision_access_or_404,
    require_read_role,
    require_write_role,
    resolve_org_decision_or_404,
    scope_queryset_to_membership,
)
from decisions.models import Decision, DecisionStatus
from decisions.realtime import decision_event_broker, event_stream_generator
from decisions.renderers import ServerSentEventRenderer
from decisions.serializers import DecisionSerializer, DecisionSubmitSerializer
from decisions.services import AuditLogService, DecisionWorkflowService


class DecisionViewSet(viewsets.ViewSet):
    """
    ViewSet for Decision operations.

    Endpoints:
        POST /api/v1/decisions/ - Create decision
        GET  /api/v1/decisions/{id}/ - Retrieve decision
        POST /api/v1/decisions/{id}/submit/ - Submit decision
    """

    serializer_class = DecisionSerializer
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _publish_decision_event(decision: Decision) -> None:
        serialized = DecisionSerializer(decision).data
        decision_event_broker.publish(
            event_name="decision.upsert",
            payload={
                "type": "decision.upsert",
                "decision": serialized,
            },
        )

    def list(self, request):
        """
        List decisions for operator dashboard.

        Access policy:
            - Staff/superuser: can view all decisions
            - Regular user: can view only owned decisions
        """
        membership = get_user_membership_or_raise(request.user)
        require_read_role(membership)
        queryset = scope_queryset_to_membership(Decision.objects.all(), membership)
        if membership.role != OrganizationRole.ADMIN:
            user_id = str(request.user.id) if request.user.id is not None else ""
            username = request.user.get_username()
            queryset = queryset.filter(Q(created_by=user_id) | Q(created_by=username))

        status_param = request.query_params.get("status")
        if status_param:
            statuses = [
                item.strip().lower() for item in status_param.split(",") if item.strip()
            ]
            valid_statuses = {choice for choice, _ in DecisionStatus.choices}
            invalid_statuses = [
                value for value in statuses if value not in valid_statuses
            ]
            if invalid_statuses:
                raise ValidationError({"status": "Invalid status filter"})
            status_query = Q()
            for status_value in statuses:
                status_query |= Q(status__iexact=status_value)
            queryset = queryset.filter(status_query)

        query_param = request.query_params.get("q")
        if query_param:
            queryset = queryset.filter(
                Q(title__icontains=query_param)
                | Q(description__icontains=query_param)
                | Q(created_by__icontains=query_param)
            )

        from_param = request.query_params.get("from")
        if from_param:
            from_dt = self._parse_filter_datetime(from_param, "from", end_of_day=False)
            queryset = queryset.filter(updated_at__gte=from_dt)

        to_param = request.query_params.get("to")
        if to_param:
            to_dt = self._parse_filter_datetime(to_param, "to", end_of_day=True)
            queryset = queryset.filter(updated_at__lte=to_dt)

        queryset = queryset.order_by("-updated_at", "-id")

        limit_param = request.query_params.get("limit")
        offset_param = request.query_params.get("offset", "0")

        offset = self._parse_filter_int(offset_param, "offset")
        if offset < 0:
            raise ValidationError({"offset": "Offset must be >= 0"})

        if limit_param is not None:
            limit = self._parse_filter_int(limit_param, "limit")
            if limit < 0:
                raise ValidationError({"limit": "Limit must be >= 0"})
            queryset = queryset[offset : offset + limit]
        elif offset > 0:
            queryset = queryset[offset:]

        serializer = DecisionSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @staticmethod
    def _parse_filter_int(value: str, field_name: str) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError({field_name: f"{field_name} must be an integer"})

    @staticmethod
    def _parse_filter_datetime(
        value: str, field_name: str, end_of_day: bool
    ) -> dt.datetime:
        parsed_dt = parse_datetime(value)
        if parsed_dt is not None:
            if timezone.is_naive(parsed_dt):
                return timezone.make_aware(parsed_dt)
            return parsed_dt

        parsed_date = parse_date(value)
        if parsed_date is not None:
            time_value = dt.time.max if end_of_day else dt.time.min
            combined = dt.datetime.combine(parsed_date, time_value)
            return timezone.make_aware(combined)

        raise ValidationError({field_name: f"{field_name} must be an ISO datetime"})

    @action(
        detail=False,
        methods=["get"],
        url_path="stream",
        renderer_classes=[ServerSentEventRenderer],
    )
    def stream(self, request):
        """
        Stream decision realtime updates over SSE.

        Access policy:
            - Authenticated users only
        """
        queue, unsubscribe = decision_event_broker.subscribe()

        def event_stream():
            try:
                yield from event_stream_generator(queue)
            finally:
                unsubscribe()

        response = StreamingHttpResponse(
            streaming_content=event_stream(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    @staticmethod
    def _resolve_decision(pk: str, request) -> Decision:
        try:
            decision_id = uuid.UUID(pk)
        except (ValueError, AttributeError):
            raise NotFound(f"Invalid decision ID: {pk}")

        membership = get_user_membership_or_raise(request.user)
        return resolve_org_decision_or_404(membership, str(decision_id))

    def create(self, request):
        """
        Create a new decision.

        Request body:
            - title (required): Decision title
            - description (required): Decision description
            - priority (optional): Priority -10 to 10, default 0
            - metadata (optional): Additional metadata as JSON

        Returns:
            201 Created with decision data
            400 Bad Request if validation fails
        """
        membership = get_user_membership_or_raise(request.user)
        require_write_role(membership)
        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create decision
        user_id = str(request.user.id) if request.user and request.user.id else ""
        decision = serializer.save(
            created_by=user_id,
            organization=membership.organization,
        )

        # Create audit log
        AuditLogService.log_create(decision=decision, actor_type="api")

        # Return response
        output_serializer = DecisionSerializer(decision)
        self._publish_decision_event(decision)
        dispatch_event_to_webhooks(
            organization=membership.organization,
            event_type=WEBHOOK_EVENT_DECISION_CREATED,
            payload={"decision": output_serializer.data},
        )
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        """
        Retrieve a decision by ID.

        Args:
            pk: Decision UUID

        Returns:
            200 OK with decision data
            404 Not Found if decision doesn't exist
        """
        membership = get_user_membership_or_raise(request.user)
        require_read_role(membership)
        decision = self._resolve_decision(pk, request)
        require_decision_access_or_404(membership, request.user, decision)

        serializer = DecisionSerializer(decision)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """
        Submit a decision for processing.

        Args:
            pk: Decision UUID

        Returns:
            202 Accepted if submitted successfully
            400 Bad Request if decision cannot be submitted
            404 Not Found if decision doesn't exist
        """
        membership = get_user_membership_or_raise(request.user)
        require_write_role(membership)
        decision = self._resolve_decision(pk, request)
        require_decision_access_or_404(membership, request.user, decision)

        # Validate empty payload
        submit_serializer = DecisionSubmitSerializer(data=request.data)
        submit_serializer.is_valid(raise_exception=True)

        try:
            # Submit decision (includes audit logging and queue publishing)
            DecisionWorkflowService.submit_decision(decision)
        except ValueError as e:
            raise ValidationError({"status": str(e)})

        # Return response
        decision.refresh_from_db()
        self._publish_decision_event(decision)
        dispatch_event_to_webhooks(
            organization=membership.organization,
            event_type=WEBHOOK_EVENT_DECISION_SUBMITTED,
            payload={
                "decision_id": str(decision.id),
                "status": decision.status,
            },
        )
        return Response(
            {
                "id": str(decision.id),
                "status": decision.status,
                "message": "Decision queued for processing",
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        """
        Retry a failed decision.

        Access policy:
            - Authenticated users only
            - Owner or staff users only
        """
        membership = get_user_membership_or_raise(request.user)
        require_write_role(membership)
        decision = self._resolve_decision(pk, request)
        require_decision_access_or_404(membership, request.user, decision)

        try:
            DecisionWorkflowService.retry_decision(decision)
        except ValueError as e:
            raise ValidationError({"status": str(e)})

        decision.refresh_from_db()
        self._publish_decision_event(decision)
        dispatch_event_to_webhooks(
            organization=membership.organization,
            event_type=WEBHOOK_EVENT_DECISION_RETRY_REQUESTED,
            payload={
                "decision_id": str(decision.id),
                "status": decision.status,
            },
        )
        return Response(
            {
                "id": str(decision.id),
                "status": decision.status,
                "message": "Decision queued for retry",
            },
            status=status.HTTP_202_ACCEPTED,
        )
