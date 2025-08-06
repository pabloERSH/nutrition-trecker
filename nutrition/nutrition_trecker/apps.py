from django.apps import AppConfig


class NutritionTreckerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'nutrition_trecker'

    def ready(self):
        from nutrition_trecker import signals
        from nutrition_trecker.management import commands
