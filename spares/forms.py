from django import forms
from accounts.forms import AccessibleFormMixin
from django.forms import inlineformset_factory
from .models import (
    SparesItem, SupplierQuote, SupplierQuoteItem, SupplierQuoteTax,
    PurchaseOrder, PurchaseOrderItem, PurchaseOrderTax,
    PurchaseInvoice, PurchaseInvoiceItem, PurchaseInvoiceTax,
    CounterSale, CounterSaleItem,
    CounterSaleReturn, CounterSaleReturnItem,
    SparesIssueAlteration, SparesIssueAlterationItem, SparesIssueAlterationDeletedItem,
    StockTransfer, StockTransferItem,
    StockCountUpdate, StockCountItem,
    RequestSupplierQuote, RequestSupplierQuoteItem,
    SparesPurchaseEstimationMaster, SparesPurchaseEstimationItem, SparesPurchaseEstimationLabor,
    ServiceSparesIssueReturn, ServiceSparesIssueReturnItem,
    VehicleSparesMaster, SparesMRPPriceRevision, SparesMRPPriceRevisionItem,
    SparesProfitPercentageSettings, SparesPurchaseQtyDaysSettings,
    ServiceSparesWarranty, ServiceSparesWarrantyItem,
)


class SparesItemForm(AccessibleFormMixin, forms.ModelForm):
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


class SupplierQuoteForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = SupplierQuote
        exclude = ['quote_no', 'created_at', 'updated_at', 'created_by',
                   'total_quantity', 'total_amount', 'total_taxes', 'grand_total']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valid_till': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'request_quotation': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'quotation_number': forms.TextInput(attrs={'class': 'form-control'}),
            'additional_discount_percent': forms.NumberInput(attrs={'class': 'form-control'}),
            'additional_discount_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'terms_and_conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_reverse_charge': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['request_quotation'].required = False


class SupplierQuoteItemForm(AccessibleFormMixin, forms.ModelForm):
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


class _TaxChargeLineFormBase(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        fields = ['apply_type', 'account_head', 'tax_rate', 'amount']
        widgets = {
            'apply_type':   forms.Select(attrs={'class': 'form-select', 'style': 'min-width:160px'}),
            'account_head': forms.TextInput(attrs={'class': 'form-control', 'style': 'min-width:200px', 'placeholder': 'e.g. Input Tax CGST'}),
            'tax_rate':     forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:80px'}),
            'amount':       forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:100px'}),
        }


class SupplierQuoteTaxForm(_TaxChargeLineFormBase):
    class Meta(_TaxChargeLineFormBase.Meta):
        model = SupplierQuoteTax


SupplierQuoteTaxFormSet = inlineformset_factory(
    SupplierQuote, SupplierQuoteTax,
    form=SupplierQuoteTaxForm, extra=1, can_delete=True
)


class PurchaseOrderForm(AccessibleFormMixin, forms.ModelForm):
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
            'customer_order':       forms.Select(attrs={'class': 'form-select'}),
            'estimation':           forms.Select(attrs={'class': 'form-select'}),
            'load_status':          forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # customer_order/estimation only make sense when their matching Get-*
        # checkbox is set -- reference behavior, not enforced at the model layer.
        self.fields['customer_order'].required = False
        self.fields['estimation'].required = False


class PurchaseOrderItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ['item', 'warehouse', 'quantity', 'uom', 'rate', 'required_by',
                  'used_qty', 'ordered_qty', 'average', 'stock_qty', 'one_month_qty',
                  'part_no', 'delivery_need_qty', 'branch']
        widgets = {
            'item':      forms.Select(attrs={'class': 'form-select item-select', 'style': 'min-width:180px'}),
            'warehouse': forms.Select(attrs={'class': 'form-select', 'style': 'min-width:140px'}),
            'quantity':  forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'style': 'min-width:70px'}),
            'uom':       forms.TextInput(attrs={'class': 'form-control', 'style': 'min-width:60px'}),
            'rate':      forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:90px'}),
            'required_by': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'style': 'min-width:130px'}),
            'used_qty':    forms.NumberInput(attrs={'class': 'form-control', 'style': 'min-width:70px'}),
            'ordered_qty': forms.NumberInput(attrs={'class': 'form-control', 'style': 'min-width:70px'}),
            'average':     forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:70px'}),
            'stock_qty':   forms.NumberInput(attrs={'class': 'form-control', 'style': 'min-width:70px'}),
            'one_month_qty': forms.NumberInput(attrs={'class': 'form-control', 'style': 'min-width:70px'}),
            'part_no':     forms.TextInput(attrs={'class': 'form-control', 'style': 'min-width:90px'}),
            'delivery_need_qty': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'style': 'min-width:80px'}),
            'branch':      forms.Select(attrs={'class': 'form-select', 'style': 'min-width:120px'}),
        }


PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder, PurchaseOrderItem,
    form=PurchaseOrderItemForm, extra=1, can_delete=True
)


class PurchaseOrderTaxForm(_TaxChargeLineFormBase):
    class Meta(_TaxChargeLineFormBase.Meta):
        model = PurchaseOrderTax


PurchaseOrderTaxFormSet = inlineformset_factory(
    PurchaseOrder, PurchaseOrderTax,
    form=PurchaseOrderTaxForm, extra=1, can_delete=True
)


class PurchaseInvoiceForm(AccessibleFormMixin, forms.ModelForm):
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
            'payment_type': forms.Select(attrs={'class': 'form-select'}),
            'cash_account': forms.TextInput(attrs={'class': 'form-control'}),
            'pay_mode': forms.TextInput(attrs={'class': 'form-control'}),
            'has_tcs': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tcs_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_reverse_charge': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PurchaseInvoiceItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = PurchaseInvoiceItem
        fields = ['item', 'warehouse', 'rack', 'bin', 'quantity', 'uom', 'rate', 'sgst', 'cgst',
                  'item_category', 'part_no']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select item-select', 'style': 'min-width:180px'}),
            'warehouse': forms.Select(attrs={'class': 'form-select', 'style': 'min-width:140px'}),
            'rack': forms.Select(attrs={'class': 'form-select', 'style': 'min-width:80px'}),
            'bin': forms.Select(attrs={'class': 'form-select', 'style': 'min-width:80px'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'style': 'min-width:70px'}),
            'uom': forms.TextInput(attrs={'class': 'form-control', 'style': 'min-width:60px'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:90px'}),
            'sgst': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:70px'}),
            'cgst': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:70px'}),
            'item_category': forms.TextInput(attrs={'class': 'form-control', 'style': 'min-width:100px'}),
            'part_no': forms.TextInput(attrs={'class': 'form-control', 'style': 'min-width:90px'}),
        }


PurchaseInvoiceItemFormSet = inlineformset_factory(
    PurchaseInvoice, PurchaseInvoiceItem,
    form=PurchaseInvoiceItemForm, extra=1, can_delete=True
)


class PurchaseInvoiceTaxForm(_TaxChargeLineFormBase):
    class Meta(_TaxChargeLineFormBase.Meta):
        model = PurchaseInvoiceTax


PurchaseInvoiceTaxFormSet = inlineformset_factory(
    PurchaseInvoice, PurchaseInvoiceTax,
    form=PurchaseInvoiceTaxForm, extra=1, can_delete=True
)


class CounterSaleForm(AccessibleFormMixin, forms.ModelForm):
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
            'sale_type': forms.Select(attrs={'class': 'form-select'}),
            'spot_sale': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ledger_voucher_no': forms.Select(attrs={'class': 'form-select'}),
            'accounts_from': forms.TextInput(attrs={'class': 'form-control'}),
            'accounts_to': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_ref_no': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_ref_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'balance_delivery_qty': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'counter_sale_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ledger_voucher_no'].required = False


class CounterSaleItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = CounterSaleItem
        fields = ['item', 'rack', 'bin', 'quantity', 'rate', 'gst_percent',
                  'delivery_balance_qty', 'stock_qty', 'issue_status']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select item-select', 'style': 'min-width:180px'}),
            'rack': forms.Select(attrs={'class': 'form-select', 'style': 'min-width:80px'}),
            'bin': forms.Select(attrs={'class': 'form-select', 'style': 'min-width:80px'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'style': 'min-width:70px'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:90px'}),
            'gst_percent': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:70px'}),
            'delivery_balance_qty': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'style': 'min-width:90px'}),
            'stock_qty': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'style': 'min-width:80px'}),
            'issue_status': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


