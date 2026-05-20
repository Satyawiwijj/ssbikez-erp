from django import forms

from .models import (BayAssignment, JobCard, LaborCharge, OutworkEntry,
                     ServiceAppointment, ServiceBay, ServiceEnquiry, ServiceInvoice)

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


class ServiceInvoiceForm(forms.ModelForm):
    class Meta:
        model  = ServiceInvoice
        fields = ('job_card', 'subtotal', 'gst_amount', 'discount_amount',
                  'final_amount', 'invoice_date')
        widgets = {
            'invoice_date': forms.DateInput(attrs={'type': 'date'}),
        }


class LaborChargeForm(forms.ModelForm):
    class Meta:
        model  = LaborCharge
        fields = ('job_card', 'service_name', 'labor_cost')


class OutworkEntryForm(forms.ModelForm):
    class Meta:
        model  = OutworkEntry
        fields = ('job_card', 'vendor_name', 'work_description', 'cost')
