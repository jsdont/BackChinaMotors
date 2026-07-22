"""Уведомление пользователей по e-mail и SMS.

Полностью рабочий код: e-mail уходит через настроенный Django EMAIL_BACKEND
(SMTP, если заданы секреты, иначе консоль/лог), SMS — через HTTP-шлюз, если
задан SMS_GATEWAY_URL. Пока секреты не заданы — ничего наружу не уходит, но
и запрос никогда не падает: все ошибки только логируются.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

log = logging.getLogger(__name__)


def send_sms(phone, text):
    """Отправить SMS через настроенный HTTP-шлюз. Возвращает True/False.
    Без SMS_GATEWAY_URL — тихо ничего не делает (возвращает False)."""
    url = getattr(settings, "SMS_GATEWAY_URL", "")
    if not url or not phone:
        return False
    try:
        import requests  # ленивый импорт — SMS может быть не настроен вовсе
        requests.post(
            url,
            data={
                "login": getattr(settings, "SMS_GATEWAY_LOGIN", ""),
                "psw": getattr(settings, "SMS_GATEWAY_PASSWORD", ""),
                "phones": phone,
                "mes": text,
                "sender": getattr(settings, "SMS_GATEWAY_SENDER", ""),
            },
            timeout=8,
        )
        return True
    except Exception as e:  # noqa: BLE001 — уведомление не должно ронять запрос
        log.warning("SMS send failed for %s: %s", phone, e)
        return False


def notify_user(user, subject, message):
    """Уведомить пользователя по e-mail (если есть адрес) и SMS (если настроен
    шлюз). Безопасно для вызова из вьюх — никогда не бросает исключение."""
    if user is None:
        return

    email = getattr(user, "email", None)
    if email:
        try:
            send_mail(
                subject,
                message,
                getattr(settings, "DEFAULT_FROM_EMAIL", None),
                [email],
                fail_silently=True,
            )
        except Exception as e:  # noqa: BLE001
            log.warning("email notify failed for %s: %s", email, e)

    phone = getattr(user, "phone", None)
    if phone:
        send_sms(phone, f"{subject}. {message}")
