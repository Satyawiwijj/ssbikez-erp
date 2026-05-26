from django.contrib import admin

from .models import CustomerVehicle


@admin.register(CustomerVehicle)
class CustomerVehicleAdmin(admin.ModelAdmin):
    list_display  = ('customer', 'vehicle', 'registration_no', 'purchase_date', 'insurance_expiry')
    search_fields = ('customer__full_name', 'customer__phone', 'registration_no', 'vehicle__chassis_no')
    list_filter   = ('purchase_date',)
    readonly_fields = ('created_at',)
