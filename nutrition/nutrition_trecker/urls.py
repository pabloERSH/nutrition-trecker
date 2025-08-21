from rest_framework import routers
from rest_framework_nested import routers as nested_routers
from nutrition_trecker import views
from django.urls import path, include

# Основной роутер
router = routers.DefaultRouter()
router.register(r"base-food", views.BaseFoodViewSet, basename="base-food")
router.register(r"custom-food", views.CustomFoodViewSet, basename="custom-food")
router.register(r"user-favorite", views.UserFavoriteViewSet, basename="user-favorite")
router.register(r"recipes", views.RecipeViewSet, basename="recipe")
router.register(r"eaten-food", views.EatenFoodViewSet, basename="eaten-food")

# Вложенный роутер для ингредиентов рецепта
recipe_router = nested_routers.NestedDefaultRouter(router, r"recipes", lookup="recipe")
recipe_router.register(
    r"ingredients", views.RecipeIngredientViewSet, basename="recipe-ingredients"
)

urlpatterns = [
    path("nutrition/", include(router.urls)),
    path("nutrition/", include(recipe_router.urls)),
]
