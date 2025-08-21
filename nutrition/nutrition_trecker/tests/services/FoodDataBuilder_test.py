import pytest
from unittest.mock import patch
import os
from nutrition_trecker.models import EatenFood, Recipe
from nutrition_trecker.services.FoodDataBuilder import FoodDataBuilder
from rest_framework.request import Request
from io import BytesIO
import base64
from PIL import Image
from rest_framework.exceptions import ValidationError


@pytest.mark.django_db
class TestFoodDataBuilder:
    def test_parse_date_range_one_date(self, dates, factory):
        drf_request = Request(factory.get(f"/?date={dates[0]}"))

        dates_dict = FoodDataBuilder.parse_date_range(drf_request)

        assert dates_dict["date"] == dates[0]
        assert dates_dict["start_date"] is None
        assert dates_dict["end_date"] is None

    def test_parse_date_range_start_end_dates(self, dates, factory):
        start_date = dates[-1].isoformat()
        end_date = dates[0].isoformat()
        drf_request = Request(
            factory.get(f"/?start_date={start_date}&end_date={end_date}")
        )

        dates_dict = FoodDataBuilder.parse_date_range(drf_request)

        assert dates_dict["date"] is None
        assert dates_dict["start_date"].isoformat() == start_date
        assert dates_dict["end_date"].isoformat() == end_date

    def test_parse_date_range_without_dates(self, dates, factory):
        drf_request = Request(factory.get(f"/?qwerty={12345}"))

        dates_dict = FoodDataBuilder.parse_date_range(drf_request)

        assert dates_dict["date"] is None
        assert dates_dict["start_date"] is None
        assert dates_dict["end_date"] is None

    def test_parse_date_range_invalid_start_end_dates(self, dates, factory):
        with pytest.raises(ValidationError):
            start_date = dates[-1].isoformat()
            end_date = dates[0].isoformat()
            drf_request = Request(
                factory.get(f"/?start_date={end_date}&end_date={start_date}")
            )

            FoodDataBuilder.parse_date_range(drf_request)

    def test_eaten_food_nutritions_list_build_success(self, active_user_food):
        queryset = EatenFood.objects.filter(user_id=1)

        results, total = FoodDataBuilder._eaten_food_nutritions_list_build(queryset)

        assert len(results) == 8
        assert isinstance(results[0], dict)
        assert isinstance(total, dict)
        assert total["proteins"] == 134.6
        assert total["fats"] == 40.7
        assert total["carbohydrates"] == 126.6
        assert total["kcal"] == 1414.9

    def test_eaten_food_nutritions_list_build_0_rows(self, active_user_food):
        queryset = EatenFood.objects.filter(user_id=2)

        results, total = FoodDataBuilder._eaten_food_nutritions_list_build(queryset)

        assert len(results) == 0
        assert isinstance(total, dict)
        assert total["proteins"] == 0.0
        assert total["fats"] == 0.0
        assert total["carbohydrates"] == 0.0
        assert total["kcal"] == 0.0

    def test_eaten_food_range_days_total_list_build_success(
        self, dates, active_user_food
    ):
        start_date = dates[-1]
        end_date = dates[0]
        qs = EatenFood.objects.filter(user_id=1)

        res = FoodDataBuilder._eaten_food_range_days_total_list_build(
            qs, start_date, end_date
        )

        assert len(res) == 7
        assert isinstance(res[start_date], dict)
        assert res[start_date]["proteins"] == 32.4
        assert res[start_date]["fats"] == 7.5
        assert res[start_date]["carbohydrates"] == 14.4
        assert res[start_date]["kcal"] == 255.6

    def test_eaten_food_range_days_total_list_build_invalid_dates(self, dates):
        with pytest.raises(ValidationError):
            start_date = dates[-1]
            end_date = dates[0]
            qs = EatenFood.objects.filter(user_id=1)

            FoodDataBuilder._eaten_food_range_days_total_list_build(
                qs, end_date, start_date
            )

    def test_eaten_food_list_data_build_one_date(
        self,
        dates,
        active_user_food,
        factory,
        mock_parse_date,
        mock_eaten_food_nutritions_list_build,
    ):
        drf_request = Request(factory.get(f"/?date={dates[0]}"))
        qs = EatenFood.objects.filter(user_id=1)

        with patch(
            "nutrition_trecker.services.FoodDataBuilder.FoodDataBuilder.parse_date_range",
            return_value=mock_parse_date,
        ):
            with patch(
                "nutrition_trecker.services.FoodDataBuilder.FoodDataBuilder._eaten_food_nutritions_list_build",
                return_value=mock_eaten_food_nutritions_list_build,
            ):
                response = FoodDataBuilder.eaten_food_list_data_build(qs, drf_request)

        assert response["eaten"] == mock_eaten_food_nutritions_list_build[0]
        assert response["total_nutrition"] == mock_eaten_food_nutritions_list_build[1]

    def test_eaten_food_list_data_build_range_dates(
        self,
        dates,
        active_user_food,
        factory,
        mock_parse_date_range,
        mock_eaten_food_range_days_total_list_build,
    ):
        start_date = dates[-1].isoformat()
        end_date = dates[0].isoformat()
        drf_request = Request(
            factory.get(f"/?start_date={start_date}&end_date={end_date}")
        )
        qs = EatenFood.objects.filter(user_id=1)

        with patch(
            "nutrition_trecker.services.FoodDataBuilder.FoodDataBuilder.parse_date_range",
            return_value=mock_parse_date_range,
        ):
            with patch(
                "nutrition_trecker.services.FoodDataBuilder.FoodDataBuilder._eaten_food_range_days_total_list_build",
                return_value=mock_eaten_food_range_days_total_list_build,
            ):
                response = FoodDataBuilder.eaten_food_list_data_build(qs, drf_request)

        assert len(response["days"]) == 2
        assert (
            response["days"][dates[1]]
            == mock_eaten_food_range_days_total_list_build[dates[1]]
        )
        assert (
            response["days"][dates[0]]
            == mock_eaten_food_range_days_total_list_build[dates[0]]
        )

    def test_eaten_food_list_data_build_no_dates(self, factory):
        drf_request = Request(factory.get(f"/?qwerty={12345}"))
        qs = EatenFood.objects.filter(user_id=1)

        with pytest.raises(ValidationError):
            FoodDataBuilder.eaten_food_list_data_build(qs, drf_request)

    def test_eaten_food_list_data_build_no_rows_in_qs(
        self, factory, active_user_food, dates
    ):
        with pytest.raises(ValidationError):
            drf_request = Request(factory.get(f"/?date={dates[0]}"))
            qs = EatenFood.objects.filter(user_id=2)
            FoodDataBuilder.eaten_food_list_data_build(qs, drf_request)

    def test_recipe_list_data_build_success(self, recipe_with_ingredients):
        qs = Recipe.objects.filter(user_id=1)

        recipes = FoodDataBuilder.recipe_list_data_build(qs)

        assert len(recipes) == 1
        assert isinstance(recipes[0], dict)
        assert recipes[0]["name"] == "Борщ"

    def test_eaten_food_eaten_food_stats_graph_draw(
        self, dates, active_user_food, factory
    ):
        start_date = dates[-1].isoformat()
        end_date = dates[0].isoformat()

        drf_request = Request(
            factory.get(
                f"/?start_date={start_date}&end_date={end_date}"
                "&proteins_level=35&fats_level=20&carbohydrates_level=100&kcal_level=1300"
            )
        )

        # Получаем queryset
        queryset = EatenFood.objects.filter(user_id=1)

        # Вызываем тестируемый метод
        result = FoodDataBuilder.eaten_food_stats_graph_draw(queryset, drf_request)

        # Проверяем результаты
        assert isinstance(result, list)
        assert (
            len(result) == 4
        )  # Должно быть 4 графика (белки, жиры, углеводы, калории)

        # Проверяем каждый график
        for i, img_base64 in enumerate(result):
            assert isinstance(img_base64, str)

            try:
                # Декодируем изображение
                img_data = base64.b64decode(img_base64)
                img = Image.open(BytesIO(img_data))

                # Проверяем что это PNG изображение
                assert img.format == "PNG"

                # Сохраняем для визуальной проверки
                graph_dir = os.path.join(os.path.dirname(__file__), "test_graphs")
                graph_path = os.path.join(graph_dir, f"test_graph_{i}.png")
                img.save(graph_path)
                print(f"График {i} сохранен как test_graph_{i}.png")

            except Exception as e:
                pytest.fail(f"Ошибка декодирования графика {i}: {str(e)}")
