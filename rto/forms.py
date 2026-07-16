import re

from django import forms
from accounts.forms import AccessibleFormMixin
from django.forms import inlineformset_factory

from .models import (Form20Creation, NumberOrderEntryCreation, NumberPlateIssue,
                     NumberPlateOrder, NumberReceiptEntryCreation, RCBook, RCBookCreation,
                     RCBookIssue, RCBookIssueItem, RCHandOver, RegisterNumberMaster,
                     RegistrationArea, RegistrationNoCreation, RegpayCreation, RegpayCreationItem,
                     RegPayBaseAmount, RTOPayment, RTOPaymentItem, RTORegistration)

REGISTRATION_NUMBER_PATTERN = r'^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{1,4}$'


class RTORegistrationForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = RTORegistration
        fields = ('sales_order', 'form20_number', 'registration_number',
                  'rto_charges', 'registration_status')
        widgets = {
            'form20_number':       forms.TextInput(attrs={'placeholder': 'e.g. F20-2026-CBE-001'}),
            'registration_number': forms.TextInput(attrs={'placeholder': 'e.g. TN11CD5678'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['registration_status'].required = True
        self.fields['rto_charges'].required         = True
        self.fields['form20_number'].help_text      = (
            'Enter the Form 20 number from the RTO receipt, e.g. F20-2026-CBE-001'
        )
        self.fields['registration_number'].help_text = (
            'Vehicle registration number assigned by RTO, e.g. TN11CD5678'
        )
        self.fields['rto_charges'].help_text = 'Total RTO charges paid in ₹ (enter 0 if not yet paid).'

    def clean_form20_number(self):
        value = (self.cleaned_data.get('form20_number') or '').strip()
        if value and len(value) < 5:
            raise forms.ValidationError(
                'Form 20 number seems too short. Enter the full number, e.g. F20-2026-CBE-001.'
            )
        return value or None

    def clean_registration_number(self):
        value = (self.cleaned_data.get('registration_number') or '').strip().upper()
        if value and not re.match(REGISTRATION_NUMBER_PATTERN, value):
            raise forms.ValidationError(
                'Enter a valid registration number, e.g. TN11CD5678.'
            )
        return value or None

    def clean_rto_charges(self):
        from decimal import Decimal
        charges = self.cleaned_data.get('rto_charges')
        if charges is None:
            raise forms.ValidationError('RTO charges are required (enter 0 if not yet paid).')
        if charges < Decimal('0'):
            raise forms.ValidationError('RTO charges cannot be negative.')
        return charges


class NumberPlateOrderForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = NumberPlateOrder
        fields = ('rto', 'plate_number', 'vendor_name', 'issue_date', 'status')
        widgets = {
            'issue_date':   forms.DateInput(attrs={'type': 'date'}),
            'plate_number': forms.TextInput(attrs={'placeholder': 'e.g. TN11CD5678'}),
            'vendor_name':  forms.TextInput(attrs={'placeholder': 'Name of number plate vendor'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['plate_number'].required = True
        self.fields['vendor_name'].required  = True
        self.fields['status'].required       = True
        self.fields['plate_number'].help_text = 'Registration number printed on the plate, e.g. TN11CD5678'
        self.fields['vendor_name'].help_text  = 'Name of the vendor who manufactures/supplies the plate.'

    def clean_plate_number(self):
        value = (self.cleaned_data.get('plate_number') or '').strip().upper()
        if not value:
            raise forms.ValidationError('Plate number is required.')
        if not re.match(REGISTRATION_NUMBER_PATTERN, value):
            raise forms.ValidationError(
                'Enter a valid registration number for the plate, e.g. TN11CD5678.'
            )
        return value

    def clean_vendor_name(self):
        value = (self.cleaned_data.get('vendor_name') or '').strip()
        if not value:
            raise forms.ValidationError('Vendor name is required.')
        return value


class RCBookForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = RCBook
        fields = ('rto_registration', 'rc_number', 'issue_date',
                  'issued_to', 'status', 'hp_endorsed', 'hp_bank_name', 'notes')
        widgets = {
            'issue_date': forms.DateInput(attrs={'type': 'date'}),
            'notes':      forms.Textarea(attrs={'rows': 3}),
            'rc_number':  forms.TextInput(attrs={'placeholder': 'e.g. TN11CD5678-RC'}),
        }


# ===========================================================================
# GAP 19, 20 forms
# ===========================================================================

from .models import RegPayment, RTOIncome


class RegPaymentForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = RegPayment
        fields = ('payment_type', 'amount', 'receipt_number', 'payment_date', 'notes')
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class RTOIncomeForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = RTOIncome
        fields = ('income_type', 'amount', 'collected_from', 'date', 'notes')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


# ===========================================================================
# Phase 6 — new-vehicle RTO forms
# ===========================================================================

class RegistrationAreaForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = RegistrationArea
        fields = ('name', 'is_active')


class RegPayBaseAmountForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = RegPayBaseAmount
        fields = ('vehicle', 'amount')


class RegisterNumberMasterForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = RegisterNumberMaster
        fields = ('register_number', 'is_used')


class RCHandOverForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = RCHandOver
        fields = ('sales_order', 'rc_book_received', 'noc', 'vehicle_received',
                  'year_of_make', 'hp_endorsement', 'to_received', 'rc_book_number')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ('rc_book_received', 'noc', 'vehicle_received'):
            self.fields[f].required = True

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('rc_book_received') == 'yes' and not cleaned.get('rc_book_number'):
            self.add_error('rc_book_number', 'Required when RC Book Received is Yes.')
        return cleaned


class Form20CreationForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = Form20Creation
        fields = ('sales_order', 'registration_area', 'engine_no', 'frame_no', 'application_no')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['registration_area'].required = True


class RegistrationNoCreationForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = RegistrationNoCreation
        fields = ('sales_order', 'form20', 'registration_area', 'reg_no',
                  'frame_no', 'engine_no', 'status', 'remark')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['registration_area'].required = True


class RTOPaymentForm(AccessibleFormMixin, forms.ModelForm):
    reference_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)

    class Meta:
        model  = RTOPayment
        fields = ('direction', 'pay_type', 'cash_account', 'bank_name',
                  'agent_type', 'agent', 'reference_no', 'reference_date', 'payment_status')

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('direction') == 'expense' and not cleaned.get('agent_type'):
            self.add_error('agent_type', 'Required for Expense direction.')
        return cleaned


class RTOPaymentItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = RTOPaymentItem
        fields = ('sales_order', 'branch', 'flag_amount', 'fine_amount', 'license_amount')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ('branch', 'flag_amount', 'fine_amount', 'license_amount'):
            self.fields[f].required = False


RTOPaymentItemFormSet = inlineformset_factory(
    RTOPayment, RTOPaymentItem, form=RTOPaymentItemForm, extra=1, can_delete=True
)


class RegpayCreationForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = RegpayCreation
        fields = ('registration_area', 'supplier', 'transaction_charges',
                  'pending_amount', 'payment_status')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ('transaction_charges', 'pending_amount'):
            self.fields[f].required = False


class RegpayCreationItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = RegpayCreationItem
        fields = ('sales_order', 'vehicle_type', 'profit', 'amount_from_customer')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ('profit', 'amount_from_customer'):
            self.fields[f].required = False


RegpayCreationItemFormSet = inlineformset_factory(
    RegpayCreation, RegpayCreationItem, form=RegpayCreationItemForm, extra=1, can_delete=True
)


class NumberOrderEntryCreationForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = NumberOrderEntryCreation
        fields = ('sales_order', 'agent', 'registration_area', 'application_type',
                  'chassis_no', 'engine_no', 're_order')


class NumberReceiptEntryCreationForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = NumberReceiptEntryCreation
        fields = ('order_entry', 'agent', 'payment_type', 'rate', 'cgst', 'sgst', 'total')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['total'].required = False


class NumberPlateIssueForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = NumberPlateIssue
        fields = ('receipt_entry', 'issue_type', 'sub_dealer_name', 'transfer_to_branch',
                  'is_frame', 'frame', 'warehouse', 'rack', 'bin', 'frame_amount')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ('sub_dealer_name', 'transfer_to_branch', 'frame', 'warehouse', 'rack', 'bin'):
            self.fields[f].required = False


class RCBookCreationForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = RCBookCreation
        fields = ('rto_registration', 'agent', 'registration_area', 'post_by_rto', 'rc_number')


class RCBookIssueForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = RCBookIssue
        fields = ('rc_book_creation', 'issue_type', 'from_branch', 'to_branch', 'sub_dealer_name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ('from_branch', 'to_branch', 'sub_dealer_name'):
            self.fields[f].required = False


class RCBookIssueItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = RCBookIssueItem
        fields = ('exchange_vehicle', 'vehicle_number', 'party_name')


RCBookIssueItemFormSet = inlineformset_factory(
    RCBookIssue, RCBookIssueItem, form=RCBookIssueItemForm, extra=1, can_delete=True
)
