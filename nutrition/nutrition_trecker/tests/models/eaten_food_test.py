import pytest
from nutrition_trecker.models import EatenFood
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.conf import settings
from decimal import Decimal


@pytest.mark.django_db
class TestEatenFoodModel:
    """Класс для тестирования модели EatenFood"""

    def test_create_eatenfood_manual_success(self):
        eaten_food = EatenFood.objects.create(
            user_id=1,
            name="Qwerty",
            proteins=10,
            fats=10,
            carbohydrates=10,
            weight_grams=200
        )

        assert eaten_food.proteins == 10
        assert eaten_food.weight_grams == 200

    def test_create_eatenfood_manual_sum_over_100(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            EatenFood.objects.create(
                user_id=1,
                name="Qwerty",
                proteins=35,
                fats=35,
                carbohydrates=35,
                weight_grams=200
            )

    def test_create_eatenfood_manual_with_invalid_source(self, custom_food):
        with pytest.raises(IntegrityError), transaction.atomic():
            EatenFood.objects.create(
                user_id=1,
                name="Qwerty",
                custom_food=custom_food,
                proteins=1,
                fats=1,
                carbohydrates=1,
                weight_grams=200
            )

    def test_create_eatenfood_basefood_with_invalid_source(self, base_food):
        with pytest.raises(IntegrityError), transaction.atomic():
            EatenFood.objects.create(
                user_id=1,
                name="Qwerty",
                base_food=base_food,
                weight_grams=200
            )

    def test_create_eatenfood_manual_without_fats(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            EatenFood.objects.create(
                user_id=1,
                name="Qwerty",
                proteins=1,
                carbohydrates=1,
                weight_grams=200
            )

    def test_create_eatenfood_manual_without_weight(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            EatenFood.objects.create(
                user_id=1,
                name="Qwerty",
                proteins=1,
                carbohydrates=1
            )

    def test_create_eatenfood_manual_with_invalid_weight(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            EatenFood.objects.create(
                user_id=1,
                name="Qwerty",
                proteins=1,
                carbohydrates=1,
                weight_grams = -100
            )

    def test_clean_eatenfood_manual_sum_over_100(self):
        with pytest.raises(ValidationError):
            eaten_food = EatenFood(
                user_id=1,
                name="Qwerty",
                proteins=35,
                fats=35,
                carbohydrates=35,
                weight_grams=200
            )
            eaten_food.full_clean()

    def test_clean_eatenfood_manual_without_proteins(self):
        with pytest.raises(ValidationError):
            eaten_food = EatenFood(
                user_id=1,
                name="Qwerty",
                fats=1,
                carbohydrates=1,
                weight_grams=200
            )
            eaten_food.full_clean()

    def test_clean_eatenfood_manual_with_invalid_source(self, base_food):
        with pytest.raises(ValidationError):
            eaten_food = EatenFood(
                user_id=1,
                base_food=base_food,
                name="Qwerty",
                proteins=1,
                fats=1,
                carbohydrates=1,
                weight_grams=200
            )
            eaten_food.full_clean()

    def test_create_eatenfood_basefood_success(self, base_food):
        eaten_food = EatenFood.objects.create(
            user_id=1,
            base_food=base_food,
            weight_grams=200
        )

        assert eaten_food.base_food == base_food
        assert eaten_food.weight_grams == 200

    def test_create_eatenfood_customfood_success(self, custom_food):
        eaten_food = EatenFood.objects.create(
            user_id=1,
            custom_food=custom_food,
            weight_grams=200
        )

        assert eaten_food.custom_food == custom_food
        assert eaten_food.weight_grams == 200

    def test_create_eatenfood_recipe_success(self, recipe_with_igredients):
        eaten_food = EatenFood.objects.create(
            user_id=2,
            recipe_food=recipe_with_igredients,
            weight_grams=350
        )

        assert eaten_food.recipe_food == recipe_with_igredients
        assert eaten_food.weight_grams == 350

    def test_create_eatenfood_with_valid_eaten_at(self, custom_food):
        date = timezone.now() - timezone.timedelta(days=settings.MAX_EATEN_FOOD_AGE_DAYS - 1)
        eaten_food = EatenFood.objects.create(
            user_id=1,
            eaten_at=date,
            custom_food=custom_food,
            weight_grams=200
        )
        
        assert eaten_food.eaten_at == date

    def test_create_eatenfood_with_invalid_old_eaten_at(self, custom_food):
        date = timezone.now() - timezone.timedelta(days=settings.MAX_EATEN_FOOD_AGE_DAYS + 1)
        with pytest.raises(IntegrityError), transaction.atomic():
            EatenFood.objects.create(
                user_id=1,
                eaten_at=date,
                custom_food=custom_food,
                weight_grams=200
            )

    def test_create_eatenfood_with_invalid_future_eaten_at(self, custom_food):
        date = timezone.now() + timezone.timedelta(seconds=10)
        with pytest.raises(IntegrityError), transaction.atomic():
            EatenFood.objects.create(
                user_id=1,
                eaten_at=date,
                custom_food=custom_food,
                weight_grams=200
            )

    def test_clean_eatenfood_with_valid_eaten_at(self, custom_food):
        date = timezone.now() - timezone.timedelta(days=settings.MAX_EATEN_FOOD_AGE_DAYS - 1)
        eaten_food = EatenFood(
            user_id=1,
            eaten_at=date,
            custom_food=custom_food,
            weight_grams=200
        )
        
        eaten_food.full_clean()

    def test_clean_eatenfood_with_invalid_old_eaten_at(self, custom_food):
        date = timezone.now() - timezone.timedelta(days=settings.MAX_EATEN_FOOD_AGE_DAYS + 1)
        with pytest.raises(ValidationError):
            eaten_food = EatenFood(
                user_id=1,
                eaten_at=date,
                custom_food=custom_food,
                weight_grams=200
            )
            eaten_food.full_clean()

    def test_clean_eatenfood_with_invalid_future_eaten_at(self, custom_food):
        date = timezone.now() + timezone.timedelta(seconds=10)
        with pytest.raises(ValidationError):
            eaten_food = EatenFood(
                user_id=1,
                eaten_at=date,
                custom_food=custom_food,
                weight_grams=200
            )
            eaten_food.full_clean()

    def test_eaten_food_pre_delete_signal_base_food(self, base_food):
        eaten_food = EatenFood.objects.create(
            user_id=1,
            base_food=base_food,
            weight_grams=200
        )
        base_food.delete()
        eaten_food.refresh_from_db()

        assert eaten_food.base_food == None
        assert eaten_food.name == "Курица"
        assert eaten_food.proteins == 20.0
        assert eaten_food.fats == 5.0
        assert eaten_food.carbohydrates == 0.0

    def test_eaten_food_pre_delete_signal_custom_food(self, custom_food):
        eaten_food = EatenFood.objects.create(
            user_id=1,
            custom_food=custom_food,
            weight_grams=200
        )
        custom_food.delete()
        eaten_food.refresh_from_db()

        assert eaten_food.base_food == None
        assert eaten_food.name == "Мой продукт"
        assert eaten_food.proteins == 20.0
        assert eaten_food.fats == 10.0
        assert eaten_food.carbohydrates == 30.0

    def test_eaten_food_pre_delete_signal_recipe_food(self, recipe_with_igredients):
        eaten_food = EatenFood.objects.create(
            user_id=1,
            recipe_food=recipe_with_igredients,
            weight_grams=200
        )

        recipe_with_igredients.delete()
        eaten_food.refresh_from_db()

        assert eaten_food.recipe_food == None
        assert eaten_food.name == "Тестовый рецепт"
        assert eaten_food.proteins == Decimal("16.0")
        assert eaten_food.fats == Decimal("4.6")
        assert eaten_food.carbohydrates == Decimal("11.4")
