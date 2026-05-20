from django.contrib import admin

from .models import (BayAssignment, JobCard, LaborCharge, OutworkEntry,
                     ServiceAppointment, ServiceBay, ServiceEnquiry, ServiceInvoice)


@admin.register(ServiceEnquiry)
class ServiceEnquiryAdmin(admin.ModelAdmin):
    list_display    = ('customer_vehicle', 'created_by', 'status', 'created_at')
    search_fields   = ('customer_vehicle__customer__full_name',
                       'customer_vehicle__registration_no')
    list_filter     = ('status',)
    readonly_fields = ('created_at',)


@admin.register(ServiceAppointment)
class ServiceAppointmentAdmin(admin.ModelAdmin):
    list_display    = ('service_enquiry', 'appointment_date', 'service_type', 'status')
    list_filter     = ('status', 'service_type')
    readonly_fields = ('created_at',)


@admin.register(JobCard)
class JobCardAdmin(admin.ModelAdmin):
    list_display    = ('customer_vehicle', 'service_advisor', 'floor_supervisor',
                       'service_status', 'odometer_reading', 'created_at')
    search_fields   = ('customer_vehicle__customer__full_name',
                       'customer_vehicle__registration_no')
    list_filter     = ('service_status', 'branch')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ServiceBay)
class ServiceBayAdmin(admin.ModelAdmin):
    list_display    = ('bay_name', 'status')
    list_filter     = ('status',)
    readonly_fields = ('created_at',)


@admin.register(BayAssignment)
class BayAssignmentAdmin(admin.ModelAdmin):
    list_display    = ('job_card', 'bay', 'mechanic', 'start_time',
                       'end_time', 'assignment_status')
    list_filter     = ('assignment_status',)
    readonly_fields = ('created_at',)


@admin.register(ServiceInvoice)
class ServiceInvoiceAdmin(admin.ModelAdmin):
    list_display    = ('job_card', 'subtotal', 'gst_amount', 'discount_amount',
                       'final_amount', 'invoice_date')
    search_fields   = ('job_card__customer_vehicle__customer__full_name',)
    list_filter     = ('invoice_date',)
    readonly_fields = ('created_at',)


@admin.register(LaborCharge)
class LaborChargeAdmin(admin.ModelAdmin):
    list_display    = ('job_card', 'service_name', 'labor_cost')
    readonly_fields = ('created_at',)


@admin.register(OutworkEntry)
class OutworkEntryAdmin(admin.ModelAdmin):
    list_display    = ('job_card', 'vendor_name', 'status', 'issued_at', 'returned_at', 'cost')
    list_filter     = ('status',)
    search_fields   = ('vendor_name', 'job_card__id')
    readonly_fields = ('issued_at', 'created_at')
