"""GAP 4/5/9/10/11 views — appended into service.views via import."""
from decimal import Decimal
import datetime as _dt

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.audit import log_action
from .models import JobCard


# ---------------------------------------------------------------------------
# GAP 4: Job Card workflow — advance status
# ---------------------------------------------------------------------------

_WORKFLOW_ORDER = [
    'pending', 'water_wash', 'in_bay', 'in_progress',
    'final_inspection', 'ready', 'invoiced',
]


@login_required
@require_POST
def jobcard_advance_status(request, pk):
    jc = get_object_or_404(JobCard, pk=pk)
    current = jc.service_status
    try:
        idx = _WORKFLOW_ORDER.index(current)
    except ValueError:
        idx = -1
    if idx < 0 or idx >= len(_WORKFLOW_ORDER) - 1:
        messages.warning(request, 'Job card is already at the final step.')
        return redirect('service:jobcard_detail', pk=pk)
    next_status = _WORKFLOW_ORDER[idx + 1]
    jc.service_status = next_status
    jc.save(update_fields=['service_status'])
    log_action(request, 'Job Card', 'update', pk)
    messages.success(request, 'Status advanced to ' + jc.get_service_status_display() + '.')
    return redirect('service:jobcard_detail', pk=pk)


# ---------------------------------------------------------------------------
# GAP 5: Issue Spare from Job Card
# ---------------------------------------------------------------------------

@login_required
def jobcard_issue_spare(request, pk):
    from spares.models import (SparesItem, SparesIssueAlteration,
                               SparesIssueAlterationItem, StockLedger)
    from masters.models import Warehouse, Rack, Bin

    jc = get_object_or_404(JobCard, pk=pk)

    if request.method == 'POST':
        try:
            item_id  = int(request.POST.get('item') or 0)
            quantity = Decimal(request.POST.get('quantity') or '0')
            rack_id  = request.POST.get('rack') or None
            bin_id   = request.POST.get('bin') or None
        except Exception:
            messages.error(request, 'Invalid input.')
            return redirect('service:jobcard_issue_spare', pk=pk)

        if not item_id or quantity <= 0:
            messages.error(request, 'Select an item and a positive quantity.')
            return redirect('service:jobcard_issue_spare', pk=pk)

        item = get_object_or_404(SparesItem, pk=item_id)
        rack = Rack.objects.filter(pk=rack_id).select_related('warehouse').first() if rack_id else None
        if rack:
            warehouse = rack.warehouse
        else:
            warehouse = Warehouse.objects.first()
        if not warehouse:
            messages.error(request, 'No warehouse configured. Add one in Masters.')
            return redirect('service:jobcard_detail', pk=pk)

        jc_label = 'JC-' + str(jc.pk)
        sia, _ = SparesIssueAlteration.objects.get_or_create(
            job_card=jc_label,
            defaults={
                'godown': warehouse,
                'job_type': 'service',
                'date': _dt.date.today(),
                'created_by': request.user,
            },
        )
        item_total = quantity * (item.standard_selling_rate or Decimal('0'))
        SparesIssueAlterationItem.objects.create(
            alteration=sia,
            item=item,
            quantity=quantity,
            rack_id=rack_id or None,
            bin_id=bin_id or None,
            rate=item.standard_selling_rate or Decimal('0'),
            total=item_total,
        )
        sia.spares_total = (sia.spares_total or Decimal('0')) + item_total
        sia.total = (sia.total or Decimal('0')) + item_total
        sia.updated_total = sia.total
        sia.save(update_fields=['spares_total', 'total', 'updated_total'])

        ledger = StockLedger.objects.filter(
            item=item, warehouse=warehouse, rack_id=rack_id or None, bin_id=bin_id or None,
        ).first()
        if ledger:
            ledger.quantity = max(Decimal('0'), (ledger.quantity or Decimal('0')) - quantity)
            ledger.save(update_fields=['quantity'])

        log_action(request, 'Spares Issue', 'create', sia.pk)
        messages.success(request, 'Spare issued to ' + jc_label + '.')
        return redirect('service:jobcard_detail', pk=jc.pk)

    items = SparesItem.objects.filter(is_active=True).order_by('item_name')
    racks = Rack.objects.all()
    bins  = Bin.objects.all()
    return render(request, 'service/jobcard_issue_spare.html', {
        'jc': jc, 'items': items, 'racks': racks, 'bins': bins,
    })


# ---------------------------------------------------------------------------
# GAP 9: Warranty Claims
# ---------------------------------------------------------------------------

