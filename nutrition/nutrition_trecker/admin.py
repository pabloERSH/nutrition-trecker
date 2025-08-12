from django.contrib import admin
from .models import BaseFood


@admin.register(BaseFood)
class BaseFoodAdmin(admin.ModelAdmin):
    readonly_fields = ("kcal",)
    list_display = ("id", "proteins", "fats", "carbohydrates", "kcal")
    search_fields = ("name",)
