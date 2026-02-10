from django.db import models


class CalculatorLead(models.Model):
    calc_id = models.CharField(max_length=32, unique=True)
    source = models.CharField(max_length=32)  # calculator / contacts / tawk
    name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=64, blank=True)
    message = models.TextField(blank=True)
    page_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.calc_id
