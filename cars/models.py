# cars/models.py
from django.db import models

class Vehicle(models.Model):
    name = models.CharField(max_length=255, db_index=True)         # Модель / название
    brand = models.CharField(max_length=120, blank=True)           # Бренд
    year = models.PositiveIntegerField(null=True, blank=True)      # Год
    body_type = models.CharField(max_length=120, blank=True)       # Тип (тягач/борт/самосвал...)
    base_price_usd = models.DecimalField(max_digits=12, decimal_places=2)  # Цена, $
    image_url = models.URLField(blank=True)                        # Картинка (можно пусто)
    description = models.TextField(blank=True)                     # Описание (опционально)

    # Поля, которые могут пригодиться для калькулятора как пресеты
    customs_fixed_usd = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    duty_pct = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    vat_pct = models.DecimalField(max_digits=5, decimal_places=2, default=12)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        y = f" {self.year}" if self.year else ""
        return f"{self.name}{y}"
