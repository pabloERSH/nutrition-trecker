from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, F
from django.db.models.functions import Now
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings


class TimeStampedModel(models.Model):
    """Абстрактная модель с полями даты создания и обновления."""

    created_at = models.DateTimeField(
        _("created at"),
        auto_now_add=True,
        help_text=_("Date when the object was created"),
    )
    updated_at = models.DateTimeField(
        _("updated at"),
        auto_now=True,
        help_text=_("Date when the object was last updated"),
    )

    class Meta:
        abstract = True


class BaseFood(TimeStampedModel):
    """Официальная база продуктов (только для модераторов)."""

    name = models.CharField(
        max_length=255, unique=True, db_index=True, verbose_name="Название продукта"
    )
    proteins = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    fats = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    carbohydrates = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    kcal = models.DecimalField(
        max_digits=6, decimal_places=1, editable=False, blank=True, null=True
    )

    class Meta:
        verbose_name = "Базовый продукт"
        verbose_name_plural = "Базовые продукты"
        constraints = [
            models.CheckConstraint(
                condition=Q(proteins__lte=100 - F("fats") - F("carbohydrates")),
                name="basefood_nutrition_sum_valid",
            )
        ]

    def clean(self):
        if self.proteins + self.fats + self.carbohydrates > 100:
            raise ValidationError(
                "Сумма БЖУ не может превышать 100 г на 100 г продукта."
            )

    def calculate_kcal(self) -> float:
        """Расчёт калорий на 100 г продукта."""
        return round(
            (self.proteins * 4) + (self.fats * 9) + (self.carbohydrates * 4), 1
        )

    def save(self, *args, **kwargs):
        # Пересчёт kcal всегда, игнорируя внешние присвоения
        self.kcal = self.calculate_kcal()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.name} (Б: {self.proteins}, Ж: {self.fats}, У: {self.carbohydrates})"
        )


class UserFavorite(models.Model):
    """Модель хранит добавленные в избранное пользователями продукты из модели BaseFood"""

    user_id = models.BigIntegerField(db_index=True)
    base_food = models.ForeignKey(
        BaseFood, on_delete=models.CASCADE, related_name="favorited_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "base_food"],
                name="unique_favorite_basefood_for_user",
            )
        ]
        indexes = [models.Index(fields=["user_id"]), models.Index(fields=["base_food"])]


class CustomFood(TimeStampedModel):
    """Пользовательские продукты/модификации базовых."""

    user_id = models.BigIntegerField(db_index=True)
    custom_name = models.CharField(max_length=255, db_index=True)
    proteins = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    fats = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    carbohydrates = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    kcal = models.DecimalField(
        max_digits=6, decimal_places=1, editable=False, blank=True, null=True
    )

    class Meta:
        verbose_name = "Пользовательский продукт"
        verbose_name_plural = "Пользовательские продукты"
        indexes = [
            models.Index(fields=["user_id", "custom_name"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "custom_name"], name="unique_customfood_per_user"
            ),
            models.CheckConstraint(
                condition=Q(proteins__lte=100 - F("fats") - F("carbohydrates")),
                name="customfood_nutrition_sum_valid",
            ),
        ]

    def clean(self):
        if (self.proteins + self.fats + self.carbohydrates) > 100:
            raise ValidationError(
                "Сумма БЖУ не может превышать 100 г на 100 г продукта."
            )

    def calculate_kcal(self) -> float:
        """Расчёт калорий на 100 г продукта."""
        return round(
            (self.proteins * 4) + (self.fats * 9) + (self.carbohydrates * 4), 1
        )

    def save(self, *args, **kwargs):
        # Пересчёт kcal всегда, игнорируя внешние присвоения
        self.kcal = self.calculate_kcal()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.custom_name}, (Б: {self.proteins}, Ж: {self.fats}, У: {self.carbohydrates}) [user: {self.user_id}]"


