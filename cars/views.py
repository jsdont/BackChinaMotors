import re
import time

import requests
from django.http import JsonResponse
from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from .models import Vehicle
from .serializers import VehicleSerializer


class VehicleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Vehicle.objects.all().order_by("-id")
    serializer_class = VehicleSerializer
    permission_classes = [AllowAny]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["brand", "model", "year", "body_type"]
    ordering_fields = ["price_usd", "price_cny", "year", "id"]


# nationalbank.kz doesn't send CORS headers, so the browser can't fetch it
# directly — this proxies the request server-side and caches briefly to
# avoid hammering their feed on every calculator page load.
_RATES_CACHE = {"data": None, "fetched_at": 0}
_RATES_CACHE_TTL = 600  # seconds
_NBK_FEED_URL = "https://nationalbank.kz/rss/get_rates.cfm?fdate="


def _parse_rate(text, code):
    match = re.search(
        rf"<title>{code}</title>[\s\S]*?<description>([0-9.]+)</description>", text
    )
    return float(match.group(1)) if match else None


def rates_view(request):
    now = time.time()
    if _RATES_CACHE["data"] and now - _RATES_CACHE["fetched_at"] < _RATES_CACHE_TTL:
        return JsonResponse(_RATES_CACHE["data"])

    try:
        resp = requests.get(_NBK_FEED_URL, timeout=5)
        resp.raise_for_status()
        text = resp.text

        data = {
            "usd_kzt": _parse_rate(text, "USD"),
            "cny_kzt": _parse_rate(text, "CNY"),
        }

        if data["usd_kzt"] and data["cny_kzt"]:
            _RATES_CACHE["data"] = data
            _RATES_CACHE["fetched_at"] = now

        return JsonResponse(data)
    except Exception as e:
        # печатаем в stdout, чтобы причина была видна в `fly logs` —
        # раньше ошибка проглатывалась молча и логов вообще не было
        print(f"[rates_view] NBK fetch failed: {type(e).__name__}: {e}")
        return JsonResponse(
            {"usd_kzt": None, "cny_kzt": None, "error": f"{type(e).__name__}: {e}"},
            status=502,
        )
