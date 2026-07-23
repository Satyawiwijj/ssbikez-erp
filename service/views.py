import logging
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.audit import log_action
from accounts.permissions import require_module_action

from .forms import (BayAssignmentForm, BayInCreationForm, BayOutCreationForm,
                    ChasisDetailRowFormSet, ComplaintDetailFormSet, EngineDetailRowFormSet,
                    FinalInspectionForm, JobCardForm, JobCardSupervisorObservationFormSet,
                    LaborChargeForm,
                    LaborChargesAlterationForm, LaborDetailLineFormSet,
                    LaborSpareItemFormSet, LightDetailFormSet, OutworkEntryForm, OutworkEntryIssueForm,
                    OutworkEntryReturnForm, OutworkReturnDetailFormSet,
                    OutworkReturnSpareItemFormSet, OutworkSpareItemFormSet,
                    OutworkWorkDetailFormSet, ServiceAppointmentForm, ServiceBayForm,
                    ServiceEnquiryForm, ServiceInvoiceForm, VehicleServiceMasterForm,
                    VehicleServiceScheduleFormSet, WaterWashDoneForm)
from .models import (BayAssignment, BayInCreation, BayOutCreation, FinalInspection,
                     JobCard, LaborCharge, LaborChargesAlteration, OutworkEntry,
                     OutworkEntryIssue, OutworkEntryReturn, ServiceAppointment,
                     ServiceBay, ServiceEnquiry, ServiceInvoice, VehicleServiceMaster,
                     WaterWashDone, check_stage_order)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    def safe_count(qs):
        try:
            return qs.count()
        except Exception:
            return 0

    total_jc   = safe_count(JobCard.objects.all())
    active_jc  = safe_count(JobCard.objects.exclude(service_status__in=['invoiced']))
    total_bays = safe_count(ServiceBay.objects.all())
    total_enq  = safe_count(ServiceEnquiry.objects.all())
    recent_jc  = JobCard.objects.select_related(
        'customer_vehicle__customer', 'customer_vehicle__vehicle__bike_model', 'service_advisor'
    ).order_by('-created_at')[:10]

    return render(request, 'service/dashboard.html', {
        'total_jc':   total_jc,
        'active_jc':  active_jc,
        'total_bays': total_bays,
        'total_enq':  total_enq,
        'recent_jc':  recent_jc,
    })


# ---------------------------------------------------------------------------
# Appointment list
# ---------------------------------------------------------------------------

@login_required
def appointment_list(request):
    appointments = ServiceAppointment.objects.select_related(
        'service_enquiry__customer_vehicle__customer',
        'service_enquiry__customer_vehicle__vehicle__bike_model',
    ).order_by('-appointment_date')
    return render(request, 'service/appointment_list.html', {'appointments': appointments})


# ---------------------------------------------------------------------------
# LaborCharge list
# ---------------------------------------------------------------------------

@login_required
def labor_charge_list(request):
    charges = LaborCharge.objects.select_related(
        'job_card__customer_vehicle__customer'
    ).order_by('-id')
    return render(request, 'service/labor_charge_list.html', {'charges': charges})


# ---------------------------------------------------------------------------
# ServiceEnquiry
# ---------------------------------------------------------------------------

@login_required
def enquiry_list(request):
    q  = request.GET.get('q', '').strip()
    qs = ServiceEnquiry.objects.select_related(
        'customer_vehicle__customer',
        'customer_vehicle__vehicle__bike_model',
        'created_by',
    ).all()
    if q:
        qs = qs.filter(
            Q(customer_vehicle__customer__full_name__icontains=q) |
            Q(customer_vehicle__customer__phone__icontains=q) |
            Q(customer_vehicle__registration_no__icontains=q)
        )
    return render(request, 'service/enquiry_list.html', {'enquiries': qs, 'q': q})


@login_required
def enquiry_detail(request, pk):
    enquiry      = get_object_or_404(
        ServiceEnquiry.objects.select_related(
            'customer_vehicle__customer',
            'customer_vehicle__vehicle__bike_model',
            'created_by',
        ),
        pk=pk,
    )
    appointments = enquiry.appointments.all()
    return render(request, 'service/enquiry_detail.html', {
        'enquiry':      enquiry,
        'appointments': appointments,
    })


@login_required
@require_module_action('service', 'create')
def enquiry_create(request):
    initial = {}
    if request.GET.get('cv'):
        initial['customer_vehicle'] = request.GET['cv']
    form = ServiceEnquiryForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        enquiry = form.save()
        log_action(request, 'Service Enquiry', 'create', enquiry.pk)
        messages.success(request, 'Service enquiry created successfully.')
        return redirect('service:enquiry_detail', pk=enquiry.pk)
    return render(request, 'service/enquiry_form.html',
                  {'form': form, 'title': 'New Service Enquiry'})


@login_required
@require_module_action('service', 'edit')
def enquiry_update(request, pk):
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    enquiry = get_object_or_404(ServiceEnquiry, pk=pk)
    if not user_owns(request.user, enquiry):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    form    = ServiceEnquiryForm(request.POST or None, instance=enquiry)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Service Enquiry', 'update', pk)
        messages.success(request, 'Service enquiry updated successfully.')
        return redirect('service:enquiry_detail', pk=enquiry.pk)
    return render(request, 'service/enquiry_form.html',
                  {'form': form, 'title': 'Edit Service Enquiry'})


# ---------------------------------------------------------------------------
# ServiceAppointment
# ---------------------------------------------------------------------------

@login_required
@require_module_action('service', 'create')
def appointment_create(request):
    initial = {}
    if request.GET.get('enquiry'):
        initial['service_enquiry'] = request.GET['enquiry']
    form = ServiceAppointmentForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        appt = form.save()
        log_action(request, 'Service Appointment', 'create', appt.pk)
        messages.success(request, 'Service appointment scheduled successfully.')
        return redirect('service:enquiry_detail', pk=appt.service_enquiry_id)
    return render(request, 'service/appointment_form.html',
                  {'form': form, 'title': 'New Appointment'})


