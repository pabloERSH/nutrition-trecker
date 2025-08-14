import pytest
from nutrition_trecker.models import Recipe, RecipeIngredient


@pytest.mark.django_db
class TestRecipeModel:
    """Класс для тестирования модели Recipe"""

    def test_create_recipe_success_full_clean(self):
        recipe = Recipe.objects.create(user_id=1, name="My Recipe")

        RecipeIngredient.objects.create(
            user_id=1,
            recipe=recipe,
            weight_grams=100,
            name="Ingredient 1",
            proteins=1,
            fats=1,
            carbohydrates=1,
        )

        recipe.full_clean()

    def test_recipe_calculate_nutrition(self):
        recipe = Recipe.objects.create(user_id=1, name="My Recipe")

        RecipeIngredient.objects.create(
            user_id=1,
            recipe=recipe,
            weight_grams=100,
            name="Ingredient 1",
            proteins=1,
            fats=1,
            carbohydrates=1,
        )

        RecipeIngredient.objects.create(
            user_id=1,
            recipe=recipe,
            weight_grams=200,
            name="Ingredient 2",
            proteins=2.5,
            fats=0.6,
            carbohydrates=5.6,
        )

        nutrition = recipe.calculate_nutrition()

        assert nutrition["total_weight"] == 300

        assert nutrition["per_100g"]["proteins"] == 2.0
        assert nutrition["per_100g"]["fats"] == 0.7
        assert nutrition["per_100g"]["carbohydrates"] == 4.1
        assert nutrition["per_100g"]["kcal"] == 30.9

        assert nutrition["total"]["proteins"] == 6.0
        assert nutrition["total"]["fats"] == 2.2
        assert nutrition["total"]["carbohydrates"] == 12.2
        assert nutrition["total"]["kcal"] == 92.6

    def test_recipe_get_ingredients_with_details(self, base_food, custom_food):
        recipe = Recipe.objects.create(user_id=1, name="My Recipe")

        RecipeIngredient.objects.create(
            user_id=1, recipe=recipe, weight_grams=100, base_food=base_food
        )

        RecipeIngredient.objects.create(
            user_id=1,
            recipe=recipe,
            weight_grams=200,
            name="Ingredient 2",
            proteins=2.5,
            fats=0.6,
            carbohydrates=5.6,
        )

        RecipeIngredient.objects.create(
            user_id=1, recipe=recipe, weight_grams=250, custom_food=custom_food
        )

        details = recipe.get_ingredients_with_details()

        assert len(details) == 3
        assert all(isinstance(ingr, dict) and ingr for ingr in details)
        required_keys = {
            "type",
            "name",
            "proteins",
            "fats",
            "carbohydrates",
            "weight_grams",
        }
        missing_keys = required_keys - {k for d in details for k in d}
        assert not missing_keys
