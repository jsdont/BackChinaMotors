"""Генерация и отправка коммерческого предложения (КП) по сделке.

При создании сделки система собирает КП в PDF из данных сделки и техники и
отправляет его на почту (клиенту и/или в компанию) через уже настроенный
EMAIL_BACKEND (Resend SMTP в проде, консоль без секретов).

Переменная часть (модель, цена, покупатель) берётся из Deal/Vehicle. Фиксированная
часть (продавец, реквизиты банка, сроки поставки, сервис-центр) по умолчанию
соответствует КП Shaanxi, но её можно переопределить через settings — чтобы
реквизиты не были захардкожены навсегда и никогда не ушли неверными.
"""

import os
import logging
from datetime import date

from django.conf import settings
from django.core.mail import EmailMessage

log = logging.getLogger(__name__)

FONT_DIR = os.path.join(os.path.dirname(__file__), "assets", "fonts")
KP_ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets", "kp")
LETTERHEAD = os.path.join(KP_ASSET_DIR, "letterhead.jpg")  # шапка SHACMAN
SEAL = os.path.join(KP_ASSET_DIR, "seal.jpg")              # печать + подпись

from . import kp_defaults


def _cfg(name, default):
    return getattr(settings, name, default)


def _template():
    """Шаблон КП из БД (KPSettings, правится в админке). None — если таблицы
    ещё нет или БД недоступна: тогда работаем на дефолтах из kp_defaults."""
    try:
        from .models import KPSettings
        return KPSettings.load()
    except Exception:  # noqa: BLE001
        return None


def _seller_from(tpl):
    if tpl is not None:
        return {
            "name": tpl.seller_name, "address": tpl.seller_address,
            "bank": tpl.bank, "bank_address": tpl.bank_address,
            "account": tpl.account, "swift": tpl.swift,
        }
    return {
        "name": kp_defaults.SELLER_NAME, "address": kp_defaults.SELLER_ADDRESS,
        "bank": kp_defaults.BANK, "bank_address": kp_defaults.BANK_ADDRESS,
        "account": kp_defaults.ACCOUNT, "swift": kp_defaults.SWIFT,
    }


def _delivery_terms(tpl):
    return tpl.delivery_terms if tpl else kp_defaults.DELIVERY_TERMS


def _timeline(tpl):
    raw = tpl.timeline if tpl else kp_defaults.TIMELINE
    return [ln.strip() for ln in (raw or "").splitlines() if ln.strip()]


def _service_center(tpl):
    return tpl.service_center if tpl else kp_defaults.SERVICE_CENTER


def _show_seal(tpl):
    return tpl.show_seal if tpl is not None else True


def _fmt_amount(value):
    """123456.00 -> '123 456' (без копеек, пробел-разделитель тысяч)."""
    if value is None:
        return ""
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return str(value)
    return f"{n:,}".replace(",", " ")


def _fmt_price(value):
    """Цена в валюте: 44326.36 -> '44 326.36', 298000 -> '298 000'.

    Отдельно от _fmt_amount, который округляет до целых. В тенге копейки
    бессмысленны, а вот доллары сравнивают с полем калькулятора, где стоит
    ровно два знака (toFixed(2)) — округлив здесь, мы показали бы 44 326
    против 44 326.36 и снова дали повод думать, что цены разъехались.
    """
    if value is None or value == "":
        return ""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return str(value)
    whole = f"{int(abs(n)):,}".replace(",", " ")
    sign = "-" if n < 0 else ""
    kop = round(abs(n) - int(abs(n)), 2)
    if kop:
        # Десятичная запятая, как в русской типографике и как на странице КП
        # (Intl.NumberFormat('ru-RU')). С точкой одно и то же число выглядело
        # бы в двух форматах документа по-разному.
        return f"{sign}{whole},{int(round(kop * 100)):02d}"
    return f"{sign}{whole}"


def _fmt_iso_date(value):
    """'2026-07-31' -> '31.07.2026'. Пустое/кривое значение — пустая строка."""
    if not value:
        return ""
    try:
        from datetime import date as _date
        return _date.fromisoformat(str(value)).strftime("%d.%m.%Y")
    except (TypeError, ValueError):
        return ""


