# cars/admin.py
from django import forms
from django.contrib import admin
from .models import Vehicle


class VehicleAdminForm(forms.ModelForm):
    images = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "https://.../1.jpg\nhttps://.../2.jpg"}),
        required=False,
        label="Фото галереи",
        help_text="Вставьте ссылки на фото — по одной на строку. Превью появится ниже.",
    )

    class Meta:
        model = Vehicle
        fields = "__all__"
        # Django admin не назначает свою ширину DecimalField/IntegerField
        # (только CharField получает vTextField 20em) — задаём её явно,
        # каждому полю свою, вместо браузерного размера по умолчанию.
        widgets = {
            "brand": forms.TextInput(attrs={"style": "width: 12em"}),
            "model": forms.TextInput(attrs={"style": "width: 12em"}),
            "body_type": forms.TextInput(attrs={"style": "width: 24em"}),
            "category": forms.TextInput(attrs={"style": "width: 16em"}),
            "city": forms.TextInput(attrs={"style": "width: 12em"}),
            "wheel_formula": forms.TextInput(attrs={"style": "width: 4em"}),
            "gearbox": forms.TextInput(attrs={"style": "width: 10em"}),
            "year": forms.NumberInput(attrs={"style": "width: 4em"}),
            "weight_t": forms.NumberInput(attrs={"style": "width: 4em"}),
            "load_capacity_t": forms.NumberInput(attrs={"style": "width: 6em"}),
            "engine_power_hp": forms.NumberInput(attrs={"style": "width: 6em"}),
            "mileage_km": forms.NumberInput(attrs={"style": "width: 8em"}),
            "price_usd": forms.NumberInput(attrs={"style": "width: 7em"}),
            "price_cny": forms.NumberInput(attrs={"style": "width: 7em"}),
            "price_kzt": forms.NumberInput(attrs={"style": "width: 8em"}),
            "image_url": forms.URLInput(attrs={"style": "width: 30em"}),
            "tiktok_url": forms.URLInput(attrs={"style": "width: 30em"}),
        }

    class Media:
        js = ("cars/admin_image_preview.js",)

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
    list_display = ("id", "body_type", "brand", "model", "category", "city", "year", "price_cny", "price_usd", "price_kzt", "weight_t", "wheel_formula", "availability", "owner", "is_approved")
    list_filter = ("availability", "category", "is_approved")
    search_fields = ("brand", "model", "body_type", "category", "city", "owner__phone")
    list_per_page = 50
    list_editable = ("year", "price_cny", "price_usd", "price_kzt", "weight_t", "wheel_formula", "availability", "is_approved")

    actions = ["approve_listings"]

    def approve_listings(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"Одобрено объявлений: {updated}")
    approve_listings.short_description = "Одобрить выбранные объявления"
