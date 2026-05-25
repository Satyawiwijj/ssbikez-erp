import re

from django import forms

from .models import NumberPlateOrder, RTORegistration


class RTORegistrationForm(forms.ModelForm):
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
        if value and not re.match(r'^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{1,4}$', value):
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


class NumberPlateOrderForm(forms.ModelForm):
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
        if not re.match(r'^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{1,4}$', value):
            raise forms.ValidationError(
                'Enter a valid registration number for the plate, e.g. TN11CD5678.'
            )
        return value

    def clean_vendor_name(self):
        value = (self.cleaned_data.get('vendor_name') or '').strip()
        if not value:
            raise forms.ValidationError('Vendor name is required.')
        return value