@login_required
@require_module_action('service', 'edit')
def appointment_update(request, pk):
    appt = get_object_or_404(ServiceAppointment, pk=pk)
    form = ServiceAppointmentForm(request.POST or None, instance=appt)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Service Appointment', 'update', pk)
        messages.success(request, 'Service appointment updated successfully.')
        return redirect('service:enquiry_detail', pk=appt.service_enquiry_id)
    return render(request, 'service/appointment_form.html',
                  {'form': form, 'title': 'Edit Appointment'})


@login_required
@require_POST
@require_module_action('service', 'edit')
def appointment_cancel(request, pk):
    from accounts.permissions import user_owns
    appt = get_object_or_404(ServiceAppointment, pk=pk)
    if appt.service_enquiry_id and not user_owns(request.user, appt.service_enquiry):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    appt.status = ServiceAppointment.Status.CANCELLED
    appt.save(update_fields=['status'])
    log_action(request, 'Service Appointment', 'update', pk)
    messages.success(request, 'Service appointment cancelled.')
    return redirect('service:enquiry_detail', pk=appt.service_enquiry_id)


# ---------------------------------------------------------------------------
# JobCard
# ---------------------------------------------------------------------------

@login_required
def jobcard_list(request):
    q             = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    qs = JobCard.objects.select_related(
        'customer_vehicle__customer',
        'customer_vehicle__vehicle__bike_model',
        'service_advisor',
        'branch',
    ).all()
    if q:
        qs = qs.filter(
            Q(customer_vehicle__customer__full_name__icontains=q) |
            Q(customer_vehicle__registration_no__icontains=q)
        )
    if status_filter:
        qs = qs.filter(service_status=status_filter)
    paginator = Paginator(qs, 25)
    page_obj  = paginator.get_page(request.GET.get('page'))
    return render(request, 'service/jobcard_list.html', {
        'job_cards':      page_obj,
        'page_obj':       page_obj,
        'q':              q,
        'status_filter':  status_filter,
        'status_choices': JobCard.ServiceStatus.choices,
    })


@login_required
def jobcard_detail(request, pk):
    job_card = get_object_or_404(
        JobCard.objects.select_related(
            'customer_vehicle__customer',
            'customer_vehicle__vehicle__bike_model',
            'service_advisor',
            'floor_supervisor',
            'branch',
        ),
        pk=pk,
    )
    bay_assignments  = job_card.bay_assignments.select_related('bay', 'mechanic').all()
    labor_charges    = job_card.labor_charges.all()
    total_labor      = labor_charges.aggregate(total=Sum('labor_cost'))['total'] or Decimal('0.00')
    outwork_entries  = job_card.outwork_entries.all()
    spares_issues    = _spares_issued_for(job_card)
    # GAP 14, 15, 26, 30, 31
    revisit = getattr(job_card, 'revisit', None)
    service_childs = job_card.service_childs.all() if hasattr(job_card, 'service_childs') else []
    additional_approvals = job_card.additional_approvals.all() if hasattr(job_card, 'additional_approvals') else []
    insurance_claims = job_card.insurance_claims.all() if hasattr(job_card, 'insurance_claims') else []
    cv = job_card.customer_vehicle
    warranty_active = getattr(cv, 'warranty_active', False)
    warranty_end = getattr(cv, 'warranty_end_date', None)
    free_services_remaining = getattr(cv, 'free_services_remaining', 0)
    free_services_used = getattr(cv, 'free_services_used', 0)
    total_free_services = getattr(cv, 'total_free_services', 0)
    return render(request, 'service/jobcard_detail.html', {
        'job_card':        job_card,
        'bay_assignments': bay_assignments,
        'labor_charges':   labor_charges,
        'total_labor':     total_labor,
        'spares_issues':   spares_issues,
        'outwork_entries': outwork_entries,
        'revisit':         revisit,
        'service_childs':  service_childs,
        'additional_approvals': additional_approvals,
        'insurance_claims': insurance_claims,
        'warranty_active': warranty_active,
        'warranty_end':    warranty_end,
        'free_services_remaining': free_services_remaining,
        'free_services_used':      free_services_used,
        'total_free_services':     total_free_services,
        'complaint_details':       job_card.complaint_details.select_related('customer_complaint').all(),
        'supervisor_observations': job_card.supervisor_observations.select_related('complaint').all(),
        'engine_details':          job_card.engine_details.all(),
        'light_details':           job_card.light_details.all(),
        'chasis_details':          job_card.chasis_details.all(),
    })


def _jobcard_checklist_formsets(request, instance=None):
    post = request.POST or None
    return {
        'complaint_formset':    ComplaintDetailFormSet(post, instance=instance, prefix='complaints'),
        'observation_formset':  JobCardSupervisorObservationFormSet(post, instance=instance, prefix='observations'),
        'engine_formset':       EngineDetailRowFormSet(post, instance=instance, prefix='engine'),
        'light_formset':        LightDetailFormSet(post, instance=instance, prefix='lights'),
        'chasis_formset':       ChasisDetailRowFormSet(post, instance=instance, prefix='chasis'),
    }


@login_required
@require_module_action('service', 'create')
def jobcard_create(request):
    from accounts.permissions import user_is_manager
    is_manager = user_is_manager(request.user)
    initial = {}
    if request.GET.get('cv'):
        initial['customer_vehicle'] = request.GET['cv']
    form = JobCardForm(request.POST or None, initial=initial)
    if not is_manager:
        form.fields.pop('service_advisor', None)
    checklists = _jobcard_checklist_formsets(request)
    if request.method == 'POST':
        if form.is_valid() and all(fs.is_valid() for fs in checklists.values()):
            jc = form.save(commit=False)
            if not is_manager:
                jc.service_advisor = request.user
            jc.save()
            for fs in checklists.values():
                fs.instance = jc
                fs.save()
            log_action(request, 'Job Card', 'create', jc.pk)
            messages.success(request, 'Job card created successfully.')
            return redirect('service:jobcard_detail', pk=jc.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'service/jobcard_form.html',
                  {'form': form, 'title': 'New Job Card', **checklists})


