from django import forms
from django.utils import timezone

from customers.models import VehicleStock

from django.forms import inlineformset_factory

from .models import (ExchangeVehicle, Prospect, SalesAppointment, SalesFeedback,
                     SalesEnquiry, SalesEnquiryCallLog, SalesEnquiryHistory,
                     SalesFeedbackItem, VehicleAllotment, VehicleDelivery,
                     VehicleFitting, VehicleSalesOrder)


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
        fields = (
            'customer', 'sales_executive', 'bike_model', 'branch',
            'enquiry_source', 'status', 'whatsapp_no', 'email',
            'purpose', 'expected_purchase_date',
            # ERP alignment
            'customer_enquiry_date', 'customer_type', 'gender', 'enquiry_type',
            'test_ride_taken', 'payment_type', 'customer_interested_in_exchange',
            'source_of_information',
            'address_line1', 'address_line2', 'address_line3', 'address_line4',
            'district', 'city', 'state', 'pincode',
            'remarks',
        )
        widgets = {
            'remarks': forms.Textarea(attrs={'rows': 3}),
            'expected_purchase_date':  forms.DateInput(attrs={'type': 'date'}),
            'customer_enquiry_date':   forms.DateInput(attrs={'type': 'date'}),
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
        fields = (
            'enquiry', 'appointment_date', 'purpose', 'status',
            'vehicle_code', 'vehicle_name', 'gender', 'phone_no', 'address',
            'whatsapp_no', 'is_cancelled_postponed', 'cancel_reason',
        )
        widgets = {
            'appointment_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'
            ),
            'address':       forms.Textarea(attrs={'rows': 2}),
            'cancel_reason': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['appointment_date'].input_formats = ['%Y-%m-%dT%H:%M']
        # Auto-fill phone/vehicle from enquiry on new forms
        if not self.instance.pk and 'enquiry' not in (self.data or {}):
            pass
        for field in ('vehicle_code', 'vehicle_name', 'gender', 'address', 'whatsapp_no', 'cancel_reason'):
            self.fields[field].required = False

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
        fields = (
            'enquiry', 'appointment', 'vehicle_name', 'phone_no',
            'feedback_notes', 'next_followup_date', 'feed_back_date', 'created_by',
        )
        widgets = {
            'feedback_notes':     forms.Textarea(attrs={'rows': 3}),
            'next_followup_date': forms.DateInput(attrs={'type': 'date'}),
            'feed_back_date':     forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ('vehicle_name', 'phone_no', 'feed_back_date', 'appointment'):
            self.fields[field].required = False


class VehicleChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        parts = [str(obj.bike_model)]
        if obj.chassis_no:
            parts.append(obj.chassis_no)
        if obj.color:
            parts.append(obj.color)
        return ' — '.join(parts)


class VehicleSalesOrderForm(forms.ModelForm):
    vehicle = VehicleChoiceField(
        queryset=VehicleStock.objects.none(),
        help_text='Only available (unsold) vehicles are listed.',
    )

    class Meta:
        model  = VehicleSalesOrder
        fields = ('enquiry', 'customer', 'vehicle', 'sales_executive', 'branch',
                  'booking_amount', 'discount_amount', 'total_amount', 'sales_status')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vehicle'].queryset = VehicleStock.objects.filter(
            stock_status=VehicleStock.StockStatus.AVAILABLE
        ).select_related('bike_model').order_by('bike_model__model_name')
        self.fields['total_amount'].help_text  = 'Full on-road / ex-showroom price. Minimum ₹50,000.'
        self.fields['booking_amount'].help_text = 'Advance collected at booking. Minimum ₹1,000.'
        self.fields['discount_amount'].help_text = 'Maximum discount is 20% of total amount.'

    def clean(self):
        from decimal import Decimal
        cleaned_data    = super().clean()
        booking_amount  = cleaned_data.get('booking_amount')
        total_amount    = cleaned_data.get('total_amount')
        discount_amount = cleaned_data.get('discount_amount')

        if total_amount is not None and total_amount < Decimal('50000'):
            self.add_error('total_amount', 'Total amount must be at least ₹50,000.')

        if booking_amount is not None and booking_amount < Decimal('1000'):
            self.add_error('booking_amount', 'Booking amount must be at least ₹1,000.')

        if booking_amount is not None and total_amount is not None:
            if booking_amount > total_amount:
                self.add_error('booking_amount',
                               'Booking amount cannot exceed the total order amount.')

        if discount_amount is not None and total_amount is not None and total_amount > 0:
            max_discount = total_amount * Decimal('0.20')
            if discount_amount > max_discount:
                self.add_error('discount_amount',
                               f'Discount cannot exceed 20% of total amount (₹{max_discount:.0f}).')

        return cleaned_data


class VehicleDeliveryForm(forms.ModelForm):
    class Meta:
        model  = VehicleDelivery
        fields = (
            'sales_order', 'delivery_date', 'delivered_by', 'remarks',
            'checklist_insurance', 'checklist_rc_book', 'checklist_warranty',
            'checklist_toolkit', 'checklist_accessories',
        )
        widgets = {
            'delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'remarks':       forms.Textarea(attrs={'rows': 3}),
        }


class ExchangeVehicleForm(forms.ModelForm):
    class Meta:
        model  = ExchangeVehicle
        fields = ('sales_order', 'old_vehicle_model', 'registration_no', 'valuation_amount',
                  'rc_handed_over', 'rc_handover_date')
        widgets = {
            'registration_no':  forms.TextInput(attrs={'placeholder': 'e.g. TN11CD5678'}),
            'rc_handover_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_vehicle_model'].required = True
        self.fields['registration_no'].required   = True
        self.fields['valuation_amount'].required  = True
        self.fields['registration_no'].help_text  = 'Vehicle registration number, e.g. TN11CD5678'
        self.fields['valuation_amount'].help_text = 'Assessed trade-in value in ₹'

    def clean_registration_no(self):
        import re
        value = (self.cleaned_data.get('registration_no') or '').strip().upper()
        if not value:
            raise forms.ValidationError('Registration number is required.')
        if not re.match(r'^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{1,4}$', value):
            raise forms.ValidationError(
                'Enter a valid registration number, e.g. TN11CD5678.'
            )
        return value

    def clean_valuation_amount(self):
        from decimal import Decimal
        amount = self.cleaned_data.get('valuation_amount')
        if amount is None:
            raise forms.ValidationError('Valuation amount is required.')
        if amount <= Decimal('0'):
            raise forms.ValidationError('Valuation amount must be greater than zero.')
        return amount


class VehicleAllotmentForm(forms.ModelForm):
    class Meta:
        model  = VehicleAllotment
        fields = ('sales_order', 'vehicle', 'notes')
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional notes about this allotment'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only available or reserved vehicles can be allotted
        self.fields['vehicle'].queryset = VehicleStock.objects.filter(
            stock_status__in=['available', 'reserved']
        ).select_related('bike_model')


class VehicleFittingForm(forms.ModelForm):
    class Meta:
        model  = VehicleFitting
        fields = ('sales_order', 'fitting_name', 'description', 'cost')
        widgets = {
            'description':  forms.Textarea(attrs={'rows': 2}),
            'fitting_name': forms.TextInput(attrs={'placeholder': 'e.g. Crash Guard, Seat Cover, Side Box'}),
        }

    def clean_cost(self):
        from decimal import Decimal
        cost = self.cleaned_data.get('cost')
        if cost is None or cost < Decimal('0'):
            raise forms.ValidationError('Cost cannot be negative.')
        return cost


# ---------------------------------------------------------------------------
# ERP Alignment — inline formsets for call logs, history, feedback items
# ---------------------------------------------------------------------------

class CallLogForm(forms.ModelForm):
    class Meta:
        model  = SalesEnquiryCallLog
        fields = ('unique_id', 'call_from', 'bill_sec', 'start_time', 'audio_url', 'notes')
        widgets = {
            'unique_id':  forms.TextInput(attrs={'class': 'form-control'}),
            'call_from':  forms.TextInput(attrs={'class': 'form-control'}),
            'bill_sec':   forms.NumberInput(attrs={'class': 'form-control', 'style': 'min-width:70px'}),
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'audio_url':  forms.URLInput(attrs={'class': 'form-control'}),
            'notes':      forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class HistoryForm(forms.ModelForm):
    class Meta:
        model  = SalesEnquiryHistory
        fields = ('update_date', 'remarks', 'status')
        widgets = {
            'update_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'remarks':     forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'status':      forms.Select(attrs={'class': 'form-select'}),
        }


class FeedbackItemForm(forms.ModelForm):
    class Meta:
        model  = SalesFeedbackItem
        fields = ('points', 'feedback_type', 'response', 'rating')
        widgets = {
            'points':        forms.TextInput(attrs={'class': 'form-control'}),
            'feedback_type': forms.Select(attrs={'class': 'form-select'}),
            'response':      forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'rating':        forms.Select(attrs={'class': 'form-select'}),
        }


CallLogFormSet = inlineformset_factory(
    SalesEnquiry, SalesEnquiryCallLog,
    form=CallLogForm, extra=1, can_delete=True
)

HistoryFormSet = inlineformset_factory(
    SalesEnquiry, SalesEnquiryHistory,
    form=HistoryForm, extra=1, can_delete=True
)

FeedbackItemFormSet = inlineformset_factory(
    SalesFeedback, SalesFeedbackItem,
    form=FeedbackItemForm, extra=1, can_delete=True
)


# ---------------------------------------------------------------------------
# FEATURE 1 — Sales Target Form
# ---------------------------------------------------------------------------

from .models import SalesTarget, TestRideLog, PDIChecklist


class SalesTargetForm(forms.ModelForm):
    class Meta:
        model = SalesTarget
        fields = ('sales_executive', 'month', 'year', 'target_enquiries',
                  'target_test_rides', 'target_conversions', 'target_revenue')
        widgets = {
            'month': forms.NumberInput(attrs={'min': 1, 'max': 12}),
            'year':  forms.NumberInput(attrs={'min': 2024, 'max': 2035}),
        }


class TestRideLogForm(forms.ModelForm):
    class Meta:
        model = TestRideLog
        fields = ('enquiry', 'vehicle', 'rider_name', 'rider_phone',
                  'license_number', 'accompanied_by', 'start_time',
                  'start_odometer', 'feedback_after_ride')
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'feedback_after_ride': forms.Textarea(attrs={'rows': 2}),
        }


class PDIChecklistForm(forms.ModelForm):
    class Meta:
        model = PDIChecklist
        exclude = ('sales_order', 'inspected_by', 'inspection_date',
                   'is_approved', 'approved_by')
        widgets = {'overall_remarks': forms.Textarea(attrs={'rows': 3})}
