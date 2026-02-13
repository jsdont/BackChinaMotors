from django.db import models
from catalog.models import Product

class CalculatorLead(models.Model):
    from django.conf import settings

    calc_id = models.CharField(max_length=32, unique=True)
    source = models.CharField(max_length=32)  # calculator / contacts / tawk
    name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=64, blank=True)
    message = models.TextField()
    page_url = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.calc_id

    STATUS_CHOICES = [
        ("new", "New"),
        ("in_progress", "In Progress"),
        ("won", "Won"),
        ("lost", "Lost"),
    ]


    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads"
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_leads"
    )
    profit_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    from django.core.exceptions import ValidationError

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.status == "won":
            if not self.product:
                raise ValidationError("Won deal must have a product selected.")

            # фиксируем прибыль в момент продажи
            if not self.profit_snapshot:
                self.profit_snapshot = self.product.profit

    def save(self, *args, **kwargs):
        if self.status == "won" and self.product:
            if not self.profit_snapshot:
                self.profit_snapshot = self.product.profit

        super().save(*args, **kwargs)




    

     

