from rest_framework import viewsets, status
from nutrition_trecker import models, serializers
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import action
from common.permissions.IsOwner403Permission import IsOwner403Permission
from django.db.models import Prefetch
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.views.decorators.vary import vary_on_headers
from nutrition_trecker.services.FoodDataBuilder import FoodDataBuilder
from common.filters.FuzzySearchFilter import FuzzySearchFilter
from common.utils.CacheHelper import CacheHelper
from common.decorators.cache_response import cache_response
from common.mixins.AutocompleteMixin import AutocompleteMixin


class BaseFoodViewSet(AutocompleteMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.BaseFoodSerializer
    queryset = models.BaseFood.objects.all()

    filter_backends = [FuzzySearchFilter]
    search_fields = ["name"]

    @cache_response(
        entity="base_food",
        ttl=60 * 60,
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CustomFoodViewSet(AutocompleteMixin, viewsets.ModelViewSet):
    serializer_class = serializers.CustomFoodSerializer
    permission_classes = [IsOwner403Permission]

    filter_backends = [FuzzySearchFilter]
    search_fields = ["custom_name"]
    autocomplete_search_fields = ["custom_name"]

    def get_queryset(self):
        return models.CustomFood.objects.filter(user_id=self.request.user.telegram_id)

    def perform_create(self, serializer):
        serializer.save(user_id=self.request.user.telegram_id)

    def perform_update(self, serializer):
        serializer.save(user_id=self.request.user.telegram_id)

    @cache_response(entity="custom_food", ttl=60 * 30, per_user=True)
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class UserFavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.UserFavoriteSerializer
    permission_classes = [IsOwner403Permission]
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        return models.UserFavorite.objects.filter(user_id=self.request.user.telegram_id)


class RecipeViewSet(AutocompleteMixin, viewsets.ModelViewSet):
    serializer_class = serializers.RecipeSerializer
    permission_classes = [IsOwner403Permission]

    filter_backends = [FuzzySearchFilter]
    search_fields = ["name", "description"]
    autocomplete_search_fields = ["name"]

    def get_queryset(self):
        ingredients_prefetch = Prefetch(
            "ingredients",
            queryset=models.RecipeIngredient.objects.select_related(
                "base_food", "custom_food"
            ),
        )
        return models.Recipe.objects.filter(
            user_id=self.request.user.telegram_id
        ).prefetch_related(ingredients_prefetch)

    @cache_response(
        entity="recipe",
        ttl=60 * 5,
        per_user=True,
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            recipes = FoodDataBuilder.recipe_list_data_build(page)
            return self.get_paginated_response(recipes)

        # если пагинация выключена
        recipes = FoodDataBuilder.recipe_list_data_build(queryset)
        return Response(recipes, status=status.HTTP_200_OK)


class RecipeIngredientViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.RecipeIngredientSerializer
    permission_classes = [IsOwner403Permission]

    def _get_recipe(self):
        return get_object_or_404(
            models.Recipe,
            id=self.kwargs.get("recipe_pk"),
            user_id=self.request.user.telegram_id,
        )

    def get_queryset(self):
        recipe = self._get_recipe()
        return recipe.ingredients.select_related("base_food", "custom_food")

    def perform_create(self, serializer):
        serializer.save(
            recipe=self._get_recipe(), user_id=self.request.user.telegram_id
        )

    def perform_update(self, serializer):
        serializer.save(
            recipe=self._get_recipe(), user_id=self.request.user.telegram_id
        )

    @cache_response(
        entity="recipe_ingredient",
        ttl=60 * 5,
        per_user=True,
    )
    def list(self, request, *args, **kwargs):
        recipe = self._get_recipe()

        data = {
            "recipe_name": recipe.name,
            "ingredients": recipe.get_ingredients_with_details(),
        }

        return Response(data, status=status.HTTP_200_OK)


class EatenFoodViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.EatenFoodSerializer
    permission_classes = [IsOwner403Permission]

    def get_queryset(self):
        ingredients_prefetch = Prefetch(
            "recipe_food__ingredients",
            queryset=models.RecipeIngredient.objects.select_related(
                "base_food", "custom_food"
            ),
        )

        return (
            models.EatenFood.objects.filter(user_id=self.request.user.telegram_id)
            .select_related("base_food", "custom_food", "recipe_food")
            .prefetch_related(ingredients_prefetch)
        )

    def list(self, request, *args, **kwargs):
        dates = FoodDataBuilder.parse_date_range(request)
        user_id = request.user.telegram_id

        if dates["date"]:
            cache_key = CacheHelper.make_cache_key(
                "eatenfood", f"list:date:{dates['date'].isoformat()}", user_id
            )
        elif dates["start_date"] and dates["end_date"]:
            cache_key = CacheHelper.make_cache_key(
                "eatenfood",
                f"list:dates:{dates['start_date'].isoformat()}:{dates['end_date'].isoformat()}",
                user_id,
            )
        else:
            return Response(
                {"message": "Требуется выбрать дату."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        eatenfood = cache.get(cache_key)
        if eatenfood is None:
            qs = self.get_queryset()
            eatenfood = FoodDataBuilder.eaten_food_list_data_build(qs, dates)
            cache.set(cache_key, eatenfood, 60 * 5)

        return Response(eatenfood, status=status.HTTP_200_OK)

    @method_decorator(cache_page(60 * 3))
    @method_decorator(vary_on_headers("Authorization"))
    @action(detail=False, methods=["get"])
    def nutrition_charts(self, request):
        qs = self.get_queryset()

        stats_graphs = FoodDataBuilder.eaten_food_stats_graph_draw(qs, request)

        return Response(
            {
                "proteins_chart": stats_graphs[0],
                "fats_chart": stats_graphs[1],
                "carbs_chart": stats_graphs[2],
                "kcal_chart": stats_graphs[3],
            },
            status=status.HTTP_200_OK,
        )
