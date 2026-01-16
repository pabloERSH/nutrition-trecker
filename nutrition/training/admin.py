from django.contrib import admin
from .models import BaseExercise


@admin.register(BaseExercise)
class BaseExerciseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "description",
        "primary_muscle_group",
        "secondary_muscle_group",
        "exercise_type",
        "equipment_type",
        "image",
        "image_thumbnail",
    )
    search_fields = ("name",)
