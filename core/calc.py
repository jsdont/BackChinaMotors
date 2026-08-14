"""Расчёт стоимости под ключ — один источник формулы на весь бэкенд.

До этого модуля формула жила только во фронтенде (china-motors-site,
js/calculator.js). Мгновенное КП должно показывать ТЕ ЖЕ суммы, что
калькулятор, иначе человек, который посчитал сам, а потом скачал КП,
увидит два разных итога по одной машине и не поверит ни одному.

Поэтому здесь портирована ровно та логика, что в calculator.js:
профиль техники → ставка пошлины → НДС → пакет расходов → доставка →
утильсбор и регистрация. Ставки и сборы берутся не из констант, а из
CalcConfig (та же запись, что отдаётся калькулятору эндпоинтом
/api/calc-config/), поэтому правка в админке меняет обе стороны сразу.

Вызывается из двух мест, и только из них:
  core.kp_instant.build_instant_kp      → JSON для страницы КП
  core.kp_instant.build_instant_kp_pdf  → официальный PDF
Дублировать формулу в третьем месте нельзя — вся суть модуля в этом.
"""

import logging

log = logging.getLogger(__name__)


# ============================================================================
#  Профиль техники
#
#  Калькулятор определяет профиль по <select id="type">, а не по полям
#  каталога. Человек, пришедший с карточки, попадает туда так:
#
#    catalog.js canonBody(...)  → 'Самосвал' | 'Тягач' | 'Полуприцеп' |
#                                 'Прицеп' | 'Кран' | 'Спец. техника'
#    calculator.js              → ищет <option> по ТОЧНОМУ совпадению текста
#    detectVehicleProfile(value)→ профиль
#
#  Мы повторяем эту цепочку целиком, включая её неочевидные места (см.
#  комментарии ниже), потому что задача модуля — совпасть с калькулятором,
#  а не посчитать «как правильнее».
# ============================================================================

# (текст <option>, value) — в том же порядке, что в calculator.html.
# Первый элемент важен: на него откатывается select, когда точного
# совпадения по тексту не нашлось.
TYPE_OPTIONS = [
    ("Прицепы", "TRAILER"),
    ("Полуприцепы", "SEMITRAILER"),
    ("Самосвал", "TRUCK"),
    ("Тягач", "TRACTOR_N3"),
    ("Спец. техника", "SPECIAL"),
    ("Кран", "SPECIAL"),
    ("Манипулятор", "SPECIAL"),
    ("Миксер", "SPECIAL"),
    ("Бензовоз", "SPECIAL"),
    ("Автовышка", "SPECIAL"),
    ("Ассенизатор", "SPECIAL"),
    ("Рефрижератор", "TRUCK"),
    ("Автофургон", "TRUCK"),
]


def canon_body(title, raw):
    """Порт canonBody() из catalog.js — как карточка называет тип техники."""
    s = f"{title or ''} {raw or ''}".lower()
    if "самосвал" in s:
        return "Самосвал"
    if "тягач" in s:
        return "Тягач"
    if "полуприцеп" in s:
        return "Полуприцеп"
    if "прицеп" in s:
        return "Прицеп"
    if "кран" in s:
        return "Кран"
    return "Спец. техника"


def resolve_type(vehicle):
    """(value, text) выбранного <option> — как его выставил бы калькулятор.

    Тонкость, которую нельзя «исправить» в одностороннем порядке: canonBody
    отдаёт «Полуприцеп» и «Прицеп» в единственном числе, а в списке они
    стоят во множественном («Полуприцепы», «Прицепы»). Точного совпадения
    нет, select остаётся на первом пункте, и оба вида прицепов уезжают в
    профиль TRUCK — со своим утильсбором и первичной регистрацией, которых
    у прицепа быть не должно.

    Это расхождение живёт во фронтенде и сегодня; повторяем его здесь
    намеренно, чтобы КП и калькулятор показывали одно число. Чинить нужно
    в обоих местах разом и отдельной задачей — иначе документ разойдётся с
    тем, что клиент только что видел на калькуляторе.
    """
    title = " ".join(x for x in [vehicle.brand, vehicle.model, vehicle.body_type] if x).strip()
    raw = vehicle.category or vehicle.body_type or ""
    canon = canon_body(title, raw)

    for text, value in TYPE_OPTIONS:
        if text == canon:
            return value, text
    return TYPE_OPTIONS[0][1], TYPE_OPTIONS[0][0]


def detect_profile(type_value):
    """Порт detectVehicleProfile(). Значение TRAILER сюда не попадает как
    профиль: в оригинале оно тоже проваливается в TRUCK (см. resolve_type)."""
    if type_value == "CAR":
        return "CAR"
    if type_value == "SEMITRAILER":
        return "TRAILER"
    if type_value == "TRACTOR_N3":
        return "TRACTOR_N3"
    if type_value == "SPECIAL":
        return "SPECIAL"
    return "TRUCK"