CounterSaleItemFormSet = inlineformset_factory(
    CounterSale, CounterSaleItem,
    form=CounterSaleItemForm, extra=1, can_delete=True
)


class CounterSaleReturnForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = CounterSaleReturn
        exclude = ['return_no', 'created_at', 'created_by', 'total_amount']
        widgets = {
            'original_sale': forms.Select(attrs={'class': 'form-select'}),
            'return_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'stock_return_done': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'amount_refund_done': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'godown': forms.Select(attrs={'class': 'form-select'}),
            'gst_category': forms.TextInput(attrs={'class': 'form-control'}),
            'accounts_from': forms.TextInput(attrs={'class': 'form-control'}),
            'accounts_to': forms.TextInput(attrs={'class': 'form-control'}),
            'advance_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


class CounterSaleReturnItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = CounterSaleReturnItem
        fields = ['item', 'quantity', 'return_qty', 'rate', 'issue_status', 'delivery_balance_qty', 'stock_qty']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select item-select', 'style': 'min-width:180px'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'style': 'min-width:70px'}),
            'return_qty': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'style': 'min-width:70px'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:90px'}),
            'issue_status': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'delivery_balance_qty': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'style': 'min-width:90px'}),
            'stock_qty': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'style': 'min-width:80px'}),
        }


CounterSaleReturnItemFormSet = inlineformset_factory(
    CounterSaleReturn, CounterSaleReturnItem,
    form=CounterSaleReturnItemForm, extra=1, can_delete=True
)


class SparesIssueAlterationForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = SparesIssueAlteration
        exclude = ['created_at', 'created_by', 'spares_total', 'labour_total',
                   'outwork_total', 'total', 'updated_total']
        widgets = {
            'job_card': forms.Select(attrs={'class': 'form-select'}),
            'used_vehicle_job_card': forms.Select(attrs={'class': 'form-select'}),
            'mechanic': forms.Select(attrs={'class': 'form-select'}),
            'godown': forms.Select(attrs={'class': 'form-select'}),
            'job_type': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'discount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'engine_no': forms.TextInput(attrs={'class': 'form-control'}),
            'register_no': forms.TextInput(attrs={'class': 'form-control'}),
            'frame_no': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'vehicle_code': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_no': forms.TextInput(attrs={'class': 'form-control'}),
            'user': forms.Select(attrs={'class': 'form-select'}),
            'service_invoice_discount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'brand': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].required = False


class SparesIssueAlterationItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = SparesIssueAlterationItem
        fields = ['item', 'quantity', 'rack', 'bin', 'uom', 'rate', 'sgst', 'cgst', 'discount_percent',
                  'last_return_quantity', 'tax_rate', 'ref_quantity', 'stock_balance', 'is_returned']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select item-select', 'style': 'min-width:180px'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'style': 'min-width:70px'}),
            'rack': forms.Select(attrs={'class': 'form-select', 'style': 'min-width:80px'}),
            'bin': forms.Select(attrs={'class': 'form-select', 'style': 'min-width:80px'}),
            'uom': forms.TextInput(attrs={'class': 'form-control', 'style': 'min-width:70px'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:90px'}),
            'sgst': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:70px'}),
            'cgst': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:70px'}),
            'discount_percent': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:70px'}),
            'last_return_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'style': 'min-width:90px'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:70px'}),
            'ref_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'style': 'min-width:80px'}),
            'stock_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'style': 'min-width:80px'}),
            'is_returned': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SparesIssueAlterationDeletedItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = SparesIssueAlterationDeletedItem
        fields = ['item', 'quantity', 'rack', 'bin', 'rate', 'uom']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select item-select', 'style': 'min-width:180px'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'style': 'min-width:70px'}),
            'rack': forms.Select(attrs={'class': 'form-select', 'style': 'min-width:80px'}),
            'bin': forms.Select(attrs={'class': 'form-select', 'style': 'min-width:80px'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:90px'}),
            'uom': forms.TextInput(attrs={'class': 'form-control', 'style': 'min-width:70px'}),
        }


SparesIssueAlterationDeletedItemFormSet = inlineformset_factory(
    SparesIssueAlteration, SparesIssueAlterationDeletedItem,
    form=SparesIssueAlterationDeletedItemForm, extra=1, can_delete=True
)


SparesIssueAlterationItemFormSet = inlineformset_factory(
    SparesIssueAlteration, SparesIssueAlterationItem,
    form=SparesIssueAlterationItemForm, extra=1, can_delete=True
)


# ---------------------------------------------------------------------------
# Phase 7a — Stock Transfer / Stock Count Update / Request Supplier Quote
# ---------------------------------------------------------------------------

class StockTransferForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = StockTransfer
        fields = ['date_and_time', 'warehouse', 'branch']
        widgets = {
            'date_and_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'warehouse': forms.Select(attrs={'class': 'form-select'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
        }


class StockTransferItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = StockTransferItem
        fields = ['item', 'quantity', 'rate', 'uom', 'from_rack', 'from_bin',
                  'to_warehouse', 'to_rack', 'to_bin']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select item-select', 'style': 'min-width:180px'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'style': 'min-width:80px'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:90px'}),
            'uom': forms.TextInput(attrs={'class': 'form-control', 'style': 'min-width:70px'}),
            'from_rack': forms.Select(attrs={'class': 'form-select', 'style': 'min-width:100px'}),
            'from_bin': forms.Select(attrs={'class': 'form-select', 'style': 'min-width:100px'}),
            'to_warehouse': forms.Select(attrs={'class': 'form-select', 'style': 'min-width:140px'}),
            'to_rack': forms.Select(attrs={'class': 'form-select', 'style': 'min-width:100px'}),
            'to_bin': forms.Select(attrs={'class': 'form-select', 'style': 'min-width:100px'}),
        }


StockTransferItemFormSet = inlineformset_factory(
    StockTransfer, StockTransferItem, form=StockTransferItemForm, extra=1, can_delete=True
)


class StockCountUpdateForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = StockCountUpdate
        fields = ['date_and_time', 'warehouse', 'branch']
        widgets = {
            'date_and_time': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'warehouse': forms.Select(attrs={'class': 'form-select'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
        }


class StockCountItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = StockCountItem
        fields = ['item', 'rack', 'bin', 'rate', 'counted_qty']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select item-select', 'style': 'min-width:180px'}),
            'rack': forms.Select(attrs={'class': 'form-select', 'style': 'min-width:100px'}),
            'bin': forms.Select(attrs={'class': 'form-select', 'style': 'min-width:100px'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:90px'}),
            'counted_qty': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'style': 'min-width:100px'}),
        }


StockCountItemFormSet = inlineformset_factory(
    StockCountUpdate, StockCountItem, form=StockCountItemForm, extra=1, can_delete=True
)


class RequestSupplierQuoteForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = RequestSupplierQuote
        fields = ['date', 'suppliers']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'suppliers': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }


class RequestSupplierQuoteItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = RequestSupplierQuoteItem
        fields = ['spare', 'qty', 'uom']
        widgets = {
            'spare': forms.Select(attrs={'class': 'form-select item-select', 'style': 'min-width:180px'}),
            'qty': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'style': 'min-width:80px'}),
            'uom': forms.TextInput(attrs={'class': 'form-control', 'style': 'min-width:70px'}),
        }


