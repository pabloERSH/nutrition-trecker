import pytest
from nutrition_trecker import models


@pytest.mark.django_db
class TestModelsExtra:
    def test_get_type_and_get_name_methods(self, base_food, recipe, custom_food):
        eaten_food_base = models.EatenFood.objects.create(
            user_id=1, base_food=base_food, weight_grams=200
        )

        ingr = models.RecipeIngredient.objects.create(
            user_id=1, recipe=recipe, weight_grams=100, custom_food=custom_food
        )

        assert eaten_food_base.get_type() == "base"
        assert eaten_food_base.get_name() == eaten_food_base.base_food.name

        assert ingr.get_type() == "custom"
        assert ingr.get_name() == ingr.custom_food.custom_name
