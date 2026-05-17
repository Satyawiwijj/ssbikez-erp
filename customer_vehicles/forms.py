from django import forms

from customers.models import VehicleStock

from .models import CustomerVehicle


class CustomerVehicleForm(forms.ModelForm):
    class Meta:
        model  = CustomerVehicle
        fields = ('customer', 'vehicle', 'registration_no', 'purchase_date', 'insurance_expiry')
        widgets = {
            'purchase_date':    forms.DateInput(attrs={'type': 'date'}),
            'insurance_expiry': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only sold units can be linked to a customer vehicle
        self.fields['vehicle'].queryset = VehicleStock.objects.filter(
            stock_status=VehicleStock.StockStatus.SOLD
        ).select_related('bike_model')
