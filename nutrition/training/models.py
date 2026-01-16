from django.db import models
from common.models.TimeStampedModel import TimeStampedModel
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Q
from PIL import Image
import os
from io import BytesIO
from django.core.files.base import ContentFile
from django.contrib.postgres.indexes import GinIndex


# Типы упражнений
EXERCISE_TYPE_CHOICES = [
    ("STRENGTH", "Силовое"),
    ("CARDIO", "Кардио"),
    ("STRETCHING", "Растяжка"),
    ("MOBILITY", "Мобильность"),
    ("BALANCE", "Баланс"),
    ("PLYOMETRIC", "Плиометрика"),
]

# Основные группы мышц
MUSCLE_GROUP_CHOICES = [
    ("CHEST", "Грудь"),
    ("BACK", "Спина"),
    ("SHOULDERS", "Плечи"),
    ("BICEPS", "Бицепс"),
    ("TRICEPS", "Трицепс"),
    ("QUADS", "Квадрицепс"),
    ("HAMSTRINGS", "Бицепс бедра"),
    ("GLUTES", "Ягодицы"),
    ("CALVES", "Икры"),
    ("ABS", "Пресс"),
    ("FOREARMS", "Предплечья"),
    ("FULL_BODY", "Все тело"),
    ("CORE", "Кор"),
    ("TRAPEZIUS", "Трапеции"),
    ("ADDUCTORS", "Приводящие мышцы"),
    ("ABDUCTORS", "Отводящие мышцы"),
    ("NECK", "Шея"),
    ("LATS", "Широчайшие"),
    ("OBLIQUES", "Косые мышцы"),
    ("HIP_FLEXORS", "Сгибатели бедра"),
]

# Оборудование
EQUIPMENT_CHOICES = [
    ("NONE", "Без оборудования"),
    ("BARBELL", "Штанга"),
    ("DUMBBELL", "Гантели"),
    ("KETTLEBELL", "Гиря"),
    ("RESISTANCE_BAND", "Резина"),
    ("MACHINE", "Тренажер"),
    ("CABLE", "Тросовый тренажер"),
    ("MEDICINE_BALL", "Медбол"),
    ("STABILITY_BALL", "Фитбол"),
    ("TRX", "TRX"),
    ("JUMP_ROPE", "Скакалка"),
    ("PULL_UP_BAR", "Турник"),
    ("DIP_BAR", "Брусья"),
    ("BOX", "Короб"),
]


class TrainingSession(TimeStampedModel):
    """Модель для хранения информации о тренировке."""

    user_id = models.BigIntegerField(db_index=True)
    date_time = models.DateTimeField(
        default=timezone.now,
        verbose_name="Дата и время",
        help_text="Дата и время тренировки",
    )
    duration = models.PositiveIntegerField(
        verbose_name="Длительность (минуты)",
        help_text="Длительность тренировки в минутах",
        validators=[MinValueValidator(1), MaxValueValidator(1440)],
    )
    name = models.CharField(
        verbose_name="Название",
        max_length=255,
        help_text="Название тренировки",
        db_index=True,
    )
    description = models.TextField(
        verbose_name="Описание",
        blank=True,
        null=True,
        help_text="Подробное описание тренировки",
    )

    class Meta:
        verbose_name = "Тренировка"
        verbose_name_plural = "Тренировки"
        indexes = [
            models.Index(fields=["user_id", "date_time"]),
            GinIndex(
                name="training_session_name_trgm_idx",
                fields=["name", "description"],
                opclasses=["gin_trgm_ops", "gin_trgm_ops"],
            ),
        ]
        ordering = ["-date_time"]

    def __str__(self):
        return f"{self.name} - {self.date_time.strftime('%d.%m.%Y %H:%M')}"


