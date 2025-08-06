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
        _('created at'),
        auto_now_add=True,
        help_text=_('Date when the object was created')
    )
    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True,
        help_text=_('Date when the object was last updated')
    )

    class Meta:
        abstract = True


class BaseFood(TimeStampedModel):
    """Официальная база продуктов (только для модераторов)."""
    name = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        verbose_name="Название продукта"
    )
    proteins = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    fats = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    carbohydrates = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    class Meta:
        verbose_name = "Базовый продукт"
        verbose_name_plural = "Базовые продукты"
        constraints = [
            models.CheckConstraint(
                condition=Q(proteins__lte=100 - F('fats') - F('carbohydrates')),
                name="basefood_nutrition_sum_valid"
            )
        ]

    def clean(self):
        if None in [self.proteins, self.fats, self.carbohydrates]:
            raise ValidationError("Для базового продукта укажите все значения БЖУ.")

        if self.proteins + self.fats + self.carbohydrates > 100:
            raise ValidationError("Сумма БЖУ не может превышать 100 г на 100 г продукта.")

    def calculate_kcal(self) -> float:
        """Расчёт калорий на 100 г продукта."""
        return round((self.proteins * 4) + (self.fats * 9) + (self.carbohydrates * 4), 1)

    def __str__(self):
        return f"{self.name} (Б: {self.proteins}, Ж: {self.fats}, У: {self.carbohydrates})"
    

class UserFavorite(models.Model):
    user_id = models.BigIntegerField(db_index=True)
    food = models.ForeignKey(BaseFood, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['user_id', 'food']]
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['food'])
        ]


class CustomFood(TimeStampedModel):
    """Пользовательские продукты/модификации базовых."""
    user_id = models.BigIntegerField(db_index=True)
    custom_name = models.CharField(max_length=255, db_index=True)
    proteins = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    fats = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    carbohydrates = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    class Meta:
        verbose_name = "Пользовательский продукт"
        verbose_name_plural = "Пользовательские продукты"
        indexes = [
            models.Index(fields=['user_id', 'custom_name']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user_id', 'custom_name'],
                name='unique_customfood_per_user'
            ),
            models.CheckConstraint(
                condition=Q(proteins__lte=100 - F('fats') - F('carbohydrates')),
                name="customfood_nutrition_sum_valid"
            )
        ]

    def clean(self):
        if None in [self.proteins, self.fats, self.carbohydrates]:
            raise ValidationError("Для кастомного продукта укажите все значения БЖУ.")
            
        if (self.proteins + self.fats + self.carbohydrates) > 100:
            raise ValidationError("Сумма БЖУ не может превышать 100 г на 100 г продукта.")

    def calculate_kcal(self) -> float:
        """Расчёт калорий на 100 г продукта."""
        return round((self.proteins * 4) + (self.fats * 9) + (self.carbohydrates * 4), 1)

    def __str__(self):
        return f"{self.custom_name}, (Б: {self.proteins}, Ж: {self.fats}, У: {self.carbohydrates}) [user: {self.user_id}]"
    

