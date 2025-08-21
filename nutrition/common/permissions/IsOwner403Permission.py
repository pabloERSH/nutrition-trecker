from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied


class IsOwner403Permission(permissions.BasePermission):
    """
    Проверяет, что пользователь является владельцем объекта.
    Поддерживает вложенные поля.
    Возвращает 403 Forbidden, если объект существует, но не принадлежит пользователю.
    """

    owner_field = "user_id"  # можно переопределить во ViewSet

    def _get_nested_attr(self, obj, attr_path):
        """
        Достаёт вложенный атрибут по строке вида 'recipe.user_id'.
        """
        attrs = attr_path.split(".")
        value = obj
        for attr in attrs:
            value = getattr(value, attr, None)
            if value is None:
                break
        return value

    def has_object_permission(self, request, view, obj):
        owner_value = self._get_nested_attr(
            obj, getattr(view, "owner_field", self.owner_field)
        )

        # Если нет явного владельца — разрешаем доступ
        if owner_value is None:
            return True

        # Если владелец совпадает с пользователем
        if owner_value == getattr(request.user, "telegram_id", None):
            return True

        # Если объект есть, но не наш — возвращаем 403
        raise PermissionDenied("У вас нет прав доступа к этому объекту")
