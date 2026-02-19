from django.db.models import QuerySet
from rest_framework.exceptions import NotAuthenticated, NotFound, PermissionDenied

from api.models import OrganizationMembership, OrganizationRole
from decisions.models import Decision

READ_ROLES = {
    OrganizationRole.ADMIN,
    OrganizationRole.OPERATOR,
    OrganizationRole.VIEWER,
}
WRITE_ROLES = {OrganizationRole.ADMIN, OrganizationRole.OPERATOR}


def get_user_membership_or_raise(user) -> OrganizationMembership:
    """Resolve current user's organization membership or fail closed."""
    if not user or not getattr(user, "is_authenticated", False):
        raise NotAuthenticated("Authentication credentials were not provided.")

    membership = (
        OrganizationMembership.objects.select_related("organization")
        .filter(user=user)
        .order_by("created_at")
        .first()
    )
    if membership is None:
        raise PermissionDenied("No organization membership.")
    return membership


def scope_queryset_to_membership(
    queryset: QuerySet, membership: OrganizationMembership
):
    """Apply tenant filter to a queryset."""
    return queryset.filter(organization=membership.organization)


def require_read_role(membership: OrganizationMembership) -> None:
    if membership.role not in READ_ROLES:
        raise PermissionDenied("Insufficient organization role.")


def require_write_role(membership: OrganizationMembership) -> None:
    if membership.role not in WRITE_ROLES:
        raise PermissionDenied("Insufficient organization role.")


def resolve_org_decision_or_404(
    membership: OrganizationMembership, decision_id: str
) -> Decision:
    """Resolve a decision inside caller org only; hide existence across orgs."""
    decision = (
        Decision.objects.filter(organization=membership.organization, id=decision_id)
        .order_by()
        .first()
    )
    if decision is None:
        raise NotFound("Decision not found.")
    return decision


def require_decision_access_or_404(
    membership: OrganizationMembership, user, decision: Decision
) -> None:
    """Restrict non-admin roles to owned decisions; return 404 to prevent leakage."""
    if membership.role == OrganizationRole.ADMIN:
        return

    user_id = str(user.id) if user and user.id is not None else ""
    username = user.get_username() if user else ""
    if decision.created_by not in {user_id, username}:
        raise NotFound("Decision not found.")
