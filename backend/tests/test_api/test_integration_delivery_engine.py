from datetime import timedelta
from unittest.mock import patch

import httpx
import pytest
from django.utils import timezone

from api.models import (
    INTEGRATION_EVENT_DECISION_COMPLETED,
    INTEGRATION_EVENT_DECISION_FAILED,
    INTEGRATION_EVENT_WEBHOOK_FAILED,
    Integration,
    IntegrationDelivery,
    IntegrationDeliveryAttempt,
    IntegrationTrigger,
    Organization,
    OrganizationMembership,
    OrganizationRole,
    WebhookDelivery,
    WebhookSubscription,
)
from api.services.credentials_vault import decrypt_credentials, encrypt_credentials
from api.services.integration_dispatcher import dispatch_event_to_integrations
from api.services.integration_worker import process_integration_delivery
from api.services.webhook_worker import process_webhook_delivery
from decisions.models import Decision, DecisionStatus


@pytest.fixture
def org_a(db):
    return Organization.objects.create(name="Integration Dispatch Org")


@pytest.fixture
def admin_a(django_user_model, org_a):
    user = django_user_model.objects.create_user(
        username="integration-dispatch-admin",
        email="integration-dispatch-admin@example.com",
        password="pass1234",
    )
    OrganizationMembership.objects.filter(user=user).delete()
    OrganizationMembership.objects.create(
        user=user,
        organization=org_a,
        role=OrganizationRole.ADMIN,
    )
    return user


@pytest.mark.django_db
class TestIntegrationDispatch:
    def test_dispatch_creates_org_scoped_deliveries(self, org_a, admin_a):
        integration = Integration.objects.create(
            organization=org_a,
            created_by=admin_a,
            name="Slack Alerts",
            connector_type=Integration.ConnectorType.SLACK,
            config={"channel_id": "COPS"},
            credentials_encrypted=encrypt_credentials({"access_token": "xoxb"}),
            is_active=True,
        )
        IntegrationTrigger.objects.create(
            organization=org_a,
            integration=integration,
            event_type=INTEGRATION_EVENT_DECISION_COMPLETED,
            is_active=True,
            message_template="Decision {{payload.decision_id}} completed",
        )

        with patch(
            "api.services.integration_dispatcher.enqueue_integration_delivery"
        ) as mock_enqueue:
            created = dispatch_event_to_integrations(
                organization=org_a,
                event_type=INTEGRATION_EVENT_DECISION_COMPLETED,
                payload={"decision_id": "dec-1"},
            )

        assert created == 1
        delivery = IntegrationDelivery.objects.get()
        assert delivery.integration_id == integration.id
        mock_enqueue.assert_called_once_with(str(delivery.id))


