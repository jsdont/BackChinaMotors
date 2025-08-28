import os
from django.db import models
from cloudinary.models import CloudinaryField

def cloud_folder():
    base = os.getenv("CLOUDINARY_FOLDER", "china-motors")
    return f"{base}/cars"

class Car(models.Model):
    name  = models.CharField(max_length=120)
    brand = models.CharField(max_length=80, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    year  = models.PositiveIntegerField(default=2020)

    image  = CloudinaryField("image", folder=cloud_folder())
    image2 = CloudinaryField("image", folder=cloud_folder(), blank=True, null=True)
    image3 = CloudinaryField("image", folder=cloud_folder(), blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.brand} {self.name} ({self.year})"

    def card_url(self, w=480, h=320):
        return self.image.url.replace("/upload/", f"/upload/f_auto,q_auto,c_fill,g_auto,w_{w},h_{h}/")

    def hero_url(self, w=1600, h=630):
        return self.image.url.replace("/upload/", f"/upload/f_auto,q_auto,c_fill,g_center,w_{w},h_{h}/")
