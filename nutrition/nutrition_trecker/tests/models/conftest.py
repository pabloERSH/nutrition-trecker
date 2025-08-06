import pytest
from nutrition_trecker.models import BaseFood, CustomFood, Recipe, RecipeIngredient


# Fixtures


@pytest.fixture
def base_food():
    return BaseFood.objects.create(
        name="Курица", proteins=20.0, fats=5.0, carbohydrates=0.0
    )


@pytest.fixture
def custom_food():
    return CustomFood.objects.create(
        user_id=1,
        custom_name="Мой продукт",
        proteins=20.0,
        fats=10.0,
        carbohydrates=30.0,
    )


@pytest.fixture
def recipe():
    return Recipe.objects.create(user_id=1, name="Тестовый рецепт")


@pytest.fixture
def recipe_with_igredients(base_food, custom_food):
    recipe = Recipe.objects.create(user_id=1, name="Тестовый рецепт")
    RecipeIngredient.objects.create(
        recipe=recipe, weight_grams=150, base_food=base_food
    )
    RecipeIngredient.objects.create(
        recipe=recipe,
        weight_grams=200,
        name="Secret Ingredient",
        proteins=10,
        fats=0.3,
        carbohydrates=6,
    )
    RecipeIngredient.objects.create(
        recipe=recipe, weight_grams=150, custom_food=custom_food
    )
    return recipe