RequestSupplierQuoteItemFormSet = inlineformset_factory(
    RequestSupplierQuote, RequestSupplierQuoteItem,
    form=RequestSupplierQuoteItemForm, extra=1, can_delete=True
)


# ---------------------------------------------------------------------------
# Phase 7b — Spares Purchase Estimation Master
# ---------------------------------------------------------------------------

class SparesPurchaseEstimationMasterForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = SparesPurchaseEstimationMaster
        fields = ['date', 'customer_name', 'chasis_no', 'insurance_name',
                  'vehicle_code', 'vehicle_name']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'chasis_no': forms.TextInput(attrs={'class': 'form-control'}),
            'insurance_name': forms.Select(attrs={'class': 'form-select'}),
            'vehicle_code': forms.TextInput(attrs={'class': 'form-control'}),
            'vehicle_name': forms.TextInput(attrs={'class': 'form-control'}),
        }


class SparesPurchaseEstimationItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = SparesPurchaseEstimationItem
        fields = ['item', 'qty', 'amount', 'uom', 'confirm', 'gst']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select item-select', 'style': 'min-width:180px'}),
            'qty': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'style': 'min-width:80px'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:90px'}),
            'uom': forms.TextInput(attrs={'class': 'form-control', 'style': 'min-width:60px'}),
            'confirm': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'gst': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:70px'}),
        }


SparesPurchaseEstimationItemFormSet = inlineformset_factory(
    SparesPurchaseEstimationMaster, SparesPurchaseEstimationItem,
    form=SparesPurchaseEstimationItemForm, extra=1, can_delete=True
)


class SparesPurchaseEstimationLaborForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = SparesPurchaseEstimationLabor
        fields = ['date', 'labor_name', 'quantity', 'amount', 'sgst', 'cgst']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'style': 'min-width:130px'}),
            'labor_name': forms.Select(attrs={'class': 'form-select', 'style': 'min-width:150px'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:70px'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:90px'}),
            'sgst': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:70px'}),
            'cgst': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:70px'}),
        }


SparesPurchaseEstimationLaborFormSet = inlineformset_factory(
    SparesPurchaseEstimationMaster, SparesPurchaseEstimationLabor,
    form=SparesPurchaseEstimationLaborForm, extra=1, can_delete=True
)


# ---------------------------------------------------------------------------
# Phase 7c — Service Spares Issue Return
# ---------------------------------------------------------------------------

class ServiceSparesIssueReturnForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = ServiceSparesIssueReturn
        fields = ['spares_issue', 'job_card', 'phone_number', 'frame_no', 'register_no',
                  'party_name', 'spares_issue_date', 'godown', 'stock_return_done']
        widgets = {
            'spares_issue': forms.Select(attrs={'class': 'form-select'}),
            'job_card': forms.Select(attrs={'class': 'form-select'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'frame_no': forms.TextInput(attrs={'class': 'form-control'}),
            'register_no': forms.TextInput(attrs={'class': 'form-control'}),
            'party_name': forms.TextInput(attrs={'class': 'form-control'}),
            'spares_issue_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'godown': forms.Select(attrs={'class': 'form-select'}),
            'stock_return_done': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['job_card'].required = False


class ServiceSparesIssueReturnItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = ServiceSparesIssueReturnItem
        fields = ['item', 'rack', 'bin', 'rate', 'uom', 'last_return_quantity',
                  'return_qty', 'gst', 'tax_rate', 'sgst', 'cgst',
                  'discount_percentage', 'is_returned', 'ref_quantity', 'stock_balance']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select item-select', 'style': 'min-width:180px'}),
            'rack': forms.Select(attrs={'class': 'form-select', 'style': 'min-width:80px'}),
            'bin': forms.Select(attrs={'class': 'form-select', 'style': 'min-width:80px'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:90px'}),
            'uom': forms.TextInput(attrs={'class': 'form-control', 'style': 'min-width:70px'}),
            'last_return_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'style': 'min-width:90px'}),
            'return_qty': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'style': 'min-width:80px'}),
            'gst': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:70px'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:70px'}),
            'sgst': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:70px'}),
            'cgst': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:70px'}),
            'discount_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:70px'}),
            'is_returned': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ref_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'style': 'min-width:80px'}),
            'stock_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'style': 'min-width:80px'}),
        }


