from django import forms
from accounts.forms import AccessibleFormMixin

from customers.models import VehicleStock

from .models import CustomerVehicle


class CustomerVehicleForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = CustomerVehicle
        fields = ('customer', 'vehicle', 'registration_no', 'purchase_date', 'insurance_expiry')
        widgets = {
            'purchase_date':    forms.DateInput(attrs={'type': 'date'}),
            'insurance_expiry': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Allow available or sold units to be linked to a customer vehicle
        self.fields['vehicle'].queryset = VehicleStock.objects.filter(
            stock_status__in=[VehicleStock.StockStatus.AVAILABLE, VehicleStock.StockStatus.SOLD]
        ).select_related('bike_model').order_by('stock_status', 'bike_model__model_name')

    def clean_vehicle(self):
        vehicle = self.cleaned_data.get('vehicle')
        if vehicle:
            qs = CustomerVehicle.objects.filter(vehicle=vehicle)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('This vehicle is already linked to a customer record.')
        return vehicle