@login_required
@require_module_action('service', 'edit')
def jobcard_update(request, pk):
    from accounts.permissions import user_is_manager, user_owns
    from django.http import HttpResponseForbidden
    job_card = get_object_or_404(JobCard, pk=pk)
    if not user_owns(request.user, job_card):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    is_manager = user_is_manager(request.user)
    form     = JobCardForm(request.POST or None, instance=job_card)
    if not is_manager:
        form.fields.pop('service_advisor', None)
        form.fields.pop('service_status', None)
    checklists = _jobcard_checklist_formsets(request, instance=job_card)
    if request.method == 'POST':
        if form.is_valid() and all(fs.is_valid() for fs in checklists.values()):
            form.save()
            for fs in checklists.values():
                fs.save()
            log_action(request, 'Job Card', 'update', pk)
            messages.success(request, 'Job card updated successfully.')
            return redirect('service:jobcard_detail', pk=job_card.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'service/jobcard_form.html',
                  {'form': form, 'title': 'Edit Job Card', **checklists})


@login_required
@require_POST
@require_module_action('service', 'edit')
def jobcard_status_update(request, pk):
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    job_card   = get_object_or_404(JobCard, pk=pk)
    if not user_owns(request.user, job_card):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    new_status = request.POST.get('service_status')
    if new_status in dict(JobCard.ServiceStatus.choices):
        # Guard: once a Service Invoice exists for this job card, its status
        # is locked at 'invoiced' -- no rolling back to an earlier stage.
        if _job_card_has_invoice(job_card) and new_status != JobCard.ServiceStatus.INVOICED:
            messages.error(
                request,
                'Cannot change status — a Service Invoice already exists for this Job Card.'
            )
            return redirect('service:jobcard_detail', pk=job_card.pk)
        job_card.service_status = new_status
        job_card.save(update_fields=['service_status'])
        log_action(request, 'Job Card', 'update', pk)
        messages.success(request, f'Status updated to {job_card.get_service_status_display()}.')
    return redirect('service:jobcard_detail', pk=job_card.pk)


@login_required
def jobcard_print(request, pk):
    """Print-friendly job card view — no sidebar/topbar."""
    job_card = get_object_or_404(
        JobCard.objects.select_related(
            'customer_vehicle__customer',
            'customer_vehicle__vehicle__bike_model',
            'service_advisor',
            'floor_supervisor',
            'branch',
        ),
        pk=pk,
    )
    labor_charges   = job_card.labor_charges.all()
    total_labor     = labor_charges.aggregate(total=Sum('labor_cost'))['total'] or Decimal('0.00')
    outwork_entries = job_card.outwork_entries.all()
    return render(request, 'service/jobcard_print.html', {
        'job_card':       job_card,
        'labor_charges':  labor_charges,
        'total_labor':    total_labor,
        'spares_issues':  _spares_issued_for(job_card),
        'outwork_entries': outwork_entries,
    })


def _spares_issued_for(job_card):
    """Flattened spares line items issued against this job card, via the
    real job_card FK on spares.SparesIssueAlteration (Phase 2)."""
    from spares.models import SparesIssueAlterationItem
    return list(
        SparesIssueAlterationItem.objects
        .filter(alteration__job_card=job_card)
        .select_related('item', 'alteration__created_by')
    )


# ---------------------------------------------------------------------------
# ServiceBay
# ---------------------------------------------------------------------------

@login_required
def bay_list(request):
    bays = ServiceBay.objects.all()
    return render(request, 'service/bay_list.html', {'bays': bays})


@login_required
@require_module_action('service', 'create')
def bay_create(request):
    form = ServiceBayForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Service bay added successfully.')
        return redirect('service:bay_list')
    return render(request, 'service/bay_form.html',
                  {'form': form, 'title': 'Add Service Bay'})


@login_required
@require_module_action('service', 'edit')
def bay_update(request, pk):
    bay  = get_object_or_404(ServiceBay, pk=pk)
    form = ServiceBayForm(request.POST or None, instance=bay)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Service bay updated successfully.')
        return redirect('service:bay_list')
    return render(request, 'service/bay_form.html',
                  {'form': form, 'title': 'Edit Service Bay'})


# ---------------------------------------------------------------------------
# BayAssignment
# ---------------------------------------------------------------------------

@login_required
@require_module_action('service', 'create')
def bay_assignment_create(request):
    initial = {}
    if request.GET.get('jc'):
        initial['job_card'] = request.GET['jc']
    form = BayAssignmentForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        assignment = form.save()
        log_action(request, 'Bay Assignment', 'create', assignment.pk)
        messages.success(request, 'Bay assigned successfully.')
        return redirect('service:jobcard_detail', pk=assignment.job_card_id)
    return render(request, 'service/bay_assignment_form.html',
                  {'form': form, 'title': 'Assign Bay'})


@login_required
@require_module_action('service', 'edit')
def bay_assignment_update(request, pk):
    assignment = get_object_or_404(BayAssignment, pk=pk)
    form       = BayAssignmentForm(request.POST or None, instance=assignment)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Bay Assignment', 'update', pk)
        messages.success(request, 'Bay assignment updated successfully.')
        return redirect('service:jobcard_detail', pk=assignment.job_card_id)
    return render(request, 'service/bay_assignment_form.html',
                  {'form': form, 'title': 'Edit Bay Assignment'})


