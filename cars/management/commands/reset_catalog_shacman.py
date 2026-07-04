from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand

from cars.models import Vehicle

# Наценка в юанях, прибавляется к закупочной цене поставщика.
MARGIN_CNY = Decimal("14000")

# Курс для расчёта справочной цены в USD (используется только для
# автоподстановки в калькулятор на сайте, не показывается покупателю).
CNY_TO_USD = Decimal("7.2")

# (name, brand, model, year, body_type, base_price_cny)
VEHICLES = [
    ("Бетоносмеситель Shacman X3000 10 м³ Евро 5", "Shacman", "X3000", None, "Миксер", "344000"),
    ("Манипулятор Shacman L3000 6.3т 4×2 Евро 5", "Shacman", "L3000", None, "Манипулятор", "284000"),
    ("Манипулятор Shacman X3000 12т 6×4 Евро 5", "Shacman", "X3000", None, "Манипулятор", "431000"),
    ("Тягач Shacman X3000 4×2 460 л.с. механика Евро 5", "Shacman", "X3000", None, "Тягач", "284000"),
    ("Тягач Shacman X3000 6×6 Евро 5", "Shacman", "X3000", None, "Тягач", "357000"),
    ("Самосвал Shacman X3000 6×4 385 л.с. Евро 5", "Shacman", "X3000", None, "Самосвал", "293000"),
    ("Самосвал Shacman X3000 8×4 Евро 5", "Shacman", "X3000", None, "Самосвал", "344000"),
    ("Тягач Shacman X5000 4×2 автомат, задние 4 пневмоподушки Евро 5", "Shacman", "X5000", None, "Тягач", "268000"),
    ("Тягач Shacman X5000 6×4 механика, на рессорах Евро 5", "Shacman", "X5000", None, "Тягач", "346000"),
    ("Тягач Shacman X6000 4×2 автомат, задние 4 пневмоподушки Евро 5", "Shacman", "X6000", None, "Тягач", "372000"),
    ("Тягач Shacman X6000 6×4 автомат, на рессорах", "Shacman", "X6000", 2023, "Тягач", "320000"),
    ("Тягач Shacman X6000 6×4 автомат, задние 8 пневмоподушек Евро 5", "Shacman", "X6000", None, "Тягач", "407000"),
]


class Command(BaseCommand):
    help = (
        "Полностью заменяет каталог техники на фиксированный список Shacman "
        "(наценка +14000 CNY). Удаляет ВСЕ существующие записи Vehicle."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Подтвердить удаление всех текущих записей без доп. вопроса.",
        )

    def handle(self, *args, **opts):
        total_before = Vehicle.objects.count()

        if not opts["yes"]:
            answer = input(
                f"Будут удалены ВСЕ текущие записи техники ({total_before} шт.) "
                f"и созданы {len(VEHICLES)} новых. Продолжить? [y/N]: "
            )
            if answer.strip().lower() != "y":
                self.stdout.write(self.style.WARNING("Отменено."))
                return

        Vehicle.objects.all().delete()

        created = 0
        for name, brand, model, year, body_type, base_cny in VEHICLES:
            price_cny = Decimal(base_cny) + MARGIN_CNY
            price_usd = (price_cny / CNY_TO_USD).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )

            Vehicle.objects.create(
                name=name,
                brand=brand,
                model=model,
                year=year,
                body_type=body_type,
                price_cny=price_cny,
                price_usd=price_usd,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Готово: удалено {total_before}, создано {created}."
        ))
