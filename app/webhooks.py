import json
import requests
import time
import re
from app.models import CalculatorLead
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from catalog.models import Product
from django.contrib.auth.models import User, Group
from django.db.models import Count


# === НАСТРОЙКИ TELEGRAM ===
TELEGRAM_BOT_TOKEN = "8118020170:AAELAq_XPMG_7HKrqs6vTUzTxdfgiB3bxQM"
TELEGRAM_CHAT_ID = "1052457410"
# ==========================

def extract_calc_id(text: str):
    if not text:
        return None
    m = re.search(r'CM-\d{8}-\d{4}', text)
    return m.group(0) if m else None


def send_to_telegram(text: str):
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }


    r = requests.post(url, json=payload, timeout=10)
    print("TELEGRAM STATUS:", r.status_code)
    print("TELEGRAM RESPONSE:", r.text)


@csrf_exempt
def tawk_webhook(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    message = payload.get("message", {})
    message_text = message.get("text", "—")

    visitor = payload.get("visitor", {})
    page = payload.get("page", {})
    page_url = page.get("url", "—")

    city = visitor.get("city", "—")
    country = visitor.get("country", "—")

    text = (
        "💬 <b>НОВОЕ СООБЩЕНИЕ — ЧАТ (Tawk.to)</b>\n\n"
        f"<b>Сообщение:</b>\n{message_text}\n\n"
        f"<b>Город:</b> {city}, {country}\n"
        f"<b>Страница:</b> {page_url}\n"
        f"<b>Источник:</b> Онлайн-чат сайта"
    )


    send_to_telegram(text)
    return JsonResponse({"status": "ok"})

def get_next_manager():
    try:
        group = Group.objects.get(name="Manager")
        managers = group.user_set.annotate(
            leads_count=Count("assigned_leads")
        ).order_by("leads_count")

        return managers.first()
    except Group.DoesNotExist:
        return None

@csrf_exempt
def contacts_form(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # защита от мусорных запросов
    if "message" not in payload:
        return JsonResponse({"status": "ignored"})

    name = payload.get("name", "—")
    phone = payload.get("phone", "—")
    message = payload.get("message", "—")
    page_url = payload.get("page", "—").split("?")[0]


    product_id = payload.get("product_id")
    product = None

    if product_id:
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            product = None


    calc_id = extract_calc_id(message)

    manager = get_next_manager()

    lead = CalculatorLead.objects.create(
        calc_id=calc_id or "CONTACT-" + str(int(time.time())),
        source="contacts",
        name=name,
        phone=phone,
        message=message,
        page_url=page_url,
        product=product,
        manager=manager,
    )





    text = (
        "📨 <b>ЗАЯВКА — CONTACTS</b>\n\n"
        f"<b>Имя:</b> {name}\n"
        f"<b>Телефон:</b> {phone}\n\n"
        f"<b>Сообщение:</b>\n{message}\n\n"
        f"<b>Страница:</b> {page_url}\n"
        f"<b>ID:</b> {lead.calc_id}"
    )

    send_to_telegram(text)
    return JsonResponse({"status": "ok"})