class BaseExercise(TimeStampedModel):
    """Модель для хранения данных о базовых упражнений (только для модераторов)."""

    name = models.CharField(
        verbose_name="Название",
        max_length=255,
        help_text="Название базового упражнения",
        db_index=True,
    )
    primary_muscle_group = models.CharField(
        verbose_name="Основная группа мышц",
        max_length=20,
        choices=MUSCLE_GROUP_CHOICES,
        help_text="Основная целевая группа мышц",
    )
    secondary_muscle_group = models.CharField(
        verbose_name="Дополнительная группа мышц",
        max_length=20,
        choices=MUSCLE_GROUP_CHOICES,
        blank=True,
        null=True,
        help_text="Вторичная группа мышц, которая также работает",
    )
    exercise_type = models.CharField(
        verbose_name="Вид упражнения",
        max_length=15,
        choices=EXERCISE_TYPE_CHOICES,
        help_text="Тип физической активности",
    )
    equipment_type = models.CharField(
        verbose_name="Оборудование",
        max_length=20,
        choices=EQUIPMENT_CHOICES,
        help_text="Тип требуемого тренировочного оборудования",
    )
    description = models.TextField(
        verbose_name="Описание техники",
        blank=True,
        null=True,
        help_text="Подробное описание техники выполнения",
    )
    image = models.ImageField(
        verbose_name="Фото",
        upload_to="photos/base_exercises/",
        help_text="Фотография упражнения",
    )
    image_thumbnail = models.ImageField(
        upload_to="photos/base_exercises/thumbs/",
        null=True,
        blank=True,
        editable=False,
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.image and not self.image_thumbnail:
            self.create_thumbnail()

    def create_thumbnail(self, size=(150, 150)):
        """Создает миниатюру изображения"""
        if not self.image:
            return

        try:
            img = Image.open(self.image.path)

            if img.mode not in ("L", "RGB", "RGBA"):
                img = img.convert("RGB")

            img.thumbnail(size, Image.Resampling.LANCZOS)

            thumb_io = BytesIO()
            img.save(thumb_io, format="JPEG", quality=80, optimize=True)
            thumb_io.seek(0)

            filename = os.path.basename(self.image.name)
            name, ext = os.path.splitext(filename)
            thumb_filename = f"{name}_thumb{ext or '.jpg'}"

            self.image_thumbnail.save(
                thumb_filename, ContentFile(thumb_io.read()), save=False
            )

            super().save(update_fields=["image_thumbnail"])

        except Exception as e:
            print(f"Ошибка создания thumbnail: {e}")

    def delete(self, *args, **kwargs):
        """Удаляем файлы при удалении объекта"""
        if self.image:
            if os.path.isfile(self.image.path):
                os.remove(self.image.path)
        if self.image_thumbnail:
            if os.path.isfile(self.image_thumbnail.path):
                os.remove(self.image_thumbnail.path)
        super().delete(*args, **kwargs)

    class Meta:
        verbose_name = "Базовое упражнение"
        verbose_name_plural = "Базовые упражнения"
        indexes = [
            GinIndex(
                name="base_ex_name_trgm_idx",
                fields=["name"],
                opclasses=["gin_trgm_ops"],
            ),
        ]

    def __str__(self):
        return self.name


class CustomExercise(TimeStampedModel):
    """Модель для хранения данных о пользовательских упражнениях."""

    user_id = models.BigIntegerField(db_index=True)
    name = models.CharField(
        verbose_name="Название",
        max_length=255,
        help_text="Название базового упражнения",
        db_index=True,
    )
    primary_muscle_group = models.CharField(
        verbose_name="Основная группа мышц",
        max_length=20,
        choices=MUSCLE_GROUP_CHOICES,
        help_text="Основная целевая группа мышц",
    )
    secondary_muscle_group = models.CharField(
        verbose_name="Дополнительная группа мышц",
        max_length=20,
        choices=MUSCLE_GROUP_CHOICES,
        blank=True,
        null=True,
        help_text="Вторичная группа мышц, которая также работает",
    )
    exercise_type = models.CharField(
        verbose_name="Вид упражнения",
        max_length=15,
        choices=EXERCISE_TYPE_CHOICES,
        help_text="Тип физической активности",
    )
    equipment_type = models.CharField(
        verbose_name="Оборудование",
        max_length=20,
        choices=EQUIPMENT_CHOICES,
        help_text="Тип требуемого тренировочного оборудования",
    )
    description = models.TextField(
        verbose_name="Описание техники",
        blank=True,
        null=True,
        help_text="Подробное описание техники выполнения",
    )

    class Meta:
        verbose_name = "Кастомное упражнение"
        verbose_name_plural = "Кастомные упражнения"
        indexes = [
            models.Index(fields=["user_id"]),
            GinIndex(
                name="custom_ex_name_trgm_idx",
                fields=["name"],
                opclasses=["gin_trgm_ops"],
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "name"], name="unique_customexercise_per_user"
            ),
        ]

    def __str__(self):
        return self.name


