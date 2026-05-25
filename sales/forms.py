from django import forms
from django.utils import timezone

from customers.models import VehicleStock

from .models import (ExchangeVehicle, Prospect, SalesAppointment, SalesFeedback,
                     SalesEnquiry, VehicleDelivery, VehicleSalesOrder)


class SalesEnquiryForm(forms.ModelForm):
    """
    Handles both:
      • New prospect enquiry  — fill prospect_name + prospect_phone (customer optional)
      • Existing customer enquiry — select customer (prospect fields optional)
    On save, creates a Prospect record when no customer is supplied.
    """
    prospect_name  = forms.CharField(
        max_length=200, required=False, label='Prospect Name',
        widget=forms.TextInput(attrs={'placeholder': 'Full name of walk-in visitor'}),
        help_text='Fill if the visitor is not yet a registered customer.'
    )
    prospect_phone = forms.CharField(
        max_length=15, required=False, label='Prospect Phone',
        widget=forms.TextInput(attrs={'placeholder': '10-digit mobile number'}),
    )

    class Meta:
        model  = SalesEnquiry
        fields = ('customer', 'sales_executive', 'bike_model', 'branch',
                  'enquiry_source', 'status', 'remarks')
        widgets = {
            'remarks': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].required = False
        self.fields['customer'].help_text = (
            'Select an existing customer, OR fill Prospect Name + Phone above.'
        )
        # If editing an existing enquiry that has a prospect, pre-fill the fields
        if self.instance and self.instance.pk and self.instance.prospect:
            p = self.instance.prospect
            self.fields['prospect_name'].initial  = p.full_name
            self.fields['prospect_phone'].initial = p.phone

    def clean(self):
        cleaned_data   = super().clean()
        customer       = cleaned_data.get('customer')
        prospect_name  = (cleaned_data.get('prospect_name') or '').strip()
        prospect_phone = (cleaned_data.get('prospect_phone') or '').strip()
        if not customer and not (prospect_name and prospect_phone):
            raise forms.ValidationError(
                'Please either select an existing Customer '
                'or enter a Prospect Name and Phone Number.'
            )
        return cleaned_data

    def save(self, commit=True):
        instance       = super().save(commit=False)
        prospect_name  = (self.cleaned_data.get('prospect_name') or '').strip()
        prospect_phone = (self.cleaned_data.get('prospect_phone') or '').strip()

        if not instance.customer_id and prospect_name and prospect_phone:
            # Check if phone matches an existing Customer
            from customers.models import Customer
            existing_customer = Customer.objects.filter(phone=prospect_phone).first()
            if existing_customer:
                instance.customer = existing_customer
            else:
                # Create or get a Prospect
                prospect, _ = Prospect.objects.get_or_create(
                    phone=prospect_phone,
                    defaults={
                        'full_name':           prospect_name,
                        'vehicle_of_interest': instance.bike_model,
                        'enquiry_source':      instance.enquiry_source or '',
                    }
                )
                instance.prospect = prospect

        if commit:
            instance.save()
        return instance


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
        self.fields['vehicle'].queryset = VehicleStock.objects.filter(
            stock_status=VehicleStock.StockStatus.AVAILABLE
        ).select_related('bike_model')

    def clean(self):
        cleaned_data   = super().clean()
        booking_amount = cleaned_data.get('booking_amount')
        total_amount   = cleaned_data.get('total_amount')
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
