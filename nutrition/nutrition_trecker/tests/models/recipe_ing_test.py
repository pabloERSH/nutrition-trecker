import pytest
from nutrition_trecker.models import RecipeIngredient
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError


@pytest.mark.django_db
class TestRecipeIngredientModel:
    """Класс для тестирования модели RecipeIngredient"""

    def test_create_recipe_ingredient_manual_success(self, recipe):
        ing = RecipeIngredient.objects.create(
            recipe=recipe,
            name="Qwerty",
            proteins=10,
            fats=10,
            carbohydrates=10,
            weight_grams=200,
        )

        assert ing.recipe == recipe
        assert ing.proteins == 10
        assert ing.weight_grams == 200

    def test_create_recipe_ingredient_manual_sum_over_100(self, recipe):
        with pytest.raises(IntegrityError), transaction.atomic():
            RecipeIngredient.objects.create(
                recipe=recipe,
                name="Qwerty",
                proteins=35,
                fats=35,
                carbohydrates=35,
                weight_grams=200,
            )

    def test_create_recipe_ingredient_manual_with_invalid_source(
        self, recipe, custom_food
    ):
        with pytest.raises(IntegrityError), transaction.atomic():
            RecipeIngredient.objects.create(
                recipe=recipe,
                name="Qwerty",
                custom_food=custom_food,
                proteins=1,
                fats=1,
                carbohydrates=1,
                weight_grams=200,
            )

    def test_create_recipe_ingredient_basefood_with_invalid_source(
        self, recipe, base_food
    ):
        with pytest.raises(IntegrityError), transaction.atomic():
            RecipeIngredient.objects.create(
                recipe=recipe, name="Qwerty", base_food=base_food, weight_grams=200
            )

    def test_create_recipe_ingredient_manual_without_fats(self, recipe):
        with pytest.raises(IntegrityError), transaction.atomic():
            RecipeIngredient.objects.create(
                recipe=recipe,
                name="Qwerty",
                proteins=1,
                carbohydrates=1,
                weight_grams=200,
            )

    def test_create_recipe_ingredient_manual_without_weight(self, recipe):
        with pytest.raises(IntegrityError), transaction.atomic():
            RecipeIngredient.objects.create(
                recipe=recipe, name="Qwerty", proteins=1, carbohydrates=1
            )

    def test_create_recipe_ingredient_manual_with_invalid_weight(self, recipe):
        with pytest.raises(IntegrityError), transaction.atomic():
            RecipeIngredient.objects.create(
                recipe=recipe,
                name="Qwerty",
                proteins=1,
                carbohydrates=1,
                weight_grams=-100,
            )

    def test_full_clean_recipe_ingredient_manual_sum_over_100(self, recipe):
        with pytest.raises(ValidationError):
            ing = RecipeIngredient(
                recipe=recipe,
                name="Qwerty",
                proteins=35,
                fats=35,
                carbohydrates=35,
                weight_grams=200,
            )
            ing.full_clean()

    def test_full_clean_recipe_ingredient_manual_without_proteins(self, recipe):
        with pytest.raises(ValidationError):
            ing = RecipeIngredient(
                recipe=recipe, name="Qwerty", fats=1, carbohydrates=1, weight_grams=200
            )
            ing.full_clean()

    def test_full_clean_recipe_ingredient_manual_with_invalid_source(
        self, recipe, base_food
    ):
        with pytest.raises(ValidationError):
            ing = RecipeIngredient(
                recipe=recipe,
                base_food=base_food,
                name="Qwerty",
                proteins=1,
                fats=1,
                carbohydrates=1,
                weight_grams=200,
            )
            ing.full_clean()

    def test_create_recipe_ingredient_basefood_success(self, recipe, base_food):
        ing = RecipeIngredient.objects.create(
            recipe=recipe, base_food=base_food, weight_grams=200
        )

        assert ing.recipe == recipe
        assert ing.base_food == base_food
        assert ing.weight_grams == 200

    def test_create_recipe_ingredient_customfood_success(self, recipe, custom_food):
        ing = RecipeIngredient.objects.create(
            recipe=recipe, custom_food=custom_food, weight_grams=200
        )

        assert ing.recipe == recipe
        assert ing.custom_food == custom_food
        assert ing.weight_grams == 200

    def test_recipe_ingredient_pre_delete_signal_custom_food(self, custom_food, recipe):
        ingr = RecipeIngredient.objects.create(
            recipe=recipe, custom_food=custom_food, weight_grams=200
        )
        custom_food.delete()
        ingr.refresh_from_db()

        assert ingr.base_food is None
        assert ingr.name == "Мой продукт"
        assert ingr.proteins == 20.0
        assert ingr.fats == 10.0
        assert ingr.carbohydrates == 30.0

    def test_recipe_ingredient_pre_delete_signal_base_food(self, base_food, recipe):
        ingr = RecipeIngredient.objects.create(
            recipe=recipe, base_food=base_food, weight_grams=200
        )
        base_food.delete()
        ingr.refresh_from_db()

        assert ingr.base_food is None
        assert ingr.name == "Курица"
        assert ingr.proteins == 20.0
        assert ingr.fats == 5.0
        assert ingr.carbohydrates == 0.0

    def test_create_recipe_ingredient_not_unique(self, recipe, base_food):
        with pytest.raises(IntegrityError), transaction.atomic():
            RecipeIngredient.objects.create(
                recipe=recipe, weight_grams=100, base_food=base_food
            )
            RecipeIngredient.objects.create(
                recipe=recipe, weight_grams=200, base_food=base_food
            )
