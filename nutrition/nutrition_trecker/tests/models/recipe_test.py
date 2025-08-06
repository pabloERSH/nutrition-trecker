import pytest
from nutrition_trecker.models import Recipe, RecipeIngredient
from django.core.exceptions import ValidationError
from decimal import Decimal


@pytest.mark.django_db
class TestRecipeModel:
    """Класс для тестирования модели Recipe"""

    def test_create_recipe_success_clean(self):
        recipe = Recipe.objects.create(user_id=1, name="My Recipe")

        RecipeIngredient.objects.create(
            recipe=recipe,
            weight_grams=100,
            name="Ingredient 1",
            proteins=1,
            fats=1,
            carbohydrates=1,
        )

        recipe.full_clean()

    def test_create_recipe_without_ingr_clean(self):
        with pytest.raises(ValidationError):
            recipe = Recipe.objects.create(user_id=1, name="My Recipe")

            recipe.full_clean()

    def test_recipe_calculate_nutrition_per_100g(self):
        recipe = Recipe.objects.create(user_id=1, name="My Recipe")

        RecipeIngredient.objects.create(
            recipe=recipe,
            weight_grams=100,
            name="Ingredient 1",
            proteins=1,
            fats=1,
            carbohydrates=1,
        )

        RecipeIngredient.objects.create(
            recipe=recipe,
            weight_grams=200,
            name="Ingredient 2",
            proteins=2.5,
            fats=0.6,
            carbohydrates=5.6,
        )

        nutrition = recipe.calculate_nutrition_per_100g()

        assert nutrition["proteins"] == Decimal("2.0")
        assert nutrition["fats"] == Decimal("0.7")
        assert nutrition["carbohydrates"] == Decimal("4.1")
        assert nutrition["kcal"] == Decimal("30.9")

    def test_recipe_get_ingredients_with_details(self, base_food, custom_food):
        recipe = Recipe.objects.create(user_id=1, name="My Recipe")

        RecipeIngredient.objects.create(
            recipe=recipe, weight_grams=100, base_food=base_food
        )

        RecipeIngredient.objects.create(
            recipe=recipe,
            weight_grams=200,
            name="Ingredient 2",
            proteins=2.5,
            fats=0.6,
            carbohydrates=5.6,
        )

        RecipeIngredient.objects.create(
            recipe=recipe, weight_grams=250, custom_food=custom_food
        )

        details = recipe.get_ingredients_with_details()

        assert len(details) == 3
        assert details[0]["type"] == "base"
        assert details[0]["proteins"] == 20.0
        assert details[1]["type"] == "manual"
        assert details[1]["fats"] == 0.6
        assert details[2]["type"] == "custom"
        assert details[2]["carbohydrates"] == 30.0
