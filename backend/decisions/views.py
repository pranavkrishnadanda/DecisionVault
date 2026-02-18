"""
DRF ViewSets for DecisionVault.
"""

import uuid

from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import (
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.permissions import IsAuthenticated
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
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        List decisions for operator dashboard.

        Access policy:
            - Staff/superuser: can view all decisions
            - Regular user: can view only owned decisions
        """
        user = request.user
        if user.is_staff or user.is_superuser:
            queryset = Decision.objects.all().order_by("-created_at")
        else:
            user_id = str(user.id) if user.id is not None else ""
            username = user.get_username()
            queryset = Decision.objects.filter(
                Q(created_by=user_id) | Q(created_by=username)
            ).order_by("-created_at")

        serializer = DecisionSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

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
        user_id = str(request.user.id) if request.user and request.user.id else ""
        decision = serializer.save(created_by=user_id)

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
        self._enforce_owner_or_staff(request, decision)

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
        self._enforce_owner_or_staff(request, decision)

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

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        """
        Retry a failed decision.

        Access policy:
            - Authenticated users only
            - Owner or staff users only
        """
        decision = self._resolve_decision(pk)
        self._enforce_owner_or_staff(request, decision)

        try:
            DecisionWorkflowService.retry_decision(decision)
        except ValueError as e:
            raise ValidationError({"status": str(e)})

        return Response(
            {
                "id": str(decision.id),
                "status": decision.status,
                "message": "Decision queued for retry",
            },
            status=status.HTTP_202_ACCEPTED,
        )
