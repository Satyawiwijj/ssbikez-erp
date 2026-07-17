from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.audit import log_action
from accounts.permissions import require_module_action

from .forms import (PARTS_CHECK_FORMSET_MAP, UsedVehicleAdvancePaymentFormSet, UsedVehicleBayInForm,
                    UsedVehicleInsuranceUpdateForm,
                    UsedVehicleBayOutForm, UsedVehicleChasisDetailRowFormSet,
                    UsedVehicleComplaintDetailFormSet, UsedVehicleDeliveryForm,
                    UsedVehicleEngineDetailRowFormSet,
                    UsedVehicleFinalInspectionForm, UsedVehicleFinanceLoanForm,
                    UsedVehicleFittingFormSet, UsedVehicleInvoiceForm,
                    UsedVehicleInvoiceItemFormSet, UsedVehicleJobCardForm,
                    UsedVehicleLaborChargeForm, UsedVehicleLaborDetailLineFormSet,
                    UsedVehicleLaborSpareItemFormSet, UsedVehicleLightDetailFormSet,
                    UsedVehicleModelForm, UsedVehicleOthersDetailFormSet,
                    UsedVehicleOutworkEntryIssueForm, UsedVehicleOutworkEntryReturnForm,
                    UsedVehicleOutworkReturnDetailFormSet, UsedVehicleOutworkSpareItemFormSet,
                    UsedVehicleOutworkWorkDetailFormSet, UsedVehiclePurchaseInvoiceForm,
                    UsedVehiclePurchaseItemFormSet, UsedVehicleRCHandOverForm,
                    UsedVehicleRegisterNoForm, UsedVehicleSaleForm,
                    UsedVehicleSaleItemFormSet, UsedVehicleServiceInvoiceForm,
                    UsedVehicleSupervisorObservationFormSet, UsedVechileRCBookIssueForm,
                    UsedVehicleMasterSettingsForm, UsedVehicleMasterSettingsItemFormSet,
                    UsedVehicleSalesSettingForm, UsedVehicleSalesSettingItemFormSet,
                    UsedVehicleDeliveryItemFormSet, UsedVehicleDeliveryAdvancePaymentFormSet,
                    UsedVehicleLaborChargeRemoveItemFormSet,
                    UsedVehicleFinalInspectionComplaintDetailFormSet,
                    UsedVehicleFinalInspectionSupervisorObservationFormSet,
                    UsedVehicleFinalInspectionLaborChargeFormSet,
                    UsedVehicleFinalInspectionSpareItemFormSet,
                    UsedVehiclePurchaseOrderForm, UsedVehiclePurchaseOrderItemFormSet,
                    UsedVehiclePurchaseReceiptForm, UsedVehiclePurchaseReceiptItemFormSet)
from .models import (UsedVehicleBayIn, UsedVehicleBayOut, UsedVehicleDelivery,
                     UsedVehicleFinalInspection, UsedVehicleFinanceLoan, UsedVehicleInvoice,
                     UsedVehicleJobCard, UsedVehicleLaborCharge, UsedVehicleModel,
                     UsedVehicleOutworkEntryIssue, UsedVehicleOutworkEntryReturn,
                     UsedVehiclePurchaseInvoice, UsedVehicleRCHandOver,
                     UsedVehicleRegisterNo, UsedVehicleSale, UsedVehicleServiceInvoice,
                     UsedVechileRCBookIssue, UsedVehicleMasterSettings, UsedVehicleSalesSetting,
                     UsedVehicleInsuranceUpdate,
                     UsedVehiclePurchaseOrder, UsedVehiclePurchaseReceipt,
                     UsedVehiclePurchaseReceiptItem)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    return render(request, 'used_vehicles/dashboard.html', {
        'total_models': UsedVehicleModel.objects.count(),
        'total_stock':  UsedVehicleRegisterNo.objects.filter(stock_status='available').count(),
        'total_sales':  UsedVehicleSale.objects.count(),
    })


# ---------------------------------------------------------------------------
# Masters
# ---------------------------------------------------------------------------

@login_required
def model_list(request):
    qs = UsedVehicleModel.objects.select_related('manufacturer', 'sub_group').all()
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'used_vehicles/model_list.html', {
        'models': page_obj, 'page_obj': page_obj,
    })


@login_required
@require_module_action('used_vehicles', 'create')
def model_create(request):
    form = UsedVehicleModelForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        log_action(request, 'Used Vehicle Model', 'create', obj.pk)
        messages.success(request, 'Used vehicle model created.')
        return redirect('used_vehicles:model_list')
    return render(request, 'used_vehicles/model_form.html', {'form': form, 'title': 'Add Used Vehicle Model'})


@login_required
def register_no_list(request):
    qs = UsedVehicleRegisterNo.objects.select_related('used_vehicle', 'color').all()
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'used_vehicles/register_no_list.html', {
        'stock': page_obj, 'page_obj': page_obj,
    })


@login_required
@require_module_action('used_vehicles', 'create')
def register_no_create(request):
    form = UsedVehicleRegisterNoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        log_action(request, 'Used Vehicle Register No', 'create', obj.pk)
        messages.success(request, 'Register number added.')
        return redirect('used_vehicles:register_no_list')
    return render(request, 'used_vehicles/register_no_form.html', {'form': form, 'title': 'Add Used Vehicle Register No'})


# ---------------------------------------------------------------------------
# Purchase Invoice
# ---------------------------------------------------------------------------

@login_required
def purchase_list(request):
    qs = UsedVehiclePurchaseInvoice.objects.select_related('supplier', 'branch').all()
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'used_vehicles/purchase_list.html', {
        'purchases': page_obj, 'page_obj': page_obj,
    })


@login_required
@require_module_action('used_vehicles', 'create')
def purchase_create(request):
    initial = {}
    if request.GET.get('purchase_receipt'):
        initial['purchase_receipt'] = request.GET['purchase_receipt']
    form = UsedVehiclePurchaseInvoiceForm(request.POST or None, initial=initial)
    formset = UsedVehiclePurchaseItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST':
        if form.is_valid() and formset.is_valid():
            obj = form.save()
            formset.instance = obj
            formset.save()
            log_action(request, 'Used Vehicle Purchase Invoice', 'create', obj.pk)
            messages.success(request, f'{obj} created.')
            return redirect('used_vehicles:purchase_detail', pk=obj.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'used_vehicles/purchase_form.html', {
        'form': form, 'formset': formset, 'title': 'Create Used Vehicle Purchase Invoice',
    })