ServiceSparesIssueReturnItemFormSet = inlineformset_factory(
    ServiceSparesIssueReturn, ServiceSparesIssueReturnItem,
    form=ServiceSparesIssueReturnItemForm, extra=1, can_delete=True
)


# ---------------------------------------------------------------------------
# Phase 7d — Vehicle Spares Master / MRP Prices / Settings Singles /
# Service Spares Warranty
# ---------------------------------------------------------------------------

class VehicleSparesMasterForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = VehicleSparesMaster
        fields = ['spare', 'profit_percentage', 'purchase_rate', 'mrp_rate']
        widgets = {
            'spare': forms.Select(attrs={'class': 'form-select'}),
            'profit_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'purchase_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'mrp_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


class SparesMRPPriceRevisionForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = SparesMRPPriceRevision
        fields = ['date', 'price_list']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'price_list': forms.Select(attrs={'class': 'form-select'}),
        }


class SparesMRPPriceRevisionItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = SparesMRPPriceRevisionItem
        fields = ['item', 'current_price', 'updated_price']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select item-select', 'style': 'min-width:180px'}),
            'current_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:90px'}),
            'updated_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:90px'}),
        }


SparesMRPPriceRevisionItemFormSet = inlineformset_factory(
    SparesMRPPriceRevision, SparesMRPPriceRevisionItem,
    form=SparesMRPPriceRevisionItemForm, extra=1, can_delete=True
)


class SparesProfitPercentageSettingsForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = SparesProfitPercentageSettings
        fields = ['with_mrp', 'without_mrp']
        widgets = {
            'with_mrp': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'without_mrp': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


class SparesPurchaseQtyDaysSettingsForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = SparesPurchaseQtyDaysSettings
        fields = ['used_or_order_qty_days']
        widgets = {
            'used_or_order_qty_days': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class ServiceSparesWarrantyForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = ServiceSparesWarranty
        exclude = ['warranty_no', 'created_at', 'created_by', 'docstatus', 'amended_from',
                   'submitted_at', 'submitted_by', 'cancelled_at', 'cancelled_by']
        widgets = {
            'vehicle_number': forms.TextInput(attrs={'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'claim_no': forms.TextInput(attrs={'class': 'form-control'}),
            'claim_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'parts_dispatch_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'claim_received_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'invoice_no': forms.TextInput(attrs={'class': 'form-control'}),
            'invoice_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'chasis_no': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'vehicle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'history': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ndp_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'dispatch_on': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'dock_no': forms.TextInput(attrs={'class': 'form-control'}),
            'claim_register_in_pymidol': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'generate_invoice_in_pymidol': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'courier_parts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'courier_invoice_bill_on': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'claim_for': forms.TextInput(attrs={'class': 'form-control'}),
            'payment_received_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'brand': forms.Select(attrs={'class': 'form-select'}),
        }


class ServiceSparesWarrantyItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = ServiceSparesWarrantyItem
        fields = ['item', 'claim_warranty_amount', 'sgst', 'cgst', 'ndp']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select item-select', 'style': 'min-width:180px'}),
            'claim_warranty_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:100px'}),
            'sgst': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:70px'}),
            'cgst': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:70px'}),
            'ndp': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'min-width:90px'}),
        }


ServiceSparesWarrantyItemFormSet = inlineformset_factory(
    ServiceSparesWarranty, ServiceSparesWarrantyItem,
    form=ServiceSparesWarrantyItemForm, extra=1, can_delete=True
)
