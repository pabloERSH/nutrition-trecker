from django.conf import settings
from django.core.management.base import BaseCommand
from nutrition_trecker.models import EatenFood
from django.utils import timezone


class Command(BaseCommand):
    def handle(self, *args, **options):
        days_to_keep = settings.MAX_EATEN_FOOD_AGE_DAYS
        threshold = timezone.now() - timezone.timedelta(days=days_to_keep)

        deleted_count, _ = EatenFood.objects.filter(eaten_at__lt=threshold).delete()
        self.stdout.write(f"{deleted_count} old rows was deleted.")
