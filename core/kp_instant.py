"""Мгновенное КП по технике из каталога — без сделки и без менеджера.

Раньше коммерческое предложение существовало только как часть сделки:
менеджер её заводил, система собирала PDF и отправляла письмом. Клиент до
этого момента ждал. Здесь то же самое предложение собирается по одной
карточке техники, сразу, для любого посетителя.

Два выхода, одни данные:
    build_instant_kp(vehicle)      → dict → JSON для страницы /kp/<id>
    build_instant_kp_pdf(vehicle)  → bytes → официальный PDF с печатью

Оба берут разбивку из core.calc.compute_breakdown — той же функции, что
повторяет формулу калькулятора. Ни один из них не считает ничего сам.

Шаблон PDF не переписан: используется core.kp.build_kp_pdf, тот же, что
собирает КП по сделке. Отличия мгновенного КП передаются через extras —
собственный номер, пустой покупатель, текущая дата.
"""

import logging
from datetime import date

from . import calc

log = logging.getLogger(__name__)


def _kp_number(vehicle):
    """«КП-инст-101-20260731».

    Отдельная нумерация, не пересекающаяся с номерами сделок: в шапке КП
    по сделке стоит «№ сделки: 14», и если мгновенное КП тоже назовётся
    числом, менеджер не отличит документ по несуществующей сделке от
    документа по реальной. Префикс «инст» читается и без пояснений.
    """
    return f"КП-инст-{vehicle.id}-{date.today().strftime('%Y%m%d')}"


AVAILABILITY_NOTE = {
    "in_stock": "Техника в наличии, готова к отгрузке.",
    "on_order": "Под заказ: срок поставки — по срокам ниже.",
    "in_transit": "Техника в пути.",
    "out_of_stock": "",
}


def _specs(vehicle):
    """Характеристики — те же поля и тот же порядок, что _vehicle_specs()
    в core/kp.py, но в виде списка словарей для JSON."""
    from .kp import _vehicle_specs
    return [{"label": label, "value": str(value)} for label, value in _vehicle_specs(vehicle)]


def _photo_url(vehicle):
    if vehicle.image_url:
        return vehicle.image_url
    images = vehicle.images
    if isinstance(images, list) and images:
        return images[0]
    return ""


def _seller_and_terms():
    """Фиксированная часть КП — из KPSettings (админка), с откатом на
    core/kp_defaults.py. Ровно то же, что попадает в PDF."""
    from .kp import _template, _seller_from, _delivery_terms, _timeline, _service_center
    tpl = _template()
    return {
        "seller": _seller_from(tpl),
        "delivery_terms": _delivery_terms(tpl),
        "timeline": _timeline(tpl),
        "service_center": _service_center(tpl),
    }


