from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, phone, password, **extra_fields):
        if not phone:
            raise ValueError("Phone must be set")

        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone, password, **extra_fields)

    def create_superuser(self, phone, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "ADMIN")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(phone, password, **extra_fields)


class User(AbstractUser):
    ROLE_CHOICES = (
        ('CUSTOMER_PERSON', 'Клиент (физ. лицо)'),
        ('CUSTOMER_COMPANY', 'Клиент (юр. лицо)'),
        ('SERVICE_BROKER', 'Брокер (СВХ)'),
        ('SERVICE_SVH', 'СВХ'),
        ('SERVICE_LAB', 'Лаборатория'),
        ('SERVICE_LOGISTIC', 'Логист'),
        ('SERVICE_DECLARANT', 'Декларант (граница)'),
        ('BANK', 'Банк'),
        ('PARTNER', 'Партнёр-продавец'),
        ('MANAGER', 'Manager'),
        ('ADMIN', 'Admin'),
    )

    username = None
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    # Регистрация сама по себе не даёт доступа — админ подтверждает
    # аккаунт в Django admin (как в v32fix_work).
    is_verified = models.BooleanField(default=False, verbose_name="Подтверждён")
    # Момент, когда пользователь последний раз открывал уведомления. Всё, что
    # произошло по его сделкам позже, считается непрочитанным.
    notifications_seen_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.phone} ({self.role})"



class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="client_profile")
    full_name = models.CharField(max_length=255)
    iin = models.CharField(max_length=12, blank=True, default="", verbose_name="ИИН")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


class Company(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="company_profile")
    company_name = models.CharField(max_length=255, verbose_name="Название компании")
    bin = models.CharField(max_length=12, blank=True, default="", verbose_name="БИН")
    address = models.CharField(max_length=500, blank=True, default="", verbose_name="Юридический адрес")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name


class ServiceProvider(models.Model):
    # Общая карточка для СВХ-стороны процесса растаможки — брокер, СВХ,
    # лаборатория, логист и декларант регистрируются одной формой с
    # выбором service_type, как register_service.ejs в v32fix_work.
    SERVICE_TYPE_CHOICES = (
        ('BROKER', 'Брокер (СВХ)'),
        ('SVH', 'СВХ'),
        ('LAB', 'Лаборатория'),
        ('LOGISTIC', 'Логист'),
        ('DECLARANT', 'Декларант (граница)'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="service_profile")
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPE_CHOICES)
    company_name = models.CharField(max_length=255, verbose_name="Название компании / ФИО")
    bin = models.CharField(max_length=12, blank=True, default="", verbose_name="БИН")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.company_name} ({self.get_service_type_display()})"


class Bank(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="bank_profile")
    bank_name = models.CharField(max_length=255, verbose_name="Название банка")
    bik = models.CharField(max_length=20, blank=True, default="", verbose_name="БИК")
    address = models.CharField(max_length=500, blank=True, default="", verbose_name="Адрес")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.bank_name


class Partner(models.Model):
    # Партнёр-продавец (Китай) — загружает объявления техники, которые
    # проходят модерацию админа, как в v32fix_work.
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="partner_profile")
    company_name = models.CharField(max_length=255, verbose_name="Название компании")
    country = models.CharField(max_length=100, blank=True, default="China", verbose_name="Страна")
    reg_no = models.CharField(max_length=100, blank=True, default="", verbose_name="Рег. номер компании")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name


class Manager(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.user.phone


class Deal(models.Model):
    STATUS_CHOICES = (
        ('AGREEMENT', 'Согласование'),
        ('CONTRACT', 'Договор'),
        ('PURCHASE_CHINA', 'Покупка в Китае'),
        ('DELIVERY_KZ', 'Доставка в КЗ'),
        ('SVH', 'СВХ'),
        ('CUSTOMS', 'Таможня'),
        ('DELIVERY_CLIENT', 'Доставка клиенту'),
        ('COMPLETED', 'Завершена'),
    )

    # Клиент — физ. или юр. лицо, оба хранятся как User (a не Client,
    # чтобы сделку мог оформить и CUSTOMER_COMPANY).
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="deals_as_customer")
    vehicle = models.ForeignKey(
        "cars.Vehicle", on_delete=models.SET_NULL, null=True, blank=True, related_name="deals"
    )
    manager = models.ForeignKey(Manager, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="AGREEMENT")
    total_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    # Детализация расчёта из калькулятора (группы строк + итог) — переносится
    # из заявки при конвертации и выводится отдельным блоком в КП.
    calc_breakdown = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title or f"Сделка #{self.pk}"


