import json
import requests

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


BOT_TOKEN = "8118020170:AAH8CNYBE5bqYMqVv0mup85U0d-RtoQyKSw"
CHAT_ID = "1052457410"
TG_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


def send_to_telegram(text: str):
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }
    try:
        requests.post(TG_API_URL, json=payload, timeout=5)
    except Exception as e:
        print("TG ERROR:", e)


@csrf_exempt
def tawk_webhook(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    print("TAWK WEBHOOK:", json.dumps(payload, indent=2, ensure_ascii=False))

    event = payload.get("event")

    visitor = payload.get("visitor", {})
    city = visitor.get("city", "—")
    country = visitor.get("country", "—")

    message = payload.get("message", {})
    text = message.get("text")

    if text:
        tg_text = (
            "📩 <b>Новое сообщение с сайта (Tawk.to)</b>\n\n"
            f"💬 <b>Сообщение:</b>\n{text}\n\n"
            f"📍 <b>Локация:</b> {city}, {country}"
        )
        send_to_telegram(tg_text)

    return JsonResponse({"status": "ok"})
