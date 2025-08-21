import pytest
from nutrition_trecker.models import (
    EatenFood,
    Recipe,
    RecipeIngredient,
    BaseFood,
    CustomFood,
)
from datetime import timedelta, datetime, timezone as dt_timezone
from django.utils import timezone
from rest_framework.test import APIRequestFactory


@pytest.fixture
def dates():
    today = timezone.now().date()
    dates = [today - timedelta(days=i) for i in range(7)]
    return dates


@pytest.fixture
def mock_parse_date(dates):
    return {"date": dates[0], "start_date": None, "end_date": None}


@pytest.fixture
def mock_parse_date_range(dates):
    return {"date": None, "start_date": dates[-1], "end_date": dates[0]}


@pytest.fixture
def mock_eaten_food_range_days_total_list_build(dates):
    return {
        dates[1]: {
            "proteins": 151.0,
            "fats": 92.0,
            "carbohydrates": 345.0,
            "kcal": 2812.0,
        },
        dates[0]: {
            "proteins": 160.0,
            "fats": 90.0,
            "carbohydrates": 350.0,
            "kcal": 2850.0,
        },
    }


@pytest.fixture
def mock_eaten_food_nutritions_list_build():
    results = [
        {
            "id": 19,
            "type": "custom",
            "custom_food_id": 17,
            "name": "Мой салат",
            "weight_grams": 200,
            "nutrition": {
                "kcal": 186.0,
                "proteins": 4.0,
                "fats": 10.0,
                "carbohydrates": 20.0,
            },
            "eaten_at": datetime(2025, 1, 2, 9, 0, tzinfo=dt_timezone.utc),
            "created_at": "2025-08-15T22:06:56.778072+00:00",
            "updated_at": "2025-08-15T22:06:56.778085+00:00",
        }
    ]
    total_nutrition = {
        "proteins": 8.0,
        "fats": 20.0,
        "carbohydrates": 40.0,
        "kcal": 372.0,
    }
    return (results, total_nutrition)


@pytest.fixture
def factory():
    return APIRequestFactory()


@pytest.fixture
def recipe_with_ingredients():
    meat = BaseFood.objects.create(
        name="Говядина", proteins=20, fats=5, carbohydrates=0
    )
    recipe = Recipe.objects.create(user_id=1, name="Борщ")
    RecipeIngredient.objects.create(
        user_id=1,
        recipe=recipe,
        weight_grams=100,
        name="Свекла",
        proteins=1.5,
        fats=0.1,
        carbohydrates=9.6,
    )
    RecipeIngredient.objects.create(
        user_id=1, recipe=recipe, weight_grams=100, base_food=meat
    )

    return recipe


@pytest.fixture
def active_user_food(dates, recipe_with_ingredients):
    base_food = BaseFood.objects.create(
        name="Яблоко", proteins=0.3, fats=0.2, carbohydrates=14
    )
    custom_food = CustomFood.objects.create(
        user_id=1, custom_name="Мой салат", proteins=2, fats=5, carbohydrates=10
    )
    recipe = recipe_with_ingredients
    # 8 приёмов пищи
    # Суммарно:
    # Б: 134.3 Ж: 41.5 У: 126

    # Б: 0.3 Ж: 0.2 У: 14
    EatenFood.objects.create(
        user_id=1,
        base_food=base_food,
        weight_grams=100,
        eaten_at=timezone.make_aware(datetime.combine(dates[0], datetime.min.time())),
    )
    # Б: 4 Ж: 10 У: 20
    EatenFood.objects.create(
        user_id=1,
        custom_food=custom_food,
        weight_grams=200,
        eaten_at=timezone.make_aware(datetime.combine(dates[1], datetime.min.time())),
    )
    # Б: 0.5 Ж: 0.3 У: 21
    EatenFood.objects.create(
        user_id=1,
        base_food=base_food,
        weight_grams=150,
        eaten_at=timezone.make_aware(datetime.combine(dates[1], datetime.min.time())),
    )
    # Б: 32.3 Ж: 7.7 У: 14.4
    EatenFood.objects.create(
        user_id=1,
        recipe_food=recipe,
        weight_grams=300,
        eaten_at=timezone.make_aware(datetime.combine(dates[2], datetime.min.time())),
    )
    # Б: 0.3 Ж: 0.2 У: 14
    EatenFood.objects.create(
        user_id=1,
        base_food=base_food,
        weight_grams=100,
        eaten_at=timezone.make_aware(datetime.combine(dates[5], datetime.min.time())),
    )
    # Б: 32.3 Ж: 7.7 У: 14.4
    EatenFood.objects.create(
        user_id=1,
        recipe_food=recipe,
        weight_grams=300,
        eaten_at=timezone.make_aware(datetime.combine(dates[6], datetime.min.time())),
    )
    # Б: 32.3 Ж: 7.7 У: 14.4
    EatenFood.objects.create(
        user_id=1,
        recipe_food=recipe,
        weight_grams=300,
        eaten_at=timezone.make_aware(datetime.combine(dates[1], datetime.min.time())),
    )
    # Б: 32.3 Ж: 7.7 У: 14.4
    EatenFood.objects.create(
        user_id=1,
        recipe_food=recipe,
        weight_grams=300,
        eaten_at=timezone.make_aware(datetime.combine(dates[4], datetime.min.time())),
    )
