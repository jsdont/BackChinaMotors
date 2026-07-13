from django.conf import settings
from django.db import models


class Vehicle(models.Model):
    AVAILABILITY_CHOICES = [
        ("in_stock", "В наличии"),
        ("out_of_stock", "Нет в наличии"),
        ("on_order", "На заказ"),
    ]

    brand = models.CharField(max_length=120, blank=True, default="")
    model = models.CharField(max_length=120, blank=True, default="")
    year = models.PositiveIntegerField(null=True, blank=True)
    body_type = models.CharField(
        max_length=120,
        blank=True,
        default="",
        verbose_name="Название / модель",
        help_text="Отображается как заголовок в каталоге и на странице техники",
    )
    category = models.CharField(
        max_length=120,
        blank=True,
        default="",
        verbose_name="Категория",
        help_text="Тип техники, например: Самосвал, Тягач, Кран",
    )
    city = models.CharField(
        max_length=120,
        blank=True,
        default="",
        verbose_name="Город",
    )
    extra_info = models.TextField(
        blank=True,
        default="",
        verbose_name="Доп. информация",
        help_text="Любые дополнительные детали о технике — выводится на странице товара"
    )
    weight_t = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Полная масса ТС в тоннах"
    )
    wheel_formula = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="Колёсная формула",
        help_text="Например: 6x4"
    )
    gearbox = models.CharField(
        max_length=60,
        blank=True,
        default="",
        verbose_name="КПП",
        help_text="Например: механика, автомат"
    )
    engine_power_hp = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Мощность двигателя, л.с."
    )
    load_capacity_t = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Грузоподъёмность, т"
    )
    price_usd = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_cny = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_kzt = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Цена, ₸",
    )
    mileage_km = models.IntegerField(null=True, blank=True)
    image_url = models.URLField(blank=True, default="")
    images = models.JSONField(
        default=list,
        blank=True,
        help_text="Доп. фото галереи — список ссылок, например: "
                   '["https://.../1.jpg", "https://.../2.jpg"]'
    )
    tiktok_url = models.URLField(
        blank=True,
        default="",
        verbose_name="Видео-обзор TikTok",
        help_text="Ссылка на видео TikTok — покажется последним слайдом в галерее фото"
    )
    availability = models.CharField(
        max_length=20,
        choices=AVAILABILITY_CHOICES,
        default="in_stock",
    )
    # Пусто — официальный каталог China Motors (как раньше). Заполнено —
    # объявление, которое разместил клиент (физ. или юр. лицо) сам через
    # личный кабинет; такие объявления не публикуются, пока не одобрены.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicle_listings",
        verbose_name="Автор объявления",
        help_text="Пусто — официальный каталог; заполнено — объявление клиента",
    )
    is_approved = models.BooleanField(
        default=True,
        verbose_name="Одобрено",
        help_text="Объявления клиентов скрыты из публичного каталога, пока админ не одобрит",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        base = self.body_type or f"{self.brand} {self.model}".strip()
        return base or f"Vehicle #{self.pk}"
