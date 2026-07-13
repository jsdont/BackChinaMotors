from django.contrib import admin
from .models import User, Client, Company


class ClientInline(admin.StackedInline):
    model = Client
    can_delete = False
    extra = 0


class CompanyInline(admin.StackedInline):
    model = Company
    can_delete = False
    extra = 0


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("phone", "role", "is_verified", "is_staff", "date_joined")
    list_editable = ("is_verified",)
    list_filter = ("role", "is_verified", "is_staff")
    search_fields = ("phone", "email")
    ordering = ("-date_joined",)
    inlines = [ClientInline, CompanyInline]

    actions = ["verify_users"]

    def verify_users(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f"Подтверждено аккаунтов: {updated}")
    verify_users.short_description = "Подтвердить выбранные аккаунты"

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        inlines = []
        if obj.role == "CUSTOMER_PERSON":
            inlines.append(ClientInline(self.model, self.admin_site))
        elif obj.role == "CUSTOMER_COMPANY":
            inlines.append(CompanyInline(self.model, self.admin_site))
        return inlines


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("full_name", "iin", "user", "created_at")
    search_fields = ("full_name", "iin", "user__phone")


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("company_name", "bin", "user", "created_at")
    search_fields = ("company_name", "bin", "user__phone")
