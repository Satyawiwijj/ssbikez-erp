from django.contrib import admin

from .models import FinanceLoan, InsurancePolicy, Invoice, Payment


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display  = ('invoice_number', 'sales_order', 'final_amount', 'invoice_date', 'created_at')
    search_fields = ('invoice_number', 'sales_order__customer__full_name')
    list_filter   = ('invoice_date',)
    readonly_fields = ('created_at',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = ('invoice', 'payment_method', 'amount', 'payment_status', 'payment_date')
    list_filter   = ('payment_method', 'payment_status')
    readonly_fields = ('created_at',)


@admin.register(InsurancePolicy)
class InsurancePolicyAdmin(admin.ModelAdmin):
    list_display  = ('policy_number', 'sales_order', 'provider_name', 'premium_amount', 'start_date', 'end_date')
    search_fields = ('policy_number', 'provider_name', 'sales_order__customer__full_name')
    list_filter   = ('start_date',)
    readonly_fields = ('created_at',)


@admin.register(FinanceLoan)
class FinanceLoanAdmin(admin.ModelAdmin):
    list_display  = ('sales_order', 'bank_name', 'loan_amount', 'tenure_months', 'emi_amount', 'loan_status')
    list_filter   = ('loan_status',)
    readonly_fields = ('created_at',)