@login_required
def purchase_detail(request, pk):
    obj = get_object_or_404(UsedVehiclePurchaseInvoice, pk=pk)
    return render(request, 'used_vehicles/purchase_detail.html', {'obj': obj})


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def purchase_submit(request, pk):
    obj = get_object_or_404(UsedVehiclePurchaseInvoice, pk=pk)
    try:
        obj.submit(request.user)
        log_action(request, 'Used Vehicle Purchase Invoice', 'update', pk)
        messages.success(request, f'{obj} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:purchase_detail', pk=pk)


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def purchase_cancel(request, pk):
    obj = get_object_or_404(UsedVehiclePurchaseInvoice, pk=pk)
    try:
        obj.cancel(request.user)
        log_action(request, 'Used Vehicle Purchase Invoice', 'update', pk)
        messages.success(request, f'{obj} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:purchase_detail', pk=pk)


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def purchase_amend(request, pk):
    obj = get_object_or_404(UsedVehiclePurchaseInvoice, pk=pk)
    try:
        new_obj = obj.amend()
        for item in obj.items.all():
            item.pk = None
            item.invoice = new_obj
            item.save()
        log_action(request, 'Used Vehicle Purchase Invoice', 'create', new_obj.pk)
        messages.success(request, f'Amended as {new_obj}.')
        return redirect('used_vehicles:purchase_detail', pk=new_obj.pk)
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:purchase_detail', pk=pk)


# ---------------------------------------------------------------------------
# Phase 10 — Purchase Order -> Purchase Receipt
# ---------------------------------------------------------------------------

@login_required
def purchase_order_list(request):
    qs = UsedVehiclePurchaseOrder.objects.select_related('supplier', 'branch').all()
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'used_vehicles/purchase_order_list.html', {
        'orders': page_obj, 'page_obj': page_obj,
    })


@login_required
@require_module_action('used_vehicles', 'create')
def purchase_order_create(request):
    form = UsedVehiclePurchaseOrderForm(request.POST or None)
    formset = UsedVehiclePurchaseOrderItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST':
        if form.is_valid() and formset.is_valid():
            obj = form.save()
            formset.instance = obj
            formset.save()
            log_action(request, 'Used Vehicle Purchase Order', 'create', obj.pk)
            messages.success(request, f'{obj} created.')
            return redirect('used_vehicles:purchase_order_detail', pk=obj.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'used_vehicles/purchase_order_form.html', {
        'form': form, 'formset': formset, 'title': 'Create Used Vehicle Purchase Order',
    })


@login_required
def purchase_order_detail(request, pk):
    obj = get_object_or_404(UsedVehiclePurchaseOrder, pk=pk)
    return render(request, 'used_vehicles/purchase_order_detail.html', {
        'obj': obj, 'items': obj.purchase_items.all(), 'receipts': obj.receipts.all(),
    })


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def purchase_order_submit(request, pk):
    obj = get_object_or_404(UsedVehiclePurchaseOrder, pk=pk)
    try:
        obj.submit(request.user)
        log_action(request, 'Used Vehicle Purchase Order', 'update', pk)
        messages.success(request, f'{obj} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:purchase_order_detail', pk=pk)


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def purchase_order_cancel(request, pk):
    obj = get_object_or_404(UsedVehiclePurchaseOrder, pk=pk)
    try:
        obj.cancel(request.user)
        log_action(request, 'Used Vehicle Purchase Order', 'update', pk)
        messages.success(request, f'{obj} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:purchase_order_detail', pk=pk)


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def purchase_order_amend(request, pk):
    obj = get_object_or_404(UsedVehiclePurchaseOrder, pk=pk)
    try:
        new_obj = obj.amend()
        for item in obj.purchase_items.all():
            item.pk = None
            item.order = new_obj
            item.save()
        log_action(request, 'Used Vehicle Purchase Order', 'create', new_obj.pk)
        messages.success(request, f'Amended as {new_obj}.')
        return redirect('used_vehicles:purchase_order_detail', pk=new_obj.pk)
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:purchase_order_detail', pk=pk)


@login_required
def purchase_receipt_list(request):
    qs = UsedVehiclePurchaseReceipt.objects.select_related('purchase_order', 'supplier').all()
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'used_vehicles/purchase_receipt_list.html', {
        'receipts': page_obj, 'page_obj': page_obj,
    })


@login_required
@require_module_action('used_vehicles', 'create')
def purchase_receipt_create(request):
    initial = {}
    if request.GET.get('purchase_order'):
        po = get_object_or_404(UsedVehiclePurchaseOrder, pk=request.GET['purchase_order'])
        initial['purchase_order'] = po.pk
        initial['supplier'] = po.supplier_id
    form = UsedVehiclePurchaseReceiptForm(request.POST or None, initial=initial)
    formset = UsedVehiclePurchaseReceiptItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST':
        if form.is_valid() and formset.is_valid():
            # Phase-11 -- reject an over-receipt: this receipt's item quantities
            # (plus anything already received against the same PO) must not exceed
            # what the linked Purchase Order actually ordered.
            po = form.cleaned_data.get('purchase_order')
            over_receipt_error = None
            if po:
                ordered_qty = po.purchase_items.aggregate(t=Sum('quantity'))['t'] or Decimal('0')
                already_received = UsedVehiclePurchaseReceiptItem.objects.filter(
                    receipt__purchase_order=po
                ).exclude(
                    receipt__docstatus=UsedVehiclePurchaseReceipt.DocStatus.CANCELLED
                ).aggregate(t=Sum('quantity'))['t'] or Decimal('0')
                new_qty = sum(
                    (f.cleaned_data.get('quantity') or Decimal('0'))
                    for f in formset.forms
                    if f.cleaned_data and not f.cleaned_data.get('DELETE')
                )
                total_received = already_received + new_qty
                if total_received > ordered_qty:
                    over_receipt_error = (
                        f"Received quantity ({total_received}) would exceed {po}'s ordered "
                        f"quantity ({ordered_qty})."
                    )
            if over_receipt_error:
                messages.error(request, over_receipt_error)
            else:
                obj = form.save()
                formset.instance = obj
                formset.save()
                log_action(request, 'Used Vehicle Purchase Receipt', 'create', obj.pk)
                messages.success(request, f'{obj} created.')
                return redirect('used_vehicles:purchase_receipt_detail', pk=obj.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    return render(request, 'used_vehicles/purchase_receipt_form.html', {
        'form': form, 'formset': formset, 'title': 'Create Used Vehicle Purchase Receipt',
    })


@login_required
def purchase_receipt_detail(request, pk):
    obj = get_object_or_404(UsedVehiclePurchaseReceipt, pk=pk)
    return render(request, 'used_vehicles/purchase_receipt_detail.html', {
        'obj': obj, 'items': obj.purchase_items.all(), 'invoices': obj.invoices.all(),
    })


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def purchase_receipt_submit(request, pk):
    obj = get_object_or_404(UsedVehiclePurchaseReceipt, pk=pk)
    try:
        obj.submit(request.user)
        log_action(request, 'Used Vehicle Purchase Receipt', 'update', pk)
        messages.success(request, f'{obj} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:purchase_receipt_detail', pk=pk)


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def purchase_receipt_cancel(request, pk):
    obj = get_object_or_404(UsedVehiclePurchaseReceipt, pk=pk)
    try:
        obj.cancel(request.user)
        log_action(request, 'Used Vehicle Purchase Receipt', 'update', pk)
        messages.success(request, f'{obj} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:purchase_receipt_detail', pk=pk)


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def purchase_receipt_amend(request, pk):
    obj = get_object_or_404(UsedVehiclePurchaseReceipt, pk=pk)
    try:
        new_obj = obj.amend()
        for item in obj.purchase_items.all():
            item.pk = None
            item.receipt = new_obj
            item.save()
        log_action(request, 'Used Vehicle Purchase Receipt', 'create', new_obj.pk)
        messages.success(request, f'Amended as {new_obj}.')
        return redirect('used_vehicles:purchase_receipt_detail', pk=new_obj.pk)
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:purchase_receipt_detail', pk=pk)


# ---------------------------------------------------------------------------
# Sale
# ---------------------------------------------------------------------------

@login_required
def sale_list(request):
    qs = UsedVehicleSale.objects.select_related('customer', 'vehicle_number').all()
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'used_vehicles/sale_list.html', {
        'sales': page_obj, 'page_obj': page_obj,
    })


