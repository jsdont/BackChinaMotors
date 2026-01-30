from django.db import models


class Vehicle(models.Model):
    name = models.CharField(max_length=255, blank=True, default="")
    brand = models.CharField(max_length=120, blank=True, default="")
    model = models.CharField(max_length=120, blank=True, default="")
    year = models.PositiveIntegerField(null=True, blank=True)
    body_type = models.CharField(max_length=120, blank=True, default="")
    weight_t = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Полная масса ТС в тоннах"
    )
    price_usd = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    mileage_km = models.IntegerField(null=True, blank=True)
    image_url = models.URLField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        base = self.name or f"{self.brand} {self.model}".strip()
        return base or f"Vehicle #{self.pk}"
