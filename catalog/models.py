from django.db import models

class Product(models.Model):
    AVAIL_CHOICES = [
        ('В наличии', 'В наличии'),
        ('Под заказ', 'Под заказ'),
    ]
    id = models.SlugField(primary_key=True, max_length=80)  # например: x3000-6x4-e5
    title = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=100)             # Самосвалы, Тягачи, ...
    availability = models.CharField(max_length=20, choices=AVAIL_CHOICES, default='Под заказ')
    image_url = models.URLField(blank=True)                 # https://.../img.jpg
    specs = models.JSONField(default=list, blank=True)      # ["Евро 5", "6×4", "460 л.с."]
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['price']

    def __str__(self):
        return self.title
