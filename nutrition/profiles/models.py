from django.db import models
from django.utils import timezone
from common.models.TimeStampedModel import TimeStampedModel


class UserProfile(TimeStampedModel):
    """Профиль пользователя для расчётов и контекста LLM."""

    GENDER_CHOICES = [("M", "Мужчина"), ("F", "Женщина")]

    GOAL_CHOICES = [
        ("CUT", "Похудение"),
        ("MAINTAIN", "Поддержание"),
        ("BULK", "Набор массы"),
    ]

    ACTIVITY_CHOICES = [
        (1.2, "Сидячий"),
        (1.375, "Легкий (1-3 тренировки/нед)"),
        (1.55, "Средний (3-5 тренировок/нед)"),
        (1.725, "Высокий (6-7 тренировок/нед)"),
        (1.9, "Экстремальный"),
    ]

    user_id = models.BigIntegerField(primary_key=True)

    # Биометрия теперь разрешает null
    gender = models.CharField(
        max_length=1, choices=GENDER_CHOICES, null=True, blank=True
    )
    birth_date = models.DateField(null=True, blank=True)
    height = models.PositiveSmallIntegerField(null=True, blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    body_fat = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True
    )

    activity_level = models.FloatField(choices=ACTIVITY_CHOICES, default=1.2)
    goal_type = models.CharField(
        max_length=10, choices=GOAL_CHOICES, default="MAINTAIN"
    )

    target_weight = models.PositiveSmallIntegerField(default=0)

    # БЖУ по умолчанию 0
    target_proteins = models.PositiveSmallIntegerField(default=0)
    target_fats = models.PositiveSmallIntegerField(default=0)
    target_carbs = models.PositiveSmallIntegerField(default=0)

    dietary_restrictions = models.TextField(blank=True)

    @property
    def age(self):
        if not self.birth_date:
            return 0
        today = timezone.now().date()
        bd = self.birth_date  # Django автоматически конвертирует из БД в объект date
        return today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))

    @property
    def target_calories(self):
        # Если БЖУ не заполнены, вернет 0
        p = self.target_proteins or 0
        f = self.target_fats or 0
        c = self.target_carbs or 0
        return (p * 4) + (c * 4) + (f * 9)
