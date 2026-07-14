from django import forms
from accounts.forms import AccessibleFormMixin
from django.forms import inlineformset_factory
from django.utils import timezone

from .models import (BayAssignment, BayInCreation, BayOutCreation, ChasisDetailRow,
                     ComplaintDetail, EngineDetailRow, FinalInspection,
                     InsuranceEstimation, JobCard, JobCardSupervisorObservation,
                     LaborCharge, LaborChargesAlteration,
                     LaborDetailLine, LaborSpareItem, LightDetail, OutworkEntry, OutworkEntryIssue,
                     OutworkEntryReturn, OutworkReturnDetail, OutworkReturnSpareItem,
                     OutworkSpareItem, OutworkWorkDetail, ServiceAppointment, ServiceBay,
                     ServiceDiscountMaster, ServiceEnquiry, ServiceInvoice,
                     VehicleServiceMaster, VehicleServiceSchedule, WarrantyClaim,
                     WaterWashDone)

_DT_WIDGET = forms.DateTimeInput(attrs={'type': 'datetime-local'})
_DT_FORMATS = ['%Y-%m-%dT%H:%M']


class ServiceEnquiryForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = ServiceEnquiry
        fields = ('customer_vehicle', 'created_by', 'issue_description', 'status')


class ServiceAppointmentForm(AccessibleFormMixin, forms.ModelForm):
    appointment_date = forms.DateTimeField(
        widget=_DT_WIDGET,
        input_formats=_DT_FORMATS,
    )

    class Meta:
        model  = ServiceAppointment
        fields = (
            'service_enquiry', 'appointment_date', 'service_type', 'status',
            'phone_no', 'whatsapp_no', 'chassis_no', 'vehicle_name',
            'is_cancelled_postponed',
        )
        widgets = {
            'chassis_no':   forms.TextInput(attrs={'placeholder': 'Chassis number'}),
            'vehicle_name': forms.TextInput(attrs={'placeholder': 'Vehicle name/model'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ('phone_no', 'whatsapp_no', 'chassis_no', 'vehicle_name'):
            self.fields[f].required = False

    def clean_appointment_date(self):
        date = self.cleaned_data.get('appointment_date')
        if date:
            instance_date = getattr(self.instance, 'appointment_date', None)
            if not self.instance.pk or instance_date != date:
                if date < timezone.now():
                    raise forms.ValidationError('Appointment date cannot be in the past.')
        return date


class JobCardForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = JobCard
        fields = ('customer_vehicle', 'service_appointment', 'service_advisor',
                  'floor_supervisor', 'branch', 'odometer_reading',
                  'problem_description', 'service_status')


class ServiceBayForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = ServiceBay
        fields = ('bay_name', 'status')


class BayAssignmentForm(AccessibleFormMixin, forms.ModelForm):
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


class ServiceInvoiceForm(AccessibleFormMixin, forms.ModelForm):
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


class LaborChargeForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = LaborCharge
        fields = ('job_card', 'service_name', 'labor_cost')


class OutworkEntryForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = OutworkEntry
        fields = ('job_card', 'vendor_name', 'work_description', 'cost')


# ---------------------------------------------------------------------------
# Phase 2 — reference-parity workshop stage documents
# ---------------------------------------------------------------------------

class WaterWashDoneForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = WaterWashDone
        fields = ('job_card', 'register_number', 'vehicle_code')


class BayInCreationForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = BayInCreation
        fields = ('job_card', 'mechanic', 'vehicle_code', 'register_no', 'date_time')
        widgets = {'date_time': _DT_WIDGET}


class BayOutCreationForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = BayOutCreation
        fields = ('job_card', 'mechanic', 'vehicle_code', 'remarks', 'date_time')
        widgets = {
            'date_time': _DT_WIDGET,
            'remarks':   forms.Textarea(attrs={'rows': 2}),
        }


class FinalInspectionForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = FinalInspection
        fields = ('job_card', 'rework', 'vehicle_name', 'chasis_number',
                  'mechanic_name', 'register_number', 'final_inspection_remarks',
                  'revisit')
        widgets = {'final_inspection_remarks': forms.Textarea(attrs={'rows': 3})}


class OutworkEntryIssueForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = OutworkEntryIssue
        fields = ('job_card', 'vendor_name', 'godown', 'gate_pass')


class OutworkWorkDetailForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = OutworkWorkDetail
        fields = ('work_name', 'party', 'quantity', 'amount', 'tax', 'total_amount', 'work_type')


OutworkWorkDetailFormSet = inlineformset_factory(
    OutworkEntryIssue, OutworkWorkDetail, form=OutworkWorkDetailForm, extra=1, can_delete=True
)


class OutworkSpareItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = OutworkSpareItem
        fields = ('item', 'rack', 'bin', 'quantity', 'rate', 'sgst', 'cgst', 'total')


OutworkSpareItemFormSet = inlineformset_factory(
    OutworkEntryIssue, OutworkSpareItem, form=OutworkSpareItemForm, extra=1, can_delete=True
)


class OutworkEntryReturnForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = OutworkEntryReturn
        fields = ('outwork_issue', 'job_card', 'rework', 'payment_type', 'supplier',
                  'actual_amount', 'billing_amount', 'vendor_spares_amount', 'pending_amount')


class OutworkReturnDetailForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = OutworkReturnDetail
        fields = ('work_name', 'quantity', 'amount')


OutworkReturnDetailFormSet = inlineformset_factory(
    OutworkEntryReturn, OutworkReturnDetail, form=OutworkReturnDetailForm, extra=1, can_delete=True
)


class OutworkReturnSpareItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = OutworkReturnSpareItem
        fields = ('item', 'quantity', 'rate', 'total')


OutworkReturnSpareItemFormSet = inlineformset_factory(
    OutworkEntryReturn, OutworkReturnSpareItem, form=OutworkReturnSpareItemForm, extra=1, can_delete=True
)


class LaborChargesAlterationForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = LaborChargesAlteration
        fields = ('job_card', 'labours_name')


class LaborDetailLineForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = LaborDetailLine
        fields = ('labor_name', 'quantity', 'amount', 'sgst', 'cgst', 'total', 'discount')


LaborDetailLineFormSet = inlineformset_factory(
    LaborChargesAlteration, LaborDetailLine, form=LaborDetailLineForm, extra=1, can_delete=True
)


class LaborSpareItemForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = LaborSpareItem
        fields = ('item', 'quantity', 'rate', 'total')


LaborSpareItemFormSet = inlineformset_factory(
    LaborChargesAlteration, LaborSpareItem, form=LaborSpareItemForm, extra=1, can_delete=True
)


# ---------------------------------------------------------------------------
# Phase 4 — Job Card inspection-checklist child tables
# ---------------------------------------------------------------------------

class ComplaintDetailForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = ComplaintDetail
        fields = ('customer_complaint', 'details', 'status', 'complaint_check_box', 'estimated_amount')


ComplaintDetailFormSet = inlineformset_factory(
    JobCard, ComplaintDetail, form=ComplaintDetailForm, extra=1, can_delete=True
)


class JobCardSupervisorObservationForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = JobCardSupervisorObservation
        fields = ('complaint', 'details', 'complaint_check_box', 'estimated_amount')


JobCardSupervisorObservationFormSet = inlineformset_factory(
    JobCard, JobCardSupervisorObservation, form=JobCardSupervisorObservationForm, extra=1, can_delete=True
)


class EngineDetailRowForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = EngineDetailRow
        fields = ('variant', 'items', 'yes', 'no', 'ok', 'high', 'low', 'area_mention',
                  'yes_status', 'no_status', 'ok_status', 'high_status', 'low_status', 'mention_status')


EngineDetailRowFormSet = inlineformset_factory(
    JobCard, EngineDetailRow, form=EngineDetailRowForm, extra=1, can_delete=True
)


class LightDetailForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = LightDetail
        fields = ('items', 'yes', 'no')


LightDetailFormSet = inlineformset_factory(
    JobCard, LightDetail, form=LightDetailForm, extra=1, can_delete=True
)


class ChasisDetailRowForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = ChasisDetailRow
        fields = ('variant', 'items', 'yes', 'no', 'ok', 'high', 'low', 'good', 'bad', 'na',
                  'yes_status', 'no_status', 'good_status', 'bad_status', 'na_status',
                  'ok_status', 'high_status')


ChasisDetailRowFormSet = inlineformset_factory(
    JobCard, ChasisDetailRow, form=ChasisDetailRowForm, extra=1, can_delete=True
)


class WarrantyClaimForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = WarrantyClaim
        fields = ('job_card', 'description', 'claimed_amount',
                  'approved_amount', 'status', 'notes')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'notes':       forms.Textarea(attrs={'rows': 2}),
        }


class InsuranceEstimationForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = InsuranceEstimation
        fields = ('job_card', 'insurance_company', 'policy_number',
                  'labour_estimate', 'spares_estimate',
                  'approved_amount', 'status', 'notes')
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class ServiceDiscountMasterForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = ServiceDiscountMaster
        fields = ('service_type', 'discount_percent', 'is_active')
        widgets = {
            'service_type': forms.TextInput(attrs={'placeholder': 'e.g. free_service, paid_service, accidental'}),
        }


# ===========================================================================
# GAP 14-31 forms
# ===========================================================================

from .models import (AdditionalWorkApproval, CustomerCall, InsuranceClaim,
                     JobCardRevisit, JobCardServiceChild)


class JobCardRevisitForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = JobCardRevisit
        fields = ('next_service_km', 'next_service_days', 'next_service_date', 'notes')
        widgets = {
            'next_service_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class JobCardServiceChildForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = JobCardServiceChild
        fields = ('task_name', 'description', 'assigned_to', 'status')
        widgets = {'description': forms.Textarea(attrs={'rows': 2})}


class CustomerCallForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = CustomerCall
        fields = ('customer_vehicle', 'purpose', 'notes', 'outcome', 'next_call_date')
        widgets = {
            'next_call_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class InsuranceClaimForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = InsuranceClaim
        fields = ('job_card', 'insurance_estimation', 'claim_number',
                  'insurance_company', 'policy_number', 'claim_amount',
                  'approved_amount', 'status', 'settlement_date', 'notes')
        widgets = {
            'settlement_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class AdditionalWorkApprovalForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = AdditionalWorkApproval
        fields = ('description', 'estimated_labour', 'estimated_spares')
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}


# ---------------------------------------------------------------------------
# FEATURE 4 — Service Reminder Form
# ---------------------------------------------------------------------------

from .models import ServiceReminder


class ServiceReminderForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = ServiceReminder
        fields = ('customer_vehicle', 'reminder_date', 'reminder_type',
                  'due_km', 'notes', 'status', 'assigned_to')
        widgets = {
            'reminder_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


# ---------------------------------------------------------------------------
# ERP Alignment — Vehicle Service Master
# ---------------------------------------------------------------------------

class VehicleServiceMasterForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = VehicleServiceMaster
        fields = ('bike_model', 'vehicle_code')


class VehicleServiceScheduleForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model  = VehicleServiceSchedule
        fields = ('service_type', 'days_from_purchase', 'km_from_purchase')
        widgets = {
            'days_from_purchase': forms.NumberInput(attrs={'class': 'form-control', 'style': 'min-width:90px'}),
            'km_from_purchase':   forms.NumberInput(attrs={'class': 'form-control', 'style': 'min-width:90px'}),
        }


VehicleServiceScheduleFormSet = inlineformset_factory(
    VehicleServiceMaster, VehicleServiceSchedule,
    form=VehicleServiceScheduleForm, extra=1, can_delete=True
)
