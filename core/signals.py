"""Сигналы приложения core."""

import logging

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Deal

log = logging.getLogger(__name__)


@receiver(post_save, sender=Deal)
def send_kp_on_deal_created(sender, instance, created, **kwargs):
    """При создании сделки отправить коммерческое предложение на почту.

    Отправка выполняется после коммита транзакции (on_commit), чтобы КП уходил
    только по реально созданной сделке, и никогда не роняет запрос. Отключается
    флагом settings.KP_AUTOSEND = False.
    """
    if not created:
        return
    if not getattr(settings, "KP_AUTOSEND", True):
        return

    def _send():
        from .kp import send_kp_for_deal
        send_kp_for_deal(instance)

    transaction.on_commit(_send)