# ---------------------------------------------------------------------------
# LaborCharge
# ---------------------------------------------------------------------------

@login_required
@require_module_action('service', 'create')
def labor_charge_create(request):
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    initial = {}
    jc_id = request.POST.get('job_card') or request.GET.get('jc')
    if jc_id:
        initial['job_card'] = jc_id
        job_card = get_object_or_404(JobCard, pk=jc_id)
        if not user_owns(request.user, job_card):
            return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    form = LaborChargeForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        charge = form.save()
        log_action(request, 'Labor Charge', 'create', charge.pk)
        messages.success(request, 'Labor charge added successfully.')
        return redirect('service:jobcard_detail', pk=charge.job_card_id)
    return render(request, 'service/labor_charge_form.html',
                  {'form': form, 'title': 'Add Labor Charge'})


@login_required
@require_module_action('service', 'edit')
def labor_charge_update(request, pk):
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    charge = get_object_or_404(LaborCharge, pk=pk)
    if not user_owns(request.user, charge.job_card):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    form   = LaborChargeForm(request.POST or None, instance=charge)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Labor Charge', 'update', pk)
        messages.success(request, 'Labor charge updated successfully.')
        return redirect('service:jobcard_detail', pk=charge.job_card_id)
    return render(request, 'service/labor_charge_form.html',
                  {'form': form, 'title': 'Edit Labor Charge'})


@login_required
@require_POST
@require_module_action('service', 'delete')
def labor_charge_delete(request, pk):
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    charge = get_object_or_404(LaborCharge, pk=pk)
    if not user_owns(request.user, charge.job_card):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    jc_pk  = charge.job_card_id
    charge.delete()
    log_action(request, 'Labor Charge', 'delete', pk)
    messages.success(request, 'Labor charge deleted.')
    return redirect('service:jobcard_detail', pk=jc_pk)


# ---------------------------------------------------------------------------
# ServiceInvoice
# ---------------------------------------------------------------------------

@login_required
@require_module_action('service', 'create')
def service_invoice_create(request):
    initial = {}
    jc_pk = request.GET.get('jc')
    if jc_pk:
        initial['job_card'] = jc_pk
        # Redirect to existing invoice rather than raising a duplicate error
        existing = ServiceInvoice.objects.filter(job_card_id=jc_pk).first()
        if existing:
            messages.info(request, 'A service invoice already exists for this job card.')
            return redirect('service:service_invoice_detail', pk=existing.pk)
    form = ServiceInvoiceForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        # Guard: the workshop pipeline (Pending -> Water Wash -> In Bay ->
        # In Progress -> Outwork -> Final Inspection -> Ready -> Invoiced) is
        # only meaningful if billing can't skip straight to Invoiced -- a Job
        # Card must have completed Final Inspection (status Ready) first.
        target_job_card = get_object_or_404(JobCard, pk=form.cleaned_data['job_card'].pk)
        if target_job_card.service_status != JobCard.ServiceStatus.READY:
            messages.error(
                request,
                f'Cannot create a Service Invoice — Job Card status is '
                f'"{target_job_card.get_service_status_display()}", not "Ready". '
                f'Complete Final Inspection first.'
            )
            return redirect('service:jobcard_detail', pk=target_job_card.pk)
        invoice = form.save(commit=False)
        # Include time to avoid duplicate invoice_number on same day for same job card
        invoice.invoice_number = f'SINV-{invoice.job_card_id}-{timezone.now().strftime("%Y%m%d%H%M%S")}'
        invoice.save()
        # Calculate totals from labour, spares, outwork
        invoice.calculate_totals()
        # Advance job card to invoiced
        JobCard.objects.filter(pk=invoice.job_card_id).update(service_status='invoiced')
        # Increment free_services_used if vehicle is under warranty and has free services
        try:
            from .models import JobCard as JC
            from django.db.models import F
            from customer_vehicles.models import CustomerVehicle
            _jc = JC.objects.select_related('customer_vehicle').get(pk=invoice.job_card_id)
            _cv = _jc.customer_vehicle
            if _cv and _cv.warranty_active and _cv.free_services_remaining > 0:
                CustomerVehicle.objects.filter(pk=_cv.pk).update(
                    free_services_used=F('free_services_used') + 1
                )
        except Exception as exc:
            logger.error("Failed to increment free_services_used for job card %s: %s",
                         invoice.job_card_id, exc)
        log_action(request, 'Service Invoice', 'create', invoice.pk)
        messages.success(request, 'Service invoice created and totals calculated.')
        return redirect('service:service_invoice_detail', pk=invoice.pk)
    job_card = None
    if request.GET.get('jc'):
        from .models import JobCard as JC
        job_card = JC.objects.filter(pk=request.GET['jc']).first()
    return render(request, 'service/service_invoice_form.html',
                  {'form': form, 'title': 'Create Service Invoice', 'job_card': job_card})


@login_required
@require_module_action('service', 'edit')
def service_invoice_update(request, pk):
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    invoice = get_object_or_404(ServiceInvoice, pk=pk)
    if not user_owns(request.user, invoice.job_card):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    form    = ServiceInvoiceForm(request.POST or None, instance=invoice)
    if request.method == 'POST' and form.is_valid():
        form.save()
        invoice.calculate_totals()  # Recalculate in case discount changed
        log_action(request, 'Service Invoice', 'update', pk)
        messages.success(request, 'Service invoice updated successfully.')
        return redirect('service:service_invoice_detail', pk=invoice.pk)
    return render(request, 'service/service_invoice_form.html',
                  {'form': form, 'invoice': invoice, 'title': 'Edit Service Invoice'})


