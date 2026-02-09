import json
import requests

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# === НАСТРОЙКИ TELEGRAM ===
TELEGRAM_BOT_TOKEN = "8118020170:AAH8CNYBE5bqYMqVv0mup85U0d-RtoQyKSw"
TELEGRAM_CHAT_ID = "1052457410"
# ==========================


def send_to_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }
    requests.post(url, json=payload, timeout=10)


@csrf_exempt
def tawk_webhook(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # ===== Извлекаем данные =====
    message_text = payload.get("message", {}).get("text", "")
    visitor = payload.get("visitor", {})
    city = visitor.get("city", "—")
    country = visitor.get("country", "—")
    event = payload.get("event", "unknown")

    text = (
        "📩 <b>Новое сообщение с сайта (Tawk.to)</b>\n\n"
        f"💬 <b>Сообщение:</b>\n{message_text}\n\n"
        f"📍 <b>Город:</b> {city}, {country}\n"
        f"⚙️ <b>Событие:</b> {event}"
    )

    # ===== ОТПРАВКА В TELEGRAM =====
    send_to_telegram(text)

    return JsonResponse({"status": "ok"})
