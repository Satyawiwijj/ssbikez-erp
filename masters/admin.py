from django.contrib import admin
from .models import SparesCategory, Supplier, Warehouse, Rack, Bin, VehicleType, NormalHelmetMaster


@admin.register(SparesCategory)
class SparesCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['supplier_name', 'contact_person', 'phone', 'city', 'is_active']
    list_filter = ['is_active', 'state']
    search_fields = ['supplier_name', 'phone', 'gstin']


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['name', 'warehouse_type', 'city', 'is_active']
    list_filter = ['warehouse_type', 'is_active']


@admin.register(Rack)
class RackAdmin(admin.ModelAdmin):
    list_display = ['name', 'warehouse']
    list_filter = ['warehouse']


@admin.register(Bin)
class BinAdmin(admin.ModelAdmin):
    list_display = ['name', 'rack']
    list_filter = ['rack__warehouse']


@admin.register(VehicleType)
class VehicleTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    search_fields = ['name']


@admin.register(NormalHelmetMaster)
class NormalHelmetMasterAdmin(admin.ModelAdmin):
    list_display = ['helmet_code', 'helmet_name', 'vehicle_category', 'part_number', 'gst_percent', 'disabled']
    list_filter = ['disabled', 'vehicle_category']
    search_fields = ['helmet_code', 'helmet_name', 'part_number']
