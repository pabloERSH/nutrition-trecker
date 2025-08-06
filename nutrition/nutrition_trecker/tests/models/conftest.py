import pytest
from nutrition_trecker.models import BaseFood, CustomFood, Recipe


# Fixtures

@pytest.fixture
def base_food():
    return BaseFood.objects.create(
        name="Курица",
        proteins=20.0,
        fats=5.0,
        carbohydrates=0.0
    )

@pytest.fixture
def custom_food():
    return CustomFood.objects.create(
        user_id=1,
        custom_name="Мой продукт",
        proteins=20.0,
        fats=10.0,
        carbohydrates=30.0
    )

@pytest.fixture
def recipe():
    return Recipe.objects.create(
        user_id=1,
        name="Тестовый рецепт"
    )
