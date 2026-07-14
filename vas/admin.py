from django.contrib import admin

from .models import (AMCPackage, AMCType, ProtectionPlusPackage, RSAPackage, RSAType,
                     RSACreation, VASStockLedger, VASSupplierInvoice, WarrantyType)


@admin.register(AMCPackage)
class AMCPackageAdmin(admin.ModelAdmin):
    list_display    = ('customer_vehicle', 'amc_type', 'start_date',
                       'end_date', 'amount', 'status', 'docstatus')
    search_fields   = ('customer_vehicle__customer__full_name',
                       'customer_vehicle__registration_no')
    list_filter     = ('status', 'docstatus')
    readonly_fields = ('created_at',)


@admin.register(RSAPackage)
class RSAPackageAdmin(admin.ModelAdmin):
    list_display    = ('customer_vehicle', 'rsa_type', 'start_date',
                       'end_date', 'amount', 'status', 'docstatus')
    search_fields   = ('customer_vehicle__customer__full_name',
                       'customer_vehicle__registration_no')
    list_filter     = ('status', 'docstatus')
    readonly_fields = ('created_at',)


@admin.register(ProtectionPlusPackage)
class ProtectionPlusPackageAdmin(admin.ModelAdmin):
    list_display    = ('customer_vehicle', 'warranty_type',
                       'start_date', 'end_date', 'amount', 'status', 'docstatus')
    search_fields   = ('customer_vehicle__customer__full_name',
                       'customer_vehicle__registration_no')
    list_filter     = ('status', 'docstatus')
    readonly_fields = ('created_at',)


@admin.register(AMCType)
class AMCTypeAdmin(admin.ModelAdmin):
    list_display  = ('code', 'name', 'amc_amount', 'is_active')
    search_fields = ('code', 'name')


@admin.register(RSAType)
class RSATypeAdmin(admin.ModelAdmin):
    list_display  = ('code', 'name', 'rsa_amount', 'is_active')
    search_fields = ('code', 'name')


@admin.register(WarrantyType)
class WarrantyTypeAdmin(admin.ModelAdmin):
    list_display  = ('code', 'name', 'is_active')
    search_fields = ('code', 'name')


@admin.register(VASStockLedger)
class VASStockLedgerAdmin(admin.ModelAdmin):
    list_display = ('plan_type', 'current_stock')


@admin.register(RSACreation)
class RSACreationAdmin(admin.ModelAdmin):
    list_display = ('rsa_type', 'supplier', 'rsa_amount', 'expected_date', 'docstatus')
    list_filter  = ('docstatus',)


@admin.register(VASSupplierInvoice)
class VASSupplierInvoiceAdmin(admin.ModelAdmin):
    list_display    = ('invoice_number', 'supplier', 'invoice_date', 'total_amount', 'payment_status', 'docstatus')
    search_fields   = ('invoice_number', 'supplier__supplier_name')
    list_filter     = ('payment_status', 'docstatus')
    readonly_fields = ('invoice_number', 'created_at')
