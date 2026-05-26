from django import forms

from .models import AMCPackage, ProtectionPlusPackage, RSAPackage

_DATE_WIDGET = forms.DateInput(attrs={'type': 'date'})


class AMCPackageForm(forms.ModelForm):
    start_date = forms.DateField(widget=_DATE_WIDGET, required=False)
    end_date   = forms.DateField(widget=_DATE_WIDGET, required=False)

    class Meta:
        model  = AMCPackage
        fields = ('customer_vehicle', 'package_name', 'start_date',
                  'end_date', 'amount', 'status')


class RSAPackageForm(forms.ModelForm):
    start_date = forms.DateField(widget=_DATE_WIDGET, required=False)
    end_date   = forms.DateField(widget=_DATE_WIDGET, required=False)

    class Meta:
        model  = RSAPackage
        fields = ('customer_vehicle', 'provider_name', 'start_date',
                  'end_date', 'amount', 'status')


class ProtectionPlusPackageForm(forms.ModelForm):
    start_date = forms.DateField(widget=_DATE_WIDGET, required=False)
    end_date   = forms.DateField(widget=_DATE_WIDGET, required=False)

    class Meta:
        model  = ProtectionPlusPackage
        fields = ('customer_vehicle', 'package_name', 'provider_name',
                  'start_date', 'end_date', 'amount', 'status')
