from django import forms

from .models import BikeModel, Customer, VehicleStock


class CustomerForm(forms.ModelForm):
    class Meta:
        model  = Customer
        fields = ('full_name', 'phone', 'email', 'address', 'aadhaar_no', 'pan_no')
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }


class BikeModelForm(forms.ModelForm):
    class Meta:
        model  = BikeModel
        fields = ('brand', 'model_name', 'variant', 'fuel_type',
                  'available_colors', 'ex_showroom_price')
        widgets = {
            'available_colors': forms.Textarea(attrs={'rows': 2}),
        }


class VehicleStockForm(forms.ModelForm):
    class Meta:
        model  = VehicleStock
        fields = ('bike_model', 'branch', 'engine_no', 'chassis_no',
                  'color', 'stock_status', 'warehouse_location', 'purchase_date')
        widgets = {
            'purchase_date': forms.DateInput(attrs={'type': 'date'}),
        }
