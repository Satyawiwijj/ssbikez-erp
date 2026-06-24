from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AuditLog, Branch, FuelExpense, ModulePermission, Role, User


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display  = ('branch_name', 'phone', 'gstin', 'is_active', 'created_at')
    list_filter   = ('is_active',)
    search_fields = ('branch_name', 'gstin', 'phone')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display  = ('role_name', 'description', 'created_at')
    search_fields = ('role_name',)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ('first_name', 'last_name', 'email', 'role', 'branch', 'status', 'is_active')
    list_filter   = ('status', 'role', 'branch', 'is_staff')
    search_fields = ('first_name', 'last_name', 'email', 'username')
    ordering      = ('first_name', 'last_name')

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profile', {'fields': ('role', 'branch', 'phone', 'status')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Profile', {'fields': ('role', 'branch', 'phone', 'status')}),
    )


@admin.register(ModulePermission)
class ModulePermissionAdmin(admin.ModelAdmin):
    list_display   = ('role', 'module', 'can_view', 'can_create', 'can_edit', 'can_delete', 'updated_at')
    list_filter    = ('role', 'module')
    list_editable  = ('can_view', 'can_create', 'can_edit', 'can_delete')


@admin.register(FuelExpense)
class FuelExpenseAdmin(admin.ModelAdmin):
    list_display  = ('vehicle', 'amount', 'fuel_date', 'voucher_number', 'created_by')
    list_filter   = ('fuel_date',)
    search_fields = ('vehicle__chassis_no', 'voucher_number')
    readonly_fields = ('created_at',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display  = ('user', 'module_name', 'action_name', 'record_id', 'ip_address', 'created_at')
    list_filter   = ('action_name', 'module_name')
    search_fields = ('user__first_name', 'user__last_name', 'module_name', 'ip_address')
    readonly_fields = ('user', 'module_name', 'action_name', 'record_id', 'ip_address', 'created_at')
