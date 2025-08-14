from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


class ModelCleanMixin:
    """Миксин для вызова model.full_clean() в DRF."""

    def validate(self, attrs):
        if hasattr(super(), "validate"):
            attrs = super().validate(attrs)

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
