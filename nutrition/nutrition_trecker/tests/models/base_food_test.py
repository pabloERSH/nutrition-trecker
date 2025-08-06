import pytest
from nutrition_trecker.models import BaseFood
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction


@pytest.mark.django_db
class TestBaseFoodModel:
    """Класс для тестирования модели BaseFood"""

    def test_create_basefood_success(self):
        food = BaseFood.objects.create(
            name="Яблоко",
            proteins=0.4,
            fats=0.4,
            carbohydrates=11.8
        )
        assert food.name == "Яблоко"
        assert food.proteins == 0.4
        assert food.fats == 0.4
        assert food.carbohydrates == 11.8

    def test_create_basefood_invalid_nutrition_clean(self):
        with pytest.raises(ValidationError):
            food = BaseFood(
                name="Qwerty",
                proteins=35,
                fats=35,
                carbohydrates=35
            )
            food.full_clean()

    def test_create_basefood_invalid_nutrition_constraints(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            BaseFood.objects.create(
                name="Qwerty",
                proteins=35,
                fats=35,
                carbohydrates=35
            )

    def test_calculate_kcal(self):
        food = BaseFood(
            name="Qwerty",
            proteins=10.5,
            fats=11,
            carbohydrates=12.1
        )
        assert food.calculate_kcal() == pytest.approx(189.4)
