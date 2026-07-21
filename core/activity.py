"""Хелпер для записи лога изменений по сделке (аудит-трейл).

Вызывается из вьюх в момент действия — там известен и объект, и кто его
меняет (request.user). internal=True помечает событие как внутреннее (видит
только менеджер, например расходы)."""


def log_activity(deal, actor, text, internal=False):
    from .models import DealActivity

    if deal is None:
        return None

    if actor is not None and not getattr(actor, "is_authenticated", False):
        actor = None

    return DealActivity.objects.create(
        deal=deal,
        actor=actor,
        text=text[:500],
        internal=internal,
    )
