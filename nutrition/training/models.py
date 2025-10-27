from django.db import models
from common.models.TimeStampedModel import TimeStampedModel
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Q


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
        ]


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

    class Meta:
        verbose_name = "Базовое упражнение"
        verbose_name_plural = "Базовые упражнения"


class CustomExercise(TimeStampedModel):
    """Модель для хранения данных о пользовательских упражнениях."""

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
    description = models.TextField(
        verbose_name="Описание техники",
        blank=True,
        null=True,
        help_text="Подробное описание техники выполнения",
    )
    image = models.ImageField(
        verbose_name="Фото",
        upload_to="photos/custom_exercises/",
        help_text="Фотография упражнения",
    )

    class Meta:
        verbose_name = "Кастомное упражнение"
        verbose_name_plural = "Кастомные упражнения"


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

    class Meta:
        verbose_name = "Выполненное упражнение"
        verbose_name_plural = "Выполненные упражнения"
        indexes = [
            models.Index(fields=["user_id", "training_session"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    (Q(custom_exercise__is_null=False) & Q(base_exercise__is_null=True))
                    | (
                        Q(custom_exercise__is_null=True)
                        & Q(base_exercise__is_null=False)
                    )
                ),
                name="completed_exercise_has_valid_source",
            ),
        ]


class ExerciseSet(TimeStampedModel):
    """Модель для хранения данных о подходе в упражнении."""

    completed_exercise = models.ForeignKey(
        CompletedExercise,
        db_index=True,
        related_name="exercise_set",
        verbose_name="Подход",
        on_delete=models.CASCADE,
    )
    repetitions = models.PositiveSmallIntegerField(
        verbose_name="Повторения",
        validators=[MinValueValidator(1)],
        help_text="Количество повторений в подходе",
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
    set_number = models.PositiveSmallIntegerField(
        verbose_name="Номер подхода",
        validators=[MinValueValidator(1)],
        default=1,
        help_text="Порядковый номер подхода (1, 2, 3...)",
    )
