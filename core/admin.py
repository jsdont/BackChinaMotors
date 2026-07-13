from django.contrib import admin
from .models import User, Client, Company, ServiceProvider, Bank, Partner


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
