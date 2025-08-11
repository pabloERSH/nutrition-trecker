import pytest
from nutrition_trecker.models import CustomFood
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction


@pytest.mark.django_db
class TestCustomFoodModel:
    """Класс для тестирования модели CustomFood"""

    def test_create_customfood_success(self):
        food = CustomFood.objects.create(
            user_id=1, custom_name="Qwerty", proteins=10.5, fats=11, carbohydrates=12.1
        )

        assert food.user_id == 1
        assert food.custom_name == "Qwerty"
        assert food.proteins == 10.5
        assert food.fats == 11
        assert food.carbohydrates == 12.1

    def test_calculate_kcal(self):
        food = CustomFood(
            user_id=1, custom_name="Qwerty", proteins=10.5, fats=11, carbohydrates=12.1
        )
        assert food.calculate_kcal() == pytest.approx(189.4)

    def test_create_customfood_invalid_nutrition_full_clean(self):
        with pytest.raises(ValidationError):
            food = CustomFood(
                user_id=3, custom_name="Qwerty", proteins=35, fats=35, carbohydrates=35
            )
            food.full_clean()

    def test_create_customfood_invalid_nutrition_constraints(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            CustomFood.objects.create(
                user_id=2, custom_name="Qwerty", proteins=35, fats=35, carbohydrates=35
            )