def _vehicle_title(vehicle):
    """Короткое наименование товара для строки таблицы."""
    if not vehicle:
        return "Транспортное средство"
    parts = []
    head = (vehicle.body_type or "").strip()
    if not head:
        head = " ".join(x for x in [vehicle.brand, vehicle.model] if x).strip()
    if head:
        parts.append(head)
    if vehicle.category and vehicle.category not in head:
        parts.insert(0, vehicle.category)
    if vehicle.year:
        parts.append(str(vehicle.year))
    return " ".join(parts).strip() or "Транспортное средство"


def _vehicle_specs(vehicle):
    """Список пар (label, value) — характеристики для блока под таблицей."""
    if not vehicle:
        return []
    rows = [
        ("Марка / модель", " ".join(x for x in [vehicle.brand, vehicle.model] if x).strip()),
        ("Категория", vehicle.category),
        ("Год выпуска", vehicle.year),
        ("Колёсная формула", vehicle.wheel_formula),
        ("Полная масса, т", vehicle.weight_t),
        ("Грузоподъёмность, т", vehicle.load_capacity_t),
        ("Мощность двигателя, л.с.", vehicle.engine_power_hp),
        ("КПП", vehicle.gearbox),
    ]
    return [(label, value) for label, value in rows if value not in (None, "", 0)]


def _customer_name(customer):
    if not customer:
        return ""
    for attr in ("get_full_name",):
        fn = getattr(customer, attr, None)
        if callable(fn):
            full = fn()
            if full and full.strip():
                return full.strip()
    for attr in ("company_name", "full_name", "name", "phone", "username"):
        val = getattr(customer, attr, "")
        if val:
            return str(val)
    return ""


def _fetch_image(url, max_width=1000):
    """Скачать фото по URL, ужать до max_width и вернуть JPEG в BytesIO.

    Ужимаем, чтобы КП-вложение не весило мегабайты (фото из каталога бывают
    2–3 МБ). При любой ошибке возвращаем None — фото в КП необязательно.
    """
    if not url:
        return None
    try:
        import io
        import requests
        resp = requests.get(url, timeout=8)
        if resp.status_code != 200 or not resp.content:
            return None
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(resp.content))
            img.load()
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            if img.width > max_width:
                h = round(img.height * max_width / img.width)
                img = img.resize((max_width, h), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80, optimize=True)
            buf.seek(0)
            return buf
        except Exception:
            # Pillow недоступен/формат экзотичный — отдаём как есть.
            return io.BytesIO(resp.content)
    except Exception as e:  # noqa: BLE001 — фото в КП необязательно
        log.info("KP: vehicle image fetch failed (%s): %s", url, e)
    return None


def _breakdown_from_rows(deal):
    """Собрать детализацию из построчных DealCalcRow (если заданы в админке).
    Возвращает dict как calc_breakdown, либо None если строк нет."""
    try:
        rows = list(deal.calc_rows.all())
    except Exception:  # noqa: BLE001 — связь может быть недоступна
        return None
    if not rows:
        return None
    from collections import OrderedDict
    groups = OrderedDict()
    total = 0
    for r in rows:
        try:
            total += float(r.amount or 0)
        except (TypeError, ValueError):
            pass
        groups.setdefault(r.group or "", []).append([r.label, r.amount])
    return {"groups": [{"title": g, "rows": rs} for g, rs in groups.items()],
            "total": total}