# ============================================================================
#  Ставки
# ============================================================================

def duty_rate(profile, type_text, cfg):
    """Порт getDutyRate(). type_text — видимый текст пункта списка."""
    t = (type_text or "").lower()
    rules = cfg.get("duty_rules") or {}

    # Гусеничный экскаватор и фронтальный погрузчик — 0%. В списке
    # калькулятора таких пунктов нет, поэтому на практике эти ветки не
    # срабатывают; оставлены, чтобы порт совпадал с оригиналом построчно.
    if "экскаватор" in t and "гусен" in t:
        return 0.0
    if "погрузчик" in t and "фронт" in t:
        return 0.0

    # Остальная «спецтехника» (манипулятор, автовышка, миксер) — это
    # грузовик с надстройкой, ТН ВЭД 8704, пошлина как у грузового.
    if "кран" in t:
        return float(rules.get("CRANE") or 0.08)
    if "трал" in t:
        return float(rules.get("TRAL") or 0.09)
    if profile == "TRAILER":
        return 0.10
    return float(rules.get("DEFAULT") or 0.10)


def util_coef_by_weight(weight_t, profile):
    """Порт getUtilCoefByWeight()."""
    # Седельный тягач считается по классу автопоезда 20–50 т независимо от
    # собственной массы — подтверждено реальными таможенными расчётами.
    if profile == "TRACTOR_N3":
        return 11.0
    if weight_t <= 2.5:
        return 3.5
    if weight_t <= 3.5:
        return 7.5
    if weight_t <= 5:
        return 7.5
    if weight_t <= 8:
        return 8.0
    if weight_t <= 12:
        return 9.5
    if weight_t <= 20:
        return 10.5
    return 20.5


def first_reg_rate(age, profile, intl):
    """Порт getFirstRegRateByAge()."""
    if profile == "TRAILER":
        return 0
    # Международник (N3) до 7 лет — льгота до 01.01.2028, ст. 830 НК РК.
    if profile == "TRACTOR_N3" and intl and age <= 7:
        return 0
    if age <= 1:
        return 0.25
    if age == 2:
        return 240
    if profile == "TRACTOR_N3":
        return 350 if 3 <= age <= 6 else 2500
    return 350 if 3 <= age <= 4 else 2500


def expense_package(profile, rate, cfg):
    """Порт getExpensePackage() — ветка спецтехники/грузовых.

    Легковые (M1) сюда не попадают: в каталоге China Motors их нет, а
    угадывать объём двигателя и тип топлива по карточке нельзя — утильсбор
    для M1 считается по объёму. Если легковые появятся, ветку нужно
    добавить сюда, а не в вызывающий код.
    """
    fees = cfg.get("fees") or {}
    diesel = cfg.get("diesel") or {}

    diesel_sum = float(diesel.get("liters") or 200) * float(diesel.get("price_kzt_per_l") or 335)
    declarant_sum = 250 * rate                      # декларант на границе, 250 $
    svh_sum = 0 if profile == "TRAILER" else float(fees.get("svh") or 91000)

    mandatory = [
        ("ЭПТС", float(fees.get("eptc") or 0)),
        ("СБКТС", float(fees.get("sbkts") or 0)),
        ("Кнопка SOS", float(fees.get("sos") or 0)),
        ("Таможенный сбор", float(fees.get("customs_fee") or 0)),
        ("Услуги Брокера на СВХ", float(fees.get("broker_service") or 0)),
        ("СВХ", svh_sum),
        ("Брокер на границе", declarant_sum),
        ("Коридор", float(fees.get("red_corridor") or 0)),
    ]

    # «Доставка» — это водитель, топливо, страховка и платная дорога, ровно
    # так эти статьи сгруппированы в реальных счетах на растаможку.
    # Отдельной строки «доставка до Алматы» здесь нет намеренно: в счетах
    # её не существует, и клиент платил бы за доставку дважды.
    delivery = [
        ("Водитель", float(fees.get("driver") or 0)),
        ("Солярка", diesel_sum),
        ("AdBlue", float(fees.get("adblue") or 0)),
        ("Страховка", float(fees.get("insurance") or 0)),
        ("Платная дорога", float(fees.get("toll_road") or 0)),
    ]
    return {"mandatory": mandatory, "delivery": delivery}


def current_mrp(cfg):
    """Порт getCurrentMRP()."""
    from datetime import date
    year = cfg.get("current_year") or date.today().year
    table = cfg.get("mrp_by_year") or {}
    return float(table.get(str(year)) or table.get(year) or 4325)


