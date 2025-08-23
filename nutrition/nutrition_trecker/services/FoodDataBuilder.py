from django.utils.dateparse import parse_date
from django.db.models import QuerySet
from nutrition_trecker import models
from rest_framework.request import Request
from rest_framework.exceptions import ValidationError
from datetime import timedelta, date
import matplotlib
from typing import TypedDict, List, Optional, Tuple, Union, Dict

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from io import BytesIO
import base64


class NutritionInfo(TypedDict):
    proteins: float
    fats: float
    carbohydrates: float
    kcal: float


class EatenFoodInfo(TypedDict):
    id: int
    type: str
    name: str
    weight_grams: float
    nutrition: NutritionInfo
    eaten_at: str
    created_at: str
    updated_at: str
    base_food_id: Optional[int]
    custom_food_id: Optional[int]
    recipe_id: Optional[int]


class RecipeInfo(TypedDict):
    id: int
    name: str
    description: str
    created_at: str
    updated_at: str
    nutrition: NutritionInfo


class FoodDataBuilder:
    """Класс для получения данных из моделей nutrition_trecker"""

    @classmethod
    def parse_date_range(cls, request: Request) -> Dict[str, Optional[date]]:
        """
        Парсит диапазон дат или одну конкретную дату из request.
        Возвращает словарь {"date": date, "start_date": start_date, "end_date": end_date},
        где значения - datetime.date объекты или None.
        """
        date_str = request.query_params.get("date")
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        if date_str:
            date = parse_date(date_str)
            return {"date": date, "start_date": None, "end_date": None}
        elif start_date_str and end_date_str:
            start_date = parse_date(start_date_str)
            end_date = parse_date(end_date_str)
            if start_date > end_date:
                raise ValidationError(
                    {"detail": "Начальная дата должна быть раньше конечной"}
                )
            return {"date": None, "start_date": start_date, "end_date": end_date}
        else:
            return {"date": None, "start_date": None, "end_date": None}

    @classmethod
    def _eaten_food_nutritions_list_build(
        cls, qs: QuerySet[models.EatenFood]
    ) -> Tuple[List[EatenFoodInfo], NutritionInfo]:
        """
        Возвращает tuple со списком продуктов и блюд с полным кбжу
        из данного queryset и суммарный кбжу в виде словаря.
        """
        total_nutrition = {
            "proteins": 0.0,
            "fats": 0.0,
            "carbohydrates": 0.0,
            "kcal": 0.0,
        }
        results = []
        for eaten in qs:
            food = dict()
            food["id"] = eaten.pk
            food["type"] = eaten.get_type()
            match food["type"]:
                case "base":
                    food["base_food_id"] = eaten.base_food_id
                case "custom":
                    food["custom_food_id"] = eaten.custom_food_id
                case "recipe":
                    food["recipe_id"] = eaten.recipe_food_id
            food["name"] = eaten.get_name()
            food["weight_grams"] = eaten.weight_grams
            food["nutrition"] = eaten.get_nutrition()
            food["eaten_at"] = eaten.eaten_at
            food["created_at"] = eaten.created_at.isoformat()
            food["updated_at"] = eaten.updated_at.isoformat()

            total_nutrition["proteins"] += food["nutrition"]["proteins"]
            total_nutrition["fats"] += food["nutrition"]["fats"]
            total_nutrition["carbohydrates"] += food["nutrition"]["carbohydrates"]
            total_nutrition["kcal"] += food["nutrition"]["kcal"]

            for key, value in total_nutrition.items():
                total_nutrition[key] = round(value, 1)

            results.append(food)

        return (results, total_nutrition)

    @classmethod
    def _eaten_food_range_days_total_list_build(
        cls, qs: QuerySet[models.EatenFood], start_date: date, end_date: date
    ) -> Dict[date, NutritionInfo]:
        """Возвращает словарь с суммарным кбжу из данного queryset по каждому дню из данного диапазона."""
        if start_date > end_date:
            raise ValidationError(
                {"detail": "Начальная дата должна быть раньше конечной"}
            )
        days = (end_date - start_date).days + 1
        days_list = [start_date + timedelta(days=i) for i in range(days)]
        results = dict()
        for day in days_list:
            total_nutrition = {
                "proteins": 0.0,
                "fats": 0.0,
                "carbohydrates": 0.0,
                "kcal": 0.0,
            }
            for eaten in qs.filter(eaten_at__date=day):
                nutrition = eaten.get_nutrition()
                total_nutrition["proteins"] += nutrition["proteins"]
                total_nutrition["fats"] += nutrition["fats"]
                total_nutrition["carbohydrates"] += nutrition["carbohydrates"]
                total_nutrition["kcal"] += nutrition["kcal"]

            for key, value in total_nutrition.items():
                total_nutrition[key] = round(value, 1)

            results[day] = total_nutrition

        return results

    @classmethod
    def eaten_food_list_data_build(
        cls, queryset: QuerySet[models.EatenFood], request: Request
    ) -> Union[
        Dict[str, Union[str, List[EatenFoodInfo], NutritionInfo]],
        Dict[date, NutritionInfo],
    ]:
        """
        Возвращает словарь с данными о приёмах пищи из EatenFood за выбранную дату,
        полностью подготовленными к ответу (без ForeignKey и т.д. - только данные).
        Если Выбран диапазон дат, то возвращает словарь с суммарным кбжу на
        каждый день из диапазона.
        """

        response = dict()

        dates = cls.parse_date_range(request)
        date_flag = False

        if dates["date"]:
            queryset = queryset.filter(eaten_at__date=dates["date"])
            response["date"] = dates["date"].isoformat()
            date_flag = True
        elif dates["start_date"] and dates["end_date"]:
            queryset = queryset.filter(
                eaten_at__date__range=(dates["start_date"], dates["end_date"])
            )
            response["start_date"] = dates["start_date"].isoformat()
            response["end_date"] = dates["end_date"].isoformat()
        else:
            raise (
                ValidationError(
                    "Для получения данных о приёмах пищи нужно выбрать дату или диапазон дат."
                )
            )

        if not queryset.exists():
            raise ValidationError("В выбранную дату нет записей о приёмах пищи.")

        if date_flag:
            results, total_nutrition = cls._eaten_food_nutritions_list_build(queryset)
            response["eaten"] = results
            response["total_nutrition"] = total_nutrition
        else:
            results = cls._eaten_food_range_days_total_list_build(
                queryset, dates["start_date"], dates["end_date"]
            )
            response["days"] = results

        return response

    @classmethod
    def recipe_list_data_build(
        cls, queryset: QuerySet[models.Recipe]
    ) -> List[RecipeInfo]:
        """Возвращает список с информацией о рецептах и суммарным кбжу + средним кбжу на 100 грамм блюда"""
        result = []

        for recipe in queryset:
            rc = {
                "id": recipe.pk,
                "name": recipe.name,
                "description": recipe.description,
                "created_at": recipe.created_at.isoformat(),
                "updated_at": recipe.updated_at.isoformat(),
                "nutrition": recipe.calculate_nutrition(),
            }
            result.append(rc)

        return result

    @classmethod
    def eaten_food_stats_graph_draw(
        cls, queryset: QuerySet[models.EatenFood], request: Request
    ) -> List[str]:
        """
        Возвращает 4 графика в формате base64 с демонстрацией суммарного количества
        каждого нутриента в приёмах пищи за каждый день из данного диапазона.
        Если в request кроме дат будут указаны желаемые уровни по суммам нутриентов,
        на графиках они будут отображены пунктирной линией (например proteints_level: 150).
        """
        dates = cls.parse_date_range(request)
        if not dates["start_date"] or not dates["end_date"]:
            raise ValidationError(
                "Для построения статистики нужно предоставить начальную и конечную даты."
            )

        days_data = cls._eaten_food_range_days_total_list_build(
            queryset, dates["start_date"], dates["end_date"]
        )

        if not days_data:
            raise ValidationError(
                "Нет данных для построения графиков в указанном диапазоне дат."
            )

        proteins_level = request.query_params.get("proteins_level", None)
        fats_level = request.query_params.get("fats_level", None)
        carbohydrates_level = request.query_params.get("carbohydrates_level", None)
        kcal_level = request.query_params.get("kcal_level", None)

        sorted_dates = sorted(days_data.keys())
        dates_str = [d.strftime("%d.%m") for d in sorted_dates]

        nutrients = [
            {
                "key": "proteins",
                "title": "Белки (г)",
                "color": "skyblue",
                "level": float(proteins_level) if proteins_level else None,
            },
            {
                "key": "fats",
                "title": "Жиры (г)",
                "color": "lightcoral",
                "level": float(fats_level) if fats_level else None,
            },
            {
                "key": "carbohydrates",
                "title": "Углеводы (г)",
                "color": "lightgreen",
                "level": float(carbohydrates_level) if carbohydrates_level else None,
            },
            {
                "key": "kcal",
                "title": "Калории (ккал)",
                "color": "gold",
                "level": float(kcal_level) if kcal_level else None,
            },
        ]

        images_base64 = []

        for nutrient in nutrients:
            # Подготовка данных для текущего нутриента
            values = [days_data[d][nutrient["key"]] for d in sorted_dates]

            # Создаем график
            plt.figure(figsize=(10, 5))
            bars = plt.bar(
                dates_str, values, color=nutrient["color"], edgecolor="black", alpha=0.7
            )

            # Добавляем линию уровня (если указана)
            if nutrient["level"] is not None:
                plt.axhline(
                    y=nutrient["level"],
                    color="red",
                    linestyle="--",
                    linewidth=1,
                    label=f'Цель: {nutrient["level"]}',
                )
                plt.legend()

            # Настройки графика
            plt.title(nutrient["title"], fontsize=14)
            plt.xlabel("Дата", fontsize=12)
            plt.ylabel(nutrient["title"].split(" (")[0], fontsize=12)
            plt.grid(axis="y", linestyle="--", alpha=0.5)
            plt.xticks(rotation=45)

            # Добавляем значения на столбцы
            for bar in bars:
                height = bar.get_height()
                plt.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    f"{height}",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

            # Сохраняем в base64
            buf = BytesIO()
            plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
            plt.close()

            buf.seek(0)
            image_base64 = base64.b64encode(buf.read()).decode("utf-8")
            images_base64.append(image_base64)
            buf.close()

        return images_base64
