from rest_framework import serializers


class OwnedPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    """Кастомное поле для проверки принадлежности объекта пользователю"""

    def __init__(self, **kwargs):
        self.owner_field = kwargs.pop("owner_field", "user_id")
        super().__init__(**kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        request = self.context.get("request")
        if request and hasattr(request.user, "telegram_id"):
            filter_kwargs = {self.owner_field: request.user.telegram_id}
            return queryset.filter(**filter_kwargs)
        return queryset.none()

    def to_internal_value(self, data):
        try:
            return super().to_internal_value(data)
        except serializers.ValidationError:
            raise serializers.ValidationError(
                "Объект не существует или вам не принадлежит"
            )
