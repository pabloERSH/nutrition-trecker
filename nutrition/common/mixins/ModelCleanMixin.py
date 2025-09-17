from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


class ModelCleanMixin:
    """Миксин для вызова model.full_clean() в DRF."""

    def validate(self, attrs):
        if hasattr(super(), "validate"):
            attrs = super().validate(attrs)

        # Проверяем, есть ли поле user_id в модели
        model = getattr(self.Meta, "model")
        if hasattr(model, "_meta") and "user_id" in [
            field.name for field in model._meta.fields
        ]:
            # Получаем user_id из request.user.telegram_id
            request = self.context.get("request")
            if request and hasattr(request.user, "telegram_id"):
                attrs["user_id"] = request.user.telegram_id

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