def _render_breakdown(deal, h, para, pdf):
    """Вывести блок «Расчёт стоимости под ключ».

    Приоритет — построчные строки из админки (DealCalcRow); если их нет —
    JSON deal.calc_breakdown (например, из калькулятора).
    Ожидаемая структура:
        {"groups": [{"title": str, "rows": [[label, amount], ...]}, ...],
         "total": number}
    """
    bd = _breakdown_from_rows(deal) or getattr(deal, "calc_breakdown", None)
    if not isinstance(bd, dict):
        return
    groups = bd.get("groups")
    if not isinstance(groups, list) or not groups:
        return

    h("Расчёт стоимости под ключ", 12)
    for group in groups:
        if not isinstance(group, dict):
            continue
        gtitle = group.get("title")
        if gtitle:
            para(str(gtitle), bold=True)
        for row in group.get("rows", []) or []:
            try:
                label, amount = row[0], row[1]
            except (TypeError, IndexError, KeyError):
                continue
            para(f"•  {label}: {_fmt_amount(amount)} ₸")
        pdf.ln(1)

    total = bd.get("total")
    if total is not None:
        para(f"ИТОГО под ключ: {_fmt_amount(total)} ₸", bold=True)
    pdf.ln(3)


def build_kp_pdf(deal, extras=None):
    """Собрать КП и вернуть содержимое PDF (bytes).

    extras (необязательно) позволяет переопределить поля, которых нет в сделке —
    используется ручным конструктором КП в кабинете менеджера:
        number            — номер в шапке вместо «№ сделки»
        buyer_name        — покупатель
        quantity          — количество единиц техники
        availability_note — строка о наличии («15 единиц в Хоргосе»)
        timeline          — свой список сроков вместо шаблонного
        unit_price_kzt    — цена за единицу для ячейки «Сумма, ₸»; имеет
                            приоритет над vehicle.price_kzt
    """
    from fpdf import FPDF  # ленивый импорт — тянем зависимость только при генерации

    extras = extras or {}

    # fontTools при встраивании шрифта сыпет INFO-логами про subsetting — глушим.
    logging.getLogger("fontTools").setLevel(logging.WARNING)

    tpl = _template()
    seller = _seller_from(tpl)
    vehicle = deal.vehicle
    customer = deal.customer

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font("DejaVu", "", os.path.join(FONT_DIR, "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf"))
    pdf.add_page()
    epw = pdf.epw  # эффективная ширина страницы

    def h(text, size=15):
        pdf.set_x(pdf.l_margin)
        pdf.set_font("DejaVu", "B", size)
        pdf.multi_cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    def para(text, size=10, bold=False):
        pdf.set_x(pdf.l_margin)
        pdf.set_font("DejaVu", "B" if bold else "", size)
        pdf.multi_cell(0, 5, text, new_x="LMARGIN", new_y="NEXT")

    # --- Шапка (фирменный бланк SHACMAN) ---------------------------------
    if os.path.exists(LETTERHEAD):
        try:
            pdf.image(LETTERHEAD, x=pdf.l_margin, w=epw)
            pdf.ln(2)
        except Exception as e:  # noqa: BLE001
            log.info("KP: letterhead embed failed: %s", e)

    # --- Заголовок --------------------------------------------------------
    h("Коммерческое предложение", 17)
    number = extras.get("number") or (f"№ сделки: {deal.pk}" if getattr(deal, "pk", None) else "")
    head_line = f"{number}    " if number else ""
    # Дата выдачи — из документа, если он заморожен (мгновенное КП хранит её
    # в снимке), иначе сегодняшняя. Перевыпуск снимка через месяц не должен
    # молча проставить в старом PDF свежую дату.
    issued = _fmt_iso_date(extras.get("issued_on")) or date.today().strftime("%d.%m.%Y")
    para(f"{head_line}Дата: {issued}")
    name = extras.get("buyer_name") or _customer_name(customer)
    if name:
        para(f"Покупатель: {name}")
    # Срок действия предложения. Цена посчитана по курсу на дату выдачи, и
    # бессрочной быть не может — в бумажных КП компании эта строка тоже есть.
    valid_until = _fmt_iso_date(extras.get("valid_until"))
    if valid_until:
        para(f"Предложение действительно до: {valid_until}", bold=True)
    pdf.ln(3)

    # --- Продавец / реквизиты --------------------------------------------
    h("Продавец", 12)
    para(seller["name"], bold=True)
    para(f"Адрес: {seller['address']}")
    para(f"Банк: {seller['bank']}")
    para(f"Адрес банка: {seller['bank_address']}")
    para(f"Счёт: {seller['account']}")
    para(f"SWIFT: {seller['swift']}")
    pdf.ln(3)

    # --- Товар и цена -----------------------------------------------------
    h("Предмет предложения", 12)
    title = _vehicle_title(vehicle)
    para(title, bold=True)

    # Фото техники из карточки (если есть) — как в оригинальном КП.
    photo_url = ""
    if vehicle:
        photo_url = getattr(vehicle, "image_url", "") or ""
        if not photo_url:
            imgs = getattr(vehicle, "images", None)
            if isinstance(imgs, list) and imgs:
                photo_url = imgs[0]
    if photo_url:
        photo = _fetch_image(photo_url)
        if photo is not None:
            try:
                pdf.image(photo, x=pdf.l_margin, w=90)
                pdf.ln(2)
            except Exception as e:  # noqa: BLE001
                log.info("KP: vehicle image embed failed: %s", e)

    if vehicle and vehicle.extra_info:
        para(vehicle.extra_info)
    pdf.ln(1)

    # Таблица: Кол-во | Цена USD | Цена CNY | Сумма ₸
    try:
        qty = max(1, int(extras.get("quantity") or 1))
    except (TypeError, ValueError):
        qty = 1
    # Приоритет: явно переданная цена за единицу → цена из карточки → сумма
    # сделки. Явный override нужен мгновенному КП (core/kp_instant.py): там
    # ячейка «Сумма, ₸» обязана показывать тот же итог, что и разбивка ниже
    # на этой же странице, а vehicle.price_kzt заводится руками и с расчётом
    # сходится только пока его сводит менеджер. Документ, показывающий два
    # разных итога, хуже документа с приблизительным одним.
    # Цена в КП должна совпадать с итогом калькулятора.
    # Приоритет:
    # 1. Явно переданная цена (для специальных КП)
    # 2. Итог калькулятора (calc_breakdown / DealCalcRow)
    # 3. Старая цена из карточки техники — только если расчёта нет.
    
    raw_kzt = extras.get("unit_price_kzt")

    if raw_kzt is None:
        breakdown = _breakdown_from_rows(deal) or getattr(deal, "calc_breakdown", None)
        if isinstance(breakdown, dict) and breakdown.get("total") is not None:
            raw_kzt = breakdown["total"]

    if raw_kzt is None:
        raw_kzt = getattr(deal, "total_price", None)

    if raw_kzt is None:
        raw_kzt = vehicle.price_kzt if (vehicle and vehicle.price_kzt) else None

    total_kzt = None
    if raw_kzt is not None:
        try:
            # Всё, что попадает в raw_kzt, — цена ЗА ЕДИНИЦУ, поэтому умножаем.
            # Без множителя КП на две машины показывало бы в «Сумма, ₸» цену
            # одной, расходясь со строкой «под ключ» на странице, где
            # количество учтено (kp_instant: breakdown.total * qty).
            total_kzt = float(raw_kzt) * qty
        except (TypeError, ValueError):
            total_kzt = raw_kzt

    # Цены в долларах и юанях тоже переопределяемы. Мгновенное КП передаёт
    # сюда доллары из расчёта (выведенные из юаней по курсу документа), а не
    # vehicle.price_usd: сохранённое в карточке число живёт своей жизнью и с
    # текущим курсом обычно не сходится. Для КП по сделке ничего не меняется —
    # extras там этих ключей не содержит.
    price_usd = _fmt_price(extras.get("price_usd") if extras.get("price_usd") is not None
                           else (vehicle.price_usd if vehicle else None))
    price_cny = _fmt_price(extras.get("price_cny") if extras.get("price_cny") is not None
                           else (vehicle.price_cny if vehicle else None))
    price_kzt = _fmt_amount(total_kzt)
    with pdf.table(
        col_widths=(20, 27, 27, 26),
        text_align=("CENTER", "RIGHT", "RIGHT", "RIGHT"),
        first_row_as_headings=True,
        width=epw,
    ) as table:
        row = table.row()
        for head in ("Кол-во", "Цена, USD", "Цена, CNY", "Сумма, ₸"):
            row.cell(head)
        row = table.row()
        row.cell(str(qty))
        row.cell(price_usd or "по запросу")
        row.cell(price_cny or "—")
        row.cell(price_kzt or "по запросу")
    pdf.ln(2)

    availability = (extras.get("availability_note") or "").strip()
    if availability:
        para(availability)
    pdf.ln(2)

    # --- Характеристики ---------------------------------------------------
    specs = _vehicle_specs(vehicle)
    if specs:
        h("Характеристики", 12)
        for label, value in specs:
            para(f"•  {label}: {value}")
        pdf.ln(3)

    # --- Расчёт стоимости под ключ (из калькулятора) ---------------------
    _render_breakdown(deal, h, para, pdf)

    # --- Условия и сроки поставки ----------------------------------------
    h("Условия поставки", 12)
    para(f"Условия поставки: {extras.get('delivery_terms') or _delivery_terms(tpl)}", bold=True)
    pdf.ln(1)
    steps = extras.get("timeline")
    if isinstance(steps, str):
        steps = [s.strip() for s in steps.splitlines() if s.strip()]
    for step in (steps or _timeline(tpl)):
        para(f"•  {step}")
    pdf.ln(3)

    # --- Сервис-центр -----------------------------------------------------
    h("Сервис и гарантия", 12)
    para(_service_center(tpl))

    # --- Печать и подпись продавца ---------------------------------------
    if _show_seal(tpl) and os.path.exists(SEAL):
        try:
            pdf.ln(4)
            pdf.image(SEAL, x=pdf.l_margin, w=60)
        except Exception as e:  # noqa: BLE001
            log.info("KP: seal embed failed: %s", e)

    out = pdf.output()
    return bytes(out)