class Recipe(TimeStampedModel):
    user_id = models.BigIntegerField(db_index=True, verbose_name="Пользователь")
    name = models.CharField(max_length=255, verbose_name="Название рецепта")
    description = models.TextField(blank=True, verbose_name="Описание")

    class Meta:
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"

    def clean(self):
        if not self.ingredients.exists() and self.pk:
            raise ValidationError("Рецепт не может быть без ингредиентов!")

    def calculate_nutrition_per_100g(self) -> dict:
        """
        Возвращает средние БЖУ и калории на 100 г рецепта.
        Пример вывода: {'proteins': 15.2, 'fats': 8.5, 'carbohydrates': 20.1, 'kcal': 210.3}
        """
        from decimal import Decimal
        total = {
            'weight': 0,
            'proteins': Decimal('0'),
            'fats': Decimal('0'),
            'carbohydrates': Decimal('0')
        }

        ingredients = self.ingredients.select_related('base_food', 'custom_food').all()

        for ing in ingredients:
            total['weight'] += ing.weight_grams  # Суммируем вес

            # Расчёт нутриентов в зависимости от типа ингредиента
            if ing.base_food:  # Базовый продукт
                food = ing.base_food
                total['proteins'] += food.proteins * ing.weight_grams / 100
                total['fats'] += food.fats * ing.weight_grams / 100
                total['carbohydrates'] += food.carbohydrates * ing.weight_grams / 100

            elif ing.custom_food:  # Пользовательский продукт
                food = ing.custom_food
                total['proteins'] += food.proteins * ing.weight_grams / 100
                total['fats'] += food.fats * ing.weight_grams / 100
                total['carbohydrates'] += food.carbohydrates * ing.weight_grams / 100

            else:  # Ручной ввод
                total['proteins'] += ing.proteins * ing.weight_grams / 100
                total['fats'] += ing.fats * ing.weight_grams / 100
                total['carbohydrates'] += ing.carbohydrates * ing.weight_grams / 100

        # Нормируем на 100 г (если вес рецепта > 0)
        if total['weight'] == 0:
            return {
                'weight': 0,
                'proteins': Decimal('0'),
                'fats': Decimal('0'),
                'carbohydrates': Decimal('0')
            }

        return {
            'proteins': round(total['proteins'] * 100 / total['weight'], 1),
            'fats': round(total['fats'] * 100 / total['weight'], 1),
            'carbohydrates': round(total['carbohydrates'] * 100 / total['weight'], 1),
            'kcal': round((4 * total['proteins'] + 9 * total['fats'] + 4 * total['carbohydrates']) * 100 / total['weight'], 1)
        }

    def get_ingredients_with_details(self) -> list:
        """
        Возвращает список ингредиентов с деталями.
        Пример вывода:
        [
            {
                'type': 'base',
                'name': 'Куриная грудка',
                'weight': 200,
                'proteins': 22.0,
                'fats': 2.5,
                'carbohydrates': 0.0
            },
            ...
        ]
        """
        ingredients = []
        for ing in self.ingredients.select_related('base_food', 'custom_food').all():
            ingredient_data = {
                'weight': ing.weight_grams,
                'proteins': None,
                'fats': None,
                'carbohydrates': None
            }

            if ing.base_food:
                ingredient_data.update({
                    'type': 'base',
                    'name': ing.base_food.name,
                    'proteins': float(ing.base_food.proteins),
                    'fats': float(ing.base_food.fats),
                    'carbohydrates': float(ing.base_food.carbohydrates)
                })
            elif ing.custom_food:
                ingredient_data.update({
                    'type': 'custom',
                    'name': ing.custom_food.custom_name,
                    'proteins': float(ing.custom_food.proteins),
                    'fats': float(ing.custom_food.fats),
                    'carbohydrates': float(ing.custom_food.carbohydrates)
                })
            else:
                ingredient_data.update({
                    'type': 'manual',
                    'name': ing.name,
                    'proteins': float(ing.proteins),
                    'fats': float(ing.fats),
                    'carbohydrates': float(ing.carbohydrates)
                })

            ingredients.append(ingredient_data)
        return ingredients

    def __str__(self):
        return f"{self.name} (автор: {self.user_id})"
    

