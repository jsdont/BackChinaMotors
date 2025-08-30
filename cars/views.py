from rest_framework import viewsets, filters
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.conf import settings
import os
import json
import urllib.request

from .models import Vehicle
from .serializers import VehicleSerializer


class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'brand', 'model', 'body_type']
    ordering_fields = ['created_at', 'price_usd', 'year']


# ---------- КУРС USD (как и раньше, фронт дергает /api/rate/usd) ----------
@api_view(['GET'])
@permission_classes([AllowAny])
def rate_usd(request):
    """
    Возвращает текущий курс USD->KZT: {"ok": true, "rate": 5xx.xx, "source": "..."}
    Реализуй на базе твоего источника (НБ РК / MIG) — ниже пример с открытым API НБРК.
    """
    try:
        # пример: курс USD у НБРК (если у тебя уже есть своя реализация — оставь её)
        with urllib.request.urlopen("https://nationalbank.kz/rss/rates_all.xml") as resp:
            xml = resp.read().decode('utf-8', errors='ignore')

        # простейший парсинг (можно заменить на твой)
        # ищем <title>USD</title> ... <description>xxx,xx</description>
        import re
        m = re.search(r"<title>USD</title>\s*<description>([\d,\.]+)</description>", xml)
        if not m:
            return Response({"ok": False, "error": "RATE_NOT_FOUND"}, status=502)

        raw = m.group(1).replace(',', '.')
        rate = float(raw)
        return Response({"ok": True, "rate": rate, "source": "NBRK"})
    except Exception as e:
        return Response({"ok": False, "error": str(e)}, status=502)


# ---------- Telegram (как и раньше, фронт дергает /api/telegram) ----------
@api_view(['POST'])
@permission_classes([AllowAny])
def telegram_message(request):
    """
    Принимает: {"text": "..."} и пересылает в твой Telegram чат через бота.
    Ожидает переменные окружения: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
    """
    try:
        body = request.data or {}
        text = body.get("text", "").strip()
        if not text:
            return Response({"ok": False, "error": "TEXT_REQUIRED"}, status=400)

        token = os.getenv("TELEGRAM_TOKEN", getattr(settings, "TELEGRAM_TOKEN", ""))
        chat_id = os.getenv("TELEGRAM_CHAT_ID", getattr(settings, "TELEGRAM_CHAT_ID", ""))

        if not token or not chat_id:
            return Response({"ok": False, "error": "BOT_NOT_CONFIGURED"}, status=500)

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        data = json.dumps(payload).encode('utf-8')
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as resp:
            resp.read()

        return Response({"ok": True})
    except Exception as e:
        return Response({"ok": False, "error": str(e)}, status=502)
