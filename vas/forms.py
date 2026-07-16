from django import forms
from accounts.forms import AccessibleFormMixin
from django.forms import inlineformset_factory

from .models import (AMCPackage, AMCType, ProtectionPlusPackage, RSAPackage, RSAType,
                     RSACreation, VASSupplierInvoice, VASSupplierInvoiceItem, WarrantyType)

_DATE_WIDGET = forms.DateInput(attrs={'type': 'date'})


# ---------------------------------------------------------------------------
# Type masters
# ---------------------------------------------------------------------------

class AMCTypeForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = AMCType
        fields = ('code', 'name', 'amc_validity_days', 'amc_amount', 'hsn_code',
                  'ss_bikes', 'yamaha', 'deactivate_amc', 'vehicle_type',
                  'no_of_service', 'water_wash_count_free', 'service_interval_days',
                  'grace_days', 'is_active')


class RSATypeForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = RSAType
        fields = ('code', 'name', 'rsa_amount', 'hsn_code', 'is_active')


class WarrantyTypeForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = WarrantyType
        fields = ('code', 'name', 'hsn_code', 'is_active')


# ---------------------------------------------------------------------------
# Sale-side packages
# ---------------------------------------------------------------------------

class AMCPackageForm(AccessibleFormMixin, forms.ModelForm):
    start_date = forms.DateField(widget=_DATE_WIDGET, required=False)
    end_date   = forms.DateField(widget=_DATE_WIDGET, required=False)

    class Meta:
        model  = AMCPackage
        fields = ('customer_vehicle', 'amc_type', 'sales_order', 'invoice',
                  'start_date', 'end_date', 'amount', 'gst_amount', 'without_gst_amount',
                  'vehicle_number', 'chasis_number', 'ss_bikes', 'yamaha', 'status')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ('sales_order', 'invoice', 'gst_amount', 'without_gst_amount'):
            self.fields[f].required = False
        # amc_type/amount have blank=True/null=True at the model level (so a stub package
        # could in principle be built up server-side without them yet), but the create form
        # must not let a user-submitted package through without them -- reproduced a blank
        # submission being silently accepted before this fix.
        for f in ('amc_type', 'amount'):
            self.fields[f].required = True


class RSAPackageForm(AccessibleFormMixin, forms.ModelForm):
    start_date = forms.DateField(widget=_DATE_WIDGET, required=False)
    end_date   = forms.DateField(widget=_DATE_WIDGET, required=False)

    class Meta:
        model  = RSAPackage
        fields = ('customer_vehicle', 'rsa_type', 'sales_order', 'invoice', 'rsa_portal_no',
                  'start_date', 'end_date', 'amount', 'gst_amount', 'without_gst_amount', 'status')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ('sales_order', 'invoice', 'gst_amount', 'without_gst_amount'):
            self.fields[f].required = False
        for f in ('rsa_type', 'amount'):
            self.fields[f].required = True


class ProtectionPlusPackageForm(AccessibleFormMixin, forms.ModelForm):
    start_date = forms.DateField(widget=_DATE_WIDGET, required=False)
    end_date   = forms.DateField(widget=_DATE_WIDGET, required=False)

    class Meta:
        model  = ProtectionPlusPackage
        fields = ('customer_vehicle', 'warranty_type', 'sales_order', 'invoice',
                  'start_date', 'end_date', 'amount', 'gst_amount', 'without_gst_amount', 'status')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ('sales_order', 'invoice', 'gst_amount', 'without_gst_amount'):
            self.fields[f].required = False
        for f in ('warranty_type', 'amount'):
            self.fields[f].required = True


# ---------------------------------------------------------------------------
# RSA Creation
# ---------------------------------------------------------------------------

class RSACreationForm(AccessibleFormMixin, forms.ModelForm):
    expected_date = forms.DateField(widget=_DATE_WIDGET, required=False)

    class Meta:
        model  = RSACreation
        fields = ('rsa_type', 'rsa_amount', 'supplier', 'expected_date')


# ---------------------------------------------------------------------------
# VAS Supplier Invoice
# ---------------------------------------------------------------------------

class VASSupplierInvoiceForm(AccessibleFormMixin, forms.ModelForm):
    invoice_date  = forms.DateField(widget=_DATE_WIDGET)
    expected_date = forms.DateField(widget=_DATE_WIDGET, required=False)

    class Meta:
        model  = VASSupplierInvoice
        fields = ('supplier', 'invoice_date', 'branch', 'payment_type', 'pay_mode',
                  'payment_status', 'expected_date', 'cash_account',
                  'total_amount', 'pending_amount')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ('total_amount', 'pending_amount'):
            self.fields[f].required = False


class VASSupplierInvoiceItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = VASSupplierInvoiceItem
        fields = ('amc_type', 'rsa_type', 'warranty_type', 'quantity', 'hsn_code', 'rate', 'amount')


VASSupplierInvoiceItemFormSet = inlineformset_factory(
    VASSupplierInvoice, VASSupplierInvoiceItem, form=VASSupplierInvoiceItemForm,
    extra=1, can_delete=True
)
