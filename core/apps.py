from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        # Регистрируем обработчики сигналов (автоотправка КП при создании сделки).
        from . import signals  # noqa: F401
