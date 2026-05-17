from django import forms

from .models import NumberPlateOrder, RTORegistration


class RTORegistrationForm(forms.ModelForm):
    class Meta:
        model  = RTORegistration
        fields = ('sales_order', 'form20_number', 'registration_number',
                  'rto_charges', 'registration_status')


class NumberPlateOrderForm(forms.ModelForm):
    class Meta:
        model  = NumberPlateOrder
        fields = ('rto', 'plate_number', 'vendor_name', 'issue_date', 'status')
        widgets = {
            'issue_date': forms.DateInput(attrs={'type': 'date'}),
        }
