from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


class ModelCleanMixin:
    """Миксин для вызова model.full_clean() в DRF."""

    def validate(self, attrs):
        if hasattr(super(), "validate"):
            attrs = super().validate(attrs)

        # Автоматическое заполнение поля user_id
        model = getattr(self.Meta, "model")
        if hasattr(model, "_meta") and "user_id" in [
            field.name for field in model._meta.fields
        ]:
            request = self.context.get("request")
            if request and hasattr(request.user, "telegram_id"):
                attrs["user_id"] = request.user.telegram_id

        # Автоматическое заполнение поля recipe для RecipeIngredient
        if model.__name__ == "RecipeIngredient" and "recipe" not in attrs:
            view = self.context.get("view")
            if view and hasattr(view, "_get_recipe"):
                recipe = view._get_recipe()
                attrs["recipe"] = recipe

        instance = getattr(self, "instance", None)
        if instance is None:
            instance = self.Meta.model(**attrs)
        else:
            for attr, value in attrs.items():
                setattr(instance, attr, value)

        try:
            instance.full_clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict)

        return attrs
