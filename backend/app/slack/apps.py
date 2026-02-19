from django.apps import AppConfig


class SlackConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.slack"
    label = "slack_integration"
