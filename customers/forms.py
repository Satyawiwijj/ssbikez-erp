import re

from django import forms
from accounts.forms import AccessibleFormMixin
from django.forms import inlineformset_factory

from .models import BikeModel, Customer, VehicleStock, VehicleMasterSettings, VehicleMasterSettingsItem


class CustomerForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = Customer
        fields = ('full_name', 'phone', 'email', 'address', 'state', 'aadhaar_no', 'pan_no')
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        if phone:
            if not re.fullmatch(r'[6-9]\d{9}', phone):
                raise forms.ValidationError('Enter a valid 10-digit Indian mobile number (starts with 6-9).')
            # Duplicate check (exclude current instance)
            qs = Customer.objects.filter(phone=phone)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('A customer with this phone number already exists.')
        return phone

    def clean_aadhaar_no(self):
        aadhaar = (self.cleaned_data.get('aadhaar_no') or '').strip()
        if aadhaar:
            digits = re.sub(r'\D', '', aadhaar)
            if len(digits) != 12:
                raise forms.ValidationError('Aadhaar number must be 12 digits.')
            qs = Customer.objects.filter(aadhaar_no=aadhaar)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('A customer with this Aadhaar number already exists.')
        return aadhaar

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if email:
            qs = Customer.objects.filter(email__iexact=email)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('A customer with this email address already exists.')
        return email


class BikeModelForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = BikeModel
        fields = ('brand', 'model_name', 'variant', 'fuel_type',
                  'available_colors', 'ex_showroom_price', 'dealer_cost_price')
        widgets = {
            'available_colors': forms.Textarea(attrs={'rows': 2}),
        }


class VehicleStockForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = VehicleStock
        fields = ('bike_model', 'branch', 'engine_no', 'chassis_no',
                  'color', 'stock_status', 'warehouse_location', 'purchase_date')
        widgets = {
            'purchase_date': forms.DateInput(attrs={'type': 'date'}),
        }


class VehicleMasterSettingsForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = VehicleMasterSettings
        fields = ('vehicle', 'has_exchange_vehicle', 'service_settings', 'exchange_vehicle_id')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service_settings'].required = False
        self.fields['exchange_vehicle_id'].required = False


class VehicleMasterSettingsItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = VehicleMasterSettingsItem
        fields = ('vehicle_name', 'model', 'chasis_no', 'code', 'engine', 'color', 'book_no', 'color_code')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vehicle_name'].required = False


VehicleMasterSettingsItemFormSet = inlineformset_factory(
    VehicleMasterSettings, VehicleMasterSettingsItem,
    form=VehicleMasterSettingsItemForm, extra=1, can_delete=True
)