@login_required
@require_module_action('used_vehicles', 'create')
def sale_create(request):
    from accounts.permissions import user_is_manager
    is_manager = user_is_manager(request.user)
    form = UsedVehicleSaleForm(request.POST or None)
    if not is_manager:
        form.fields.pop('sales_executive', None)
    fittings_formset = UsedVehicleFittingFormSet(request.POST or None, prefix='fittings')
    items_formset = UsedVehicleSaleItemFormSet(request.POST or None, prefix='items')
    advance_formset = UsedVehicleAdvancePaymentFormSet(request.POST or None, prefix='advance')
    if request.method == 'POST':
        if (form.is_valid() and fittings_formset.is_valid()
                and items_formset.is_valid() and advance_formset.is_valid()):
            obj = form.save(commit=False)
            if not is_manager:
                obj.sales_executive = request.user
            obj.save()
            fittings_formset.instance = obj
            fittings_formset.save()
            items_formset.instance = obj
            items_formset.save()
            advance_formset.instance = obj
            advance_formset.save()
            log_action(request, 'Used Vehicle Sale', 'create', obj.pk)
            if obj.vehicle_number.stock_status != UsedVehicleRegisterNo.StockStatus.AVAILABLE:
                messages.warning(
                    request,
                    f"Warning: {obj.vehicle_number.registration_no} is currently "
                    f"'{obj.vehicle_number.get_stock_status_display()}', not Available -- "
                    f"this Draft sale will be blocked from submitting until that changes."
                )
            messages.success(request, f'{obj} created.')
            return redirect('used_vehicles:sale_detail', pk=obj.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'used_vehicles/sale_form.html', {
        'form': form, 'fittings_formset': fittings_formset, 'items_formset': items_formset,
        'advance_formset': advance_formset, 'title': 'Create Used Vehicle Sale',
    })


@login_required
def sale_detail(request, pk):
    obj = get_object_or_404(UsedVehicleSale, pk=pk)
    return render(request, 'used_vehicles/sale_detail.html', {'obj': obj})


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def sale_submit(request, pk):
    from accounts.permissions import user_owns
    obj = get_object_or_404(UsedVehicleSale, pk=pk)
    if not user_owns(request.user, obj):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        obj.submit(request.user)
        log_action(request, 'Used Vehicle Sale', 'update', pk)
        messages.success(request, f'{obj} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:sale_detail', pk=pk)


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def sale_cancel(request, pk):
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    obj = get_object_or_404(UsedVehicleSale, pk=pk)
    if not user_owns(request.user, obj):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        obj.cancel(request.user)
        log_action(request, 'Used Vehicle Sale', 'update', pk)
        messages.success(request, f'{obj} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:sale_detail', pk=pk)


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def sale_amend(request, pk):
    from accounts.permissions import user_owns
    obj = get_object_or_404(UsedVehicleSale, pk=pk)
    if not user_owns(request.user, obj):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        new_obj = obj.amend()
        for fitting in obj.fittings.all():
            fitting.pk = None
            fitting.sale = new_obj
            fitting.save()
        for item in obj.items.all():
            item.pk = None
            item.sale = new_obj
            item.save()
        for adv in obj.advance_payments.all():
            adv.pk = None
            adv.sale = new_obj
            adv.save()
        log_action(request, 'Used Vehicle Sale', 'create', new_obj.pk)
        messages.success(request, f'Amended as {new_obj}.')
        return redirect('used_vehicles:sale_detail', pk=new_obj.pk)
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:sale_detail', pk=pk)


# ---------------------------------------------------------------------------
# Finance Loan
# ---------------------------------------------------------------------------

@login_required
@require_module_action('used_vehicles', 'create')
def loan_create(request):
    initial = {}
    if request.GET.get('sale'):
        initial['sale'] = request.GET['sale']
    form = UsedVehicleFinanceLoanForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        log_action(request, 'Used Vehicle Finance Loan', 'create', obj.pk)
        messages.success(request, 'Finance loan recorded.')
        return redirect('used_vehicles:sale_detail', pk=obj.sale_id)
    return render(request, 'used_vehicles/loan_form.html', {'form': form, 'title': 'Add Finance Loan'})


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------

@login_required
@require_module_action('used_vehicles', 'create')
def delivery_create(request):
    initial = {}
    if request.GET.get('sale'):
        initial['sale'] = request.GET['sale']
    form = UsedVehicleDeliveryForm(request.POST or None, initial=initial)
    items_formset = UsedVehicleDeliveryItemFormSet(request.POST or None, prefix='items')
    advance_formset = UsedVehicleDeliveryAdvancePaymentFormSet(request.POST or None, prefix='advance')
    if request.method == 'POST':
        if form.is_valid() and items_formset.is_valid() and advance_formset.is_valid():
            obj = form.save()
            items_formset.instance = obj
            items_formset.save()
            advance_formset.instance = obj
            advance_formset.save()
            log_action(request, 'Used Vehicle Delivery', 'create', obj.pk)
            messages.success(request, 'Delivery recorded.')
            return redirect('used_vehicles:delivery_detail', pk=obj.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'used_vehicles/delivery_form.html', {
        'form': form, 'items_formset': items_formset, 'advance_formset': advance_formset,
        'title': 'Record Used Vehicle Delivery',
    })


