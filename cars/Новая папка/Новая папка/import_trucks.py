# cars/management/commands/import_trucks.py
from django.core.management.base import BaseCommand
from cars.models import Vehicle
import pandas as pd

# Подстрой названия колонок под свою Excel-таблицу
COLS = {
    'name': ['Модель', 'Name', 'Модель/Комплектация'],
    'brand': ['Бренд', 'Brand'],
    'year': ['Год', 'Year'],
    'body_type': ['Тип', 'Body'],
    'base_price_usd': ['Цена_$', 'USD', 'Price'],
    'image_url': ['Image', 'Картинка', 'Фото'],
    'description': ['Описание', 'Description'],
    'customs_fixed_usd': ['ТС_$', 'Customs_fixed'],
    'duty_pct': ['Пошлина_%', 'Duty_%'],
    'vat_pct': ['НДС_%', 'VAT_%'],
}

def pick(row, keys, default=None, as_int=False, as_float=False):
    for k in keys:
        if k in row and pd.notna(row[k]):
            val = row[k]
            if as_int:
                try: return int(val)
                except: return default
            if as_float:
                try: return float(val)
                except: return default
            return str(val).strip()
    return default

class Command(BaseCommand):
    help = "Импорт грузовой техники из Excel"

    def add_arguments(self, parser):
        parser.add_argument('path', type=str, help='Путь к .xlsx')

    def handle(self, *args, **opts):
        df = pd.read_excel(opts['path'])
        created = 0
        for _, r in df.iterrows():
            row = r.to_dict()
            name = pick(row, COLS['name']) or ''
            if not name:
                continue
            defaults = {
                'brand': pick(row, COLS['brand'], '') or '',
                'year': pick(row, COLS['year'], None, as_int=True),
                'body_type': pick(row, COLS['body_type'], '') or '',
                'base_price_usd': pick(row, COLS['base_price_usd'], 0, as_float=True) or 0,
                'image_url': pick(row, COLS['image_url'], '') or '',
                'description': pick(row, COLS['description'], '') or '',
                'customs_fixed_usd': pick(row, COLS['customs_fixed_usd'], None, as_float=True),
                'duty_pct': pick(row, COLS['duty_pct'], 10, as_float=True) or 10,
                'vat_pct': pick(row, COLS['vat_pct'], 12, as_float=True) or 12,
            }
            Vehicle.objects.update_or_create(name=name, year=defaults['year'], defaults=defaults)
            created += 1
        self.stdout.write(self.style.SUCCESS(f'Импортировано/обновлено: {created}'))
