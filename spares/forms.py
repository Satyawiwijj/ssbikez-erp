from django import forms

from service.models import JobCard

from .models import (CounterSale, CounterSaleItem, PurchaseOrder,
                     PurchaseOrderItem, SparePart, SparesCategory,
                     SparesIssue, Supplier)


class SparesCategoryForm(forms.ModelForm):
    class Meta:
        model  = SparesCategory
        fields = ('category_name',)


class SparePartForm(forms.ModelForm):
    class Meta:
        model  = SparePart
        fields = ('category', 'part_name', 'part_number', 'mrp',
                  'stock_quantity', 'rack_location', 'bin_location')


class SupplierForm(forms.ModelForm):
    class Meta:
        model  = Supplier
        fields = ('supplier_name', 'phone', 'email', 'address')


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model  = PurchaseOrder
        fields = ('supplier', 'total_amount', 'status')


class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model  = PurchaseOrderItem
        fields = ('purchase_order', 'spare_part', 'quantity', 'price')


class CounterSaleForm(forms.ModelForm):
    class Meta:
        model  = CounterSale
        fields = ('customer', 'branch', 'invoice_number', 'total_amount', 'created_by')


class CounterSaleItemForm(forms.ModelForm):
    class Meta:
        model  = CounterSaleItem
        fields = ('counter_sale', 'spare_part', 'quantity', 'unit_price')

    def clean(self):
        cleaned_data = super().clean()
        spare_part   = cleaned_data.get('spare_part')
        quantity     = cleaned_data.get('quantity') or 0
        if spare_part and quantity > 0:
            available = spare_part.stock_quantity
            if quantity > available:
                self.add_error(
                    'quantity',
                    f'Insufficient stock. Available: {available} units.'
                )
        return cleaned_data


class SparesIssueForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['job_card'].queryset = JobCard.objects.exclude(
            service_status=JobCard.ServiceStatus.INVOICED
        ).select_related('customer_vehicle__customer')

    class Meta:
        model  = SparesIssue
        fields = ('job_card', 'spare_part', 'quantity_issued',
                  'quantity_returned', 'unit_price', 'issued_by')

    def clean(self):
        cleaned_data    = super().clean()
        spare_part      = cleaned_data.get('spare_part')
        quantity_issued = cleaned_data.get('quantity_issued') or 0
        if spare_part and quantity_issued > 0 and not self.instance.pk:
            available = spare_part.stock_quantity
            if quantity_issued > available:
                self.add_error(
                    'quantity_issued',
                    f'Insufficient stock. Available: {available} units.'
                )
        return cleaned_data