@login_required
def delivery_detail(request, pk):
    obj = get_object_or_404(UsedVehicleDelivery, pk=pk)
    return render(request, 'used_vehicles/delivery_detail.html', {
        'obj': obj, 'items': obj.delivery_items.all(), 'advance_payments': obj.advance_payments.all(),
    })


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def delivery_submit(request, pk):
    obj = get_object_or_404(UsedVehicleDelivery, pk=pk)
    try:
        obj.submit(request.user)
        log_action(request, 'Used Vehicle Delivery', 'update', pk)
        messages.success(request, 'Delivery submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:delivery_detail', pk=pk)


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def delivery_cancel(request, pk):
    obj = get_object_or_404(UsedVehicleDelivery, pk=pk)
    try:
        obj.cancel(request.user)
        log_action(request, 'Used Vehicle Delivery', 'update', pk)
        messages.success(request, 'Delivery cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:delivery_detail', pk=pk)


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------

@login_required
@require_module_action('used_vehicles', 'create')
def invoice_create(request):
    initial = {}
    if request.GET.get('sale'):
        initial['sale'] = request.GET['sale']
    form = UsedVehicleInvoiceForm(request.POST or None, initial=initial)
    formset = UsedVehicleInvoiceItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST':
        if form.is_valid() and formset.is_valid():
            obj = form.save()
            formset.instance = obj
            formset.save()
            log_action(request, 'Used Vehicle Invoice', 'create', obj.pk)
            messages.success(request, f'{obj} created.')
            return redirect('used_vehicles:invoice_detail', pk=obj.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'used_vehicles/invoice_form.html', {
        'form': form, 'formset': formset, 'title': 'Create Used Vehicle Invoice',
    })


@login_required
def invoice_detail(request, pk):
    obj = get_object_or_404(UsedVehicleInvoice, pk=pk)
    return render(request, 'used_vehicles/invoice_detail.html', {'obj': obj})


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def invoice_submit(request, pk):
    obj = get_object_or_404(UsedVehicleInvoice, pk=pk)
    if obj.md_approval_requested and not obj.md_approved:
        messages.error(request, 'MD approval is required before submitting this invoice.')
        return redirect('used_vehicles:invoice_detail', pk=pk)
    try:
        obj.submit(request.user)
        log_action(request, 'Used Vehicle Invoice', 'update', pk)
        messages.success(request, f'{obj} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:invoice_detail', pk=pk)


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def invoice_cancel(request, pk):
    obj = get_object_or_404(UsedVehicleInvoice, pk=pk)
    try:
        obj.cancel(request.user)
        log_action(request, 'Used Vehicle Invoice', 'update', pk)
        messages.success(request, f'{obj} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:invoice_detail', pk=pk)


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def invoice_md_approve(request, pk):
    from django.utils import timezone
    obj = get_object_or_404(UsedVehicleInvoice, pk=pk)
    obj.md_approved = True
    obj.md_approved_by = request.user
    obj.md_approved_at = timezone.now()
    obj.save(update_fields=['md_approved', 'md_approved_by', 'md_approved_at'])
    log_action(request, 'Used Vehicle Invoice', 'update', pk)
    messages.success(request, 'Approved as MD.')
    return redirect('used_vehicles:invoice_detail', pk=pk)


# ---------------------------------------------------------------------------
# RC Hand Over / RC Book Issue
# Phase 13 — restructured onto DocStatusMixin (Draft/Submitted/Cancelled +
# amend), matching the reference's is_submittable=1 on both. Follows the
# same list/detail/submit/cancel/amend view shape as purchase_order_* above
# and sales.dealer_rc_handover_* / rto.rc_book_issue_* (closest same-shaped
# sibling docs elsewhere in this codebase). Created docs now land as Draft
# and the create-flow redirects to the doc's own detail page (where Submit
# lives) instead of straight back to sale_detail -- previously `status` was
# the only state and could be set to its terminal value directly on create;
# now that a real docstatus lifecycle exists, "handed over" / "issued" is
# finalized via Submit, matching every sibling Submittable doc in this file.
# ---------------------------------------------------------------------------

@login_required
def rc_handover_list(request):
    qs = UsedVehicleRCHandOver.objects.select_related('sale').all()
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'used_vehicles/rc_handover_list.html', {
        'handovers': page_obj, 'page_obj': page_obj,
    })


@login_required
@require_module_action('used_vehicles', 'create')
def rc_handover_create(request):
    initial = {}
    if request.GET.get('sale'):
        initial['sale'] = request.GET['sale']
    form = UsedVehicleRCHandOverForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        log_action(request, 'Used Vehicle RC Hand Over', 'create', obj.pk)
        messages.success(request, 'RC Hand Over recorded.')
        return redirect('used_vehicles:rc_handover_detail', pk=obj.pk)
    return render(request, 'used_vehicles/rc_handover_form.html', {'form': form, 'title': 'RC Hand Over'})


@login_required
def rc_handover_detail(request, pk):
    obj = get_object_or_404(UsedVehicleRCHandOver, pk=pk)
    return render(request, 'used_vehicles/rc_handover_detail.html', {'obj': obj})


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def rc_handover_submit(request, pk):
    obj = get_object_or_404(UsedVehicleRCHandOver, pk=pk)
    try:
        obj.submit(request.user)
        log_action(request, 'Used Vehicle RC Hand Over', 'update', pk)
        messages.success(request, f'{obj} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:rc_handover_detail', pk=pk)


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def rc_handover_cancel(request, pk):
    obj = get_object_or_404(UsedVehicleRCHandOver, pk=pk)
    try:
        obj.cancel(request.user)
        log_action(request, 'Used Vehicle RC Hand Over', 'update', pk)
        messages.success(request, f'{obj} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:rc_handover_detail', pk=pk)


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def rc_handover_amend(request, pk):
    obj = get_object_or_404(UsedVehicleRCHandOver, pk=pk)
    try:
        new_obj = obj.amend()
        log_action(request, 'Used Vehicle RC Hand Over', 'create', new_obj.pk)
        messages.success(request, f'Amended as {new_obj}.')
        return redirect('used_vehicles:rc_handover_detail', pk=new_obj.pk)
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:rc_handover_detail', pk=pk)


@login_required
def rc_book_issue_list(request):
    qs = UsedVechileRCBookIssue.objects.select_related('sale').all()
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'used_vehicles/rc_book_issue_list.html', {
        'issues': page_obj, 'page_obj': page_obj,
    })


@login_required
@require_module_action('used_vehicles', 'create')
def rc_book_issue_create(request):
    initial = {}
    if request.GET.get('sale'):
        initial['sale'] = request.GET['sale']
    form = UsedVechileRCBookIssueForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        log_action(request, 'Used Vehicle RC Book Issue', 'create', obj.pk)
        messages.success(request, 'RC Book Issue recorded.')
        return redirect('used_vehicles:rc_book_issue_detail', pk=obj.pk)
    return render(request, 'used_vehicles/rc_book_issue_form.html', {'form': form, 'title': 'RC Book Issue'})


