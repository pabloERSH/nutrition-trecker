from django.db.models.signals import pre_delete, post_save
from django.dispatch import receiver
from .models import EatenFood, BaseFood, CustomFood, Recipe
from django.db import IntegrityError

@receiver(pre_delete, sender=BaseFood)
def save_base_food_data(sender, instance, **kwargs):    
    """Сохранение данных перед удалёнием продукта из BaseFood в связанных с ним записях в EatenFood"""
    if EatenFood.objects.filter(base_food=instance).exists:
        EatenFood.objects.filter(base_food=instance).update(
            name = instance.name,
            proteins = instance.proteins,
            fats = instance.fats,
            carbohydrates = instance.carbohydrates,
            base_food = None
        )

@receiver(pre_delete, sender=CustomFood)
def save_custom_food_data(sender, instance, **kwargs):
    """Сохранение данных перед удалёнием продукта из CustomFood в связанных с ним записях в EatenFood"""
    if EatenFood.objects.filter(custom_food=instance).exists:
        EatenFood.objects.filter(custom_food=instance).update(
            name = instance.custom_name,
            proteins = instance.proteins,
            fats = instance.fats,
            carbohydrates = instance.carbohydrates,
            custom_food = None
        )

@receiver(pre_delete, sender=Recipe)
def save_recipe_data(sender, instance, **kwargs):
    """Сохранение данных перед удалёнием блюда из Recipe в связанных с ним записях в EatenFood"""
    if EatenFood.objects.filter(recipe_food=instance).exists:
        nutrition = instance.calculate_nutrition_per_100g()
        EatenFood.objects.filter(recipe_food=instance).update(
            name = instance.name,
            proteins = nutrition['proteins'],
            fats = nutrition['fats'],
            carbohydrates = nutrition['carbohydrates'],
            recipe_food = None
        )
    