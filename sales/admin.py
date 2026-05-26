from django.contrib import admin

from .models import (ExchangeVehicle, SalesAppointment, SalesFeedback,
                     SalesEnquiry, VehicleDelivery, VehicleSalesOrder)


@admin.register(SalesEnquiry)
class SalesEnquiryAdmin(admin.ModelAdmin):
    list_display  = ('customer', 'bike_model', 'sales_executive',
                     'enquiry_source', 'status', 'created_at')
    search_fields = ('customer__full_name', 'customer__phone')
    list_filter   = ('status', 'enquiry_source', 'branch')
    readonly_fields = ('created_at',)


@admin.register(SalesAppointment)
class SalesAppointmentAdmin(admin.ModelAdmin):
    list_display  = ('enquiry', 'appointment_date', 'purpose', 'status')
    list_filter   = ('status', 'purpose')
    readonly_fields = ('created_at',)


@admin.register(SalesFeedback)
class SalesFeedbackAdmin(admin.ModelAdmin):
    list_display  = ('enquiry', 'next_followup_date', 'created_by', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(VehicleSalesOrder)
class VehicleSalesOrderAdmin(admin.ModelAdmin):
    list_display  = ('customer', 'vehicle', 'sales_executive',
                     'total_amount', 'sales_status', 'created_at')
    search_fields = ('customer__full_name', 'customer__phone')
    list_filter   = ('sales_status', 'branch')
    readonly_fields = ('created_at',)


@admin.register(VehicleDelivery)
class VehicleDeliveryAdmin(admin.ModelAdmin):
    list_display  = ('sales_order', 'delivery_date', 'delivered_by')
    list_filter   = ('delivery_date',)
    search_fields = ('sales_order__customer__full_name',)
    readonly_fields = ('created_at',)


@admin.register(ExchangeVehicle)
class ExchangeVehicleAdmin(admin.ModelAdmin):
    list_display  = ('sales_order', 'old_vehicle_model', 'registration_no', 'valuation_amount')
    readonly_fields = ('created_at',)
