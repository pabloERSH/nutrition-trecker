from django.db.models.signals import pre_delete
from django.dispatch import receiver
from .models import EatenFood, BaseFood, CustomFood, Recipe, RecipeIngredient
import logging


logger = logging.getLogger("nutrition_trecker")


@receiver(pre_delete, sender=BaseFood)
def eaten_food_save_base_food_data(sender, instance, **kwargs):
    """Сохранение данных перед удалёнием продукта из BaseFood в связанных с ним записях в EatenFood"""
    rows = EatenFood.objects.filter(base_food=instance)
    if rows.exists():
        rows.update(
            name=instance.name,
            proteins=instance.proteins,
            fats=instance.fats,
            carbohydrates=instance.carbohydrates,
            base_food=None,
        )
        logger.info(
            f"Rows in eaten_food updated after BaseFood(id={instance.id}) was deleted"
        )


@receiver(pre_delete, sender=CustomFood)
def eaten_food_save_custom_food_data(sender, instance, **kwargs):
    """Сохранение данных перед удалёнием продукта из CustomFood в связанных с ним записях в EatenFood"""
    rows = EatenFood.objects.filter(custom_food=instance)
    if rows.exists():
        rows.update(
            name=instance.custom_name,
            proteins=instance.proteins,
            fats=instance.fats,
            carbohydrates=instance.carbohydrates,
            custom_food=None,
        )
        logger.info(
            f"Rows in eaten_food updated after CustomFood(id={instance.id}) was deleted"
        )


@receiver(pre_delete, sender=Recipe)
def eaten_food_save_recipe_data(sender, instance, **kwargs):
    """Сохранение данных перед удалёнием блюда из Recipe в связанных с ним записях в EatenFood"""
    rows = EatenFood.objects.filter(recipe_food=instance)
    if rows.exists():
        nutrition = instance.calculate_nutrition_per_100g()
        rows.update(
            name=instance.name,
            proteins=nutrition["proteins"],
            fats=nutrition["fats"],
            carbohydrates=nutrition["carbohydrates"],
            recipe_food=None,
        )
        logger.info(
            f"Rows in eaten_food updated after Recipe(id={instance.id}) was deleted"
        )


@receiver(pre_delete, sender=BaseFood)
def recipe_ingredient_save_base_food_data(sender, instance, **kwargs):
    """Сохранение данных перед удалёнием блюда из BaseFood в связанных с ним записях в RecipeIngredient"""
    rows = RecipeIngredient.objects.filter(base_food=instance)
    if rows.exists():
        rows.update(
            name=instance.name,
            proteins=instance.proteins,
            fats=instance.fats,
            carbohydrates=instance.carbohydrates,
            base_food=None,
        )
        logger.info(
            f"Rows in recipe_ingredient updated after BaseFood(id={instance.id}) was deleted"
        )


@receiver(pre_delete, sender=CustomFood)
def recipe_ingredient_save_custom_food_data(sender, instance, **kwargs):
    """Сохранение данных перед удалёнием блюда из BaseFood в связанных с ним записях в RecipeIngredient"""
    rows = RecipeIngredient.objects.filter(custom_food=instance)
    if rows.exists():
        rows.update(
            name=instance.custom_name,
            proteins=instance.proteins,
            fats=instance.fats,
            carbohydrates=instance.carbohydrates,
            custom_food=None,
        )
        logger.info(
            f"Rows in recipe_ingredient updated after CustomFood(id={instance.id}) was deleted"
        )
