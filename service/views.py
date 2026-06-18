from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.audit import log_action

from .forms import (BayAssignmentForm, JobCardForm, LaborChargeForm, OutworkEntryForm,
                    ServiceAppointmentForm, ServiceBayForm, ServiceEnquiryForm,
                    ServiceInvoiceForm, VehicleServiceMasterForm,
                    VehicleServiceScheduleFormSet)
from .models import (BayAssignment, JobCard, LaborCharge, OutworkEntry,
                     ServiceAppointment, ServiceBay, ServiceEnquiry, ServiceInvoice,
                     VehicleServiceMaster)


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
def enquiry_update(request, pk):
    enquiry = get_object_or_404(ServiceEnquiry, pk=pk)
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
def appointment_cancel(request, pk):
    appt        = get_object_or_404(ServiceAppointment, pk=pk)
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
    })


@login_required
def jobcard_create(request):
    from accounts.permissions import user_is_manager
    is_manager = user_is_manager(request.user)
    initial = {}
    if request.GET.get('cv'):
        initial['customer_vehicle'] = request.GET['cv']
    form = JobCardForm(request.POST or None, initial=initial)
    if not is_manager:
        form.fields.pop('service_advisor', None)
    if request.method == 'POST' and form.is_valid():
        jc = form.save(commit=False)
        if not is_manager:
            jc.service_advisor = request.user
        jc.save()
        log_action(request, 'Job Card', 'create', jc.pk)
        messages.success(request, 'Job card created successfully.')
        return redirect('service:jobcard_detail', pk=jc.pk)
    return render(request, 'service/jobcard_form.html',
                  {'form': form, 'title': 'New Job Card'})


@login_required
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
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Job Card', 'update', pk)
        messages.success(request, 'Job card updated successfully.')
        return redirect('service:jobcard_detail', pk=job_card.pk)
    return render(request, 'service/jobcard_form.html',
                  {'form': form, 'title': 'Edit Job Card'})


@login_required
@require_POST
def jobcard_status_update(request, pk):
    job_card   = get_object_or_404(JobCard, pk=pk)
    new_status = request.POST.get('service_status')
    if new_status in dict(JobCard.ServiceStatus.choices):
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
    """
    SparesIssueAlteration.job_card is a free-text label ('JC-<pk>'), not a
    real FK — this looks it up by that label and flattens to line items.
    """
    from spares.models import SparesIssueAlterationItem
    return list(
        SparesIssueAlterationItem.objects
        .filter(alteration__job_card=f'JC-{job_card.pk}')
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
def bay_create(request):
    form = ServiceBayForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Service bay added successfully.')
        return redirect('service:bay_list')
    return render(request, 'service/bay_form.html',
                  {'form': form, 'title': 'Add Service Bay'})


@login_required
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
def labor_charge_create(request):
    initial = {}
    if request.GET.get('jc'):
        initial['job_card'] = request.GET['jc']
    form = LaborChargeForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        charge = form.save()
        log_action(request, 'Labor Charge', 'create', charge.pk)
        messages.success(request, 'Labor charge added successfully.')
        return redirect('service:jobcard_detail', pk=charge.job_card_id)
    return render(request, 'service/labor_charge_form.html',
                  {'form': form, 'title': 'Add Labor Charge'})


@login_required
def labor_charge_update(request, pk):
    charge = get_object_or_404(LaborCharge, pk=pk)
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
def labor_charge_delete(request, pk):
    charge = get_object_or_404(LaborCharge, pk=pk)
    jc_pk  = charge.job_card_id
    charge.delete()
    log_action(request, 'Labor Charge', 'delete', pk)
    messages.success(request, 'Labor charge deleted.')
    return redirect('service:jobcard_detail', pk=jc_pk)


# ---------------------------------------------------------------------------
# ServiceInvoice
# ---------------------------------------------------------------------------

@login_required
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
        except Exception:
            pass
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
    from accounts.models import CompanySettings
    settings_ = CompanySettings.get_instance()
    rate_total = (settings_.cgst_rate or 0) + (settings_.sgst_rate or 0)
    if rate_total:
        cgst_amount = (invoice.gst_amount * settings_.cgst_rate / rate_total).quantize(Decimal('0.01'))
        sgst_amount = (invoice.gst_amount * settings_.sgst_rate / rate_total).quantize(Decimal('0.01'))
    else:
        cgst_amount = sgst_amount = (invoice.gst_amount / Decimal('2')).quantize(Decimal('0.01'))
    return render(request, 'service/service_invoice_detail.html', {
        'invoice':         invoice,
        'labor_charges':   labor_charges,
        'spares_issues':   spares_issues,
        'outwork_entries': outwork_entries,
        'cgst_amount':     cgst_amount,
        'sgst_amount':     sgst_amount,
    })


# ---------------------------------------------------------------------------
# OutworkEntry
# ---------------------------------------------------------------------------

@login_required
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
def reminder_update(request, pk):
    reminder = get_object_or_404(ServiceReminder, pk=pk)
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
def enquiry_delete(request, pk):
    from django.db.models import ProtectedError
    enq = get_object_or_404(ServiceEnquiry, pk=pk)
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
def appointment_delete(request, pk):
    from django.db.models import ProtectedError
    apt = get_object_or_404(ServiceAppointment, pk=pk)
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