def build_instant_kp(vehicle, quantity=1, cfg=None, rates=None, base_url=""):
    """Данные мгновенного КП — структура, которую читает kp.js.

    ВАЖНО про price.kzt_total. Здесь НЕ используется vehicle.price_kzt,
    хотя КП по сделке в эту же ячейку таблицы подставляет именно его.
    Причина: на странице и в PDF итог виден дважды — в ячейке «Сумма, ₸»
    таблицы количество/цена и строкой «под ключ» под разбивкой. price_kzt
    заводится в карточку руками и живёт своей жизнью: он устаревает при
    смене курса, его правят отдельно от расчёта. Разойдись эти два числа —
    документ противоречит сам себе, и доверять нельзя ни одному.

    Поэтому оба места питает breakdown.total, посчитанный только что.
    price_kzt остаётся ценой каталога и в КП не попадает вовсе.
    """
    cfg = cfg or calc.load_config()
    rates = rates or calc.live_rates(cfg)

    breakdown = calc.compute_breakdown(vehicle, cfg=cfg, rates=rates)
    qty = max(1, int(quantity or 1))
    fixed = _seller_and_terms()

    from .kp import _vehicle_title

    return {
        "number": _kp_number(vehicle),
        "date": date.today().isoformat(),
        # Клиента ещё нет: КП выдаётся до того, как человек себя назвал.
        "buyer_name": "",
        "seller": fixed["seller"],
        "vehicle": {
            "id": vehicle.id,
            "title": _vehicle_title(vehicle),
            "photo_url": _photo_url(vehicle),
            "extra_info": vehicle.extra_info or "",
            "specs": _specs(vehicle),
        },
        "quantity": qty,
        # Все три числа приходят из ОДНОГО расчёта. usd здесь — не
        # vehicle.price_usd из карточки, а доллары, выведенные из юаней по
        # тому же курсу, что и вся разбивка (calc.resolve_price). Иначе
        # таблица показывала бы одну цену, а разбивка считалась бы от другой.
        "price": {
            "usd": breakdown["price"]["usd"],
            "cny": breakdown["price"]["cny"],
            "kzt_total": breakdown["total"] * qty,
        },
        "availability_note": AVAILABILITY_NOTE.get(vehicle.availability, ""),
        "breakdown": breakdown,
        "delivery_terms": fixed["delivery_terms"],
        "timeline": fixed["timeline"],
        "service_center": fixed["service_center"],
        # Ссылка на официальный PDF. Имя поля закреплено фронтендом
        # (kp.js читает именно kp_pdf_url) — не переименовывать.
        #
        # Абсолютная, а не относительная. Сайт живёт на chinamotors.kz, а API
        # на отдельном хосте: относительный путь браузер разрешил бы от
        # страницы и ушёл бы за PDF не туда. base_url подставляет view из
        # самого запроса, поэтому ссылка верна и на проде, и локально.
        "kp_pdf_url": f"{base_url.rstrip('/')}/api/kp/{vehicle.id}/pdf/",
    }


def build_instant_kp_pdf(vehicle, quantity=1, cfg=None, rates=None):
    """Официальный PDF по технике — тот же шаблон, что у КП по сделке.

    Шаблон не дублируется: core.kp.build_kp_pdf принимает объект с полями
    сделки, а «сделку» без сделки уже умеет изображать _ManualDeal —
    адаптер, написанный для ручного конструктора КП в кабинете менеджера.
    Переиспользуем его, и печать с подписью, шапка продавца, условия
    поставки и сервис-центр приезжают сами.
    """
    from .kp import build_kp_pdf, _ManualDeal

    data = build_instant_kp(vehicle, quantity=quantity, cfg=cfg, rates=rates)

    per_unit = data["breakdown"]["total"]
    deal = _ManualDeal(vehicle, total_price=per_unit, breakdown=data["breakdown"])

    extras = {
        "number": data["number"],
        # Покупателя нет — в шапке будет прочерк, а не чужое имя.
        "buyer_name": "—",
        "quantity": data["quantity"],
        "availability_note": data["availability_note"],
        "delivery_terms": data["delivery_terms"],
        "timeline": data["timeline"],
        # Ячейку «Сумма, ₸» питает итог разбивки, а не vehicle.price_kzt:
        # оба числа документа должны быть одним числом. PDF умножит это
        # значение на quantity сам.
        "unit_price_kzt": per_unit,
        "price_usd": data["price"]["usd"],
        "price_cny": data["price"]["cny"],
    }
    return build_kp_pdf(deal, extras)


# ============================================================================
#  Заморозка: снимок вместо пересчёта на каждое открытие
# ============================================================================