@login_required
def service_invoice_detail(request, pk):
    invoice = get_object_or_404(
        ServiceInvoice.objects.select_related(
            'job_card__customer_vehicle__customer',
            'job_card__customer_vehicle__vehicle__bike_model',
            'job_card__branch',
        ),
        pk=pk
    )
    labor_charges   = invoice.job_card.labor_charges.all()
    spares_issues   = _spares_issued_for(invoice.job_card)
    outwork_entries = invoice.job_card.outwork_entries.all()
    from billing.models import split_gst
    cgst_amount, sgst_amount, igst_amount = split_gst(
        invoice.gst_amount, invoice.job_card.customer_vehicle.customer
    )
    return render(request, 'service/service_invoice_detail.html', {
        'invoice':         invoice,
        'labor_charges':   labor_charges,
        'spares_issues':   spares_issues,
        'outwork_entries': outwork_entries,
        'cgst_amount':     cgst_amount,
        'sgst_amount':     sgst_amount,
        'igst_amount':     igst_amount,
        'is_interstate':   igst_amount > 0,
    })


# ---------------------------------------------------------------------------
# OutworkEntry
# ---------------------------------------------------------------------------

@login_required
@require_module_action('service', 'create')
def outwork_create(request):
    initial = {}
    if request.GET.get('jc'):
        initial['job_card'] = request.GET['jc']
    form = OutworkEntryForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        entry = form.save()
        log_action(request, 'Outwork', 'create', entry.pk)
        messages.success(request, 'Vehicle sent for outwork successfully.')
        return redirect('service:jobcard_detail', pk=entry.job_card_id)
    return render(request, 'service/outwork_form.html',
                  {'form': form, 'title': 'Send for Outwork'})


@login_required
@require_module_action('service', 'edit')
def outwork_update(request, pk):
    entry = get_object_or_404(OutworkEntry, pk=pk)
    form  = OutworkEntryForm(request.POST or None, instance=entry)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Outwork', 'update', pk)
        messages.success(request, 'Outwork entry updated successfully.')
        return redirect('service:jobcard_detail', pk=entry.job_card_id)
    return render(request, 'service/outwork_form.html',
                  {'form': form, 'title': 'Edit Outwork Entry'})


@login_required
@require_POST
def outwork_return(request, pk):
    entry             = get_object_or_404(OutworkEntry, pk=pk)
    entry.status      = OutworkEntry.Status.RETURNED
    entry.returned_at = timezone.now()
    entry.save(update_fields=['status', 'returned_at'])
    log_action(request, 'Outwork', 'update', pk)
    messages.success(request, 'Outwork marked as returned.')
    return redirect('service:jobcard_detail', pk=entry.job_card_id)


# GAP 4/5/9/10/11 views
from service._gap_views import (
    jobcard_advance_status, jobcard_issue_spare,
    warranty_claim_list, warranty_claim_create, warranty_claim_detail, warranty_claim_update,
    insurance_estimation_create, insurance_estimation_detail, insurance_estimation_update,
    discount_master_list, discount_master_create,
)

# GAP 14-31 views imported from sub-module
from service._gap14_31_views import *  # noqa: E402,F401,F403



# ============================================================
# FEATURE 4 — Service Reminders
# ============================================================
from .models import ServiceReminder
from .forms import ServiceReminderForm


@login_required
def reminder_list(request):
    reminders = ServiceReminder.objects.select_related(
        'customer_vehicle__customer',
        'customer_vehicle__vehicle__bike_model',
        'assigned_to'
    )
    rtype = request.GET.get('type', '')
    if rtype:
        reminders = reminders.filter(reminder_type=rtype)
    from datetime import date
    today = date.today()
    return render(request, 'service/reminder_list.html', {
        'reminders': reminders, 'today': today, 'filter_type': rtype,
    })


@login_required
@require_module_action('service', 'edit')
def reminder_update(request, pk):
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    reminder = get_object_or_404(ServiceReminder, pk=pk)
    if not user_owns(request.user, reminder):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    if request.method == 'POST':
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        if new_status in dict(ServiceReminder.Status.choices):
            reminder.status = new_status
            if notes:
                reminder.notes = notes
            reminder.save()
            from django.contrib import messages as _msg
            _msg.success(request, 'Reminder updated.')
        return redirect('service:reminder_list')
    return render(request, 'service/reminder_update.html', {'reminder': reminder})


# ============================================================
# FEATURE 7 — Technician Productivity Report
# ============================================================

@login_required
def technician_report(request):
    from datetime import date
    from django.db.models import Count, Sum
    import calendar as _cal
    today = date.today()
    month = int(request.GET.get('month', today.month))
    year  = int(request.GET.get('year',  today.year))

    from accounts.models import User as _User
    technicians = _User.objects.filter(
        bay_assignments__job_card__created_at__month=month,
        bay_assignments__job_card__created_at__year=year
    ).annotate(
        job_cards_count=Count('bay_assignments__job_card', distinct=True),
        total_labour=Sum('bay_assignments__job_card__labor_charges__labor_cost')
    ).distinct().order_by('-job_cards_count')

    context = {
        'month': month, 'year': year,
        'month_name': _cal.month_name[month],
        'technicians': technicians,
    }
    return render(request, 'service/technician_report.html', context)


# ---------------------------------------------------------------------------
# Delete views — Issue 11
# ---------------------------------------------------------------------------

@login_required
@require_POST
@require_module_action('service', 'delete')
def enquiry_delete(request, pk):
    from django.db.models import ProtectedError
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    enq = get_object_or_404(ServiceEnquiry, pk=pk)
    if not user_owns(request.user, enq):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        enq.delete()
        log_action(request, 'ServiceEnquiry', 'delete', pk)
        messages.success(request, f'Service enquiry SENQ-{pk} deleted.')
    except ProtectedError:
        messages.error(
            request,
            f'Cannot delete SENQ-{pk}: it has linked appointments or job cards.'
        )
        return redirect('service:enquiry_detail', pk=pk)
    return redirect('service:enquiry_list')


