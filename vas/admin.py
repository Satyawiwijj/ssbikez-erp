from django.contrib import admin

from .models import AMCPackage, ProtectionPlusPackage, RSAPackage


@admin.register(AMCPackage)
class AMCPackageAdmin(admin.ModelAdmin):
    list_display    = ('customer_vehicle', 'package_name', 'start_date',
                       'end_date', 'amount', 'status')
    search_fields   = ('customer_vehicle__customer__full_name',
                       'customer_vehicle__registration_no')
    list_filter     = ('status',)
    readonly_fields = ('created_at',)


@admin.register(RSAPackage)
class RSAPackageAdmin(admin.ModelAdmin):
    list_display    = ('customer_vehicle', 'provider_name', 'start_date',
                       'end_date', 'amount', 'status')
    search_fields   = ('customer_vehicle__customer__full_name',
                       'customer_vehicle__registration_no')
    list_filter     = ('status',)
    readonly_fields = ('created_at',)


@admin.register(ProtectionPlusPackage)
class ProtectionPlusPackageAdmin(admin.ModelAdmin):
    list_display    = ('customer_vehicle', 'package_name', 'provider_name',
                       'start_date', 'end_date', 'amount', 'status')
    search_fields   = ('customer_vehicle__customer__full_name',
                       'customer_vehicle__registration_no')
    list_filter     = ('status',)
    readonly_fields = ('created_at',)
