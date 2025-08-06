from django.contrib import admin
from .models import BaseFood

@admin.register(BaseFood)
class BaseFoodAdmin(admin.ModelAdmin):
    list_display = ('name', 'proteins', 'fats', 'carbohydrates')
    search_fields = ('name',)