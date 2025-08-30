import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from cars.models import Vehicle


class Command(BaseCommand):
    help = "Импорт грузовой техники из .xlsx в таблицу Vehicle"

    def add_arguments(self, parser):
        parser.add_argument("xlsx_path", type=str, help="Путь к .xlsx файлу")

    def handle(self, *args, **opts):
        path = opts["xlsx_path"]
        try:
            df = pd.read_excel(path)
        except Exception as e:
            raise CommandError(f"Не удалось прочитать файл: {e}")

        # Нормализуем названия столбцов (без учета регистра/пробелов)
        cols = {str(c).strip().lower(): c for c in df.columns}

        def pick(*variants):
            for v in variants:
                key = v.lower()
                if key in cols:
                    return cols[key]
            return None

        c_name = pick("name", "название", "модель", "наименование")
        c_brand = pick("brand", "бренд", "марка")
        c_model = pick("model", "модель")
        c_year = pick("year", "год", "год выпуска")
        c_body = pick("body_type", "тип кузова", "тип")
        c_price = pick("price_usd", "цена, $", "цена usd", "цена $", "price")
        c_mileage = pick("mileage_km", "пробег", "пробег, км")
        c_image = pick("image_url", "фото", "image", "image url", "изображение")

        created, updated = 0, 0

        for _, row in df.iterrows():
            name = str(row.get(c_name, "")).strip() if c_name else ""
            brand = str(row.get(c_brand, "")).strip() if c_brand else ""
            model = str(row.get(c_model, "")).strip() if c_model else ""
            year = row.get(c_year)
            body_type = str(row.get(c_body, "")).strip() if c_body else ""
            price_usd = row.get(c_price)
            mileage_km = row.get(c_mileage)
            image_url = str(row.get(c_image, "")).strip() if c_image else ""

            obj, is_created = Vehicle.objects.update_or_create(
                name=name or f"{brand} {model}".strip(),
                defaults=dict(
                    brand=brand,
                    model=model,
                    year=int(year) if pd.notna(year) else None,
                    body_type=body_type,
                    price_usd=float(price_usd) if pd.notna(price_usd) else None,
                    mileage_km=int(mileage_km) if pd.notna(mileage_km) else None,
                    image_url=image_url,
                ),
            )
            created += 1 if is_created else 0
            updated += 0 if is_created else 1

        self.stdout.write(self.style.SUCCESS(
            f"Готово: создано {created}, обновлено {updated}. Всего: {len(df)}"
        ))
