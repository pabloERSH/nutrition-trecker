from common.mixins import ModelCleanMixin
from rest_framework import serializers
from nutrition_trecker import models


class BaseFoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BaseFood
        fields = "__all__"
        read_only_fields = fields


class CustomFoodSerializer(ModelCleanMixin, serializers.ModelSerializer):
    class Meta:
        model = models.CustomFood
        fields = "__all__"


class RecipeSerializer(ModelCleanMixin, serializers.ModelSerializer):
    class Meta:
        model = models.Recipe
        fields = ["id", "user_id", "name", "description"]
        read_only_fields = ["id", "user_id"]


class RecipeIngredientSerializer(ModelCleanMixin, serializers.ModelSerializer):
    class Meta:
        model = models.RecipeIngredient
        fields = [
            "id",
            "recipe",
            "base_food",
            "custom_food",
            "name",
            "proteins",
            "fats",
            "carbohydrates",
            "weight_grams",
        ]
        read_only_fields = [
            "id",
            "recipe",
        ]  # recipe задаём через URL вложенного эндпоинта


class EatenFoodSerializer(ModelCleanMixin, serializers.ModelSerializer):
    class Meta:
        model = models.EatenFood
        fields = "__all__"


class UserFavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.UserFavorite
        fields = "__all__"