def _recipients(deal):
    """Список получателей: явный e-mail для КП + клиент + почта компании
    (без дублей и пустых)."""
    to = []
    for email in (getattr(deal, "kp_email", "") or "",
                  getattr(deal.customer, "email", None) or ""):
        if email and email not in to:
            to.append(email)
    company = _cfg("COMPANY_EMAIL", "") or ""
    if company and company not in to:
        to.append(company)
    return to


def send_kp_for_deal(deal):
    """Собрать КП и отправить письмом. Безопасно: никогда не бросает исключение."""
    try:
        to = _recipients(deal)
        if not to:
            log.info("KP: no recipients for deal %s — skip", deal.pk)
            return False

        pdf_bytes = build_kp_pdf(deal)
        subject = f"Коммерческое предложение — сделка №{deal.pk}"
        title = _vehicle_title(deal.vehicle)
        body = (
            "Здравствуйте!\n\n"
            f"Во вложении — коммерческое предложение по сделке №{deal.pk} "
            f"({title}).\n\n"
            "С уважением,\nChina Motors"
        )
        msg = EmailMessage(
            subject=subject,
            body=body,
            from_email=_cfg("DEFAULT_FROM_EMAIL", None),
            to=to,
        )
        msg.attach(f"KP_deal_{deal.pk}.pdf", pdf_bytes, "application/pdf")
        msg.send(fail_silently=True)
        log.info("KP sent for deal %s to %s", deal.pk, ", ".join(to))
        return True
    except Exception as e:  # noqa: BLE001 — отправка КП не должна ронять создание сделки
        log.warning("KP send failed for deal %s: %s", getattr(deal, "pk", None), e)
        return False


