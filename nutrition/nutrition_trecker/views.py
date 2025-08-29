from rest_framework import viewsets, status
from nutrition_trecker import models, serializers
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import action
from common.permissions import IsOwner403Permission
from django.db.models import Prefetch
from nutrition_trecker import documents
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.views.decorators.vary import vary_on_headers
from nutrition_trecker.services.FoodDataBuilder import FoodDataBuilder
from nutrition_trecker.services.FoodSearcher import FoodSearcher
from common.utils.CacheHelper import CacheHelper


class BaseFoodViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.BaseFoodSerializer
    document = documents.BaseFoodDocument

    def list(self, request, *args, **kwargs):
        """Кэшируем готовый список продуктов для BaseFood."""
        cache_key = CacheHelper.make_cache_key("basefood", "list")

        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        queryset = models.BaseFood.objects.all()
        serializer = self.get_serializer(queryset, many=True)
        cache.set(cache_key, serializer.data, 60 * 60 * 24 * 7)  # 7 дней

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def autocomplete(self, request):
        """Endpoint для автокомплита при поиске base-food, возвращает список возможных дополнений с доп. информацией из elasticsearch."""
        query = request.query_params.get("q")
        limit = request.query_params.get("limit", 10)
        search_results = FoodSearcher.autocomplete(self.document, query, limit=limit)
        return Response(search_results, status=status.HTTP_200_OK)

    @method_decorator(cache_page(60 * 5))  # 5 минут
    @action(detail=False, methods=["get"])
    def search(self, request):
        """Endpoint для полнотекстового поиска base-food. Возвращает полную информацию о продуктах, подошедших под поиск."""
        query = request.query_params.get("q")
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 20))
        offset = (page - 1) * limit
        search_results = FoodSearcher.search(
            self.document, query, limit=limit, offset=offset
        )

        food_ids = search_results["ids"]
        foods = self.get_queryset().filter(id__in=food_ids)
        food_map = {food.id: food for food in foods}
        ordered_foods = [food_map[id] for id in food_ids if id in food_map]

        serializer = self.get_serializer(ordered_foods, many=True)

        return Response(
            {
                "total": search_results["total"],
                "took_ms": search_results["took_ms"],
                "limit": limit,
                "page": page,
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class CustomFoodViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.CustomFoodSerializer
    permission_classes = [IsOwner403Permission]
    document = documents.CustomFoodDocument

    def get_queryset(self):
        return models.CustomFood.objects.filter(user_id=self.request.user.telegram_id)

    def perform_create(self, serializer):
        serializer.save(user_id=self.request.user.telegram_id)

    def perform_update(self, serializer):
        serializer.save(user_id=self.request.user.telegram_id)

    def list(self, request, *args, **kwargs):
        user_id = request.user.telegram_id
        cache_key = CacheHelper.make_cache_key("customfood", "list", user_id)
        customfood = cache.get(cache_key)
        if customfood is None:
            customfood = self.get_queryset()
            cache.set(cache_key, customfood, 60 * 10)
        return Response(customfood, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def autocomplete(self, request):
        """Endpoint для автокомплита при поиске custom-food, возвращает список возможных дополнений с доп. информацией из elasticsearch."""
        query = request.query_params.get("q")
        limit = request.query_params.get("limit", 10)
        search_results = FoodSearcher.autocomplete(
            self.document, query, limit=limit, user_id=self.request.user.telegram_id
        )
        return Response(search_results, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def search(self, request):
        """Endpoint для полнотекстового поиска custom-food. Возвращает полную информацию о продуктах, подошедших под поиск."""
        query = request.query_params.get("q")
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 20))
        offset = (page - 1) * limit
        search_results = FoodSearcher.search(
            self.document,
            query,
            limit=limit,
            offset=offset,
            user_id=self.request.user.telegram_id,
        )

        food_ids = search_results["ids"]
        foods = self.get_queryset().filter(id__in=food_ids)
        food_map = {food.id: food for food in foods}
        ordered_foods = [food_map[id] for id in food_ids if id in food_map]

        serializer = self.get_serializer(ordered_foods, many=True)

        return Response(
            {
                "total": search_results["total"],
                "took_ms": search_results["took_ms"],
                "limit": limit,
                "page": page,
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class UserFavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.UserFavoriteSerializer
    permission_classes = [IsOwner403Permission]
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        return models.UserFavorite.objects.filter(user_id=self.request.user.telegram_id)

    def perform_create(self, serializer):
        serializer.save(user_id=self.request.user.telegram_id)

    def perform_update(self, serializer):
        serializer.save(user_id=self.request.user.telegram_id)


class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.RecipeSerializer
    permission_classes = [IsOwner403Permission]
    document = documents.RecipeDocument

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

    def perform_create(self, serializer):
        serializer.save(user_id=self.request.user.telegram_id)

    def perform_update(self, serializer):
        serializer.save(user_id=self.request.user.telegram_id)

    def list(self, request, *args, **kwargs):
        user_id = request.user.telegram_id
        cache_key = CacheHelper.make_cache_key("recipe", "list", user_id)
        recipes = cache.get(cache_key)
        if recipes is None:
            qs = self.get_queryset()
            recipes = FoodDataBuilder.recipe_list_data_build(qs)
            cache.set(cache_key, recipes, 60 * 5)
        return Response(recipes, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def autocomplete(self, request):
        """Endpoint для автокомплита при поиске recipe, возвращает список возможных дополнений с доп. информацией из elasticsearch."""
        query = request.query_params.get("q")
        limit = request.query_params.get("limit", 10)
        search_results = FoodSearcher.autocomplete(
            self.document, query, limit=limit, user_id=self.request.user.telegram_id
        )
        return Response(search_results, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def search(self, request):
        """Endpoint для полнотекстового поиска recipe. Возвращает полную информацию о продуктах, подошедших под поиск."""
        query = request.query_params.get("q")
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 20))
        offset = (page - 1) * limit
        search_results = FoodSearcher.search(
            self.document,
            query,
            limit=limit,
            offset=offset,
            user_id=self.request.user.telegram_id,
        )

        recipes_ids = search_results["ids"]
        recipes = self.get_queryset().filter(id__in=recipes_ids)
        recipes_map = {recipe.id: recipe for recipe in recipes}
        ordered_recipes = [recipes_map[id] for id in recipes_ids if id in recipes_map]

        res = FoodDataBuilder.recipe_list_data_build(ordered_recipes)

        return Response(
            {
                "total": search_results["total"],
                "took_ms": search_results["took_ms"],
                "limit": limit,
                "page": page,
                "results": res,
            },
            status=status.HTTP_200_OK,
        )


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

    def list(self, request, *args, **kwargs):
        recipe_pk = self.kwargs.get("recipe_pk")
        user_id = request.user.telegram_id
        cache_key = CacheHelper.make_cache_key(
            f"recipe_ingredient:recipe_id:{recipe_pk}", "list", user_id
        )
        ingredients = cache.get(cache_key)
        if ingredients is None:
            recipe = self._get_recipe()
            ingredients = {
                "recipe_name": recipe.name,
                "ingredients": recipe.get_ingredients_with_details(),
            }
            cache.set(cache_key, ingredients, 60 * 5)
        return Response(
            ingredients,
            status=status.HTTP_200_OK,
        )


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

    def perform_create(self, serializer):
        serializer.save(user_id=self.request.user.telegram_id)

    def perform_update(self, serializer):
        serializer.save(user_id=self.request.user.telegram_id)

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
            eatenfood = FoodDataBuilder.eaten_food_list_data_build(qs, request)
            cache.set(cache_key, eatenfood, 60 * 5)

        return Response(eatenfood, status=status.HTTP_200_OK)

    @method_decorator(cache_page(60 * 3))
    @method_decorator(vary_on_headers("Authorization"))
    @action(detail=False, methods=["get"])
    def nutrition_stats(self, request):
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
