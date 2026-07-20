from rest_framework.permissions import BasePermission

MANAGER_ROLES = ("MANAGER", "ADMIN")


class IsManager(BasePermission):
    """Доступ только менеджеру/админу (или staff-пользователю). Используется
    для оперативного кабинета менеджера — обзор всех сделок и заявок."""

    message = "Доступно только менеджеру."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_staff or getattr(user, "role", None) in MANAGER_ROLES)
        )
