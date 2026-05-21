from django import forms
from django.utils import timezone

from customers.models import VehicleStock

from .models import (ExchangeVehicle, SalesAppointment, SalesFeedback,
                     SalesEnquiry, VehicleDelivery, VehicleSalesOrder)


class SalesEnquiryForm(forms.ModelForm):
    class Meta:
        model  = SalesEnquiry
        fields = ('customer', 'sales_executive', 'bike_model', 'branch',
                  'enquiry_source', 'status', 'remarks')
        widgets = {
            'remarks': forms.Textarea(attrs={'rows': 3}),
        }


class SalesAppointmentForm(forms.ModelForm):
    class Meta:
        model  = SalesAppointment
        fields = ('enquiry', 'appointment_date', 'purpose', 'status')
        widgets = {
            'appointment_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['appointment_date'].input_formats = ['%Y-%m-%dT%H:%M']

    def clean_appointment_date(self):
        date = self.cleaned_data.get('appointment_date')
        if date:
            # Validate future date only when creating or when the date has changed
            instance_date = getattr(self.instance, 'appointment_date', None)
            if not self.instance.pk or instance_date != date:
                if date < timezone.now():
                    raise forms.ValidationError('Appointment date cannot be in the past.')
        return date


class SalesFeedbackForm(forms.ModelForm):
    class Meta:
        model  = SalesFeedback
        fields = ('enquiry', 'feedback_notes', 'next_followup_date', 'created_by')
        widgets = {
            'feedback_notes':     forms.Textarea(attrs={'rows': 3}),
            'next_followup_date': forms.DateInput(attrs={'type': 'date'}),
        }


class VehicleSalesOrderForm(forms.ModelForm):
    class Meta:
        model  = VehicleSalesOrder
        fields = ('enquiry', 'customer', 'vehicle', 'sales_executive', 'branch',
                  'booking_amount', 'discount_amount', 'total_amount', 'sales_status')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only available stock can be ordered
        self.fields['vehicle'].queryset = VehicleStock.objects.filter(
            stock_status=VehicleStock.StockStatus.AVAILABLE
        ).select_related('bike_model')

    def clean(self):
        cleaned_data    = super().clean()
        booking_amount  = cleaned_data.get('booking_amount')
        total_amount    = cleaned_data.get('total_amount')
        if booking_amount is not None and total_amount is not None:
            if booking_amount > total_amount:
                self.add_error('booking_amount',
                               'Booking amount cannot exceed the total order amount.')
        return cleaned_data


class VehicleDeliveryForm(forms.ModelForm):
    class Meta:
        model  = VehicleDelivery
        fields = ('sales_order', 'delivery_date', 'delivered_by', 'remarks')
        widgets = {
            'delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'remarks':       forms.Textarea(attrs={'rows': 3}),
        }


class ExchangeVehicleForm(forms.ModelForm):
    class Meta:
        model  = ExchangeVehicle
        fields = ('sales_order', 'old_vehicle_model', 'registration_no', 'valuation_amount')
