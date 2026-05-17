from django.contrib import admin

from .models import NumberPlateOrder, RTORegistration


@admin.register(RTORegistration)
class RTORegistrationAdmin(admin.ModelAdmin):
    list_display  = ('sales_order', 'form20_number', 'registration_number',
                     'rto_charges', 'registration_status', 'created_at')
    search_fields = ('form20_number', 'registration_number',
                     'sales_order__customer__full_name')
    list_filter   = ('registration_status',)
    readonly_fields = ('created_at',)


@admin.register(NumberPlateOrder)
class NumberPlateOrderAdmin(admin.ModelAdmin):
    list_display  = ('rto', 'plate_number', 'vendor_name', 'issue_date', 'status')
    list_filter   = ('status',)
    readonly_fields = ('created_at',)