# ============================================================================
#  Ручной конструктор КП (кабинет менеджера) — без привязки к сделке
# ============================================================================

class _ManualVehicle:
    """Техника для КП, собранная вручную или из карточки каталога."""

    def __init__(self, d):
        g = d.get
        self.brand = g("brand", "") or ""
        self.model = g("model", "") or ""
        self.year = g("year") or None
        self.body_type = g("title", "") or ""
        self.category = g("category", "") or ""
        self.city = g("city", "") or ""
        self.extra_info = g("description", "") or ""
        self.weight_t = g("weight_t") or None
        self.wheel_formula = g("wheel_formula", "") or ""
        self.gearbox = g("gearbox", "") or ""
        self.engine_power_hp = g("engine_power_hp") or None
        self.load_capacity_t = g("load_capacity_t") or None
        self.price_usd = g("price_usd") or None
        self.price_cny = g("price_cny") or None
        self.price_kzt = g("price_kzt") or None
        self.image_url = g("image_url", "") or ""
        self.images = g("images") or []


class _ManualDeal:
    """Минимальная «сделка» для генератора: только то, что читает build_kp_pdf."""

    pk = None
    calc_rows = None       # строк расчёта нет — _breakdown_from_rows вернёт None
    kp_email = ""

    def __init__(self, vehicle, total_price=None, breakdown=None):
        self.vehicle = vehicle
        self.customer = None
        self.total_price = total_price
        self.calc_breakdown = breakdown


