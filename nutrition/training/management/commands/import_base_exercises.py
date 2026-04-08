import csv
import os
from django.core.management.base import BaseCommand
from django.core.files import File
from training.models import (
    BaseExercise,
    MUSCLE_GROUP_CHOICES,
    EXERCISE_TYPE_CHOICES,
    EQUIPMENT_CHOICES,
)


class Command(BaseCommand):
    help = "Загружает базовые упражнения из CSV и привязывает фото"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv_file",
            type=str,
            default="training/data/base_exercises.csv",
        )
        parser.add_argument(
            "--image_dir",
            type=str,
            default="training/data/exercise_photos/",
            help="Папка, где лежат исходные файлы картинок",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Очистить таблицу перед загрузкой",
        )

    def handle(self, *args, **options):
        csv_file_path = options["csv_file"]
        image_dir = options["image_dir"]

        if options["clear"]:
            BaseExercise.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Таблица очищена"))

        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f"Файл {csv_file_path} не найден!"))
            return

        # Создаем множества допустимых значений для быстрой проверки
        valid_muscle_groups = {choice[0] for choice in MUSCLE_GROUP_CHOICES}
        valid_exercise_types = {choice[0] for choice in EXERCISE_TYPE_CHOICES}
        valid_equipment = {choice[0] for choice in EQUIPMENT_CHOICES}

        # Добавляем None как допустимое значение для secondary_muscle_group
        valid_muscle_groups.add(None)

        stats = {"processed": 0, "created": 0, "updated": 0, "skipped": 0, "errors": 0}

        with open(csv_file_path, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                stats["processed"] += 1

                try:
                    # Проверка обязательных полей
                    name = row.get("name", "").strip()
                    if not name:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Строка {stats['processed']}: пропущено (нет названия)"
                            )
                        )
                        stats["skipped"] += 1
                        continue

                    # Проверка primary_muscle_group
                    primary_muscle = row["primary_muscle_group"].strip()
                    if primary_muscle not in valid_muscle_groups:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Строка {stats['processed']} ({name}): "
                                f"пропущено - неверная группа мышц '{primary_muscle}'"
                            )
                        )
                        stats["skipped"] += 1
                        continue

                    # Проверка secondary_muscle_group
                    secondary_muscle = row["secondary_muscle_group"].strip()
                    if secondary_muscle not in ["", "NONE"]:
                        if secondary_muscle not in valid_muscle_groups:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Строка {stats['processed']} ({name}): "
                                    f"пропущено - неверная вторичная группа мышц '{secondary_muscle}'"
                                )
                            )
                            stats["skipped"] += 1
                            continue

                    # Проверка exercise_type
                    exercise_type = row["exercise_type"].strip()
                    if exercise_type not in valid_exercise_types:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Строка {stats['processed']} ({name}): "
                                f"пропущено - неверный тип упражнения '{exercise_type}'"
                            )
                        )
                        stats["skipped"] += 1
                        continue

                    # Проверка equipment
                    equipment = row["equipment"].strip()
                    if equipment not in valid_equipment:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Строка {stats['processed']} ({name}): "
                                f"пропущено - неверный тип оборудования '{equipment}'"
                            )
                        )
                        stats["skipped"] += 1
                        continue

                    # Все проверки пройдены - создаем/обновляем запись
                    exercise, created = BaseExercise.objects.update_or_create(
                        name=name,
                        defaults={
                            "primary_muscle_group": primary_muscle,
                            "secondary_muscle_group": (
                                secondary_muscle
                                if secondary_muscle not in ["", "NONE"]
                                else None
                            ),
                            "exercise_type": exercise_type,
                            "equipment_type": equipment,
                            "description": row.get("description", "").strip(),
                        },
                    )

                    # Работа с фото
                    image_filename = row.get("image_filename", "").strip()
                    if image_filename:
                        img_path = os.path.join(image_dir, image_filename)
                        if os.path.exists(img_path):
                            with open(img_path, "rb") as f:
                                # Имя файла для сохранения в MEDIA:
                                exercise.image.save(image_filename, File(f), save=True)
                            self.stdout.write(f"  Добавлено фото для {exercise.name}")
                        else:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"  Файл {image_filename} не найден в {image_dir}"
                                )
                            )

                    if created:
                        stats["created"] += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"Создано: {exercise.name}")
                        )
                    else:
                        stats["updated"] += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"Обновлено: {exercise.name}")
                        )

                except Exception as e:
                    stats["errors"] += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"Ошибка в строке {stats['processed']} ({row.get('name', 'Unknown')}): {e}"
                        )
                    )

        # Вывод статистики
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("ЗАВЕРШЕНО"))
        self.stdout.write(f"Обработано строк: {stats['processed']}")
        self.stdout.write(f"Создано: {stats['created']}")
        self.stdout.write(f"Обновлено: {stats['updated']}")
        self.stdout.write(f"Пропущено: {stats['skipped']}")
        self.stdout.write(f"Ошибок: {stats['errors']}")
        self.stdout.write("=" * 50)
