# cars/admin.py
from django import forms
from django.contrib import admin
from .models import Vehicle


class VehicleAdminForm(forms.ModelForm):
    images = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "https://.../1.jpg\nhttps://.../2.jpg"}),
        required=False,
        label="Images",
        help_text="Просто вставьте ссылки на фото — по одной на строку.",
    )

    class Meta:
        model = Vehicle
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and isinstance(self.instance.images, list):
            self.initial["images"] = "\n".join(self.instance.images)

    def clean_images(self):
        raw = self.cleaned_data.get("images", "")
        return [line.strip() for line in raw.splitlines() if line.strip()]


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    form = VehicleAdminForm
    list_display = ("id", "brand", "model", "body_type", "year", "price_cny", "price_usd", "weight_t", "availability")
    list_filter = ("availability", "body_type")
    search_fields = ("brand", "model", "body_type")
    list_per_page = 50
    list_editable = ("weight_t", "availability")