class RecipeIngredient(TimeStampedModel):
    recipe = models.ForeignKey(
        Recipe,
        db_index=True, 
        related_name="ingredients", 
        verbose_name="Рецепт", 
        on_delete=models.CASCADE
    )
    weight_grams = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10000)]
    )

    # Варианты источника
    base_food = models.ForeignKey(
        BaseFood,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    custom_food = models.ForeignKey(
        CustomFood,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Ручной ввод
    name = models.CharField(max_length=255, null=True, blank=True)
    proteins = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    fats = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    carbohydrates = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    def clean(self):
        # Проверяем, что выбран ровно один источник данных
        sources_count = sum([
            self.base_food is not None,
            self.custom_food is not None,
            self.name is not None and self.proteins is not None and self.fats is not None and self.carbohydrates is not None
        ])
        
        if sources_count != 1:
            raise ValidationError("Должен быть выбран ровно один источник данных: base_food, custom_food или ручной ввод")

        # Проверка для ручного ввода
        if self.base_food is None and self.custom_food is None:
            if None in [self.name, self.proteins, self.fats, self.carbohydrates]:
                raise ValidationError("Для ручного ввода необходимо указать название и все значения БЖУ")
            
            if (self.proteins + self.fats + self.carbohydrates) > 100:
                raise ValidationError("Сумма БЖУ не может превышать 100 г на 100 г продукта")

        # Проверка, что для base_food/custom_food не указаны ручные значения
        if self.base_food is not None or self.custom_food is not None:
            if any([self.name is not None, self.proteins is not None, self.fats is not None, self.carbohydrates is not None]):
                raise ValidationError("При выборе base_food или custom_food нельзя указывать ручные значения БЖУ")

    class Meta:
        verbose_name = "Ингредиент"
        constraints = [
            models.CheckConstraint(
                condition=(
                    (Q(base_food__isnull=False) & Q(custom_food__isnull=True) & Q(name__isnull=True) & Q(proteins__isnull=True) & Q(fats__isnull=True) & Q(carbohydrates__isnull=True)) |   # Только base
                    (Q(base_food__isnull=True) & Q(custom_food__isnull=False) & Q(name__isnull=True) & Q(proteins__isnull=True) & Q(fats__isnull=True) & Q(carbohydrates__isnull=True)) |   # Только custom
                    (Q(base_food__isnull=True) & Q(custom_food__isnull=True) & Q(name__isnull=True) & Q(proteins__isnull=True) & Q(fats__isnull=True) & Q(carbohydrates__isnull=True)) |   # Только recipe
                    ((Q(base_food__isnull=True) & Q(custom_food__isnull=True) & Q(name__isnull=False) & Q(proteins__isnull=False) & Q(fats__isnull=False) & Q(carbohydrates__isnull=False)) &
                    Q(proteins__lte=100 - F('fats') - F('carbohydrates')))     # мгновенная запись
                ),
                name="recipeingredient_has_valid_source"
            ),
            models.CheckConstraint(
                condition=Q(weight_grams__gte=1) & Q(weight_grams__lte=10000),
                name="recipeingredient_weight_valid"
            ),
        ]
    

class EatenFood(TimeStampedModel):
    """Записи о потреблённых продуктах."""
    user_id = models.BigIntegerField(db_index=True)
    eaten_at = models.DateTimeField(default=timezone.now, help_text=f"Дата не может быть старше {settings.MAX_EATEN_FOOD_AGE_DAYS} дней.")
    weight_grams = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10000)]
    )
    
    # Варианты источников
    base_food = models.ForeignKey(
        BaseFood,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    custom_food = models.ForeignKey(
        CustomFood,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    recipe_food = models.ForeignKey(
        Recipe,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    
    # Поля для разового ввода
    name = models.CharField(max_length=255, null=True, blank=True)
    proteins = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    fats = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    carbohydrates = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    class Meta:
        verbose_name = "Приём пищи"
        verbose_name_plural = "Приёмы пищи"
        indexes = [
            models.Index(fields=['user_id', 'eaten_at']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    (Q(base_food__isnull=False) & Q(custom_food__isnull=True) & Q(name__isnull=True) & Q(proteins__isnull=True) & Q(fats__isnull=True) & Q(carbohydrates__isnull=True) & Q(recipe_food__isnull=True)) |   # Только base
                    (Q(base_food__isnull=True) & Q(custom_food__isnull=False) & Q(name__isnull=True) & Q(proteins__isnull=True) & Q(fats__isnull=True) & Q(carbohydrates__isnull=True) & Q(recipe_food__isnull=True)) |   # Только custom
                    (Q(base_food__isnull=True) & Q(custom_food__isnull=True) & Q(name__isnull=True) & Q(proteins__isnull=True) & Q(fats__isnull=True) & Q(carbohydrates__isnull=True) & Q(recipe_food__isnull=False)) |   # Только recipe
                    ((Q(base_food__isnull=True) & Q(custom_food__isnull=True) & Q(name__isnull=False) & Q(proteins__isnull=False) & Q(fats__isnull=False) & Q(carbohydrates__isnull=False) & Q(recipe_food__isnull=True)) &
                    Q(proteins__lte=100 - F('fats') - F('carbohydrates')))     # мгновенная запись
                ),
                name="eatenfood_has_valid_source"
            ),
            models.CheckConstraint(
                condition=Q(weight_grams__gte=1) & Q(weight_grams__lte=10000),
                name="eatenfood_weight_valid"
            ),
            models.CheckConstraint(
                condition=Q(eaten_at__lte=Now()) &  # Не в будущем
                          Q(eaten_at__gte=Now() - timezone.timedelta(days=settings.MAX_EATEN_FOOD_AGE_DAYS)), # Не раньше заданного
                name="eatenfood_date_valid"
            )
        ]

    def clean(self):
        # Проверяем, что дата приёма пищи выбрана правильно
        now = timezone.now()
        max_age = now - timezone.timedelta(days=settings.MAX_EATEN_FOOD_AGE_DAYS)
        if self.eaten_at < max_age:
            raise ValidationError(f"Дата приёма пищи не может быть выбрана раньше, чем {settings.MAX_EATEN_FOOD_AGE_DAYS} дней назад")

        if self.eaten_at > now:
            raise ValidationError("Дата приёма пищи не может быть в будущем")

        # Проверяем, что выбран ровно один источник данных
        sources_count = sum([
            self.base_food is not None,
            self.custom_food is not None,
            self.recipe_food is not None,
            self.name is not None and self.proteins is not None and self.fats is not None and self.carbohydrates is not None
        ])
        
        if sources_count != 1:
            raise ValidationError("Должен быть выбран ровно один источник данных: base_food, custom_food, recipe_food или ручной ввод")

        # Проверка для ручного ввода
        if all([self.base_food is None, self.custom_food is None, self.recipe_food is None]):
            if None in [self.name, self.proteins, self.fats, self.carbohydrates]:
                raise ValidationError("Для ручного ввода необходимо указать название и все значения БЖУ")
            
            if (self.proteins + self.fats + self.carbohydrates) > 100:
                raise ValidationError("Сумма БЖУ не может превышать 100 г на 100 г продукта")

        # Проверка, что для base_food/custom_food не указаны ручные значения
        if any([self.base_food is not None, self.custom_food is not None, self.recipe_food is not None]):
            if any([self.name is not None, self.proteins is not None, self.fats is not None, self.carbohydrates is not None]):
                raise ValidationError("При выборе base_food, custom_food или recipe_food нельзя указывать ручные значения БЖУ")
        
    def calculate_total_kcal(self) -> float:
        """Расчёт калорий для указанного веса."""
        if self.base_food:
            kcal_per_100g = self.base_food.calculate_kcal()
        elif self.custom_food:
            kcal_per_100g = self.custom_food.calculate_kcal()
        elif self.recipe_food:
            kcal_per_100g = self.recipe_food.calculate_nutrition_per_100g()['kcal']
        else:
            kcal_per_100g = (self.proteins * 4) + (self.fats * 9) + (self.carbohydrates * 4)
        
        return round(kcal_per_100g * self.weight_grams / 100, 1)

    def get_nutrition(self) -> dict:
        """Возвращает БЖУ для отчётов."""
        if self.base_food:
            source = self.base_food
        elif self.custom_food:
            source = self.custom_food
        else:
            return {
                'proteins': self.proteins,
                'fats': self.fats,
                'carbohydrates': self.carbohydrates
            }
        
        return {
            'proteins': source.proteins,
            'fats': source.fats,
            'carbohydrates': source.carbohydrates
        }
    