class DealAssignment(models.Model):
    # Кто из сервисных аккаунтов ведёт эту сделку на каждом этапе —
    # аналог tasks/serviceAssignments в v32fix_work, только без карты и
    # автоматических счетов (MVP).
    ROLE_CHOICES = (
        ('BROKER', 'Брокер (СВХ)'),
        ('SVH', 'СВХ'),
        ('LAB', 'Лаборатория'),
        ('LOGISTIC', 'Логист'),
        ('DECLARANT', 'Декларант (граница)'),
        ('BANK', 'Банк'),
    )
    TASK_STATUS_CHOICES = (
        ('PENDING', 'Ожидает'),
        ('IN_PROGRESS', 'В работе'),
        ('DONE', 'Завершено'),
    )

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="assignments")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    assigned_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="deal_assignments"
    )
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default="PENDING")
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("deal", "role")

    def __str__(self):
        return f"{self.deal} — {self.get_role_display()}"


class Document(models.Model):
    DOCUMENT_TYPES = (
        ('CONTRACT', 'Договор'),
        ('GTD', 'ГТД'),
        ('CMR', 'CMR'),
        ('ACCEPTANCE', 'Акт приёма'),
        ('PHOTO', 'Фото'),
    )

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='documents/')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Comment(models.Model):
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Payment(models.Model):
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_confirmed = models.BooleanField(default=False)
    confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Expense(models.Model):
    # Расход по сделке — внутренние затраты (закупка, логистика, растаможка
    # и т.д.). ВИДЯТ ТОЛЬКО МЕНЕДЖЕРЫ: клиенту эти суммы не показываются,
    # они нужны для расчёта прибыли (P&L) = стоимость сделки − расходы.
    CATEGORY_CHOICES = (
        ('PURCHASE', 'Закупка в Китае'),
        ('LOGISTICS', 'Логистика / доставка'),
        ('CUSTOMS', 'Растаможка'),
        ('CERTIFICATION', 'Сертификация (СБКТС/ЭПТС)'),
        ('SVH', 'СВХ / хранение'),
        ('OTHER', 'Прочее'),
    )

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="expenses")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='OTHER')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=255, blank=True, default="")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_category_display()} — {self.amount}"


class DealStage(models.Model):
    # Кастомный этап сделки («конструктор сценариев»): менеджер составляет
    # для конкретной сделки свой план из произвольных шагов сверх фиксированной
    # воронки Deal.status. Клиент видит этот план (чек-лист) — прозрачность.
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="stages")
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    is_done = models.BooleanField(default=False)
    note = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class DealMedia(models.Model):
    # Фото/видео по сделке — визуальное сопровождение (погрузка, склад,
    # доставка). Клиент видит галерею. Фото загружаются файлом (Cloudinary),
    # видео добавляются ссылкой (YouTube/TikTok и т.п.) — так надёжнее, чем
    # хранить видео в файловом хранилище.
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="media")
    image = models.FileField(upload_to='deal_media/', null=True, blank=True)
    video_url = models.URLField(blank=True, default="")
    caption = models.CharField(max_length=255, blank=True, default="")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.caption or (self.video_url or "media")


class DealActivity(models.Model):
    # Лог изменений по сделке (аудит): кто и что сделал. Пишется из вьюх в
    # момент действия. internal=True — событие видно только менеджеру
    # (например, расходы), остальное видит и клиент (прозрачность).
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="activities")
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    text = models.CharField(max_length=500)
    internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.text


class Lead(models.Model):
    STATUS_CHOICES = (
        ('NEW', 'Новая'),
        ('CONTACTED', 'Связались'),
        ('ARCHIVED', 'Архив'),
    )

    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    source = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
    created_at = models.DateTimeField(auto_now_add=True)


class KPSettings(models.Model):
    """Шаблон коммерческого предложения (продавец, реквизиты банка, условия и
    сроки поставки, сервис-центр, печать). Singleton — одна запись, правится в
    админке без деплоя. Значения по умолчанию — из core/kp_defaults.py."""

    from . import kp_defaults as _d

    seller_name = models.CharField("Продавец", max_length=255, default=_d.SELLER_NAME)
    seller_address = models.TextField("Адрес продавца", default=_d.SELLER_ADDRESS)
    bank = models.CharField("Банк", max_length=255, default=_d.BANK)
    bank_address = models.TextField("Адрес банка", default=_d.BANK_ADDRESS)
    account = models.CharField("Счёт (IBAN/ACCOUNT)", max_length=120, default=_d.ACCOUNT)
    swift = models.CharField("SWIFT", max_length=60, default=_d.SWIFT)
    delivery_terms = models.CharField("Условия поставки", max_length=255, default=_d.DELIVERY_TERMS)
    timeline = models.TextField("Сроки поставки", default=_d.TIMELINE,
                                help_text="По одному пункту на строку")
    service_center = models.TextField("Сервис-центр", default=_d.SERVICE_CENTER)
    show_seal = models.BooleanField("Показывать печать и подпись", default=True)

    class Meta:
        verbose_name = "Коммерческое предложение (шаблон)"
        verbose_name_plural = "Коммерческое предложение (шаблон)"

    def __str__(self):
        return "Шаблон КП"

    def save(self, *args, **kwargs):
        self.pk = 1  # singleton — всегда одна запись
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