class Recipe(TimeStampedModel):
    user_id = models.BigIntegerField(db_index=True, verbose_name="Пользователь")
    name = models.CharField(max_length=255, verbose_name="Название рецепта")
    description = models.TextField(blank=True, verbose_name="Описание")

    class Meta:
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"

    def calculate_nutrition_per_100g(self) -> dict:
        """
        Возвращает средние БЖУ и калории на 100 г рецепта.
        Пример вывода: {'proteins': 15.2, 'fats': 8.5, 'carbohydrates': 20.1, 'kcal': 210.3}
        """
        total = {
            "weight": 0.0,
            "proteins": 0.0,
            "fats": 0.0,
            "carbohydrates": 0.0,
        }

        ingredients = self.ingredients.select_related("base_food", "custom_food")

        for ing in ingredients:
            total["weight"] += ing.weight_grams  # Суммируем вес

            nutrition = ing.get_nutrition()

            total["proteins"] += nutrition["proteins"]
            total["fats"] += nutrition["fats"]
            total["carbohydrates"] += nutrition["carbohydrates"]

        # Нормируем на 100 г (если вес рецепта > 0)
        if total["weight"] == 0:
            return {
                "weight": 0.0,
                "proteins": 0.0,
                "fats": 0.0,
                "carbohydrates": 0.0,
                "kcal": 0.0,
            }

        return {
            "proteins": round(total["proteins"] * 100 / total["weight"], 1),
            "fats": round(total["fats"] * 100 / total["weight"], 1),
            "carbohydrates": round(total["carbohydrates"] * 100 / total["weight"], 1),
            "kcal": round(
                (4 * total["proteins"] + 9 * total["fats"] + 4 * total["carbohydrates"])
                * 100
                / total["weight"],
                1,
            ),
        }

    def get_ingredients_with_details(self) -> list:
        """
        Возвращает список ингредиентов с деталями.
        Пример вывода:
        [
            {
                'type': 'base',
                'name': 'Куриная грудка',
                'weight_grams': 200,
                'proteins': 44.0,
                'fats': 5.0,
                'carbohydrates': 0.0,
                'kcal': 221.0
            },
            ...
        ]
        """
        ingredients = []
        for ing in self.ingredients.select_related("base_food", "custom_food"):
            nutrition = ing.get_nutrition()

            ingredient_data = {
                "type": ing.get_type(),
                "name": ing.get_name(),
                "weight_grams": ing.weight_grams,
                "proteins": nutrition["proteins"],
                "fats": nutrition["fats"],
                "carbohydrates": nutrition["carbohydrates"],
                "kcal": nutrition["kcal"],
            }

            ingredients.append(ingredient_data)
        return ingredients

    def __str__(self):
        return f"{self.name} (автор: {self.user_id})"