def _inputs_fingerprint(vehicle, cfg):
    """Отпечаток всего, что влияет на расчёт, КРОМЕ курса.

    Курс намеренно не входит: его колебание — это ровно то, от чего снимок
    защищает. Зато входят цены и характеристики техники и настройки
    калькулятора: изменил админ цену или сбор — прежний документ больше не
    описывает эту машину, и следующее открытие выпустит новый.
    """
    import hashlib
    import json

    parts = {
        "vehicle": [
            str(vehicle.price_usd), str(vehicle.price_cny), str(vehicle.weight_t),
            str(vehicle.year), vehicle.category or "", vehicle.body_type or "",
            vehicle.brand or "", vehicle.model or "",
            vehicle.extra_info or "", vehicle.image_url or "",
            str(vehicle.wheel_formula or ""), str(vehicle.gearbox or ""),
            str(vehicle.engine_power_hp or ""), str(vehicle.load_capacity_t or ""),
            vehicle.availability or "",
        ],
        # Настройки калькулятора целиком: любой сбор, ставка или МРП меняет
        # итог, и документ должен перевыпуститься.
        "cfg": cfg,
        # Шаблон КП: сменились реквизиты или сроки — документ тоже другой.
        "tpl": _seller_and_terms(),
    }
    blob = json.dumps(parts, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def get_or_issue_snapshot(vehicle, base_url="", quantity=1):
    """Действующий снимок КП по технике; если его нет — выпустить новый.

    Возвращает core.models.KPSnapshot. Бросает calc.RatesUnavailable, когда
    выпустить новый снимок нельзя из-за отсутствия живого курса — но только
    если действующего снимка нет: уже выданный документ курс не трогает,
    он на то и заморожен.
    """
    from datetime import date, timedelta
    from .models import KPSnapshot, KPSettings

    cfg = calc.load_config()
    fingerprint = _inputs_fingerprint(vehicle, cfg)

    snap = (KPSnapshot.objects
            .filter(vehicle=vehicle,
                    inputs_fingerprint=fingerprint,
                    valid_until__gte=date.today())
            .order_by("-created_at")
            .first())
    if snap:
        return snap

    # Нового документа без живого курса не будет: см. calc.live_rates.
    rates = calc.live_rates(cfg)
    data = build_instant_kp(vehicle, quantity=quantity, cfg=cfg, rates=rates,
                            base_url=base_url)

    try:
        valid_days = int(KPSettings.load().kp_valid_days or 14)
    except Exception:  # noqa: BLE001 — таблицы может ещё не быть
        valid_days = 14
    issued = date.today()
    valid_until = issued + timedelta(days=valid_days)

    # Срок действия — часть документа, а не только строка в базе: он виден
    # и на странице, и в PDF.
    data["issued_on"] = issued.isoformat()
    data["valid_until"] = valid_until.isoformat()

    return KPSnapshot.objects.create(
        vehicle=vehicle,
        number=data["number"],
        issued_on=issued,
        valid_until=valid_until,
        usd_kzt=rates["usd_kzt"],
        cny_kzt=rates["cny_kzt"],
        price_usd=data["price"]["usd"],
        price_cny=data["price"]["cny"],
        total_kzt=data["price"]["kzt_total"],
        inputs_fingerprint=fingerprint,
        payload=data,
    )


def snapshot_pdf(snapshot, vehicle):
    """PDF из снимка — те же числа, что на странице, без единого пересчёта."""
    from .kp import build_kp_pdf, _ManualDeal

    data = snapshot.payload
    per_unit = data["breakdown"]["total"]
    deal = _ManualDeal(vehicle, total_price=per_unit, breakdown=data["breakdown"])

    extras = {
        "number": data["number"],
        "buyer_name": "—",
        "quantity": data.get("quantity", 1),
        "availability_note": data.get("availability_note", ""),
        "delivery_terms": data.get("delivery_terms", ""),
        "timeline": data.get("timeline"),
        "unit_price_kzt": per_unit,
        # Цены в таблице — из снимка, а не из карточки техники: карточку с
        # тех пор могли и поправить.
        "price_usd": data["price"]["usd"],
        "price_cny": data["price"]["cny"],
        "issued_on": data.get("issued_on"),
        "valid_until": data.get("valid_until"),
    }
    return build_kp_pdf(deal, extras)
