from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import (BayAssignmentForm, JobCardForm, LaborChargeForm,
                    ServiceAppointmentForm, ServiceBayForm, ServiceEnquiryForm,
                    ServiceInvoiceForm)
from .models import (BayAssignment, JobCard, LaborCharge, ServiceAppointment,
                     ServiceBay, ServiceEnquiry, ServiceInvoice)


# ---------------------------------------------------------------------------
# ServiceEnquiry
# ---------------------------------------------------------------------------

@login_required
def enquiry_list(request):
    # context: enquiries — filtered queryset; q — search string
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
    # context: enquiry — ServiceEnquiry; appointments — related queryset
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
    # context: form — ServiceEnquiryForm; title — str
    # Pre-fills customer_vehicle from GET ?cv=<pk>
    initial = {}
    if request.GET.get('cv'):
        initial['customer_vehicle'] = request.GET['cv']
    form = ServiceEnquiryForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        enquiry = form.save()
        return redirect('service:enquiry_detail', pk=enquiry.pk)
    return render(request, 'service/enquiry_form.html',
                  {'form': form, 'title': 'New Service Enquiry'})


@login_required
def enquiry_update(request, pk):
    # context: form — ServiceEnquiryForm; title — str
    enquiry = get_object_or_404(ServiceEnquiry, pk=pk)
    form    = ServiceEnquiryForm(request.POST or None, instance=enquiry)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('service:enquiry_detail', pk=enquiry.pk)
    return render(request, 'service/enquiry_form.html',
                  {'form': form, 'title': 'Edit Service Enquiry'})


# ---------------------------------------------------------------------------
# ServiceAppointment
# ---------------------------------------------------------------------------

@login_required
def appointment_create(request):
    # context: form — ServiceAppointmentForm; title — str
    # Pre-fills service_enquiry from GET ?enquiry=<pk>
    initial = {}
    if request.GET.get('enquiry'):
        initial['service_enquiry'] = request.GET['enquiry']
    form = ServiceAppointmentForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        appt = form.save()
        return redirect('service:enquiry_detail', pk=appt.service_enquiry_id)
    return render(request, 'service/appointment_form.html',
                  {'form': form, 'title': 'New Appointment'})


@login_required
def appointment_update(request, pk):
    # context: form — ServiceAppointmentForm; title — str
    appt = get_object_or_404(ServiceAppointment, pk=pk)
    form = ServiceAppointmentForm(request.POST or None, instance=appt)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('service:enquiry_detail', pk=appt.service_enquiry_id)
    return render(request, 'service/appointment_form.html',
                  {'form': form, 'title': 'Edit Appointment'})


@login_required
@require_POST
def appointment_cancel(request, pk):
    # POST only — sets status to cancelled
    appt        = get_object_or_404(ServiceAppointment, pk=pk)
    appt.status = ServiceAppointment.Status.CANCELLED
    appt.save(update_fields=['status'])
    return redirect('service:enquiry_detail', pk=appt.service_enquiry_id)


# ---------------------------------------------------------------------------
# JobCard
# ---------------------------------------------------------------------------

@login_required
def jobcard_list(request):
    # context: job_cards — filtered queryset; q — search string;
    #          status_filter — active tab value; status_choices — list
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
    return render(request, 'service/jobcard_list.html', {
        'job_cards':      qs,
        'q':              q,
        'status_filter':  status_filter,
        'status_choices': JobCard.ServiceStatus.choices,
    })


@login_required
def jobcard_detail(request, pk):
    # context: job_card — JobCard; bay_assignments — related queryset;
    #          labor_charges — related queryset; total_labor — Decimal;
    #          spares_issues — SparesIssue queryset for this job card
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
    bay_assignments = job_card.bay_assignments.select_related('bay', 'mechanic').all()
    labor_charges   = job_card.labor_charges.all()
    total_labor     = labor_charges.aggregate(total=Sum('labor_cost'))['total'] or Decimal('0.00')
    return render(request, 'service/jobcard_detail.html', {
        'job_card':        job_card,
        'bay_assignments': bay_assignments,
        'labor_charges':   labor_charges,
        'total_labor':     total_labor,
        'spares_issues':   job_card.spares_issues.select_related('spare_part', 'issued_by').all(),
    })


@login_required
def jobcard_create(request):
    # context: form — JobCardForm; title — str
    # Pre-fills customer_vehicle from GET ?cv=<pk>
    initial = {}
    if request.GET.get('cv'):
        initial['customer_vehicle'] = request.GET['cv']
    form = JobCardForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        jc = form.save()
        return redirect('service:jobcard_detail', pk=jc.pk)
    return render(request, 'service/jobcard_form.html',
                  {'form': form, 'title': 'New Job Card'})


@login_required
def jobcard_update(request, pk):
    # context: form — JobCardForm; title — str
    job_card = get_object_or_404(JobCard, pk=pk)
    form     = JobCardForm(request.POST or None, instance=job_card)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('service:jobcard_detail', pk=job_card.pk)
    return render(request, 'service/jobcard_form.html',
                  {'form': form, 'title': 'Edit Job Card'})