class RecipeIngredient(TimeStampedModel):
    user_id = models.BigIntegerField(db_index=True, verbose_name="Пользователь")
    recipe = models.ForeignKey(
        Recipe,
        db_index=True,
        related_name="ingredients",
        verbose_name="Рецепт",
        on_delete=models.CASCADE,
    )
    weight_grams = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10000)]
    )

    # Варианты источника
    base_food = models.ForeignKey(
        BaseFood, on_delete=models.SET_NULL, null=True, blank=True
    )
    custom_food = models.ForeignKey(
        CustomFood, on_delete=models.SET_NULL, null=True, blank=True
    )

    # Поля для разового ввода информации о нутриентах на 100гр
    name = models.CharField(max_length=255, null=True, blank=True)
    proteins = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    fats = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    carbohydrates = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    kcal = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        editable=False,
        null=True,
        blank=True,
    )

    def clean(self):
        # Проверяем, что ингредиент создан пользователем, который создал рецепт
        if self.user_id != self.recipe.user_id:
            raise ValidationError(
                "Ингредиент для рецепта может быть создан только пользователем, создавшим рецепт"
            )

        # Проверяем, что выбран ровно один источник данных
        sources_count = sum(
            [
                self.base_food is not None,
                self.custom_food is not None,
                self.name is not None
                and self.proteins is not None
                and self.fats is not None
                and self.carbohydrates is not None,
            ]
        )

        if sources_count != 1:
            raise ValidationError(
                "Должен быть выбран ровно один источник данных: base_food, custom_food или ручной ввод."
            )

        # Проверка для ручного ввода
        if self.base_food is None and self.custom_food is None:
            if None in [self.name, self.proteins, self.fats, self.carbohydrates]:
                raise ValidationError(
                    "Для ручного ввода необходимо указать название и все значения БЖУ."
                )

            if (self.proteins + self.fats + self.carbohydrates) > 100:
                raise ValidationError(
                    "Сумма БЖУ не может превышать 100 г на 100 г продукта."
                )

        # Проверка, что для base_food/custom_food не указаны ручные значения
        if self.base_food is not None or self.custom_food is not None:
            if any(
                [
                    self.name is not None,
                    self.proteins is not None,
                    self.fats is not None,
                    self.carbohydrates is not None,
                ]
            ):
                raise ValidationError(
                    "При выборе base_food или custom_food нельзя указывать ручные значения БЖУ."
                )

    class Meta:
        verbose_name = "Ингредиент"
        constraints = [
            models.CheckConstraint(
                condition=(
                    (
                        Q(base_food__isnull=False)
                        & Q(custom_food__isnull=True)
                        & Q(name__isnull=True)
                        & Q(proteins__isnull=True)
                        & Q(fats__isnull=True)
                        & Q(carbohydrates__isnull=True)
                    )  # Только base
                    | (
                        Q(base_food__isnull=True)
                        & Q(custom_food__isnull=False)
                        & Q(name__isnull=True)
                        & Q(proteins__isnull=True)
                        & Q(fats__isnull=True)
                        & Q(carbohydrates__isnull=True)
                    )  # Только custom
                    | (
                        Q(base_food__isnull=True)
                        & Q(custom_food__isnull=True)
                        & Q(name__isnull=True)
                        & Q(proteins__isnull=True)
                        & Q(fats__isnull=True)
                        & Q(carbohydrates__isnull=True)
                    )  # Только recipe
                    | (
                        (
                            Q(base_food__isnull=True)
                            & Q(custom_food__isnull=True)
                            & Q(name__isnull=False)
                            & Q(proteins__isnull=False)
                            & Q(fats__isnull=False)
                            & Q(carbohydrates__isnull=False)
                        )
                        & Q(proteins__lte=100 - F("fats") - F("carbohydrates"))
                    )  # мгновенная запись
                ),
                name="recipeingredient_has_valid_source",
            ),
            models.CheckConstraint(
                condition=Q(weight_grams__gte=1) & Q(weight_grams__lte=10000),
                name="recipeingredient_weight_valid",
            ),
            models.UniqueConstraint(
                fields=["user_id", "recipe", "base_food"],
                name="unique_recipe_ingredient_basefood",
                condition=Q(base_food__isnull=False),
            ),
            models.UniqueConstraint(
                fields=["user_id", "recipe", "custom_food"],
                name="unique_recipe_ingredient_customfood",
                condition=Q(custom_food__isnull=False),
            ),
            models.UniqueConstraint(
                fields=[
                    "user_id",
                    "recipe",
                    "name",
                    "proteins",
                    "fats",
                    "carbohydrates",
                ],
                name="unique_recipe_ingredient_manual",
                condition=Q(base_food__isnull=True, custom_food__isnull=True),
            ),
        ]

    def calculate_total_kcal(self) -> float:
        """Расчёт калорий для указанного веса."""
        if self.base_food:
            kcal_per_100g = self.base_food.kcal
        elif self.custom_food:
            kcal_per_100g = self.custom_food.kcal
        else:
            kcal_per_100g = (
                (self.proteins * 4) + (self.fats * 9) + (self.carbohydrates * 4)
            )

        return round(kcal_per_100g * self.weight_grams / 100, 1)

    def get_nutrition(self) -> dict:
        """Возвращает полную информацию о нутриентах"""
        coeff = self.weight_grams / 100
        if self.base_food:
            source = self.base_food
        elif self.custom_food:
            source = self.custom_food
        else:
            return {
                "proteins": round(float(self.proteins) * coeff, 1),
                "fats": round(float(self.fats) * coeff, 1),
                "carbohydrates": round(float(self.carbohydrates) * coeff, 1),
                "kcal": round(float(self.kcal) * coeff, 1),
            }

        return {
            "proteins": round(float(source.proteins) * coeff, 1),
            "fats": round(float(source.fats) * coeff, 1),
            "carbohydrates": round(float(source.carbohydrates) * coeff, 1),
            "kcal": round(float(source.kcal) * coeff, 1),
        }

    def get_name(self):
        if self.base_food:
            return self.base_food.name
        if self.custom_food:
            return self.custom_food.custom_name
        return self.name

    def get_type(self):
        if self.base_food:
            return "base"
        if self.custom_food:
            return "custom"
        return "manual"

    def save(self, *args, **kwargs):
        # Пересчёт kcal для ручного ввода всегда, игнорируя внешние присвоения
        if None not in [self.name, self.proteins, self.fats, self.carbohydrates]:
            self.kcal = self.calculate_total_kcal()
        super().save(*args, **kwargs)