@login_required
def rc_book_issue_detail(request, pk):
    obj = get_object_or_404(UsedVechileRCBookIssue, pk=pk)
    return render(request, 'used_vehicles/rc_book_issue_detail.html', {'obj': obj})


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def rc_book_issue_submit(request, pk):
    obj = get_object_or_404(UsedVechileRCBookIssue, pk=pk)
    try:
        obj.submit(request.user)
        log_action(request, 'Used Vehicle RC Book Issue', 'update', pk)
        messages.success(request, f'{obj} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:rc_book_issue_detail', pk=pk)


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def rc_book_issue_cancel(request, pk):
    obj = get_object_or_404(UsedVechileRCBookIssue, pk=pk)
    try:
        obj.cancel(request.user)
        log_action(request, 'Used Vehicle RC Book Issue', 'update', pk)
        messages.success(request, f'{obj} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:rc_book_issue_detail', pk=pk)


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def rc_book_issue_amend(request, pk):
    obj = get_object_or_404(UsedVechileRCBookIssue, pk=pk)
    try:
        new_obj = obj.amend()
        log_action(request, 'Used Vehicle RC Book Issue', 'create', new_obj.pk)
        messages.success(request, f'Amended as {new_obj}.')
        return redirect('used_vehicles:rc_book_issue_detail', pk=new_obj.pk)
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:rc_book_issue_detail', pk=pk)


# ---------------------------------------------------------------------------
# Phase 3b — Used Vehicle Job Card service pipeline
# ---------------------------------------------------------------------------