@login_required
@require_POST
def jobcard_status_update(request, pk):
    # POST only — updates service_status field only
    job_card   = get_object_or_404(JobCard, pk=pk)
    new_status = request.POST.get('service_status')
    if new_status in dict(JobCard.ServiceStatus.choices):
        job_card.service_status = new_status
        job_card.save(update_fields=['service_status'])
    return redirect('service:jobcard_detail', pk=job_card.pk)


# ---------------------------------------------------------------------------
# ServiceBay
# ---------------------------------------------------------------------------

@login_required
def bay_list(request):
    # context: bays — all ServiceBay instances
    bays = ServiceBay.objects.all()
    return render(request, 'service/bay_list.html', {'bays': bays})


@login_required
def bay_create(request):
    # context: form — ServiceBayForm; title — str
    form = ServiceBayForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('service:bay_list')
    return render(request, 'service/bay_form.html',
                  {'form': form, 'title': 'Add Service Bay'})


@login_required
def bay_update(request, pk):
    # context: form — ServiceBayForm; title — str
    bay  = get_object_or_404(ServiceBay, pk=pk)
    form = ServiceBayForm(request.POST or None, instance=bay)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('service:bay_list')
    return render(request, 'service/bay_form.html',
                  {'form': form, 'title': 'Edit Service Bay'})


# ---------------------------------------------------------------------------
# BayAssignment
# ---------------------------------------------------------------------------

@login_required
def bay_assignment_create(request):
    # context: form — BayAssignmentForm; title — str
    # Pre-fills job_card from GET ?jc=<pk>
    initial = {}
    if request.GET.get('jc'):
        initial['job_card'] = request.GET['jc']
    form = BayAssignmentForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        assignment = form.save()
        return redirect('service:jobcard_detail', pk=assignment.job_card_id)
    return render(request, 'service/bay_assignment_form.html',
                  {'form': form, 'title': 'Assign Bay'})


@login_required
def bay_assignment_update(request, pk):
    # context: form — BayAssignmentForm; title — str
    assignment = get_object_or_404(BayAssignment, pk=pk)
    form       = BayAssignmentForm(request.POST or None, instance=assignment)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('service:jobcard_detail', pk=assignment.job_card_id)
    return render(request, 'service/bay_assignment_form.html',
                  {'form': form, 'title': 'Edit Bay Assignment'})


# ---------------------------------------------------------------------------
# LaborCharge
# ---------------------------------------------------------------------------

@login_required
def labor_charge_create(request):
    # context: form — LaborChargeForm; title — str
    # Pre-fills job_card from GET ?jc=<pk>
    initial = {}
    if request.GET.get('jc'):
        initial['job_card'] = request.GET['jc']
    form = LaborChargeForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        charge = form.save()
        return redirect('service:jobcard_detail', pk=charge.job_card_id)
    return render(request, 'service/labor_charge_form.html',
                  {'form': form, 'title': 'Add Labor Charge'})


@login_required
def labor_charge_update(request, pk):
    # context: form — LaborChargeForm; title — str
    charge = get_object_or_404(LaborCharge, pk=pk)
    form   = LaborChargeForm(request.POST or None, instance=charge)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('service:jobcard_detail', pk=charge.job_card_id)
    return render(request, 'service/labor_charge_form.html',
                  {'form': form, 'title': 'Edit Labor Charge'})


@login_required
@require_POST
def labor_charge_delete(request, pk):
    # POST only — deletes a LaborCharge
    charge = get_object_or_404(LaborCharge, pk=pk)
    jc_pk  = charge.job_card_id
    charge.delete()
    return redirect('service:jobcard_detail', pk=jc_pk)


# ---------------------------------------------------------------------------
# ServiceInvoice
# ---------------------------------------------------------------------------

@login_required
def service_invoice_create(request):
    # context: form — ServiceInvoiceForm; title — str
    # Pre-fills job_card from GET ?jc=<pk>
    initial = {}
    if request.GET.get('jc'):
        initial['job_card'] = request.GET['jc']
    form = ServiceInvoiceForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        invoice = form.save()
        return redirect('service:service_invoice_detail', pk=invoice.pk)
    return render(request, 'service/service_invoice_form.html',
                  {'form': form, 'title': 'Create Service Invoice'})


@login_required
def service_invoice_update(request, pk):
    # context: form — ServiceInvoiceForm; title — str
    invoice = get_object_or_404(ServiceInvoice, pk=pk)
    form    = ServiceInvoiceForm(request.POST or None, instance=invoice)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('service:service_invoice_detail', pk=invoice.pk)
    return render(request, 'service/service_invoice_form.html',
                  {'form': form, 'title': 'Edit Service Invoice'})


@login_required
def service_invoice_detail(request, pk):
    # context: invoice — ServiceInvoice
    invoice = get_object_or_404(
        ServiceInvoice.objects.select_related(
            'job_card__customer_vehicle__customer'
        ),
        pk=pk
    )
    return render(request, 'service/service_invoice_detail.html', {'invoice': invoice})