@pytest.mark.django_db
class TestIntegrationWorker:
    def test_worker_delivers_slack_message(self, org_a, admin_a):
        integration = Integration.objects.create(
            organization=org_a,
            created_by=admin_a,
            name="Slack Alerts",
            connector_type=Integration.ConnectorType.SLACK,
            config={"channel_id": "COPS"},
            credentials_encrypted=encrypt_credentials({"access_token": "xoxb"}),
            is_active=True,
        )
        trigger = IntegrationTrigger.objects.create(
            organization=org_a,
            integration=integration,
            event_type=INTEGRATION_EVENT_DECISION_COMPLETED,
            is_active=True,
            message_template="Decision {{payload.decision_id}} completed",
        )
        delivery = IntegrationDelivery.objects.create(
            organization=org_a,
            integration=integration,
            trigger=trigger,
            event_type=INTEGRATION_EVENT_DECISION_COMPLETED,
            payload={"decision_id": "dec-1"},
        )

        with patch(
            "api.services.integration_connectors.httpx.Client.post",
            return_value=httpx.Response(status_code=200, json={"ok": True}),
        ):
            handled = process_integration_delivery(str(delivery.id))

        assert handled is True
        delivery.refresh_from_db()
        assert delivery.status == IntegrationDelivery.Status.DELIVERED
        assert delivery.attempt_count == 1
        attempt = IntegrationDeliveryAttempt.objects.get(delivery=delivery)
        assert attempt.status == IntegrationDeliveryAttempt.Status.SUCCESS

    def test_worker_refreshes_expired_slack_token(self, org_a, admin_a):
        integration = Integration.objects.create(
            organization=org_a,
            created_by=admin_a,
            name="Slack Alerts",
            connector_type=Integration.ConnectorType.SLACK,
            config={"channel_id": "COPS"},
            credentials_encrypted=encrypt_credentials(
                {"access_token": "xoxb-old", "refresh_token": "refresh-old"}
            ),
            token_expires_at=timezone.now() - timedelta(minutes=1),
            is_active=True,
        )
        trigger = IntegrationTrigger.objects.create(
            organization=org_a,
            integration=integration,
            event_type=INTEGRATION_EVENT_DECISION_COMPLETED,
            is_active=True,
            message_template="Decision {{payload.decision_id}} completed",
        )
        delivery = IntegrationDelivery.objects.create(
            organization=org_a,
            integration=integration,
            trigger=trigger,
            event_type=INTEGRATION_EVENT_DECISION_COMPLETED,
            payload={"decision_id": "dec-2"},
        )

        def _mock_refresh(connector_integration):
            connector_integration.credentials_encrypted = encrypt_credentials(
                {"access_token": "xoxb-new", "refresh_token": "refresh-new"}
            )
            connector_integration.token_expires_at = timezone.now() + timedelta(
                seconds=3600
            )
            connector_integration.save(
                update_fields=[
                    "credentials_encrypted",
                    "token_expires_at",
                    "updated_at",
                ]
            )
            return {
                "access_token": "xoxb-new",
                "refresh_token": "refresh-new",
                "expires_in": 3600,
            }

        with patch(
            "api.services.integration_connectors.refresh_slack_access_token",
            side_effect=_mock_refresh,
        ):
            with patch(
                "api.services.integration_connectors.httpx.Client.post",
                return_value=httpx.Response(status_code=200, json={"ok": True}),
            ):
                handled = process_integration_delivery(str(delivery.id))

        assert handled is True
        integration.refresh_from_db()
        credentials = decrypt_credentials(integration.credentials_encrypted)
        assert credentials["access_token"] == "xoxb-new"
        assert credentials["refresh_token"] == "refresh-new"
        assert integration.token_expires_at > timezone.now()


@pytest.mark.django_db
class TestIntegrationTriggers:
    @pytest.mark.parametrize(
        ("next_status", "expected_event"),
        [
            (DecisionStatus.COMPLETED, INTEGRATION_EVENT_DECISION_COMPLETED),
            (DecisionStatus.FAILED, INTEGRATION_EVENT_DECISION_FAILED),
        ],
    )
    def test_decision_status_transition_emits_integration_event(
        self, org_a, admin_a, next_status, expected_event
    ):
        decision = Decision.objects.create(
            organization=org_a,
            title="Signal test",
            description="status transition",
            status=DecisionStatus.PROCESSING,
            priority=0,
            created_by=str(admin_a.id),
        )

        with patch("decisions.signals.dispatch_event_to_integrations") as mock_dispatch:
            decision.status = next_status
            decision.save(update_fields=["status", "updated_at"])

        mock_dispatch.assert_called_once()
        _, kwargs = mock_dispatch.call_args
        assert kwargs["event_type"] == expected_event
        assert kwargs["organization"] == org_a

    def test_webhook_terminal_failure_emits_integration_event(self, org_a, admin_a):
        subscription = WebhookSubscription.objects.create(
            organization=org_a,
            created_by=admin_a,
            target_url="https://example.com/webhooks",
            signing_secret="webhook-secret-123456",
            events=["decision.failed"],
            is_active=True,
        )
        delivery = WebhookDelivery.objects.create(
            organization=org_a,
            subscription=subscription,
            event_type="decision.failed",
            payload={"decision_id": "dec-3"},
            max_attempts=1,
        )

        with patch(
            "api.services.webhook_worker.httpx.Client.post",
            side_effect=httpx.TimeoutException("timeout"),
        ):
            with patch(
                "api.services.webhook_worker.dispatch_event_to_integrations"
            ) as mock_dispatch:
                process_webhook_delivery(str(delivery.id))

        mock_dispatch.assert_called_once()
        _, kwargs = mock_dispatch.call_args
        assert kwargs["event_type"] == INTEGRATION_EVENT_WEBHOOK_FAILED
        assert kwargs["organization"] == org_a
