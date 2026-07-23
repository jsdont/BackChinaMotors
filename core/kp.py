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

# --- Фиксированная часть КП (значения по умолчанию — из КП Shaanxi). ----------
DEFAULT_SELLER = {
    "name": "SHAANXI HEAVY DUTY AUTOMOBILE IMPORT AND EXPORT CO., LTD",
    "address": (
        "CHINA, XIAN CITY, PROVINCE SHAANQI, JINGWEI INDUSTRIAL DISTRICT, "
        "SHAANQI AVE, ADMINISTRATIVE CENTER BLDG, 1 APT"
    ),
    "bank": "CHINA ZHESHANG BANK XI'AN BRANCH",
    "bank_address": (
        "TAIHUA JINMAO INTERNATIONAL. NO. 16. FENGHUI SOUTH ROAD, "
        "YANTA DISTRICT, XIAN CITY, SHAANXI PROVINCE"
    ),
    "account": "7910000011420100067269 (USD)",
    "swift": "ZJCBCN2NXXX",
}

DEFAULT_DELIVERY_TERMS = "DAP, СВХ НУР ЖОЛЫ, КАЗАХСТАН."

DEFAULT_TIMELINE = [
    "Экспортная декларация и регистрация документов в таможенном органе Китая — 1 день.",
    "Постановка на электронную очередь для выезда из КПП Хоргос (Китай) — 1 день.",
    "Доставка до СВХ Нур Жолы, Казахстан — 1 день.",
    "Доставка до лаборатории (установка кнопки СОС, СБКТС и ЭПТС) и СВХ Алматы — 1 день.",
    "Регистрация и утверждение СБКТС — 2 дня.",
    "Проверка на соответствие экологическим стандартам ЕАЭС ЕВРО-5 — 3 дня.",
    "Подача пакета документов в ЦЭД, оплата НДС и пошлины — 2 дня.",
    "Подача документов в АО «Жасыл Даму» и оплата утильсбора — 1 день.",
    "Утверждённый ЭПТС — 1 день.",
    "Авто ЦОН — 1 день.",
]

DEFAULT_SERVICE_CENTER = (
    "Шахман Центр в Алматы (сервис-центр): ТОО «NOMADCORE», БИН 250440006291. "
    "Адрес: Казахстан, Алматинская область, Карасайский район, с.о. Әйтей, "
    "село Айтей, КХ АКХ Ленинский, строение 1995, индекс 040900."
)


def _cfg(name, default):
    return getattr(settings, name, default)


def _seller():
    s = dict(DEFAULT_SELLER)
    s.update(_cfg("KP_SELLER", {}) or {})
    return s


def _fmt_amount(value):
    """123456.00 -> '123 456' (без копеек, пробел-разделитель тысяч)."""
    if value is None:
        return ""
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return str(value)
    return f"{n:,}".replace(",", " ")


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


def build_kp_pdf(deal):
    """Собрать КП по сделке и вернуть содержимое PDF (bytes)."""
    from fpdf import FPDF  # ленивый импорт — тянем зависимость только при генерации

    # fontTools при встраивании шрифта сыпет INFO-логами про subsetting — глушим.
    logging.getLogger("fontTools").setLevel(logging.WARNING)

    seller = _seller()
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
    para(f"№ сделки: {deal.pk}    Дата: {date.today().strftime('%d.%m.%Y')}")
    name = _customer_name(customer)
    if name:
        para(f"Покупатель: {name}")
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
    if vehicle and getattr(vehicle, "image_url", ""):
        photo = _fetch_image(vehicle.image_url)
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
    price_usd = _fmt_amount(vehicle.price_usd) if vehicle else ""
    price_cny = _fmt_amount(vehicle.price_cny) if vehicle else ""
    price_kzt = _fmt_amount(vehicle.price_kzt if (vehicle and vehicle.price_kzt) else deal.total_price)
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
        row.cell("1")
        row.cell(price_usd or "по запросу")
        row.cell(price_cny or "—")
        row.cell(price_kzt or "по запросу")
    pdf.ln(3)

    # --- Характеристики ---------------------------------------------------
    specs = _vehicle_specs(vehicle)
    if specs:
        h("Характеристики", 12)
        for label, value in specs:
            para(f"•  {label}: {value}")
        pdf.ln(3)

    # --- Условия и сроки поставки ----------------------------------------
    h("Условия поставки", 12)
    para(f"Условия поставки: {_cfg('KP_DELIVERY_TERMS', DEFAULT_DELIVERY_TERMS)}", bold=True)
    pdf.ln(1)
    for step in _cfg("KP_TIMELINE", DEFAULT_TIMELINE):
        para(f"•  {step}")
    pdf.ln(3)

    # --- Сервис-центр -----------------------------------------------------
    h("Сервис и гарантия", 12)
    para(_cfg("KP_SERVICE_CENTER", DEFAULT_SERVICE_CENTER))

    # --- Печать и подпись продавца ---------------------------------------
    if _cfg("KP_SHOW_SEAL", True) and os.path.exists(SEAL):
        try:
            pdf.ln(4)
            pdf.image(SEAL, x=pdf.l_margin, w=60)
        except Exception as e:  # noqa: BLE001
            log.info("KP: seal embed failed: %s", e)

    out = pdf.output()
    return bytes(out)


def _recipients(deal):
    """Список получателей: клиент + почта компании (без дублей и пустых)."""
    to = []
    email = getattr(deal.customer, "email", None)
    if email:
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