def _vehicle_dict_from_catalog(vehicle_id):
    """Данные техники из каталога — как основа для ручного КП."""
    from cars.models import Vehicle
    v = Vehicle.objects.filter(pk=vehicle_id).first()
    if not v:
        return None
    return {
        "brand": v.brand, "model": v.model, "year": v.year,
        "title": v.body_type, "category": v.category, "city": v.city,
        "description": v.extra_info,
        "weight_t": v.weight_t, "wheel_formula": v.wheel_formula,
        "gearbox": v.gearbox, "engine_power_hp": v.engine_power_hp,
        "load_capacity_t": v.load_capacity_t,
        "price_usd": v.price_usd, "price_cny": v.price_cny, "price_kzt": v.price_kzt,
        "image_url": v.image_url, "images": v.images,
    }


def build_manual_kp_pdf(spec):
    """Собрать КП из произвольных данных (ручной конструктор).

    spec: {
      vehicle_id?      — взять данные из каталога (поля ниже их переопределяют),
      title, description, brand, model, year, category, wheel_formula,
      weight_t, gearbox, engine_power_hp, load_capacity_t, image_url,
      price_usd, price_cny, price_kzt,
      quantity, buyer_name, number, availability_note,
      delivery_terms, timeline (строка/список),
      breakdown  — {"groups": [...], "total": n} для блока расчёта
    }
    """
    data = {}
    if spec.get("vehicle_id"):
        data = _vehicle_dict_from_catalog(spec["vehicle_id"]) or {}
    # Явно переданные поля важнее данных из каталога.
    for key in ("title", "description", "brand", "model", "year", "category",
                "city", "wheel_formula", "weight_t", "gearbox", "engine_power_hp",
                "load_capacity_t", "image_url", "price_usd", "price_cny", "price_kzt"):
        if spec.get(key) not in (None, ""):
            data[key] = spec[key]

    vehicle = _ManualVehicle(data)
    deal = _ManualDeal(vehicle, total_price=data.get("price_kzt"),
                       breakdown=spec.get("breakdown"))
    extras = {
        "number": spec.get("number") or "",
        "buyer_name": spec.get("buyer_name") or "",
        "quantity": spec.get("quantity") or 1,
        "availability_note": spec.get("availability_note") or "",
        "delivery_terms": spec.get("delivery_terms") or "",
        "timeline": spec.get("timeline"),
    }
    return build_kp_pdf(deal, extras)


def send_manual_kp(spec, recipients):
    """Отправить ручное КП письмом. Возвращает True/False."""
    to = [e.strip() for e in (recipients or []) if e and e.strip()]
    if not to:
        return False
    try:
        pdf_bytes = build_manual_kp_pdf(spec)
        title = _vehicle_title(_ManualVehicle(spec))
        msg = EmailMessage(
            subject=spec.get("subject") or "Коммерческое предложение — China Motors",
            body=("Здравствуйте!\n\nВо вложении — коммерческое предложение"
                  f"{(' по позиции ' + title) if title else ''}.\n\n"
                  "С уважением,\nChina Motors"),
            from_email=_cfg("DEFAULT_FROM_EMAIL", None),
            to=to,
        )
        msg.attach("KP.pdf", pdf_bytes, "application/pdf")
        msg.send(fail_silently=True)
        log.info("Manual KP sent to %s", ", ".join(to))
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("Manual KP send failed: %s", e)
        return False
