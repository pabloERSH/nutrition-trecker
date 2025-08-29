from django.db.models.signals import pre_delete, post_save, post_delete
from django.dispatch import receiver
import logging
from .models import EatenFood, BaseFood, CustomFood, Recipe, RecipeIngredient
from common.utils.CacheHelper import CacheHelper
from django.core.cache import cache


logger = logging.getLogger("nutrition")


@receiver(post_save, sender=BaseFood)
@receiver(post_delete, sender=BaseFood)
def invalidate_basefood_cache(sender, instance, **kwargs):
    cache_key = CacheHelper.make_cache_key("basefood", "list")
    cache.delete(cache_key)
    logger.info(f"Cache delete for BaseFood(id={instance.id})")


@receiver(post_save, sender=CustomFood)
@receiver(post_delete, sender=CustomFood)
def invalidate_customfood_cache(sender, instance, **kwargs):
    CacheHelper.bump_cache_version("customfood", instance.user_id)
    logger.info(f"Cache version bumped for CustomFood(id={instance.id})")


@receiver(post_save, sender=Recipe)
@receiver(post_delete, sender=Recipe)
def invalidate_recipe_cache(sender, instance, **kwargs):
    CacheHelper.bump_cache_version("recipe", instance.user_id)
    logger.info(f"Cache version bumped for Recipe(id={instance.id})")


@receiver(post_save, sender=RecipeIngredient)
@receiver(post_delete, sender=RecipeIngredient)
def invalidate_recipe_ingredient_cache(sender, instance, **kwargs):
    CacheHelper.bump_cache_version(
        f"recipe_ingredient:recipe_id:{instance.recipe}", instance.user_id
    )
    CacheHelper.bump_cache_version("recipe", instance.user_id)
    logger.info(f"Cache version bumped for RecipeIngredient(id={instance.id})")


@receiver(post_save, sender=EatenFood)
@receiver(post_delete, sender=EatenFood)
def invalidate_eatenfood_cache(sender, instance, **kwargs):
    CacheHelper.bump_cache_version("eaten_food", instance.user_id)
    logger.info(f"Cache version bumped for EatenFood(id={instance.id})")


@receiver(pre_delete, sender=BaseFood)
def update_eaten_food_on_base_food_delete(sender, instance, **kwargs):
    """Сохранение данных перед удалёнием продукта из BaseFood в связанных с ним записях в EatenFood"""
    rows = EatenFood.objects.filter(base_food=instance)
    if rows.exists():
        rows.update(
            name=instance.name,
            proteins=instance.proteins,
            fats=instance.fats,
            carbohydrates=instance.carbohydrates,
            kcal=instance.kcal,
            base_food=None,
        )
        logger.info(
            f"Rows in eaten_food updated after BaseFood(id={instance.id}) was deleted"
        )


@receiver(pre_delete, sender=CustomFood)
def update_eaten_food_on_custom_food_delete(sender, instance, **kwargs):
    """Сохранение данных перед удалёнием продукта из CustomFood в связанных с ним записях в EatenFood"""
    rows = EatenFood.objects.filter(custom_food=instance)
    if rows.exists():
        rows.update(
            name=instance.custom_name,
            proteins=instance.proteins,
            fats=instance.fats,
            carbohydrates=instance.carbohydrates,
            kcal=instance.kcal,
            custom_food=None,
        )
        logger.info(
            f"Rows in eaten_food updated after CustomFood(id={instance.id}) was deleted"
        )


@receiver(pre_delete, sender=Recipe)
def update_eaten_food_on_recipe_food_delete(sender, instance, **kwargs):
    """Сохранение данных перед удалёнием блюда из Recipe в связанных с ним записях в EatenFood"""
    rows = EatenFood.objects.filter(recipe_food=instance)
    if rows.exists():
        nutrition = instance.calculate_nutrition()["per_100g"]
        rows.update(
            name=instance.name,
            proteins=nutrition["proteins"],
            fats=nutrition["fats"],
            carbohydrates=nutrition["carbohydrates"],
            kcal=nutrition["kcal"],
            recipe_food=None,
        )
        logger.info(
            f"Rows in eaten_food updated after Recipe(id={instance.id}) was deleted"
        )


@receiver(pre_delete, sender=BaseFood)
def update_recipe_ingredients_on_base_food_delete(sender, instance, **kwargs):
    """Сохранение данных перед удалёнием блюда из BaseFood в связанных с ним записях в RecipeIngredient"""
    rows = RecipeIngredient.objects.filter(base_food=instance)
    if rows.exists():
        rows.update(
            name=instance.name,
            proteins=instance.proteins,
            fats=instance.fats,
            carbohydrates=instance.carbohydrates,
            kcal=instance.kcal,
            base_food=None,
        )
        logger.info(
            f"Rows in recipe_ingredient updated after BaseFood(id={instance.id}) was deleted"
        )


@receiver(pre_delete, sender=CustomFood)
def update_recipe_ingredients_on_custom_food_delete(sender, instance, **kwargs):
    """Сохранение данных перед удалёнием блюда из BaseFood в связанных с ним записях в RecipeIngredient"""
    rows = RecipeIngredient.objects.filter(custom_food=instance)
    if rows.exists():
        rows.update(
            name=instance.custom_name,
            proteins=instance.proteins,
            fats=instance.fats,
            carbohydrates=instance.carbohydrates,
            kcal=instance.kcal,
            custom_food=None,
        )
        logger.info(
            f"Rows in recipe_ingredient updated after CustomFood(id={instance.id}) was deleted"
        )