def _uv_stage_submit(request, model, pk, list_name):
    from accounts.permissions import user_owns
    obj = get_object_or_404(model, pk=pk)
    if not user_owns(request.user, obj.job_card):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        obj.submit(request.user)
        log_action(request, model.__name__, 'update', pk)
        messages.success(request, f'{obj} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect(f'used_vehicles:{list_name}_detail', pk=pk)


def _uv_stage_cancel(request, model, pk, list_name):
    from accounts.permissions import user_owns
    obj = get_object_or_404(model, pk=pk)
    if not user_owns(request.user, obj.job_card):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        obj.cancel(request.user)
        log_action(request, model.__name__, 'update', pk)
        messages.success(request, f'{obj} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect(f'used_vehicles:{list_name}_detail', pk=pk)


@login_required
def jobcard_list(request):
    qs = UsedVehicleJobCard.objects.select_related('register_no').all()
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'used_vehicles/jobcard_list.html', {
        'jobcards': page_obj, 'page_obj': page_obj,
    })


def _used_vehicle_jobcard_checklist_formsets(request, instance=None):
    post = request.POST or None
    formsets = {
        'complaint_formset':   UsedVehicleComplaintDetailFormSet(post, instance=instance, prefix='complaints'),
        'observation_formset': UsedVehicleSupervisorObservationFormSet(post, instance=instance, prefix='observations'),
        'engine_formset':      UsedVehicleEngineDetailRowFormSet(post, instance=instance, prefix='engine'),
        'light_formset':       UsedVehicleLightDetailFormSet(post, instance=instance, prefix='lights'),
        'chasis_formset':      UsedVehicleChasisDetailRowFormSet(post, instance=instance, prefix='chasis'),
        'others_formset':      UsedVehicleOthersDetailFormSet(post, instance=instance, prefix='others'),
    }
    parts_formsets = {
        category: formset_cls(post, instance=instance, prefix=f'parts_{category}')
        for category, formset_cls in PARTS_CHECK_FORMSET_MAP.items()
    }
    return formsets, parts_formsets


def _parts_formset_items(parts_formsets):
    """List of (category, human label, formset) for template rendering --
    avoids relying on an unbound formset row's instance data for the label."""
    from .models import UsedVehiclePartsCheckItem
    labels = dict(UsedVehiclePartsCheckItem.Category.choices)
    return [(category, labels[category], fs) for category, fs in parts_formsets.items()]


@login_required
@require_module_action('used_vehicles', 'create')
def jobcard_create(request):
    from accounts.permissions import user_is_manager
    is_manager = user_is_manager(request.user)
    form = UsedVehicleJobCardForm(request.POST or None)
    if not is_manager:
        form.fields.pop('service_advisor', None)
    formsets, parts_formsets = _used_vehicle_jobcard_checklist_formsets(request)
    if request.method == 'POST':
        all_valid = (form.is_valid()
                     and all(fs.is_valid() for fs in formsets.values())
                     and all(fs.is_valid() for fs in parts_formsets.values()))
        if all_valid:
            obj = form.save(commit=False)
            if not is_manager:
                obj.service_advisor = request.user
            obj.save()
            for fs in formsets.values():
                fs.instance = obj
                fs.save()
            for fs in parts_formsets.values():
                fs.instance = obj
                fs.save()
            log_action(request, 'Used Vehicle Job Card', 'create', obj.pk)
            messages.success(request, f'{obj} created.')
            return redirect('used_vehicles:jobcard_detail', pk=obj.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'used_vehicles/jobcard_form.html', {
        'form': form, 'title': 'Create Used Vehicle Job Card',
        'parts_formset_items': _parts_formset_items(parts_formsets), **formsets,
    })


@login_required
@require_module_action('used_vehicles', 'edit')
def jobcard_update(request, pk):
    from accounts.permissions import user_is_manager, user_owns
    obj = get_object_or_404(UsedVehicleJobCard, pk=pk)
    if not user_owns(request.user, obj):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    is_manager = user_is_manager(request.user)
    form = UsedVehicleJobCardForm(request.POST or None, instance=obj)
    if not is_manager:
        form.fields.pop('service_advisor', None)
        form.fields.pop('service_status', None)
    formsets, parts_formsets = _used_vehicle_jobcard_checklist_formsets(request, instance=obj)
    if request.method == 'POST':
        all_valid = (form.is_valid()
                     and all(fs.is_valid() for fs in formsets.values())
                     and all(fs.is_valid() for fs in parts_formsets.values()))
        if all_valid:
            form.save()
            for fs in formsets.values():
                fs.save()
            for fs in parts_formsets.values():
                fs.save()
            log_action(request, 'Used Vehicle Job Card', 'update', pk)
            messages.success(request, f'{obj} updated.')
            return redirect('used_vehicles:jobcard_detail', pk=obj.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'used_vehicles/jobcard_form.html', {
        'form': form, 'title': 'Edit Used Vehicle Job Card',
        'parts_formset_items': _parts_formset_items(parts_formsets), **formsets,
    })


@login_required
def jobcard_detail(request, pk):
    from .models import UsedVehiclePartsCheckItem
    obj = get_object_or_404(UsedVehicleJobCard, pk=pk)
    labels = dict(UsedVehiclePartsCheckItem.Category.choices)
    parts_by_category = [
        (category, labels[category], obj.parts_check_items.filter(category=category))
        for category in PARTS_CHECK_FORMSET_MAP.keys()
    ]
    return render(request, 'used_vehicles/jobcard_detail.html', {
        'obj': obj,
        'complaint_details':       obj.complaint_details.select_related('customer_complaint').all(),
        'supervisor_observations': obj.supervisor_observations.select_related('complaint').all(),
        'engine_details':          obj.engine_details.all(),
        'light_details':           obj.light_details.all(),
        'chasis_details':          obj.chasis_details.all(),
        'others_details':          obj.others_details.all(),
        'parts_by_category':       parts_by_category,
    })


# ---- Bay In ----

@login_required
@require_module_action('used_vehicles', 'create')
def uv_bay_in_create(request):
    initial = {}
    if request.GET.get('jc'):
        initial['job_card'] = request.GET['jc']
    form = UsedVehicleBayInForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        log_action(request, 'Used Vehicle Bay In', 'create', obj.pk)
        messages.success(request, 'Bay In recorded.')
        return redirect('used_vehicles:uv_bay_in_detail', pk=obj.pk)
    return render(request, 'used_vehicles/uv_bay_in_form.html', {'form': form, 'title': 'Used Vehicle Bay In'})


@login_required
def uv_bay_in_detail(request, pk):
    obj = get_object_or_404(UsedVehicleBayIn, pk=pk)
    return render(request, 'used_vehicles/uv_bay_in_detail.html', {'obj': obj})


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def uv_bay_in_submit(request, pk):
    return _uv_stage_submit(request, UsedVehicleBayIn, pk, 'uv_bay_in')


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def uv_bay_in_cancel(request, pk):
    return _uv_stage_cancel(request, UsedVehicleBayIn, pk, 'uv_bay_in')


# ---- Bay Out ----

@login_required
@require_module_action('used_vehicles', 'create')
def uv_bay_out_create(request):
    initial = {}
    if request.GET.get('jc'):
        initial['job_card'] = request.GET['jc']
    form = UsedVehicleBayOutForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        log_action(request, 'Used Vehicle Bay Out', 'create', obj.pk)
        messages.success(request, 'Bay Out recorded.')
        return redirect('used_vehicles:uv_bay_out_detail', pk=obj.pk)
    return render(request, 'used_vehicles/uv_bay_out_form.html', {'form': form, 'title': 'Used Vehicle Bay Out'})


@login_required
def uv_bay_out_detail(request, pk):
    obj = get_object_or_404(UsedVehicleBayOut, pk=pk)
    return render(request, 'used_vehicles/uv_bay_out_detail.html', {'obj': obj})


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def uv_bay_out_submit(request, pk):
    return _uv_stage_submit(request, UsedVehicleBayOut, pk, 'uv_bay_out')


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def uv_bay_out_cancel(request, pk):
    return _uv_stage_cancel(request, UsedVehicleBayOut, pk, 'uv_bay_out')


# ---- Final Inspection ----

@login_required
@require_module_action('used_vehicles', 'create')
def uv_final_inspection_create(request):
    initial = {}
    if request.GET.get('jc'):
        initial['job_card'] = request.GET['jc']
    form = UsedVehicleFinalInspectionForm(request.POST or None, initial=initial)
    complaint_formset = UsedVehicleFinalInspectionComplaintDetailFormSet(request.POST or None, prefix='complaints')
    observation_formset = UsedVehicleFinalInspectionSupervisorObservationFormSet(request.POST or None, prefix='observations')
    labor_formset = UsedVehicleFinalInspectionLaborChargeFormSet(request.POST or None, prefix='labor')
    spares_formset = UsedVehicleFinalInspectionSpareItemFormSet(request.POST or None, prefix='spares')
    if request.method == 'POST':
        if (form.is_valid() and complaint_formset.is_valid() and observation_formset.is_valid()
                and labor_formset.is_valid() and spares_formset.is_valid()):
            obj = form.save()
            complaint_formset.instance = obj
            complaint_formset.save()
            observation_formset.instance = obj
            observation_formset.save()
            labor_formset.instance = obj
            labor_formset.save()
            spares_formset.instance = obj
            spares_formset.save()
            log_action(request, 'Used Vehicle Final Inspection', 'create', obj.pk)
            messages.success(request, 'Final Inspection recorded.')
            return redirect('used_vehicles:uv_final_inspection_detail', pk=obj.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'used_vehicles/uv_final_inspection_form.html', {
        'form': form, 'complaint_formset': complaint_formset, 'observation_formset': observation_formset,
        'labor_formset': labor_formset, 'spares_formset': spares_formset,
        'title': 'Used Vehicle Final Inspection',
    })


@login_required
def uv_final_inspection_detail(request, pk):
    obj = get_object_or_404(UsedVehicleFinalInspection, pk=pk)
    return render(request, 'used_vehicles/uv_final_inspection_detail.html', {
        'obj': obj, 'complaints': obj.complaints_table.all(), 'observations': obj.supervisor_recomment.all(),
        'labor_charges': obj.labor_charges.all(), 'spares_lists': obj.spares_lists.all(),
    })


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def uv_final_inspection_submit(request, pk):
    return _uv_stage_submit(request, UsedVehicleFinalInspection, pk, 'uv_final_inspection')


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def uv_final_inspection_cancel(request, pk):
    return _uv_stage_cancel(request, UsedVehicleFinalInspection, pk, 'uv_final_inspection')


# ---- Outwork Entry Issue ----

@login_required
@require_module_action('used_vehicles', 'create')
def uv_outwork_issue_create(request):
    initial = {}
    if request.GET.get('jc'):
        initial['job_card'] = request.GET['jc']
    form = UsedVehicleOutworkEntryIssueForm(request.POST or None, initial=initial)
    work_formset = UsedVehicleOutworkWorkDetailFormSet(request.POST or None, prefix='work')
    spares_formset = UsedVehicleOutworkSpareItemFormSet(request.POST or None, prefix='spares')
    if request.method == 'POST':
        if form.is_valid() and work_formset.is_valid() and spares_formset.is_valid():
            obj = form.save()
            work_formset.instance = obj
            work_formset.save()
            spares_formset.instance = obj
            spares_formset.save()
            log_action(request, 'Used Vehicle Outwork Entry Issue', 'create', obj.pk)
            messages.success(request, 'Outwork Entry Issue created.')
            return redirect('used_vehicles:uv_outwork_issue_detail', pk=obj.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'used_vehicles/uv_outwork_issue_form.html', {
        'form': form, 'work_formset': work_formset, 'spares_formset': spares_formset,
        'title': 'Used Vehicle Outwork Entry Issue',
    })


@login_required
def uv_outwork_issue_detail(request, pk):
    obj = get_object_or_404(UsedVehicleOutworkEntryIssue, pk=pk)
    return render(request, 'used_vehicles/uv_outwork_issue_detail.html', {'obj': obj})


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def uv_outwork_issue_submit(request, pk):
    return _uv_stage_submit(request, UsedVehicleOutworkEntryIssue, pk, 'uv_outwork_issue')


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def uv_outwork_issue_cancel(request, pk):
    return _uv_stage_cancel(request, UsedVehicleOutworkEntryIssue, pk, 'uv_outwork_issue')


# ---- Outwork Entry Return ----

@login_required
@require_module_action('used_vehicles', 'create')
def uv_outwork_return_create(request):
    initial = {}
    if request.GET.get('issue'):
        issue = get_object_or_404(UsedVehicleOutworkEntryIssue, pk=request.GET['issue'])
        initial['outwork_issue'] = issue.pk
        initial['job_card'] = issue.job_card_id
    form = UsedVehicleOutworkEntryReturnForm(request.POST or None, initial=initial)
    details_formset = UsedVehicleOutworkReturnDetailFormSet(request.POST or None, prefix='details')
    if request.method == 'POST':
        if form.is_valid() and details_formset.is_valid():
            obj = form.save()
            details_formset.instance = obj
            details_formset.save()
            log_action(request, 'Used Vehicle Outwork Entry Return', 'create', obj.pk)
            messages.success(request, 'Outwork Entry Return created.')
            return redirect('used_vehicles:uv_outwork_return_detail', pk=obj.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'used_vehicles/uv_outwork_return_form.html', {
        'form': form, 'details_formset': details_formset, 'title': 'Used Vehicle Outwork Entry Return',
    })


@login_required
def uv_outwork_return_detail(request, pk):
    obj = get_object_or_404(UsedVehicleOutworkEntryReturn, pk=pk)
    return render(request, 'used_vehicles/uv_outwork_return_detail.html', {'obj': obj})


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def uv_outwork_return_submit(request, pk):
    return _uv_stage_submit(request, UsedVehicleOutworkEntryReturn, pk, 'uv_outwork_return')


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def uv_outwork_return_cancel(request, pk):
    return _uv_stage_cancel(request, UsedVehicleOutworkEntryReturn, pk, 'uv_outwork_return')


# ---- Labor Charge ----

@login_required
@require_module_action('used_vehicles', 'create')
def uv_labor_charge_create(request):
    initial = {}
    if request.GET.get('jc'):
        initial['job_card'] = request.GET['jc']
    form = UsedVehicleLaborChargeForm(request.POST or None, initial=initial)
    labor_formset = UsedVehicleLaborDetailLineFormSet(request.POST or None, prefix='labor')
    spares_formset = UsedVehicleLaborSpareItemFormSet(request.POST or None, prefix='spares')
    removes_formset = UsedVehicleLaborChargeRemoveItemFormSet(request.POST or None, prefix='removes')
    if request.method == 'POST':
        if (form.is_valid() and labor_formset.is_valid() and spares_formset.is_valid()
                and removes_formset.is_valid()):
            obj = form.save()
            labor_formset.instance = obj
            labor_formset.save()
            spares_formset.instance = obj
            spares_formset.save()
            removes_formset.instance = obj
            removes_formset.save()
            obj.updated_total = obj.total_amount - (obj.discount or 0)
            obj.save(update_fields=['updated_total'])
            log_action(request, 'Used Vehicle Labor Charge', 'create', obj.pk)
            messages.success(request, 'Labor Charge created.')
            return redirect('used_vehicles:uv_labor_charge_detail', pk=obj.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'used_vehicles/uv_labor_charge_form.html', {
        'form': form, 'labor_formset': labor_formset, 'spares_formset': spares_formset,
        'removes_formset': removes_formset, 'title': 'Used Vehicle Labor Charge',
    })


@login_required
def uv_labor_charge_detail(request, pk):
    obj = get_object_or_404(UsedVehicleLaborCharge, pk=pk)
    return render(request, 'used_vehicles/uv_labor_charge_detail.html', {
        'obj': obj, 'removes': obj.labor_charge_removes.all(),
    })


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def uv_labor_charge_submit(request, pk):
    return _uv_stage_submit(request, UsedVehicleLaborCharge, pk, 'uv_labor_charge')


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def uv_labor_charge_cancel(request, pk):
    return _uv_stage_cancel(request, UsedVehicleLaborCharge, pk, 'uv_labor_charge')


# ---- Service Invoice ----

@login_required
@require_module_action('used_vehicles', 'create')
def uv_service_invoice_create(request):
    initial = {}
    if request.GET.get('jc'):
        initial['job_card'] = request.GET['jc']
    form = UsedVehicleServiceInvoiceForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        obj.calculate_totals()
        log_action(request, 'Used Vehicle Service Invoice', 'create', obj.pk)
        messages.success(request, 'Service Invoice created.')
        return redirect('used_vehicles:uv_service_invoice_detail', pk=obj.pk)
    return render(request, 'used_vehicles/uv_service_invoice_form.html', {'form': form, 'title': 'Used Vehicle Service Invoice'})


@login_required
def uv_service_invoice_detail(request, pk):
    obj = get_object_or_404(UsedVehicleServiceInvoice, pk=pk)
    return render(request, 'used_vehicles/uv_service_invoice_detail.html', {'obj': obj})


# ---------------------------------------------------------------------------
# Phase 8c — Used Vehicle Master Settings
# ---------------------------------------------------------------------------

@login_required
def used_vehicle_master_settings_list(request):
    qs = UsedVehicleMasterSettings.objects.select_related('vehicle').order_by('-created_at')
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'used_vehicles/used_vehicle_master_settings_list.html', {'objs': page_obj, 'page_obj': page_obj})


