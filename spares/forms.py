from django import forms
from django.forms import inlineformset_factory
from .models import (
    SparesItem, SupplierQuote, SupplierQuoteItem,
    PurchaseOrder, PurchaseOrderItem,
    PurchaseInvoice, PurchaseInvoiceItem,
    CounterSale, CounterSaleItem,
    CounterSaleReturn, CounterSaleReturnItem,
    SparesIssueAlteration, SparesIssueAlterationItem,
)


class SparesItemForm(forms.ModelForm):
    class Meta:
        model = SparesItem
        exclude = ['item_code', 'created_at', 'updated_at', 'created_by']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            w = field.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs['class'] = 'form-check-input'
            elif isinstance(w, (forms.Select, forms.SelectMultiple)):
                w.attrs['class'] = 'form-select'
            elif isinstance(w, forms.Textarea):
                w.attrs.update({'class': 'form-control', 'rows': 3})
            else:
                w.attrs['class'] = 'form-control'

    def clean_sgst(self):
        from decimal import Decimal
        val = self.cleaned_data.get('sgst')
        if val is not None and val > Decimal('100'):
            raise forms.ValidationError('SGST rate cannot exceed 100%.')
        if val is not None and val < Decimal('0'):
            raise forms.ValidationError('SGST rate cannot be negative.')
        return val

    def clean_cgst(self):
        from decimal import Decimal
        val = self.cleaned_data.get('cgst')
        if val is not None and val > Decimal('100'):
            raise forms.ValidationError('CGST rate cannot exceed 100%.')
        if val is not None and val < Decimal('0'):
            raise forms.ValidationError('CGST rate cannot be negative.')
        return val

    def clean_max_discount(self):
        from decimal import Decimal
        val = self.cleaned_data.get('max_discount')
        if val is not None and val > Decimal('100'):
            raise forms.ValidationError('Maximum discount cannot exceed 100%.')
        if val is not None and val < Decimal('0'):
            raise forms.ValidationError('Maximum discount cannot be negative.')
        return val