@login_required
def warranty_claim_list(request):
    from .models import WarrantyClaim
    qs = WarrantyClaim.objects.select_related(
        'job_card__customer_vehicle__customer'
    ).order_by('-created_at')
    return render(request, 'service/warranty_claim_list.html', {'claims': qs})


@login_required
def warranty_claim_create(request, jc_pk=None):
    from .forms import WarrantyClaimForm
    jc = None
    initial = {}
    if jc_pk:
        jc = get_object_or_404(JobCard, pk=jc_pk)
        initial['job_card'] = jc.pk
    form = WarrantyClaimForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        wc = form.save()
        log_action(request, 'Warranty Claim', 'create', wc.pk)
        messages.success(request, 'Warranty claim ' + wc.claim_number + ' created.')
        if jc:
            return redirect('service:jobcard_detail', pk=jc.pk)
        return redirect('service:warranty_claim_detail', pk=wc.pk)
    return render(request, 'service/warranty_claim_form.html', {
        'form': form, 'jc': jc, 'title': 'New Warranty Claim',
    })


@login_required
def warranty_claim_detail(request, pk):
    from .models import WarrantyClaim
    wc = get_object_or_404(WarrantyClaim.objects.select_related(
        'job_card__customer_vehicle__customer'
    ), pk=pk)
    return render(request, 'service/warranty_claim_detail.html', {'wc': wc})


@login_required
def warranty_claim_update(request, pk):
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    from .forms import WarrantyClaimForm
    from .models import WarrantyClaim
    wc = get_object_or_404(WarrantyClaim, pk=pk)
    if not user_owns(request.user, wc.job_card):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    form = WarrantyClaimForm(request.POST or None, instance=wc)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Warranty Claim', 'update', pk)
        messages.success(request, 'Warranty claim updated.')
        return redirect('service:warranty_claim_detail', pk=pk)
    return render(request, 'service/warranty_claim_form.html', {
        'form': form, 'title': 'Edit Warranty Claim',
    })


# ---------------------------------------------------------------------------
# GAP 10: Insurance Estimation
# ---------------------------------------------------------------------------

@login_required
def insurance_estimation_create(request, jc_pk=None):
    from .forms import InsuranceEstimationForm
    jc = None
    initial = {}
    if jc_pk:
        jc = get_object_or_404(JobCard, pk=jc_pk)
        initial['job_card'] = jc.pk
    form = InsuranceEstimationForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        ie = form.save()
        log_action(request, 'Insurance Estimation', 'create', ie.pk)
        messages.success(request, 'Insurance estimation saved.')
        if jc:
            return redirect('service:jobcard_detail', pk=jc.pk)
        return redirect('service:insurance_estimation_detail', pk=ie.pk)
    return render(request, 'service/insurance_estimation_form.html', {
        'form': form, 'jc': jc, 'title': 'New Insurance Estimation',
    })


@login_required
def insurance_estimation_detail(request, pk):
    from .models import InsuranceEstimation
    ie = get_object_or_404(InsuranceEstimation.objects.select_related(
        'job_card__customer_vehicle__customer'
    ), pk=pk)
    return render(request, 'service/insurance_estimation_detail.html', {'ie': ie})


@login_required
def insurance_estimation_update(request, pk):
    from .forms import InsuranceEstimationForm
    from .models import InsuranceEstimation
    ie = get_object_or_404(InsuranceEstimation, pk=pk)
    form = InsuranceEstimationForm(request.POST or None, instance=ie)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Insurance Estimation', 'update', pk)
        messages.success(request, 'Insurance estimation updated.')
        return redirect('service:insurance_estimation_detail', pk=pk)
    return render(request, 'service/insurance_estimation_form.html', {
        'form': form, 'title': 'Edit Insurance Estimation',
    })


# ---------------------------------------------------------------------------
# GAP 11: Service Discount Master
# ---------------------------------------------------------------------------

@login_required
def discount_master_list(request):
    from .models import ServiceDiscountMaster
    qs = ServiceDiscountMaster.objects.all().order_by('service_type')
    return render(request, 'service/discount_master_list.html', {'rows': qs})


@login_required
def discount_master_create(request, pk=None):
    from .forms import ServiceDiscountMasterForm
    from .models import ServiceDiscountMaster
    instance = get_object_or_404(ServiceDiscountMaster, pk=pk) if pk else None
    form = ServiceDiscountMasterForm(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        log_action(request, 'Service Discount Master',
                   'update' if instance else 'create', obj.pk)
        messages.success(request, 'Service discount saved.')
        return redirect('service:discount_master_list')
    return render(request, 'service/discount_master_form.html', {
        'form': form, 'title': 'Service Discount',
    })