@login_required
def used_vehicle_master_settings_detail(request, pk):
    obj = get_object_or_404(
        UsedVehicleMasterSettings.objects.select_related('vehicle', 'service_settings', 'exchange_vehicle_id'), pk=pk
    )
    return render(request, 'used_vehicles/used_vehicle_master_settings_detail.html', {
        'obj': obj, 'items': obj.items.select_related('vehicle_name', 'color').all(),
    })


@login_required
@require_module_action('used_vehicles', 'create')
def used_vehicle_master_settings_create(request):
    form = UsedVehicleMasterSettingsForm(request.POST or None)
    formset = UsedVehicleMasterSettingsItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        formset.instance = obj
        formset.save()
        log_action(request, 'Used Vehicle Master Settings', 'create', obj.pk)
        messages.success(request, f'{obj.master_no} created.')
        return redirect('used_vehicles:used_vehicle_master_settings_detail', pk=obj.pk)
    return render(request, 'used_vehicles/used_vehicle_master_settings_form.html', {
        'form': form, 'formset': formset, 'title': 'New Used Vehicle Master Settings',
    })


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def used_vehicle_master_settings_submit(request, pk):
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    obj = get_object_or_404(UsedVehicleMasterSettings, pk=pk)
    if not user_owns(request.user, obj):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    existing_regs = set(UsedVehicleRegisterNo.objects.values_list('registration_no', flat=True))
    rows = obj.items.all()
    try:
        obj.submit(request.user)
        log_action(request, 'Used Vehicle Master Settings', 'update', pk)
        created = [r.register_number for r in rows if r.register_number not in existing_regs]
        skipped = [r.register_number for r in rows if r.register_number in existing_regs]
        msg = f'{obj.master_no} submitted — {len(created)} register number row(s) created.'
        if skipped:
            msg += f' Skipped {len(skipped)} duplicate registration number(s): {", ".join(skipped)}.'
        messages.success(request, msg)
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:used_vehicle_master_settings_detail', pk=pk)


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def used_vehicle_master_settings_cancel(request, pk):
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    obj = get_object_or_404(UsedVehicleMasterSettings, pk=pk)
    if not user_owns(request.user, obj):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        obj.cancel(request.user)
        log_action(request, 'Used Vehicle Master Settings', 'update', pk)
        messages.success(request, f'{obj.master_no} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:used_vehicle_master_settings_detail', pk=pk)