class SupplierQuoteForm(forms.ModelForm):
    class Meta:
        model = SupplierQuote
        exclude = ['quote_no', 'created_at', 'updated_at', 'created_by',
                   'total_quantity', 'total_amount', 'grand_total']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valid_till': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'quotation_number': forms.TextInput(attrs={'class': 'form-control'}),
            'additional_discount_percent': forms.NumberInput(attrs={'class': 'form-control'}),
            'additional_discount_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'terms_and_conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_reverse_charge': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SupplierQuoteItemForm(forms.ModelForm):
    class Meta:
        model = SupplierQuoteItem
        fields = ['item', 'quantity', 'uom', 'rate', 'required_date']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select item-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'uom': forms.TextInput(attrs={'class': 'form-control'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'required_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


SupplierQuoteItemFormSet = inlineformset_factory(
    SupplierQuote, SupplierQuoteItem,
    form=SupplierQuoteItemForm, extra=1, can_delete=True
)


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        exclude = ['po_no', 'created_at', 'updated_at', 'created_by',
                   'total_quantity', 'total_amount', 'total_taxes', 'grand_total', 'supplier_name']
        widgets = {
            'date':        forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'required_by': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'supplier':      forms.Select(attrs={'class': 'form-select'}),
            'supplier_quote': forms.Select(attrs={'class': 'form-select'}),
            'status':        forms.Select(attrs={'class': 'form-select'}),
            'supplier_gstin': forms.TextInput(attrs={'class': 'form-control'}),
            'gst_category':  forms.TextInput(attrs={'class': 'form-control'}),
            'place_of_supply': forms.TextInput(attrs={'class': 'form-control'}),
            'terms_and_conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_reverse_charge':    forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'get_customer_order':   forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'get_estimation':       forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ['item', 'warehouse', 'quantity', 'uom', 'rate', 'required_by',
                  'used_qty', 'ordered_qty', 'average', 'stock_qty', 'one_month_qty']
        widgets = {
            'item':      forms.Select(attrs={'class': 'form-select item-select'}),
            'warehouse': forms.Select(attrs={'class': 'form-select'}),
            'quantity':  forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'uom':       forms.TextInput(attrs={'class': 'form-control'}),
            'rate':      forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'required_by': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'used_qty':    forms.NumberInput(attrs={'class': 'form-control'}),
            'ordered_qty': forms.NumberInput(attrs={'class': 'form-control'}),
            'average':     forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock_qty':   forms.NumberInput(attrs={'class': 'form-control'}),
            'one_month_qty': forms.NumberInput(attrs={'class': 'form-control'}),
        }


PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder, PurchaseOrderItem,
    form=PurchaseOrderItemForm, extra=1, can_delete=True
)


class PurchaseInvoiceForm(forms.ModelForm):
    class Meta:
        model = PurchaseInvoice
        exclude = ['invoice_no', 'created_at', 'updated_at', 'created_by',
                   'total_quantity', 'total_amount', 'total_sgst', 'total_cgst',
                   'total_taxes', 'grand_total']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'purchase_order': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'supplier_gstin': forms.TextInput(attrs={'class': 'form-control'}),
            'gst_category': forms.TextInput(attrs={'class': 'form-control'}),
            'place_of_supply': forms.TextInput(attrs={'class': 'form-control'}),
            'payment_status': forms.TextInput(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_reverse_charge': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PurchaseInvoiceItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseInvoiceItem
        fields = ['item', 'warehouse', 'rack', 'bin', 'quantity', 'uom', 'rate', 'sgst', 'cgst']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select item-select'}),
            'warehouse': forms.Select(attrs={'class': 'form-select'}),
            'rack': forms.Select(attrs={'class': 'form-select'}),
            'bin': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'uom': forms.TextInput(attrs={'class': 'form-control'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'sgst': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cgst': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


PurchaseInvoiceItemFormSet = inlineformset_factory(
    PurchaseInvoice, PurchaseInvoiceItem,
    form=PurchaseInvoiceItemForm, extra=1, can_delete=True
)


class CounterSaleForm(forms.ModelForm):
    class Meta:
        model = CounterSale
        exclude = ['sale_no', 'created_at', 'updated_at', 'created_by',
                   'total_qty', 'total_amount', 'payment_status']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'customer': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'gst_category': forms.TextInput(attrs={'class': 'form-control'}),
            'godown': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'pay_type': forms.Select(attrs={'class': 'form-select'}),
            'discount_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_warranty': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CounterSaleItemForm(forms.ModelForm):
    class Meta:
        model = CounterSaleItem
        fields = ['item', 'rack', 'bin', 'quantity', 'rate', 'gst_percent']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select item-select'}),
            'rack': forms.Select(attrs={'class': 'form-select'}),
            'bin': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'gst_percent': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


CounterSaleItemFormSet = inlineformset_factory(
    CounterSale, CounterSaleItem,
    form=CounterSaleItemForm, extra=1, can_delete=True
)


class CounterSaleReturnForm(forms.ModelForm):
    class Meta:
        model = CounterSaleReturn
        exclude = ['return_no', 'created_at', 'created_by', 'total_amount']
        widgets = {
            'original_sale': forms.Select(attrs={'class': 'form-select'}),
            'return_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'stock_return_done': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'amount_refund_done': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CounterSaleReturnItemForm(forms.ModelForm):
    class Meta:
        model = CounterSaleReturnItem
        fields = ['item', 'quantity', 'rate']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select item-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


CounterSaleReturnItemFormSet = inlineformset_factory(
    CounterSaleReturn, CounterSaleReturnItem,
    form=CounterSaleReturnItemForm, extra=1, can_delete=True
)


class SparesIssueAlterationForm(forms.ModelForm):
    class Meta:
        model = SparesIssueAlteration
        exclude = ['created_at', 'created_by', 'spares_total', 'labour_total',
                   'outwork_total', 'total', 'updated_total']
        widgets = {
            'job_card': forms.TextInput(attrs={'class': 'form-control'}),
            'godown': forms.Select(attrs={'class': 'form-select'}),
            'job_type': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'discount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


class SparesIssueAlterationItemForm(forms.ModelForm):
    class Meta:
        model = SparesIssueAlterationItem
        fields = ['item', 'quantity', 'rack', 'bin', 'rate', 'discount_percent']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select item-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'rack': forms.Select(attrs={'class': 'form-select'}),
            'bin': forms.Select(attrs={'class': 'form-select'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount_percent': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


SparesIssueAlterationItemFormSet = inlineformset_factory(
    SparesIssueAlteration, SparesIssueAlterationItem,
    form=SparesIssueAlterationItemForm, extra=1, can_delete=True
)
