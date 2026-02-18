"""
DRF ViewSets for DecisionVault.
"""

import uuid

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import (
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response

from decisions.models import Decision, DecisionStatus
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

    @staticmethod
    def _resolve_decision(pk: str) -> Decision:
        try:
            decision_id = uuid.UUID(pk)
        except (ValueError, AttributeError):
            raise NotFound(f"Invalid decision ID: {pk}")

        try:
            return Decision.objects.get(id=decision_id)
        except Decision.DoesNotExist:
            raise NotFound(f"Decision not found: {pk}")

    @staticmethod
    def _enforce_owner_or_staff(request, decision: Decision) -> None:
        if not request.user or not request.user.is_authenticated:
            raise NotAuthenticated("Authentication credentials were not provided.")

        user_id = str(request.user.id) if request.user.id is not None else ""
        username = request.user.get_username()
        is_owner = decision.created_by in {user_id, username}

        if not (is_owner or request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied(
                "You do not have permission to access this decision."
            )

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
        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create decision
        decision = serializer.save()

        # Create audit log
        AuditLogService.log_create(decision=decision, actor_type="api")

        # Return response
        output_serializer = DecisionSerializer(decision)
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
        decision = self._resolve_decision(pk)

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
        decision = self._resolve_decision(pk)

        # Validate empty payload
        submit_serializer = DecisionSubmitSerializer(data=request.data)
        submit_serializer.is_valid(raise_exception=True)

        try:
            # Submit decision (includes audit logging and queue publishing)
            DecisionWorkflowService.submit_decision(decision)
        except ValueError as e:
            raise ValidationError({"status": str(e)})

        # Return response
        return Response(
            {
                "id": str(decision.id),
                "status": decision.status,
                "message": "Decision queued for processing",
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["get"])
    def workflow(self, request, pk=None):
        """
        Retrieve decision workflow state.

        Access policy:
            - Authenticated users only
            - Owner or staff users only
        """
        decision = self._resolve_decision(pk)
        self._enforce_owner_or_staff(request, decision)

        return Response(
            {
                "id": str(decision.id),
                "status": decision.status,
                "workflow_started_at": decision.workflow_started_at,
                "workflow_completed_at": decision.workflow_completed_at,
                "agent_result": decision.agent_result,
                "agent_error": decision.agent_error,
                "updated_at": decision.updated_at,
            },
            status=status.HTTP_200_OK,
        )