# ---------------------------------------------------------------------------
# Phase 8d — Used Vehicle Sales Setting
# ---------------------------------------------------------------------------

@login_required
def used_vehicle_sales_setting_list(request):
    qs = UsedVehicleSalesSetting.objects.order_by('-created_at')
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'used_vehicles/used_vehicle_sales_setting_list.html', {'objs': page_obj, 'page_obj': page_obj})


@login_required
def used_vehicle_sales_setting_detail(request, pk):
    obj = get_object_or_404(UsedVehicleSalesSetting, pk=pk)
    return render(request, 'used_vehicles/used_vehicle_sales_setting_detail.html', {
        'obj': obj, 'items': obj.items.select_related('vehicle_no').all(),
    })


@login_required
@require_module_action('used_vehicles', 'create')
def used_vehicle_sales_setting_create(request):
    form = UsedVehicleSalesSettingForm(request.POST or None)
    formset = UsedVehicleSalesSettingItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        obj = form.save()
        formset.instance = obj
        formset.save()
        log_action(request, 'Used Vehicle Sales Setting', 'create', obj.pk)
        messages.success(request, f'{obj.setting_no} created.')
        return redirect('used_vehicles:used_vehicle_sales_setting_detail', pk=obj.pk)
    return render(request, 'used_vehicles/used_vehicle_sales_setting_form.html', {
        'form': form, 'formset': formset, 'title': 'New Used Vehicle Sales Setting',
    })


@login_required
@require_module_action('used_vehicles', 'edit')
def used_vehicle_sales_setting_update(request, pk):
    obj = get_object_or_404(UsedVehicleSalesSetting, pk=pk)
    form = UsedVehicleSalesSettingForm(request.POST or None, instance=obj)
    formset = UsedVehicleSalesSettingItemFormSet(request.POST or None, instance=obj, prefix='items')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        form.save()
        formset.save()
        log_action(request, 'Used Vehicle Sales Setting', 'update', pk)
        messages.success(request, f'{obj.setting_no} updated.')
        return redirect('used_vehicles:used_vehicle_sales_setting_detail', pk=pk)
    return render(request, 'used_vehicles/used_vehicle_sales_setting_form.html', {
        'form': form, 'formset': formset, 'title': 'Edit Used Vehicle Sales Setting', 'object': obj,
    })


# ---------------------------------------------------------------------------
# Used Vehicle Insurance Update (round-3 live-verification sweep finding)
# ---------------------------------------------------------------------------

@login_required
def used_vehicle_insurance_update_list(request):
    qs = UsedVehicleInsuranceUpdate.objects.select_related('register_no', 'insurance_name').order_by('-created_at')
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'used_vehicles/used_vehicle_insurance_update_list.html', {'objs': page_obj, 'page_obj': page_obj})


@login_required
def used_vehicle_insurance_update_detail(request, pk):
    obj = get_object_or_404(
        UsedVehicleInsuranceUpdate.objects.select_related('register_no', 'insurance_name'), pk=pk
    )
    return render(request, 'used_vehicles/used_vehicle_insurance_update_detail.html', {'obj': obj})


@login_required
@require_module_action('used_vehicles', 'create')
def used_vehicle_insurance_update_create(request):
    form = UsedVehicleInsuranceUpdateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        log_action(request, 'Used Vehicle Insurance Update', 'create', obj.pk)
        messages.success(request, f'{obj.update_no} created.')
        return redirect('used_vehicles:used_vehicle_insurance_update_detail', pk=obj.pk)
    return render(request, 'used_vehicles/used_vehicle_insurance_update_form.html', {
        'form': form, 'title': 'New Used Vehicle Insurance Update',
    })


@login_required
@require_module_action('used_vehicles', 'edit')
def used_vehicle_insurance_update_update(request, pk):
    from accounts.permissions import user_owns
    obj = get_object_or_404(UsedVehicleInsuranceUpdate, pk=pk)
    if obj.docstatus != UsedVehicleInsuranceUpdate.DocStatus.DRAFT:
        return HttpResponseForbidden('Only Draft documents can be edited.')
    if not user_owns(request.user, obj):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    form = UsedVehicleInsuranceUpdateForm(request.POST or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Used Vehicle Insurance Update', 'update', pk)
        messages.success(request, f'{obj.update_no} updated.')
        return redirect('used_vehicles:used_vehicle_insurance_update_detail', pk=pk)
    return render(request, 'used_vehicles/used_vehicle_insurance_update_form.html', {
        'form': form, 'title': 'Edit Used Vehicle Insurance Update', 'object': obj,
    })


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def used_vehicle_insurance_update_submit(request, pk):
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    obj = get_object_or_404(UsedVehicleInsuranceUpdate, pk=pk)
    if not user_owns(request.user, obj):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        obj.submit(request.user)
        log_action(request, 'Used Vehicle Insurance Update', 'update', pk)
        messages.success(request, f'{obj.update_no} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:used_vehicle_insurance_update_detail', pk=pk)


@login_required
@require_POST
@require_module_action('used_vehicles', 'edit')
def used_vehicle_insurance_update_cancel(request, pk):
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    obj = get_object_or_404(UsedVehicleInsuranceUpdate, pk=pk)
    if not user_owns(request.user, obj):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        obj.cancel(request.user)
        log_action(request, 'Used Vehicle Insurance Update', 'update', pk)
        messages.success(request, f'{obj.update_no} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('used_vehicles:used_vehicle_insurance_update_detail', pk=pk)
