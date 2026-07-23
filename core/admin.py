from django.contrib import admin
from .models import User, Client, Company, ServiceProvider, Bank, Partner, Deal, DealAssignment, Comment, Payment, Document, Expense, DealStage, DealMedia, DealActivity, KPSettings


@admin.register(KPSettings)
class KPSettingsAdmin(admin.ModelAdmin):
    """Шаблон КП — одна запись (singleton), правится без деплоя."""

    fieldsets = (
        ("Продавец и банк", {
            "fields": ("seller_name", "seller_address", "bank", "bank_address",
                       "account", "swift"),
        }),
        ("Условия, сроки, сервис", {
            "fields": ("delivery_terms", "timeline", "service_center"),
        }),
        ("Оформление", {
            "fields": ("show_seal",),
        }),
    )

    def has_add_permission(self, request):
        # Singleton: не даём создавать вторую запись.
        return not KPSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class ClientInline(admin.StackedInline):
    model = Client
    can_delete = False
    extra = 0


class CompanyInline(admin.StackedInline):
    model = Company
    can_delete = False
    extra = 0


class ServiceProviderInline(admin.StackedInline):
    model = ServiceProvider
    can_delete = False
    extra = 0


class BankInline(admin.StackedInline):
    model = Bank
    can_delete = False
    extra = 0


class PartnerInline(admin.StackedInline):
    model = Partner
    can_delete = False
    extra = 0


ROLE_INLINES = {
    "CUSTOMER_PERSON": ClientInline,
    "CUSTOMER_COMPANY": CompanyInline,
    "SERVICE_BROKER": ServiceProviderInline,
    "SERVICE_SVH": ServiceProviderInline,
    "SERVICE_LAB": ServiceProviderInline,
    "SERVICE_LOGISTIC": ServiceProviderInline,
    "SERVICE_DECLARANT": ServiceProviderInline,
    "BANK": BankInline,
    "PARTNER": PartnerInline,
}


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("phone", "role", "is_verified", "is_staff", "date_joined")
    list_editable = ("is_verified",)
    list_filter = ("role", "is_verified", "is_staff")
    search_fields = ("phone", "email")
    ordering = ("-date_joined",)

    actions = ["verify_users"]

    def verify_users(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f"Подтверждено аккаунтов: {updated}")
    verify_users.short_description = "Подтвердить выбранные аккаунты"

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        inline_cls = ROLE_INLINES.get(obj.role)
        if not inline_cls:
            return []
        return [inline_cls(self.model, self.admin_site)]


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("full_name", "iin", "user", "created_at")
    search_fields = ("full_name", "iin", "user__phone")


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("company_name", "bin", "user", "created_at")
    search_fields = ("company_name", "bin", "user__phone")


@admin.register(ServiceProvider)
class ServiceProviderAdmin(admin.ModelAdmin):
    list_display = ("company_name", "service_type", "bin", "user", "created_at")
    list_filter = ("service_type",)
    search_fields = ("company_name", "bin", "user__phone")


@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
    list_display = ("bank_name", "bik", "address", "user", "created_at")
    search_fields = ("bank_name", "bik", "user__phone")


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("company_name", "country", "reg_no", "user", "created_at")
    search_fields = ("company_name", "reg_no", "user__phone")


class DealAssignmentInline(admin.TabularInline):
    # Здесь админ назначает конкретного брокера/СВХ/лабораторию/логиста/
    # декларанта/банк на сделку — выбор из выпадающего списка User
    # (подпись "телефон (роль)" помогает найти нужного).
    model = DealAssignment
    extra = 1


class PaymentInline(admin.TabularInline):
    # Менеджер добавляет платежи по сделке — клиент видит их в кабинете.
    model = Payment
    extra = 1


class DocumentInline(admin.TabularInline):
    # Менеджер загружает документы (договор/ГТД/CMR/акт/фото) — клиент видит
    # и скачивает их в кабинете. Файлы уходят в Cloudinary.
    model = Document
    extra = 1


class ExpenseInline(admin.TabularInline):
    # Внутренние расходы по сделке (клиенту не видны) — для расчёта прибыли.
    model = Expense
    extra = 1


class DealStageInline(admin.TabularInline):
    # Кастомный план сделки (конструктор сценариев).
    model = DealStage
    extra = 1


class DealMediaInline(admin.TabularInline):
    # Фото/видео по сделке.
    model = DealMedia
    extra = 1


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "customer", "vehicle", "status", "is_paid", "created_at")
    list_editable = ("status", "is_paid")
    list_filter = ("status", "is_paid")
    search_fields = ("title", "customer__phone")
    inlines = [DealAssignmentInline, DealStageInline, PaymentInline, DocumentInline, ExpenseInline, DealMediaInline]


@admin.register(DealAssignment)
class DealAssignmentAdmin(admin.ModelAdmin):
    list_display = ("deal", "role", "assigned_user", "status", "updated_at")
    list_filter = ("role", "status")
    search_fields = ("deal__title", "assigned_user__phone")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("deal", "author", "text", "created_at")
    search_fields = ("deal__title", "author__phone", "text")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("deal", "amount", "is_confirmed", "confirmed_by", "created_at")
    list_editable = ("is_confirmed",)
    list_filter = ("is_confirmed",)
    search_fields = ("deal__title",)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("deal", "type", "uploaded_by", "created_at")
    list_filter = ("type",)
    search_fields = ("deal__title",)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("deal", "category", "amount", "created_by", "created_at")
    list_filter = ("category",)
    search_fields = ("deal__title", "note")


@admin.register(DealMedia)
class DealMediaAdmin(admin.ModelAdmin):
    list_display = ("deal", "caption", "video_url", "uploaded_by", "created_at")
    search_fields = ("deal__title", "caption")


@admin.register(DealActivity)
class DealActivityAdmin(admin.ModelAdmin):
    list_display = ("deal", "text", "actor", "internal", "created_at")
    list_filter = ("internal",)
    search_fields = ("deal__title", "text")