@login_required
@require_POST
@require_module_action('service', 'delete')
def appointment_delete(request, pk):
    from django.db.models import ProtectedError
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    apt = get_object_or_404(ServiceAppointment, pk=pk)
    if apt.service_enquiry_id and not user_owns(request.user, apt.service_enquiry):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        apt.delete()
        log_action(request, 'ServiceAppointment', 'delete', pk)
        messages.success(request, 'Service appointment deleted.')
    except ProtectedError:
        messages.error(request, 'Cannot delete appointment: a job card is linked to it.')
        return redirect('service:appointment_list')
    return redirect('service:appointment_list')


@login_required
@require_POST
@require_module_action('service', 'delete')
def jobcard_delete(request, pk):
    from django.db.models import ProtectedError
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    jc = get_object_or_404(JobCard, pk=pk)
    if not user_owns(request.user, jc):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    if jc.service_status != 'pending':
        messages.error(
            request,
            f'Cannot delete JC-{pk}: status is "{jc.get_service_status_display()}". '
            'Only Pending job cards can be deleted.'
        )
        return redirect('service:jobcard_detail', pk=pk)
    try:
        jc.delete()
        log_action(request, 'JobCard', 'delete', pk)
        messages.success(request, f'Job card JC-{pk} deleted.')
    except ProtectedError:
        messages.error(request, f'Cannot delete JC-{pk}: invoices or other records are linked.')
        return redirect('service:jobcard_detail', pk=pk)
    return redirect('service:jobcard_list')


# ---------------------------------------------------------------------------
# Vehicle Service Master — ERP Alignment
# ---------------------------------------------------------------------------

@login_required
def vehicle_service_master_list(request):
    masters = VehicleServiceMaster.objects.select_related('bike_model').prefetch_related('schedules').all()
    return render(request, 'service/vehicle_service_master_list.html', {'masters': masters})


@login_required
@require_module_action('service', 'create')
def vehicle_service_master_create(request):
    form     = VehicleServiceMasterForm(request.POST or None)
    formset  = VehicleServiceScheduleFormSet(request.POST or None, prefix='schedules')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        master = form.save()
        formset.instance = master
        formset.save()
        log_action(request, 'VehicleServiceMaster', 'create', master.pk)
        messages.success(request, 'Vehicle service master created.')
        return redirect('service:vehicle_service_master_detail', pk=master.pk)
    if request.method == 'POST':
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'service/vehicle_service_master_form.html', {
        'form': form, 'formset': formset, 'title': 'New Vehicle Service Master',
    })


@login_required
def vehicle_service_master_detail(request, pk):
    master = get_object_or_404(VehicleServiceMaster.objects.select_related('bike_model').prefetch_related('schedules'), pk=pk)
    return render(request, 'service/vehicle_service_master_detail.html', {'master': master})


@login_required
@require_module_action('service', 'edit')
def vehicle_service_master_update(request, pk):
    master  = get_object_or_404(VehicleServiceMaster, pk=pk)
    form    = VehicleServiceMasterForm(request.POST or None, instance=master)
    formset = VehicleServiceScheduleFormSet(request.POST or None, instance=master, prefix='schedules')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        form.save()
        formset.save()
        log_action(request, 'VehicleServiceMaster', 'update', pk)
        messages.success(request, 'Vehicle service master updated.')
        return redirect('service:vehicle_service_master_detail', pk=master.pk)
    if request.method == 'POST':
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'service/vehicle_service_master_form.html', {
        'form': form, 'formset': formset, 'title': 'Edit Vehicle Service Master', 'master': master,
    })


# ---------------------------------------------------------------------------
# Phase 2 — reference-parity workshop stage documents
# ---------------------------------------------------------------------------

# Ordered workshop stages (earliest -> latest) with the JobCard related_name
# that holds that stage's documents. Used to guard against cancelling an
# earlier-stage document once a later stage (or the Service Invoice) already
# has a submitted document for the same Job Card.
_STAGE_RELATED_NAMES = [
    ('water_wash',       'water_wash_entries'),
    ('bay_in',           'bay_in_entries'),
    ('bay_out',          'bay_out_entries'),
    ('outwork_issue',    'outwork_issues'),
    ('outwork_return',   'outwork_returns'),
    ('final_inspection', 'final_inspections'),
]


def _job_card_has_invoice(job_card):
    return ServiceInvoice.objects.filter(job_card=job_card).exists()


def _later_stage_submitted(job_card, list_name):
    """True if a workshop stage later than `list_name` already has a
    submitted document for this job card, or a Service Invoice already
    exists (the final gate nothing earlier should be cancelled past)."""
    if _job_card_has_invoice(job_card):
        return True
    names = [n for n, _ in _STAGE_RELATED_NAMES]
    if list_name not in names:
        return False
    idx = names.index(list_name)
    from accounts.models import DocStatusMixin
    for _, related in _STAGE_RELATED_NAMES[idx + 1:]:
        manager = getattr(job_card, related, None)
        if manager is not None and manager.filter(docstatus=DocStatusMixin.DocStatus.SUBMITTED).exists():
            return True
    return False


