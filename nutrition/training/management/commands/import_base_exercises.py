import csv
import os
from django.core.management.base import BaseCommand
from training.models import BaseExercise, MUSCLE_GROUP_CHOICES, EXERCISE_TYPE_CHOICES


class Command(BaseCommand):
    help = "Загружает базовые упражнения из CSV файла"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv_file",
            type=str,
            help="Путь к CSV файлу",
            default="data/base_exercises.csv",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Очистить существующие упражнения перед загрузкой",
        )

    def handle(self, *args, **options):
        csv_file_path = options["csv_file"]

        if options["clear"]:
            self.stdout.write("Очищаем таблицу упражнений...")
            BaseExercise.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Таблица очищена"))

        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f"Файл {csv_file_path} не найден!"))
            return

        self._load_from_csv(csv_file_path)

    def _load_from_csv(self, csv_path):
        """Загружает упражнения из CSV файла"""
        with open(csv_path, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            created_count = 0
            updated_count = 0
            skipped_count = 0
            errors = []

            for row_num, row in enumerate(reader, start=2):
                try:
                    # Проверяем обязательные поля
                    required_fields = ["name", "primary_muscle_group", "exercise_type"]
                    for field in required_fields:
                        if not row.get(field):
                            raise ValueError(f"Отсутствует обязательное поле: {field}")

                    # Преобразуем строки в нужные значения
                    primary_mg = row["primary_muscle_group"].strip()
                    secondary_mg = row.get("secondary_muscle_group", "").strip()
                    exercise_type = row["exercise_type"].strip()
                    description = row.get("description", "").strip()
                    equipment = row.get("equipment", "").strip()

                    # Валидация значений
                    valid_muscle_groups = [choice[0] for choice in MUSCLE_GROUP_CHOICES]
                    valid_exercise_types = [
                        choice[0] for choice in EXERCISE_TYPE_CHOICES
                    ]

                    if secondary_mg.upper() == "NONE" or not secondary_mg:
                        secondary_mg = None

                    if primary_mg not in valid_muscle_groups:
                        raise ValueError(f"Некорректная группа мышц: {primary_mg}")

                    if secondary_mg and secondary_mg not in valid_muscle_groups:
                        raise ValueError(
                            f"Некорректная вторичная группа мышц: {secondary_mg}"
                        )

                    if exercise_type not in valid_exercise_types:
                        raise ValueError(
                            f"Некорректный тип упражнения: {exercise_type}"
                        )

                    # Проверяем, существует ли уже упражнение с таким названием
                    existing_exercise = BaseExercise.objects.filter(
                        name=row["name"]
                    ).first()

                    if existing_exercise:
                        # Обновляем существующее упражнение
                        existing_exercise.primary_muscle_group = primary_mg
                        existing_exercise.secondary_muscle_group = (
                            secondary_mg if secondary_mg else None
                        )
                        existing_exercise.exercise_type = exercise_type
                        existing_exercise.description = description
                        existing_exercise.equipment_type = equipment
                        existing_exercise.save()
                        updated_count += 1

                        self.stdout.write(
                            f"Обновлено: {row['name']} (id: {existing_exercise.id})"
                        )
                    else:
                        # Создаем новое упражнение
                        BaseExercise.objects.create(
                            name=row["name"],
                            primary_muscle_group=primary_mg,
                            secondary_muscle_group=(
                                secondary_mg if secondary_mg else None
                            ),
                            exercise_type=exercise_type,
                            description=description,
                            equipment_type=equipment,
                            # Для image можно добавить позже
                            image="",  # Пока без изображений
                        )
                        created_count += 1

                        self.stdout.write(self.style.SUCCESS(f"Создано: {row['name']}"))

                except ValueError as e:
                    error_msg = f"Строка {row_num}: {e}"
                    errors.append(error_msg)
                    self.stdout.write(self.style.ERROR(error_msg))
                    skipped_count += 1

                except Exception as e:
                    error_msg = f"Строка {row_num}: Неожиданная ошибка - {str(e)}"
                    errors.append(error_msg)
                    self.stdout.write(self.style.ERROR(error_msg))
                    skipped_count += 1

            # Выводим итоговую статистику
            self.stdout.write("\n" + "=" * 50)
            self.stdout.write(self.style.SUCCESS("ИТОГ ЗАГРУЗКИ:"))
            self.stdout.write(f"Успешно создано: {created_count}")
            self.stdout.write(f"Обновлено: {updated_count}")
            self.stdout.write(f"Пропущено из-за ошибок: {skipped_count}")

            if errors:
                self.stdout.write(self.style.WARNING("\nОшибки при загрузке:"))
                for error in errors:
                    self.stdout.write(f"  - {error}")

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nВсего упражнений в базе: {BaseExercise.objects.count()}"
                )
            )
