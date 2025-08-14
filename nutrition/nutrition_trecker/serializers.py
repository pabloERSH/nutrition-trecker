from common.mixins.ModelCleanMixin import ModelCleanMixin
from rest_framework import serializers
from nutrition_trecker import models


class BaseFoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BaseFood
        fields = "__all__"
        read_only_fields = fields


class UserFavoriteSerializer(serializers.ModelSerializer):
    base_food = BaseFoodSerializer(read_only=True)

    class Meta:
        model = models.UserFavorite
        fields = ["id", "user_id", "base_food", "created_at"]
        read_only_fields = [
            "id",
            "user_id",
            "created_at",
        ]  # user_id задаем во view через self.request.user


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
    class Meta:
        model = models.RecipeIngredient
        fields = [
            "id",
            "user_id",
            "recipe",
            "base_food",
            "custom_food",
            "name",
            "proteins",
            "fats",
            "carbohydrates",
            "weight_grams",
            "kcal",
        ]
        read_only_fields = [
            "id",
            "user_id",  # задаем во view через self.request.user
            "recipe",  # задаём через URL вложенного эндпоинта
        ]


class EatenFoodSerializer(ModelCleanMixin, serializers.ModelSerializer):
    class Meta:
        model = models.EatenFood
        fields = "__all__"
