"""GAP 14-31 views. Imported by service.views via star import."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (AdditionalWorkApprovalForm, CustomerCallForm,
                    InsuranceClaimForm, JobCardRevisitForm,
                    JobCardServiceChildForm)
from .models import (AdditionalWorkApproval, CustomerCall, InsuranceClaim,
                     JobCard, JobCardRevisit, JobCardServiceChild,
                     ServiceEnquiry)


@login_required
def revisit_create(request, jc_pk):
    jc = get_object_or_404(JobCard, pk=jc_pk)
    instance = getattr(jc, 'revisit', None)
    form = JobCardRevisitForm(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.job_card = jc
        obj.save()
        messages.success(request, 'Revisit schedule saved.')
        return redirect('service:jobcard_detail', pk=jc.pk)
    return render(request, 'service/revisit_form.html', {'form': form, 'jc': jc})


@login_required
def service_child_add(request, jc_pk):
    jc = get_object_or_404(JobCard, pk=jc_pk)
    form = JobCardServiceChildForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.job_card = jc
        obj.save()
        messages.success(request, 'Sub-task added.')
        return redirect('service:jobcard_detail', pk=jc.pk)
    return render(request, 'service/service_child_form.html', {'form': form, 'jc': jc})


@login_required
@require_POST
def service_child_toggle(request, pk):
    child = get_object_or_404(JobCardServiceChild, pk=pk)
    if child.status == JobCardServiceChild.Status.COMPLETED:
        child.status = JobCardServiceChild.Status.PENDING
        child.completed_at = None
    else:
        child.status = JobCardServiceChild.Status.COMPLETED
        child.completed_at = timezone.now()
    child.save()
    return redirect('service:jobcard_detail', pk=child.job_card_id)


@login_required
def service_enquiry_bulk_import(request):
    import csv
    from io import TextIOWrapper
    from customer_vehicles.models import CustomerVehicle

    results = None
    if request.method == 'POST' and request.FILES.get('file'):
        f = request.FILES['file']
        rows = []
        try:
            text = TextIOWrapper(f.file, encoding='utf-8-sig', errors='ignore')
            reader = csv.DictReader(text)
            rows = list(reader)
        except Exception as exc:
            messages.error(request, 'Cannot read file: ' + str(exc))

        imported, errors = [], []
        for idx, row in enumerate(rows, start=2):
            row = {(k or '').strip().lower(): (v or '').strip() for k, v in row.items()}
            try:
                reg = row.get('registration_no') or ''
                if not reg:
                    errors.append({'row': idx, 'error': 'registration_no required'})
                    continue
                cv = CustomerVehicle.objects.filter(registration_no__iexact=reg).first()
                if not cv:
                    errors.append({'row': idx, 'error': 'No vehicle for reg ' + reg})
                    continue
                enq = ServiceEnquiry.objects.create(
                    customer_vehicle=cv,
                    issue_description=row.get('issue_description', ''),
                    created_by=request.user,
                )
                imported.append({'row': idx, 'enquiry_id': enq.pk, 'reg': reg})
            except Exception as exc:
                errors.append({'row': idx, 'error': str(exc)})
        results = {
            'imported': imported, 'errors': errors,
            'imported_count': len(imported), 'error_count': len(errors),
            'total': len(rows),
        }
        if imported:
            messages.success(request, str(len(imported)) + ' enquiries created.')
    return render(request, 'service/bulk_import.html', {'results': results})


@login_required
def call_list(request):
    calls = CustomerCall.objects.select_related(
        'customer_vehicle__customer', 'called_by'
    ).order_by('-call_date')[:200]
    return render(request, 'service/call_list.html', {'calls': calls})


@login_required
def call_create(request, cv_pk=None):
    from customer_vehicles.models import CustomerVehicle
    initial = {}
    cv = None
    if cv_pk:
        cv = get_object_or_404(CustomerVehicle, pk=cv_pk)
        initial['customer_vehicle'] = cv
    form = CustomerCallForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.called_by = request.user
        obj.save()
        messages.success(request, 'Call logged.')
        return redirect('service:call_list')
    return render(request, 'service/call_form.html', {'form': form, 'cv': cv})


@login_required
def jobcard_update_customer(request, pk):
    from customers.forms import CustomerForm
    jc = get_object_or_404(
        JobCard.objects.select_related('customer_vehicle__customer'), pk=pk
    )
    customer = jc.customer_vehicle.customer
    form = CustomerForm(request.POST or None, instance=customer)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Customer details updated.')
        return redirect('service:jobcard_detail', pk=jc.pk)
    return render(request, 'service/jobcard_update_customer.html', {
        'form': form, 'jc': jc, 'customer': customer,
    })


@login_required
def insurance_claim_list(request):
    claims = InsuranceClaim.objects.select_related('job_card').order_by('-created_at')
    return render(request, 'service/insurance_claim_list.html', {'claims': claims})


@login_required
def insurance_claim_create(request, jc_pk):
    jc = get_object_or_404(JobCard, pk=jc_pk)
    form = InsuranceClaimForm(request.POST or None, initial={'job_card': jc})
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        messages.success(request, 'Insurance claim ' + obj.claim_number + ' created.')
        return redirect('service:insurance_claim_detail', pk=obj.pk)
    return render(request, 'service/insurance_claim_form.html', {'form': form, 'jc': jc})


@login_required
def insurance_claim_detail(request, pk):
    claim = get_object_or_404(InsuranceClaim.objects.select_related('job_card'), pk=pk)
    return render(request, 'service/insurance_claim_detail.html', {'claim': claim})


@login_required
def insurance_claim_update(request, pk):
    claim = get_object_or_404(InsuranceClaim, pk=pk)
    form = InsuranceClaimForm(request.POST or None, instance=claim)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Insurance claim updated.')
        return redirect('service:insurance_claim_detail', pk=claim.pk)
    return render(request, 'service/insurance_claim_form.html',
                  {'form': form, 'jc': claim.job_card})


@login_required
def additional_work_create(request, jc_pk):
    jc = get_object_or_404(JobCard, pk=jc_pk)
    form = AdditionalWorkApprovalForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.job_card = jc
        obj.save()
        messages.success(request, 'Additional work request created.')
        return redirect('service:jobcard_detail', pk=jc.pk)
    return render(request, 'service/additional_work_form.html', {'form': form, 'jc': jc})


@login_required
@require_POST
def additional_work_send(request, pk):
    awa = get_object_or_404(AdditionalWorkApproval, pk=pk)
    awa.status = AdditionalWorkApproval.Status.SENT
    awa.sent_at = timezone.now()
    awa.save()
    messages.success(request, 'Sent to customer for approval.')
    return redirect('service:jobcard_detail', pk=awa.job_card_id)


@login_required
@require_POST
def additional_work_approve(request, pk):
    awa = get_object_or_404(AdditionalWorkApproval, pk=pk)
    awa.status = AdditionalWorkApproval.Status.APPROVED
    awa.responded_at = timezone.now()
    awa.customer_response = request.POST.get('response', '') or awa.customer_response
    awa.save()
    messages.success(request, 'Additional work approved.')
    return redirect('service:jobcard_detail', pk=awa.job_card_id)


@login_required
@require_POST
def additional_work_reject(request, pk):
    awa = get_object_or_404(AdditionalWorkApproval, pk=pk)
    awa.status = AdditionalWorkApproval.Status.REJECTED
    awa.responded_at = timezone.now()
    awa.customer_response = request.POST.get('response', '') or awa.customer_response
    awa.save()
    messages.success(request, 'Additional work rejected.')
    return redirect('service:jobcard_detail', pk=awa.job_card_id)