class CompletedExercise(TimeStampedModel):
    """Модель для хранения данных о выполненных пользователями упражнений."""

    user_id = models.BigIntegerField(db_index=True)
    training_session = models.ForeignKey(
        TrainingSession,
        db_index=True,
        related_name="exercises",
        verbose_name="Упражнение",
        on_delete=models.CASCADE,
    )
    custom_exercise = models.ForeignKey(
        CustomExercise, on_delete=models.PROTECT, null=True, blank=True
    )
    base_exercise = models.ForeignKey(
        BaseExercise, on_delete=models.PROTECT, null=True, blank=True
    )
    comment = models.TextField(
        verbose_name="Комментарий",
        blank=True,
        null=True,
        help_text="Комментарий к выполненному упражнению",
    )

    class Meta:
        verbose_name = "Выполненное упражнение"
        verbose_name_plural = "Выполненные упражнения"
        indexes = [
            models.Index(fields=["user_id", "training_session"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    (Q(custom_exercise__isnull=False) & Q(base_exercise__isnull=True))
                    | (Q(custom_exercise__isnull=True) & Q(base_exercise__isnull=False))
                ),
                name="completed_exercise_has_valid_source",
            ),
        ]
        ordering = ["training_session", "id"]

    def get_type(self):
        if self.base_exercise:
            return "base"
        if self.custom_exercise:
            return "custom"

    def __str__(self):
        exercise_name = (
            self.base_exercise.name if self.base_exercise else self.custom_exercise.name
        )
        return f"{exercise_name} в {self.training_session}"


class ExerciseSet(TimeStampedModel):
    """Модель для хранения данных о подходе в упражнении."""

    user_id = models.BigIntegerField(db_index=True)
    completed_exercise = models.ForeignKey(
        CompletedExercise,
        db_index=True,
        related_name="sets",
        verbose_name="Подход",
        on_delete=models.CASCADE,
    )
    repetitions = models.PositiveSmallIntegerField(
        verbose_name="Повторения",
        validators=[MinValueValidator(1)],
        help_text="Количество повторений в подходе",
        null=True,
        blank=True,
    )
    weight = models.DecimalField(
        verbose_name="Вес (кг)",
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0.1)],
        help_text="Вес снаряда в килограммах",
    )
    duration_seconds = models.PositiveIntegerField(
        verbose_name="Время выполнения (сек)",
        blank=True,
        null=True,
        help_text="Время выполнения подхода в секундах",
    )
    distance_meters = models.DecimalField(
        verbose_name="Дистанция (м)",
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0.01)],
        help_text="Пройденная дистанция в метрах",
    )
    rest_after_set = models.PositiveIntegerField(
        verbose_name="Отдых после подхода (сек)",
        default=60,
        help_text="Время отдыха после подхода в секундах",
    )

    class Meta:
        verbose_name = "Выполненный подход"
        verbose_name_plural = "Выполненные подходы"
        indexes = [
            models.Index(fields=["completed_exercise"]),
        ]
        ordering = ["completed_exercise", "created_at"]

    def __str__(self):
        return f"Подход {self.set_number} - {self.completed_exercise}"