# ============================================================================
#  Расчёт
# ============================================================================

def _num(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


# ============================================================================
#  Цена техники в долларах
#
#  Порт js/calculator.js, строки 200-206 и 807-809. Читать вместе с ними:
#
#      const CNY_USD_MARGIN = 0.02;
#      function getCnyUsdRate(usdKztRate, cnyKztRate) {
#        return (usdKztRate / cnyKztRate) - CNY_USD_MARGIN;
#      }
#      ...
#      if (URL_PARAMS.priceCny && $('#basePrice')) {
#        const cnyUsdRate = getCnyUsdRate(LIVE_USD_KZT_RATE, LIVE_CNY_KZT_RATE);
#        $('#basePrice').value = (URL_PARAMS.priceCny / cnyUsdRate).toFixed(2);
#      } else if (URL_PARAMS.price && $('#basePrice')) {
#        $('#basePrice').value = URL_PARAMS.price;
#      }
#
#  Три вещи, которые здесь легко потерять и каждая из которых меняет цену:
#
#  1. ЮАНИ ГЛАВНЕЕ. Если у карточки есть price_cny, доллары СЧИТАЮТСЯ из
#     юаней, а сохранённый price_usd не используется вовсе. Он остаётся в
#     базе как справочная величина и с текущим курсом обычно не сходится.
#     Раньше бэкенд брал именно его — отсюда и было расхождение с
#     калькулятором на той же машине.
#  2. МАРЖА 0.02. Это не курс НБ РК, а запас на колебание при подтверждении
#     цены, вычитаемый из кросс-курса. Без него доллары выходят меньше.
#  3. ОКРУГЛЕНИЕ ДО КОПЕЕК. toFixed(2) на фронте не косметика: округлённое
#     число ложится в поле и становится БАЗОЙ расчёта. Считать от полного
#     float значит разойтись с калькулятором в последних разрядах.
# ============================================================================

CNY_USD_MARGIN = 0.02


def cny_usd_rate(usd_kzt, cny_kzt):
    """Кросс-курс юань→доллар из двух курсов НБ РК к тенге, минус маржа."""
    return (usd_kzt / cny_kzt) - CNY_USD_MARGIN


def resolve_price(vehicle, rates):
    """Цена техники в долларах и юанях — ровно как её видит калькулятор.

    Возвращает {"usd": float, "cny": float|None}. usd округлён до копеек:
    именно это число становится базой расчёта, как и на фронте.
    """
    cny = _num(vehicle.price_cny)
    usd_kzt = float(rates["usd_kzt"])
    cny_kzt = float(rates["cny_kzt"])

    if cny and usd_kzt and cny_kzt:
        cross = cny_usd_rate(usd_kzt, cny_kzt)
        if cross > 0:
            return {"usd": round(cny / cross, 2), "cny": cny}

    # Юаней нет (или кросс-курс вырожден) — тогда работает сохранённый USD,
    # как и во второй ветке на фронте.
    return {"usd": _num(vehicle.price_usd), "cny": cny or None}


def load_config():
    """Настройки калькулятора из админки — та же запись, что уходит на
    фронтенд через /api/calc-config/."""
    from .models import CalcConfig
    return CalcConfig.load().to_config()


class RatesUnavailable(RuntimeError):
    """Живого курса НБ РК нет — коммерческое предложение не выпускается."""


def live_rates(cfg=None):
    """Курс НБ РК на момент генерации. Бросает RatesUnavailable, если его нет.

    Раньше здесь стоял тихий откат на запасной курс из CalcConfig, и это
    оказалось хуже отказа. Запасная пара 493.11 / 68.50 даёт по той же
    формуле 41 512 $ там, где живая 465.19 / 68.99 даёт 44 326 $ — разница
    7% на ровном месте. В документе при этом не было ни слова о том, что
    курс ненастоящий: КП выглядело обычным и называло цену, которой никто
    не подтверждал. Через два дня после деплоя это и произошло.

    Запасной курс остаётся уместным на калькуляторе — там человек прикидывает
    и видит, какой курс подставлен. КП же обещает цену, поэтому без живого
    курса оно просто не выдаётся (см. InstantKPView: 503 и внятный текст).
    """
    try:
        # get_rates() держит общий кэш с /api/rates/ и сама не бросает.
        from cars.views import get_rates
        data = get_rates()
    except Exception as e:  # noqa: BLE001
        raise RatesUnavailable(f"источник курса недоступен: {e}") from e

    usd, cny = data.get("usd_kzt"), data.get("cny_kzt")
    if not usd or not cny:
        raise RatesUnavailable(data.get("error") or "НБ РК не отдал курс USD/CNY")
    return {"usd_kzt": float(usd), "cny_kzt": float(cny)}


def compute_breakdown(vehicle, cfg=None, rates=None):
    """Разбивка стоимости под ключ по карточке техники.

    Возвращает ту же структуру, что LAST_CALC_BREAKDOWN в calculator.js и
    что ждёт страница КП:

        {"currency": {"usd_kzt": n, "cny_kzt": n},
         "groups": [{"title": str, "rows": [[label, amount], ...]}, ...],
         "total": n}

    Суммы округлены до тенге: копейки в коммерческом предложении не имеют
    смысла, а несведённые дробные части дали бы расхождение итога со
    суммой строк на единицы тенге.
    """
    cfg = cfg or load_config()
    rates = rates or live_rates(cfg)

    rate = float(rates["usd_kzt"])
    cny_rate = float(rates["cny_kzt"])
    taxes = cfg.get("taxes") or {}
    vat_rate = float(taxes.get("vat") or 0.16)

    type_value, type_text = resolve_type(vehicle)
    profile = detect_profile(type_value)
    duty = duty_rate(profile, type_text, cfg)

    # Цена — единственная функция resolve_price() на весь бэкенд, порт
    # калькулятора. Здесь её не пересчитывают и не поправляют.
    price = resolve_price(vehicle, rates)
    price_usd = price["usd"]

    fees = cfg.get("fees") or {}
    customs_fee = float(fees.get("customs_fee") or 25950)

    base = price_usd * rate
    duty_sum = base * duty
    # Акциз в базу НДС не входит: в подтверждённых таможенных расчётах
    # заказчика отдельной строки акциза нет.
    vat_sum = (base + duty_sum + customs_fee) * vat_rate

    pkg = expense_package(profile, rate, cfg)

    weight_t = _num(vehicle.weight_t)
    mrp = current_mrp(cfg)
    from datetime import date
    current_year = cfg.get("current_year") or date.today().year
    age = max(0, int(current_year) - int(vehicle.year)) if vehicle.year else 0

    util_sum = 0.0 if profile == "TRAILER" or not weight_t else 50 * mrp * util_coef_by_weight(weight_t, profile)

    # Удостоверение международного перевозчика: в калькуляторе галочка
    # включена по умолчанию, и на неё опирается льгота для тягачей. По
    # карточке каталога узнать этот факт нельзя, поэтому берём то же
    # значение по умолчанию — иначе КП насчитает тягачу первичку, которой
    # калькулятор на том же экране не показал.
    reg_sum = first_reg_rate(age, profile, intl=True) * mrp
    plate_sum = 0.0 if profile == "TRAILER" else float(fees.get("plate") or 0)

    r = lambda x: int(round(x))  # noqa: E731

    util_rows = []
    if plate_sum > 0:
        util_rows.append(["Госномер и техпаспорт", r(plate_sum)])
    if reg_sum > 0:
        util_rows.append(["Первичная регистрация", r(reg_sum)])
    if util_sum > 0:
        label = f"Утилизационный сбор ({_fmt_weight(weight_t)} т)"
        util_rows.append([label, r(util_sum)])

    groups = [
        {"title": "Таможенная стоимость и платежи", "rows": [
            ["ТС в тенге", r(base)],
            [f"Пошлина ({round(duty * 100)}%)", r(duty_sum)],
            ["НДС", r(vat_sum)],
        ]},
        {"title": "Дополнительные расходы",
         "rows": [[label, r(amount)] for label, amount in pkg["mandatory"]]},
        {"title": "Доставка и граница",
         "rows": [[label, r(amount)] for label, amount in pkg["delivery"]]},
        {"title": "Утильсбор и регистрация", "rows": util_rows},
    ]

    # Итог — сумма ВЫВЕДЕННЫХ строк, а не параллельно посчитанное число.
    # Иначе округление строк и округление итога разойдутся, и документ
    # покажет сумму, которая не сходится со своими же строками.
    total = sum(amount for g in groups for _, amount in g["rows"])

    return {
        "currency": {"usd_kzt": rate, "cny_kzt": cny_rate},
        # Цена едет вместе с разбивкой, а не считается второй раз рядом:
        # доллары выведены из юаней по тому же курсу, что и вся разбивка,
        # и разъехаться с ней уже не могут.
        "price": {"usd": price["usd"], "cny": price["cny"]},
        "groups": groups,
        "total": total,
    }


def _fmt_weight(weight_t):
    """25.0 -> '25', 21.5 -> '21.5' — как в подписи строки утильсбора."""
    if weight_t == int(weight_t):
        return str(int(weight_t))
    return str(weight_t)
