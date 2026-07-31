import re
import time
from datetime import datetime, timedelta
from xml.sax.saxutils import escape

import requests
from django.core.files.storage import default_storage
from django.http import HttpResponse, JsonResponse
from rest_framework import viewsets, filters, generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Vehicle
from .serializers import VehicleSerializer, MyVehicleListingSerializer


class VehicleViewSet(viewsets.ReadOnlyModelViewSet):
    # Публичный каталог — только одобренные записи. Официальные позиции
    # (owner пуст) одобрены по умолчанию; объявления клиентов появятся
    # здесь только после модерации админом.
    queryset = Vehicle.objects.filter(is_approved=True).order_by("-id")
    serializer_class = VehicleSerializer
    permission_classes = [AllowAny]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["brand", "model", "year", "body_type", "category", "city"]
    ordering_fields = ["price_usd", "price_cny", "price_kzt", "year", "id"]


CUSTOMER_ROLES = ("CUSTOMER_PERSON", "CUSTOMER_COMPANY")
# Кто может размещать объявления: клиенты (продают своё) и партнёры-продавцы
# (профессиональные продавцы техники из Китая). Все объявления проходят
# модерацию (is_approved) перед показом в каталоге.
SELLER_ROLES = CUSTOMER_ROLES + ("PARTNER",)


class MyVehicleListingsView(generics.ListCreateAPIView):
    """Клиент/партнёр: список своих объявлений (товаров) + подать новое."""
    serializer_class = MyVehicleListingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Vehicle.objects.filter(owner=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        if self.request.user.role not in SELLER_ROLES:
            raise PermissionDenied("Разместить объявление может клиент или партнёр-продавец.")
        serializer.save()


class MyVehicleListingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Клиент правит/удаляет своё объявление (не влияет на is_approved)."""
    serializer_class = MyVehicleListingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Vehicle.objects.filter(owner=self.request.user)


class MyVehicleListingPhotosView(APIView):
    """Загрузка фото (файлами) для своего объявления — сохраняются в Cloudinary,
    ссылки добавляются в Vehicle.images (и image_url, если ещё пуст)."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        try:
            vehicle = Vehicle.objects.get(pk=pk, owner=request.user)
        except Vehicle.DoesNotExist:
            return Response({"detail": "Не найдено."}, status=status.HTTP_404_NOT_FOUND)

        files = request.FILES.getlist("photos")
        if not files:
            return Response({"detail": "Файлы не переданы."}, status=status.HTTP_400_BAD_REQUEST)

        urls = []
        for f in files:
            path = default_storage.save(f"listings/{f.name}", f)
            urls.append(default_storage.url(path))

        vehicle.images = [*vehicle.images, *urls]
        if not vehicle.image_url:
            vehicle.image_url = urls[0]
        vehicle.save(update_fields=["images", "image_url"])

        return Response(MyVehicleListingSerializer(vehicle).data)


# nationalbank.kz doesn't send CORS headers, so the browser can't fetch it
# directly — this proxies the request server-side and caches briefly to
# avoid hammering their feed on every calculator page load.
_RATES_CACHE = {"data": None, "fetched_at": 0}
_RATES_CACHE_TTL = 600  # seconds
_NBK_FEED_URL = "https://nationalbank.kz/rss/get_rates.cfm"


def _fetch_nbk_text():
    # fdate is required (DD.MM.YYYY) — NBK doesn't publish on weekends/
    # holidays, so walk backwards a few days until we hit one that has data.
    for days_back in range(5):
        date = (datetime.now() - timedelta(days=days_back)).strftime("%d.%m.%Y")
        resp = requests.get(_NBK_FEED_URL, params={"fdate": date}, timeout=5)
        resp.raise_for_status()
        text = resp.text
        if _parse_rate(text, "USD") and _parse_rate(text, "CNY"):
            return text
    return text  # last attempt's response, for the raw_snippet debug output


def _parse_rate(text, code):
    match = re.search(
        rf"<title>{code}</title>[\s\S]*?<description>([0-9.]+)</description>", text
    )
    return float(match.group(1)) if match else None


# Неудачу кэшируем ненадолго, а удачу — на полный срок. Без короткого
# «отрицательного» кэша каждый запрос при недоступном фиде снова перебирал бы
# пять дат по 5 секунд (до 25 с ожидания), и это било бы по выдаче КП, который
# ходит за курсом на каждый запрос. С длинным — транзитный сбой залипал бы на
# десять минут и курс не показывался бы дольше, чем он реально отсутствовал.
_RATES_FAIL_TTL = 60


def get_rates():
    """Курсы НБ РК с кэшем. Возвращает {"usd_kzt": .., "cny_kzt": ..}, где
    значения могут быть None; исключений не бросает.

    Отдельная функция, потому что за курсом ходит не только /api/rates/, но и
    генератор мгновенного КП (core.calc.live_rates), и общий кэш им нужен
    один на двоих.
    """
    now = time.time()
    cached = _RATES_CACHE["data"]
    if cached:
        ok = bool(cached.get("usd_kzt") and cached.get("cny_kzt"))
        ttl = _RATES_CACHE_TTL if ok else _RATES_FAIL_TTL
        if now - _RATES_CACHE["fetched_at"] < ttl:
            return dict(cached)

    try:
        text = _fetch_nbk_text()
        data = {
            "usd_kzt": _parse_rate(text, "USD"),
            "cny_kzt": _parse_rate(text, "CNY"),
        }
    except Exception as e:  # noqa: BLE001 — источник внешний, падать не должен
        data = {"usd_kzt": None, "cny_kzt": None, "error": f"{type(e).__name__}: {e}"}

    _RATES_CACHE["data"] = data
    _RATES_CACHE["fetched_at"] = now
    return dict(data)


def rates_view(request):
    # Коды ответа сохранены как были: 502 только когда до фида не достучались,
    # а «достучались, но курса нет» по-прежнему 200 с null — на это поведение
    # уже опирается фронтенд (home.js, calculator.js).
    data = get_rates()
    if "error" in data:
        return JsonResponse(data, status=502)
    return JsonResponse(data)


def sitemap_vehicles(request):
    """XML sitemap of every publicly listed vehicle, for search engines --
    referenced from the frontend's robots.txt. Lives on the backend since
    it's the only place that knows the current catalog."""
    vehicles = Vehicle.objects.filter(is_approved=True).order_by("-id")

    entries = []
    for v in vehicles:
        loc = escape(f"https://chinamotors.kz/product.html?id={v.id}")
        lastmod = f"<lastmod>{v.created_at.date().isoformat()}</lastmod>" if v.created_at else ""
        entries.append(
            f"<url><loc>{loc}</loc>{lastmod}"
            "<changefreq>weekly</changefreq><priority>0.8</priority></url>"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(entries) +
        "</urlset>"
    )
    return HttpResponse(xml, content_type="application/xml")
