from django.apps import AppConfig


class TrainingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "training"

    def ready(self):
        from training import signals  # noqa: F401
        from training.management import commands  # noqa: F401
