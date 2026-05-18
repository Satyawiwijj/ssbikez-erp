from django import forms

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
