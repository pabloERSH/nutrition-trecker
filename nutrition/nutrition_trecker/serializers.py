from common.mixins.ModelCleanMixin import ModelCleanMixin
from rest_framework import serializers
from nutrition_trecker import models
from common.custom.OwnedPrimaryKeyRelatedField import OwnedPrimaryKeyRelatedField


class BaseFoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BaseFood
        fields = "__all__"
        read_only_fields = fields


class UserFavoriteSerializer(serializers.ModelSerializer):
    base_food = BaseFoodSerializer(read_only=True)
    base_food_id = serializers.PrimaryKeyRelatedField(
        queryset=models.BaseFood.objects.all(),
        source="base_food",
        write_only=True,
        required=False,
    )

    class Meta:
        model = models.UserFavorite
        fields = ["id", "user_id", "base_food", "base_food_id"]
        read_only_fields = ["id", "user_id"]


class CustomFoodSerializer(ModelCleanMixin, serializers.ModelSerializer):
    class Meta:
        model = models.CustomFood
        fields = "__all__"


class RecipeSerializer(ModelCleanMixin, serializers.ModelSerializer):
    class Meta:
        model = models.Recipe
        fields = ["id", "user_id", "name", "description"]
        read_only_fields = [
            "id",
            "user_id",
        ]  # user_id задаем во view через self.request.user


class RecipeIngredientSerializer(ModelCleanMixin, serializers.ModelSerializer):
    source_type = serializers.SerializerMethodField(read_only=True)
    source_data = serializers.SerializerMethodField(read_only=True)

    base_food_id = serializers.PrimaryKeyRelatedField(
        queryset=models.BaseFood.objects.all(),
        source="base_food",
        write_only=True,
        required=False,
    )

    custom_food_id = OwnedPrimaryKeyRelatedField(
        queryset=models.CustomFood.objects.all(),
        source="custom_food",
        write_only=True,
        required=False,
        owner_field="user_id",
    )

    def get_source_type(self, obj):
        return obj.get_type()

    def get_source_data(self, obj):
        type = obj.get_type()
        data = None

        match type:
            case "base":
                data = {
                    "base_food_id": obj.base_food.id,
                    "name": obj.base_food.name,
                    "per_100g": {
                        "proteins": obj.base_food.proteins,
                        "fats": obj.base_food.fats,
                        "carbohydrates": obj.base_food.carbohydrates,
                        "kcal": obj.base_food.kcal,
                    },
                }
            case "custom":
                data = {
                    "custom_food_id": obj.custom_food.id,
                    "name": obj.custom_food.custom_name,
                    "per_100g": {
                        "proteins": obj.custom_food.proteins,
                        "fats": obj.custom_food.fats,
                        "carbohydrates": obj.custom_food.carbohydrates,
                        "kcal": obj.custom_food.kcal,
                    },
                }
            case "manual":
                data = {
                    "name": obj.name,
                    "per_100g": {
                        "proteins": obj.proteins,
                        "fats": obj.fats,
                        "carbohydrates": obj.carbohydrates,
                        "kcal": obj.kcal,
                    },
                }

        return data

    class Meta:
        model = models.RecipeIngredient
        fields = [
            "id",
            "user_id",
            "recipe",
            "base_food_id",
            "custom_food_id",
            "weight_grams",
            "source_type",
            "source_data",
        ]
        read_only_fields = ["id", "user_id", "recipe"]


class EatenFoodSerializer(ModelCleanMixin, serializers.ModelSerializer):
    source_type = serializers.SerializerMethodField(read_only=True)
    source_data = serializers.SerializerMethodField(read_only=True)

    base_food_id = serializers.PrimaryKeyRelatedField(
        queryset=models.BaseFood.objects.all(),
        source="base_food",
        write_only=True,
        required=False,
    )

    custom_food_id = OwnedPrimaryKeyRelatedField(
        queryset=models.CustomFood.objects.all(),
        source="custom_food",
        write_only=True,
        required=False,
        owner_field="user_id",
    )

    recipe_food_id = OwnedPrimaryKeyRelatedField(
        queryset=models.Recipe.objects.all(),
        source="recipe_food",
        write_only=True,
        required=False,
        owner_field="user_id",
    )

    def get_source_type(self, obj):
        return obj.get_type()

    def get_source_data(self, obj):
        type = obj.get_type()
        data = None

        match type:
            case "base":
                data = {
                    "base_food_id": obj.base_food.id,
                    "name": obj.base_food.name,
                    "per_100g": {
                        "proteins": obj.base_food.proteins,
                        "fats": obj.base_food.fats,
                        "carbohydrates": obj.base_food.carbohydrates,
                        "kcal": obj.base_food.kcal,
                    },
                }
            case "custom":
                data = {
                    "custom_food_id": obj.custom_food.id,
                    "name": obj.custom_food.custom_name,
                    "per_100g": {
                        "proteins": obj.custom_food.proteins,
                        "fats": obj.custom_food.fats,
                        "carbohydrates": obj.custom_food.carbohydrates,
                        "kcal": obj.custom_food.kcal,
                    },
                }
            case "recipe":
                nutrition = obj.recipe_food.calculate_nutrition()["per_100g"]
                data = {
                    "recipe_food_id": obj.recipe_food.id,
                    "name": obj.recipe_food.name,
                    "per_100g": {
                        "proteins": nutrition["proteins"],
                        "fats": nutrition["fats"],
                        "carbohydrates": nutrition["carbohydrates"],
                        "kcal": nutrition["kcal"],
                    },
                }
            case "manual":
                data = {
                    "name": obj.name,
                    "per_100g": {
                        "proteins": obj.proteins,
                        "fats": obj.fats,
                        "carbohydrates": obj.carbohydrates,
                        "kcal": obj.kcal,
                    },
                }

        return data

    class Meta:
        model = models.EatenFood
        fields = [
            "id",
            "user_id",
            "eaten_at",
            "base_food_id",
            "custom_food_id",
            "recipe_food_id",
            "weight_grams",
            "source_type",
            "source_data",
        ]
        read_only_fields = ["id", "user_id"]
