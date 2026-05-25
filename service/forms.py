from django import forms
from django.utils import timezone

from .models import (BayAssignment, InsuranceEstimation, JobCard, LaborCharge,
                     OutworkEntry, ServiceAppointment, ServiceBay,
                     ServiceDiscountMaster, ServiceEnquiry, ServiceInvoice,
                     WarrantyClaim)

_DT_WIDGET = forms.DateTimeInput(attrs={'type': 'datetime-local'})
_DT_FORMATS = ['%Y-%m-%dT%H:%M']


class ServiceEnquiryForm(forms.ModelForm):
    class Meta:
        model  = ServiceEnquiry
        fields = ('customer_vehicle', 'created_by', 'issue_description', 'status')


class ServiceAppointmentForm(forms.ModelForm):
    appointment_date = forms.DateTimeField(
        widget=_DT_WIDGET,
        input_formats=_DT_FORMATS,
    )

    class Meta:
        model  = ServiceAppointment
        fields = ('service_enquiry', 'appointment_date', 'service_type', 'status')

    def clean_appointment_date(self):
        date = self.cleaned_data.get('appointment_date')
        if date:
            instance_date = getattr(self.instance, 'appointment_date', None)
            if not self.instance.pk or instance_date != date:
                if date < timezone.now():
                    raise forms.ValidationError('Appointment date cannot be in the past.')
        return date


class JobCardForm(forms.ModelForm):
    class Meta:
        model  = JobCard
        fields = ('customer_vehicle', 'service_appointment', 'service_advisor',
                  'floor_supervisor', 'branch', 'odometer_reading',
                  'problem_description', 'service_status')


class ServiceBayForm(forms.ModelForm):
    class Meta:
        model  = ServiceBay
        fields = ('bay_name', 'status')


class BayAssignmentForm(forms.ModelForm):
    start_time = forms.DateTimeField(
        widget=_DT_WIDGET,
        input_formats=_DT_FORMATS,
        required=False,
    )
    end_time = forms.DateTimeField(
        widget=_DT_WIDGET,
        input_formats=_DT_FORMATS,
        required=False,
    )

    class Meta:
        model  = BayAssignment
        fields = ('job_card', 'bay', 'mechanic', 'start_time',
                  'end_time', 'assignment_status')

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end   = cleaned_data.get('end_time')
        if start and end and end <= start:
            raise forms.ValidationError('End time must be after start time.')
        return cleaned_data


class ServiceInvoiceForm(forms.ModelForm):
    """
    Minimal form — totals are auto-calculated via calculate_totals().
    Only discount_amount and status are editable by the user.
    """
    class Meta:
        model  = ServiceInvoice
        fields = ('job_card', 'discount_amount', 'status')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # job_card field is pre-filled via initial and hidden in create flow
        self.fields['discount_amount'].required = False


class LaborChargeForm(forms.ModelForm):
    class Meta:
        model  = LaborCharge
        fields = ('job_card', 'service_name', 'labor_cost')


class OutworkEntryForm(forms.ModelForm):
    class Meta:
        model  = OutworkEntry
        fields = ('job_card', 'vendor_name', 'work_description', 'cost')


class WarrantyClaimForm(forms.ModelForm):
    class Meta:
        model  = WarrantyClaim
        fields = ('job_card', 'description', 'claimed_amount',
                  'approved_amount', 'status', 'notes')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'notes':       forms.Textarea(attrs={'rows': 2}),
        }


class InsuranceEstimationForm(forms.ModelForm):
    class Meta:
        model  = InsuranceEstimation
        fields = ('job_card', 'insurance_company', 'policy_number',
                  'labour_estimate', 'spares_estimate',
                  'approved_amount', 'status', 'notes')
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class ServiceDiscountMasterForm(forms.ModelForm):
    class Meta:
        model  = ServiceDiscountMaster
        fields = ('service_type', 'discount_percent', 'is_active')
        widgets = {
            'service_type': forms.TextInput(attrs={'placeholder': 'e.g. free_service, paid_service, accidental'}),
        }
