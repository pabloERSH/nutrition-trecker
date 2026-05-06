from rest_framework import serializers
from .models import UserProfile
from datetime import date


class UserProfileSerializer(serializers.ModelSerializer):
    age = serializers.ReadOnlyField()
    target_calories = serializers.ReadOnlyField()

    class Meta:
        model = UserProfile
        fields = [
            "user_id",
            "gender",
            "birth_date",
            "height",
            "weight",
            "body_fat",
            "activity_level",
            "goal_type",
            "target_weight",
            "target_proteins",
            "target_fats",
            "target_carbs",
            "dietary_restrictions",
            "age",
            "target_calories",
        ]
        read_only_fields = ["user_id"]

    def validate_birth_date(self, value):
        if value > date.today():
            raise serializers.ValidationError("Дата рождения не может быть в будущем.")
        return value
