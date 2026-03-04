from rest_framework.permissions import BasePermission


class IsModer(BasePermission):
    message = "Только для модераторов."

    def has_permission(self, request, view):
        """Проверяет, что пользователь состоит в группе модераторов."""
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.groups.filter(name="moderators").exists()

    def has_object_permission(self, request, view, obj):
        """Проверяет права модератора на доступ к объекту."""
        return self.has_permission(request, view)


class IsOwner(BasePermission):
    message = "Доступ только владельцу объекта."

    def has_object_permission(self, request, view, obj):
        """Проверяет, что пользователь является владельцем объекта."""
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if hasattr(obj, "owner"):
            return obj.owner == user
        return obj == user