def _stage_submit(request, model, pk, list_name):
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    obj = get_object_or_404(model, pk=pk)
    if not user_owns(request.user, obj.job_card):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        obj.submit(request.user)
        log_action(request, model.__name__, 'update', pk)
        messages.success(request, f'{obj} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect(f'service:{list_name}_detail', pk=pk)


def _stage_cancel(request, model, pk, list_name):
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    obj = get_object_or_404(model, pk=pk)
    if not user_owns(request.user, obj.job_card):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    if _later_stage_submitted(obj.job_card, list_name):
        messages.error(
            request,
            'Cannot cancel — a later workshop stage (or Service Invoice) already '
            'exists for this Job Card.'
        )
        return redirect(f'service:{list_name}_detail', pk=pk)
    try:
        obj.cancel(request.user)
        log_action(request, model.__name__, 'update', pk)
        messages.success(request, f'{obj} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect(f'service:{list_name}_detail', pk=pk)


# ---- Water Wash Done ----

@login_required
@require_module_action('service', 'create')
def water_wash_create(request):
    initial = {}
    if request.GET.get('jc'):
        initial['job_card'] = request.GET['jc']
    form = WaterWashDoneForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        try:
            check_stage_order(form.cleaned_data['job_card'], JobCard.ServiceStatus.PENDING)
        except ValidationError as e:
            messages.error(request, str(e))
            return render(request, 'service/water_wash_form.html', {'form': form, 'title': 'Water Wash Done'})
        obj = form.save()
        log_action(request, 'Water Wash Done', 'create', obj.pk)
        messages.success(request, 'Water Wash Done recorded.')
        return redirect('service:water_wash_detail', pk=obj.pk)
    return render(request, 'service/water_wash_form.html', {'form': form, 'title': 'Water Wash Done'})


@login_required
def water_wash_detail(request, pk):
    obj = get_object_or_404(WaterWashDone, pk=pk)
    return render(request, 'service/water_wash_detail.html', {'obj': obj})


@login_required
@require_POST
@require_module_action('service', 'edit')
def water_wash_submit(request, pk):
    return _stage_submit(request, WaterWashDone, pk, 'water_wash')


@login_required
@require_POST
@require_module_action('service', 'edit')
def water_wash_cancel(request, pk):
    return _stage_cancel(request, WaterWashDone, pk, 'water_wash')


# ---- Bay In Creation ----

@login_required
@require_module_action('service', 'create')
def bay_in_create(request):
    initial = {}
    if request.GET.get('jc'):
        initial['job_card'] = request.GET['jc']
    form = BayInCreationForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        try:
            check_stage_order(form.cleaned_data['job_card'], JobCard.ServiceStatus.WATER_WASH)
        except ValidationError as e:
            messages.error(request, str(e))
            return render(request, 'service/bay_in_form.html', {'form': form, 'title': 'Bay In Creation'})
        obj = form.save()
        log_action(request, 'Bay In Creation', 'create', obj.pk)
        messages.success(request, 'Bay In recorded.')
        return redirect('service:bay_in_detail', pk=obj.pk)
    return render(request, 'service/bay_in_form.html', {'form': form, 'title': 'Bay In Creation'})


@login_required
def bay_in_detail(request, pk):
    obj = get_object_or_404(BayInCreation, pk=pk)
    return render(request, 'service/bay_in_detail.html', {'obj': obj})


@login_required
@require_POST
@require_module_action('service', 'edit')
def bay_in_submit(request, pk):
    return _stage_submit(request, BayInCreation, pk, 'bay_in')


@login_required
@require_POST
@require_module_action('service', 'edit')
def bay_in_cancel(request, pk):
    return _stage_cancel(request, BayInCreation, pk, 'bay_in')


# ---- Bay Out Creation ----

@login_required
@require_module_action('service', 'create')
def bay_out_create(request):
    initial = {}
    if request.GET.get('jc'):
        initial['job_card'] = request.GET['jc']
    form = BayOutCreationForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        try:
            check_stage_order(form.cleaned_data['job_card'], JobCard.ServiceStatus.IN_BAY)
        except ValidationError as e:
            messages.error(request, str(e))
            return render(request, 'service/bay_out_form.html', {'form': form, 'title': 'Bay Out Creation'})
        obj = form.save()
        log_action(request, 'Bay Out Creation', 'create', obj.pk)
        messages.success(request, 'Bay Out recorded.')
        return redirect('service:bay_out_detail', pk=obj.pk)
    return render(request, 'service/bay_out_form.html', {'form': form, 'title': 'Bay Out Creation'})


@login_required
def bay_out_detail(request, pk):
    obj = get_object_or_404(BayOutCreation, pk=pk)
    return render(request, 'service/bay_out_detail.html', {'obj': obj})


@login_required
@require_POST
@require_module_action('service', 'edit')
def bay_out_submit(request, pk):
    return _stage_submit(request, BayOutCreation, pk, 'bay_out')


@login_required
@require_POST
@require_module_action('service', 'edit')
def bay_out_cancel(request, pk):
    return _stage_cancel(request, BayOutCreation, pk, 'bay_out')


# ---- Final Inspection ----

@login_required
@require_module_action('service', 'create')
def final_inspection_create(request):
    initial = {}
    if request.GET.get('jc'):
        initial['job_card'] = request.GET['jc']
    form = FinalInspectionForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        try:
            check_stage_order(form.cleaned_data['job_card'], JobCard.ServiceStatus.OUTWORK)
        except ValidationError as e:
            messages.error(request, str(e))
            return render(request, 'service/final_inspection_form.html', {'form': form, 'title': 'Final Inspection'})
        obj = form.save()
        log_action(request, 'Final Inspection', 'create', obj.pk)
        messages.success(request, 'Final Inspection recorded.')
        return redirect('service:final_inspection_detail', pk=obj.pk)
    return render(request, 'service/final_inspection_form.html', {'form': form, 'title': 'Final Inspection'})


@login_required
def final_inspection_detail(request, pk):
    obj = get_object_or_404(FinalInspection, pk=pk)
    return render(request, 'service/final_inspection_detail.html', {'obj': obj})


@login_required
@require_POST
@require_module_action('service', 'edit')
def final_inspection_submit(request, pk):
    return _stage_submit(request, FinalInspection, pk, 'final_inspection')


@login_required
@require_POST
@require_module_action('service', 'edit')
def final_inspection_cancel(request, pk):
    return _stage_cancel(request, FinalInspection, pk, 'final_inspection')


# ---- Outwork Entry Issue ----

@login_required
@require_module_action('service', 'create')
def outwork_issue_create(request):
    initial = {}
    if request.GET.get('jc'):
        initial['job_card'] = request.GET['jc']
    form = OutworkEntryIssueForm(request.POST or None, initial=initial)
    work_formset = OutworkWorkDetailFormSet(request.POST or None, prefix='work')
    spares_formset = OutworkSpareItemFormSet(request.POST or None, prefix='spares')
    if request.method == 'POST':
        if form.is_valid() and work_formset.is_valid() and spares_formset.is_valid():
            try:
                check_stage_order(form.cleaned_data['job_card'], JobCard.ServiceStatus.IN_PROGRESS)
            except ValidationError as e:
                messages.error(request, str(e))
                return render(request, 'service/outwork_issue_form.html', {
                    'form': form, 'work_formset': work_formset, 'spares_formset': spares_formset,
                    'title': 'Outwork Entry Issue',
                })
            obj = form.save()
            work_formset.instance = obj
            work_formset.save()
            spares_formset.instance = obj
            spares_formset.save()
            log_action(request, 'Outwork Entry Issue', 'create', obj.pk)
            messages.success(request, 'Outwork Entry Issue created.')
            return redirect('service:outwork_issue_detail', pk=obj.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'service/outwork_issue_form.html', {
        'form': form, 'work_formset': work_formset, 'spares_formset': spares_formset,
        'title': 'Outwork Entry Issue',
    })


@login_required
def outwork_issue_detail(request, pk):
    obj = get_object_or_404(OutworkEntryIssue, pk=pk)
    return render(request, 'service/outwork_issue_detail.html', {'obj': obj})


@login_required
@require_POST
@require_module_action('service', 'edit')
def outwork_issue_submit(request, pk):
    return _stage_submit(request, OutworkEntryIssue, pk, 'outwork_issue')


@login_required
@require_POST
@require_module_action('service', 'edit')
def outwork_issue_cancel(request, pk):
    return _stage_cancel(request, OutworkEntryIssue, pk, 'outwork_issue')


# ---- Outwork Entry Return ----

@login_required
@require_module_action('service', 'create')
def outwork_return_create(request):
    initial = {}
    if request.GET.get('issue'):
        issue = get_object_or_404(OutworkEntryIssue, pk=request.GET['issue'])
        initial['outwork_issue'] = issue.pk
        initial['job_card'] = issue.job_card_id
    form = OutworkEntryReturnForm(request.POST or None, initial=initial)
    details_formset = OutworkReturnDetailFormSet(request.POST or None, prefix='details')
    spares_formset = OutworkReturnSpareItemFormSet(request.POST or None, prefix='spares')
    if request.method == 'POST':
        if form.is_valid() and details_formset.is_valid() and spares_formset.is_valid():
            try:
                check_stage_order(form.cleaned_data['job_card'], JobCard.ServiceStatus.OUTWORK)
            except ValidationError as e:
                messages.error(request, str(e))
                return render(request, 'service/outwork_return_form.html', {
                    'form': form, 'details_formset': details_formset, 'spares_formset': spares_formset,
                    'title': 'Outwork Entry Return',
                })
            obj = form.save()
            details_formset.instance = obj
            details_formset.save()
            spares_formset.instance = obj
            spares_formset.save()
            log_action(request, 'Outwork Entry Return', 'create', obj.pk)
            messages.success(request, 'Outwork Entry Return created.')
            return redirect('service:outwork_return_detail', pk=obj.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'service/outwork_return_form.html', {
        'form': form, 'details_formset': details_formset, 'spares_formset': spares_formset,
        'title': 'Outwork Entry Return',
    })


@login_required
def outwork_return_detail(request, pk):
    obj = get_object_or_404(OutworkEntryReturn, pk=pk)
    return render(request, 'service/outwork_return_detail.html', {'obj': obj})


@login_required
@require_POST
@require_module_action('service', 'edit')
def outwork_return_submit(request, pk):
    return _stage_submit(request, OutworkEntryReturn, pk, 'outwork_return')


@login_required
@require_POST
@require_module_action('service', 'edit')
def outwork_return_cancel(request, pk):
    return _stage_cancel(request, OutworkEntryReturn, pk, 'outwork_return')


# ---- Labor Charges Alteration ----

@login_required
@require_module_action('service', 'create')
def labor_alteration_create(request):
    initial = {}
    if request.GET.get('jc'):
        initial['job_card'] = request.GET['jc']
    form = LaborChargesAlterationForm(request.POST or None, initial=initial)
    labor_formset = LaborDetailLineFormSet(request.POST or None, prefix='labor')
    spares_formset = LaborSpareItemFormSet(request.POST or None, prefix='spares')
    if request.method == 'POST':
        if form.is_valid() and labor_formset.is_valid() and spares_formset.is_valid():
            obj = form.save()
            labor_formset.instance = obj
            labor_formset.save()
            spares_formset.instance = obj
            spares_formset.save()
            log_action(request, 'Labor Charges Alteration', 'create', obj.pk)
            messages.success(request, 'Labor Charges Alteration created.')
            return redirect('service:labor_alteration_detail', pk=obj.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'service/labor_alteration_form.html', {
        'form': form, 'labor_formset': labor_formset, 'spares_formset': spares_formset,
        'title': 'Labor Charges Alteration',
    })


@login_required
def labor_alteration_detail(request, pk):
    obj = get_object_or_404(LaborChargesAlteration, pk=pk)
    return render(request, 'service/labor_alteration_detail.html', {'obj': obj})


@login_required
@require_POST
@require_module_action('service', 'edit')
def labor_alteration_submit(request, pk):
    return _stage_submit(request, LaborChargesAlteration, pk, 'labor_alteration')


@login_required
@require_POST
@require_module_action('service', 'edit')
def labor_alteration_cancel(request, pk):
    return _stage_cancel(request, LaborChargesAlteration, pk, 'labor_alteration')
