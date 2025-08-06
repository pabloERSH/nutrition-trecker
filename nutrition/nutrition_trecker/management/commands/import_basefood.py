from django.core.management.base import BaseCommand
from nutrition_trecker.models import BaseFood
import csv

class Command(BaseCommand):
    help = 'Imports base food data from CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)

    def handle(self, *args, **options):
        with open(options['csv_file'], 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['name'].startswith('#'):
                    continue
                if BaseFood.objects.filter(name=row['name']).exists():
                    continue
                BaseFood.objects.create(
                    name=row['name'],
                    proteins=float(row['proteins']),
                    fats=float(row['fats']),
                    carbohydrates=float(row['carbohydrates'])
                )
        self.stdout.write(self.style.SUCCESS('Data imported successfully'))
        