class EatenFood(TimeStampedModel):
    """Записи о потреблённых продуктах."""

    user_id = models.BigIntegerField(db_index=True)
    eaten_at = models.DateTimeField(
        default=timezone.now,
        help_text=f"Дата не может быть старше {settings.MAX_EATEN_FOOD_AGE_DAYS} дней.",
    )
    weight_grams = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10000)]
    )

    # Варианты источников
    base_food = models.ForeignKey(
        BaseFood, on_delete=models.SET_NULL, null=True, blank=True
    )
    custom_food = models.ForeignKey(
        CustomFood, on_delete=models.SET_NULL, null=True, blank=True
    )
    recipe_food = models.ForeignKey(
        Recipe, null=True, blank=True, on_delete=models.SET_NULL
    )

    # Поля для разового ввода информации о нутриентах на 100гр
    name = models.CharField(max_length=255, null=True, blank=True)
    proteins = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    fats = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    carbohydrates = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    kcal = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        editable=False,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Приём пищи"
        verbose_name_plural = "Приёмы пищи"
        indexes = [
            models.Index(fields=["user_id", "eaten_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    (
                        Q(base_food__isnull=False)
                        & Q(custom_food__isnull=True)
                        & Q(name__isnull=True)
                        & Q(proteins__isnull=True)
                        & Q(fats__isnull=True)
                        & Q(carbohydrates__isnull=True)
                        & Q(recipe_food__isnull=True)
                    )  # Только base
                    | (
                        Q(base_food__isnull=True)
                        & Q(custom_food__isnull=False)
                        & Q(name__isnull=True)
                        & Q(proteins__isnull=True)
                        & Q(fats__isnull=True)
                        & Q(carbohydrates__isnull=True)
                        & Q(recipe_food__isnull=True)
                    )  # Только custom
                    | (
                        Q(base_food__isnull=True)
                        & Q(custom_food__isnull=True)
                        & Q(name__isnull=True)
                        & Q(proteins__isnull=True)
                        & Q(fats__isnull=True)
                        & Q(carbohydrates__isnull=True)
                        & Q(recipe_food__isnull=False)
                    )  # Только recipe
                    | (
                        (
                            Q(base_food__isnull=True)
                            & Q(custom_food__isnull=True)
                            & Q(name__isnull=False)
                            & Q(proteins__isnull=False)
                            & Q(fats__isnull=False)
                            & Q(carbohydrates__isnull=False)
                            & Q(recipe_food__isnull=True)
                        )
                        & Q(proteins__lte=100 - F("fats") - F("carbohydrates"))
                    )  # мгновенная запись
                ),
                name="eatenfood_has_valid_source",
            ),
            models.CheckConstraint(
                condition=Q(weight_grams__gte=1) & Q(weight_grams__lte=10000),
                name="eatenfood_weight_valid",
            ),
            models.CheckConstraint(
                condition=Q(eaten_at__lte=Now())  # Не в будущем
                & Q(
                    eaten_at__gte=Now()
                    - timezone.timedelta(days=settings.MAX_EATEN_FOOD_AGE_DAYS)
                ),  # Не раньше заданного
                name="eatenfood_date_valid",
            ),
        ]

    def clean(self):
        # Проверяем, что дата приёма пищи выбрана правильно
        now = timezone.now()
        max_age = now - timezone.timedelta(days=settings.MAX_EATEN_FOOD_AGE_DAYS)
        if self.eaten_at < max_age:
            raise ValidationError(
                f"Дата приёма пищи не может быть выбрана раньше, чем {settings.MAX_EATEN_FOOD_AGE_DAYS} дней назад"
            )

        if self.eaten_at > now:
            raise ValidationError("Дата приёма пищи не может быть в будущем.")

        # Проверяем, что выбран ровно один источник данных
        sources_count = sum(
            [
                self.base_food is not None,
                self.custom_food is not None,
                self.recipe_food is not None,
                self.name is not None
                and self.proteins is not None
                and self.fats is not None
                and self.carbohydrates is not None,
            ]
        )

        if sources_count != 1:
            raise ValidationError(
                "Должен быть выбран ровно один источник данных: base_food, custom_food, recipe_food или ручной ввод."
            )

        # Проверка для ручного ввода
        if all(
            [self.base_food is None, self.custom_food is None, self.recipe_food is None]
        ):
            if None in [self.name, self.proteins, self.fats, self.carbohydrates]:
                raise ValidationError(
                    "Для ручного ввода необходимо указать название и все значения БЖУ."
                )

            if (self.proteins + self.fats + self.carbohydrates) > 100:
                raise ValidationError(
                    "Сумма БЖУ не может превышать 100 г на 100 г продукта."
                )

        # Проверка, что для base_food/custom_food не указаны ручные значения
        if any(
            [
                self.base_food is not None,
                self.custom_food is not None,
                self.recipe_food is not None,
            ]
        ):
            if any(
                [
                    self.name is not None,
                    self.proteins is not None,
                    self.fats is not None,
                    self.carbohydrates is not None,
                ]
            ):
                raise ValidationError(
                    "При выборе base_food, custom_food или recipe_food нельзя указывать ручные значения БЖУ."
                )

        if self.recipe_food is not None and not self.recipe_food.ingredients.exists():
            raise ValidationError(
                "При выборе recipe_food нельзя выбирать рецепт без ингредиентов."
            )

    def calculate_total_kcal(self) -> float:
        """Расчёт калорий для указанного веса."""
        if self.base_food:
            kcal_per_100g = self.base_food.kcal
        elif self.custom_food:
            kcal_per_100g = self.custom_food.kcal
        elif self.recipe_food:
            kcal_per_100g = self.recipe_food.calculate_nutrition_per_100g()["kcal"]
        else:
            kcal_per_100g = (
                (self.proteins * 4) + (self.fats * 9) + (self.carbohydrates * 4)
            )

        return round(kcal_per_100g * self.weight_grams / 100, 1)

    def get_nutrition(self) -> dict:
        """Возвращает полную информацию о нутриентах"""
        coeff = self.weight_grams / 100
        if self.base_food:
            source = self.base_food
        elif self.custom_food:
            source = self.custom_food
        elif self.recipe_food:
            source = self.recipe_food.calculate_nutrition_per_100g()
            return {
                "proteins": round(source["proteins"] * coeff, 1),
                "fats": round(source["fats"] * coeff, 1),
                "carbohydrates": round(source["carbohydrates"] * coeff, 1),
                "kcal": round(source["kcal"] * coeff, 1),
            }
        else:
            return {
                "proteins": round(float(self.proteins) * coeff, 1),
                "fats": round(float(self.fats) * coeff, 1),
                "carbohydrates": round(float(self.carbohydrates) * coeff, 1),
                "kcal": round(float(self.kcal) * coeff, 1),
            }

        return {
            "proteins": round(float(source.proteins) * coeff, 1),
            "fats": round(float(source.fats) * coeff, 1),
            "carbohydrates": round(float(source.carbohydrates) * coeff, 1),
            "kcal": round(float(source.kcal) * coeff, 1),
        }

    def get_name(self):
        if self.base_food:
            return self.base_food.name
        if self.custom_food:
            return self.custom_food.custom_name
        if self.recipe_food:
            return self.recipe_food.name
        return self.name

    def get_type(self):
        if self.base_food:
            return "base"
        if self.custom_food:
            return "custom"
        if self.recipe_food:
            return "recipe"
        return "manual"

    def save(self, *args, **kwargs):
        # Пересчёт kcal для ручного ввода всегда, игнорируя внешние присвоения
        if None not in [self.name, self.proteins, self.fats, self.carbohydrates]:
            self.kcal = self.calculate_total_kcal()
        super().save(*args, **kwargs)
