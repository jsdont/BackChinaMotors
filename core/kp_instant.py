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
    rate = breakdown["currency"]["usd_kzt"]
    cny_rate = breakdown["currency"]["cny_kzt"]
    
    price_cny = float(vehicle.price_cny) if vehicle.price_cny else None
    
    if price_cny and cny_rate and rate:
        cny_usd_rate = (rate / cny_rate) - 0.02
        price_usd = price_cny / cny_usd_rate
    else:
        price_usd = float(vehicle.price_usd) if vehicle.price_usd else None
        
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
        "price": {
            "usd": round(price_usd, 2) if price_usd is not None else None,
            "cny": round(price_cny, 2) if price_cny is not None else None,
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
    }
    return build_kp_pdf(deal, extras)
