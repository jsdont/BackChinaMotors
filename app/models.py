from django.db import models
from catalog.models import Product
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
class CalculatorLead(models.Model):
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


    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="new",
        db_index=True
    )


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

    def clean(self):
        if self.status == "won" and not self.product:
            raise ValidationError("Won lead must have a product selected.")


    def save(self, *args, **kwargs):
        if self.status == "won":
            if not self.closed_at:
                self.closed_at = timezone.now()

            if self.product and not self.profit_snapshot:
                self.profit_snapshot = self.product.profit

        super().save(*args, **kwargs)







    

     

