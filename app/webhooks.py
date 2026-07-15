import json
import requests
import time
import re
import uuid
from app.models import CalculatorLead
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from cars.models import Vehicle
from django.contrib.auth import get_user_model

def extract_calc_id(text: str):
    if not text:
        return None
    m = re.search(r'CM-\d{8}-\d{4}', text)
    return m.group(0) if m else None

def send_to_telegram(text: str):
    # Не должно ронять запрос, оформивший заявку, если у Telegram
    # проблемы (таймаут, неверный токен и т.п.) — заявка уже сохранена
    # в CalculatorLead, доставка уведомления — best-effort.
    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
        }
        r = requests.post(url, json=payload, timeout=10)
        print("TELEGRAM STATUS:", r.status_code)
        print("TELEGRAM RESPONSE:", r.text)
        return r.ok
    except Exception as e:
        print("TELEGRAM ERROR:", e)
        return False


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
    User = get_user_model()
    managers = User.objects.filter(is_staff=True).order_by("id")

    if not managers.exists():
        return None

    last_lead = CalculatorLead.objects.exclude(manager=None).order_by("-created_at").first()

    if not last_lead or not last_lead.manager:
        return managers.first()

    manager_ids = list(managers.values_list("id", flat=True))

    try:
        current_index = manager_ids.index(last_lead.manager.id)
        next_index = (current_index + 1) % len(manager_ids)
        return managers.get(id=manager_ids[next_index])
    except ValueError:
        return managers.first()

@csrf_exempt
def contacts_form(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if "message" not in payload:
        return JsonResponse({"status": "ignored"})

    name = payload.get("name") or "—"
    phone = payload.get("phone") or "—"
    message = payload.get("message") or "—"
    page_url = (payload.get("page") or "—").split("?")[0]

    product_id = payload.get("product_id")
    product = None

    if product_id:
        try:
            product = Vehicle.objects.get(id=product_id)
        except (Vehicle.DoesNotExist, ValueError, TypeError):
            product = None

    try:
        calc_id = extract_calc_id(message)
        manager = get_next_manager()

        # time.time() урезанный до секунд — при двух заявках в одну и ту же
        # секунду (двойной клик, два разных посетителя) calc_id совпадал бы
        # и CalculatorLead.objects.create() падал на unique-constraint (500).
        # Добавляем случайный суффикс, чтобы коллизия была практически невозможна.
        lead = CalculatorLead.objects.create(
            calc_id=calc_id or f"CONTACT-{int(time.time())}-{uuid.uuid4().hex[:6]}",
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
    except Exception as e:
        print("CONTACTS FORM ERROR:", e)
        return JsonResponse({"status": "error", "error": str(e)}, status=500)

    return JsonResponse({"status": "ok"})

