import json
import requests

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# === НАСТРОЙКИ TELEGRAM ===
TELEGRAM_BOT_TOKEN = "8118020170:AAELAq_XPMG_7HKrqs6vTUzTxdfgiB3bxQM"
TELEGRAM_CHAT_ID = "1052457410"
# ==========================


def send_to_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
    }

    r = requests.post(url, json=payload, timeout=10)
    print("TELEGRAM STATUS:", r.status_code)
    print("TELEGRAM RESPONSE:", r.text)


@csrf_exempt
def tawk_webhook(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    payload = json.loads(request.body.decode("utf-8"))

    message_text = payload["message"]["text"]
    visitor = payload.get("visitor", {})
    city = visitor.get("city", "—")
    country = visitor.get("country", "—")

    text = (
        "Новое сообщение с сайта (Tawk)\n\n"
        f"{message_text}\n\n"
        f"Город: {city}, {country}"
    )

    send_to_telegram(text)
    return JsonResponse({"status": "ok"})

@csrf_exempt
def contacts_form(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name = payload.get("name", "—")
    phone = payload.get("phone", "—")
    message = payload.get("message", "—")

    text = (
        "📨 Заявка с формы Contacts\n\n"
        f"Имя: {name}\n"
        f"Телефон: {phone}\n\n"
        f"Сообщение:\n{message}"
    )


    send_to_telegram(text)

    return JsonResponse({"status": "ok"})
