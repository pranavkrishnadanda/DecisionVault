from django.apps import AppConfig


class DecisionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "decisions"
    verbose_name = "Decisions"

    def ready(self):
        import decisions.signals  # noqa: F401
