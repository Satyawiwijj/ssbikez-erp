from django.contrib import admin

from .models import BikeModel, Customer, VehicleStock


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display  = ('full_name', 'phone', 'email', 'created_at')
    search_fields = ('full_name', 'phone', 'email', 'aadhaar_no', 'pan_no')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(BikeModel)
class BikeModelAdmin(admin.ModelAdmin):
    list_display  = ('brand', 'model_name', 'variant', 'fuel_type', 'ex_showroom_price')
    search_fields = ('brand', 'model_name', 'variant')
    list_filter   = ('fuel_type',)


@admin.register(VehicleStock)
class VehicleStockAdmin(admin.ModelAdmin):
    list_display  = ('bike_model', 'chassis_no', 'engine_no', 'color', 'stock_status', 'branch')
    search_fields = ('chassis_no', 'engine_no')
    list_filter   = ('stock_status', 'branch')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('bike_model',)
