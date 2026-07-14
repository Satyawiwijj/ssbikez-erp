from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.audit import log_action
from accounts.permissions import require_module_action

from .forms import (
    BikeModelForm, CustomerForm, VehicleStockForm,
    VehicleMasterSettingsForm, VehicleMasterSettingsItemFormSet,
)
from .models import BikeModel, Customer, VehicleStock, VehicleMasterSettings


@login_required
def customer_list(request):
    q = request.GET.get('q', '').strip()
    qs = Customer.objects.all()
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(phone__icontains=q))
    paginator = Paginator(qs, 25)
    page_obj  = paginator.get_page(request.GET.get('page'))
    return render(request, 'customers/customer_list.html',
                  {'customers': page_obj, 'page_obj': page_obj, 'q': q})


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    vehicles = customer.vehicles.select_related('vehicle__bike_model').all()

    # Finance summary
    from django.db.models import Sum
    from sales.models import VehicleSalesOrder
    from billing.models import Invoice, FinanceLoan
    sales_orders = VehicleSalesOrder.objects.filter(customer=customer).select_related('vehicle__bike_model')
    invoices     = Invoice.objects.filter(sales_order__customer=customer)
    total_invoiced = invoices.aggregate(t=Sum('final_amount'))['t'] or 0
    loans          = FinanceLoan.objects.filter(sales_order__customer=customer)
    total_loan     = loans.aggregate(t=Sum('loan_amount'))['t'] or 0

    return render(request, 'customers/customer_detail.html', {
        'customer':       customer,
        'vehicles':       vehicles,
        'sales_orders':   sales_orders,
        'invoices':       invoices,
        'total_invoiced': total_invoiced,
        'loans':          loans,
        'total_loan':     total_loan,
    })


@login_required
@require_module_action('customers', 'create')
def customer_create(request):
    form = CustomerForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        customer = form.save()
        log_action(request, 'Customer', 'create', customer.pk)
        messages.success(request, 'Customer added successfully.')
        return redirect('customers:customer_detail', pk=customer.pk)
    return render(request, 'customers/customer_form.html',
                  {'form': form, 'title': 'Add Customer'})


@login_required
@require_module_action('customers', 'edit')
def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerForm(request.POST or None, instance=customer)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Customer', 'update', pk)
        messages.success(request, 'Customer updated successfully.')
        return redirect('customers:customer_detail', pk=customer.pk)
    return render(request, 'customers/customer_form.html',
                  {'form': form, 'title': 'Edit Customer'})


@login_required
def bike_model_list(request):
    bike_models = BikeModel.objects.all()
    return render(request, 'customers/bike_model_list.html', {'bike_models': bike_models})


@login_required
def bike_model_detail(request, pk):
    bike_model = get_object_or_404(BikeModel, pk=pk)
    stock = bike_model.stock.select_related('branch').all()
    return render(request, 'customers/bike_model_detail.html',
                  {'bike_model': bike_model, 'stock': stock})


@login_required
@require_module_action('vehicle_master', 'create')
def bike_model_create(request):
    form = BikeModelForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        bike_model = form.save()
        messages.success(request, 'Bike model added successfully.')
        return redirect('customers:bike_model_detail', pk=bike_model.pk)
    return render(request, 'customers/bike_model_form.html',
                  {'form': form, 'title': 'Add Bike Model'})


@login_required
@require_module_action('vehicle_master', 'edit')
def bike_model_update(request, pk):
    bike_model = get_object_or_404(BikeModel, pk=pk)
    form = BikeModelForm(request.POST or None, instance=bike_model)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Bike model updated successfully.')
        return redirect('customers:bike_model_detail', pk=bike_model.pk)
    return render(request, 'customers/bike_model_form.html',
                  {'form': form, 'title': 'Edit Bike Model'})


@login_required
def vehicle_stock_list(request):
    stock_list = VehicleStock.objects.select_related('bike_model', 'branch').all()
    return render(request, 'customers/vehicle_stock_list.html', {'stock_list': stock_list})


@login_required
def vehicle_stock_detail(request, pk):
    stock = get_object_or_404(
        VehicleStock.objects.select_related('bike_model', 'branch'), pk=pk
    )
    return render(request, 'customers/vehicle_stock_detail.html', {'stock': stock})


@login_required
@require_module_action('vehicle_master', 'create')
def vehicle_stock_create(request):
    form = VehicleStockForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        stock = form.save()
        log_action(request, 'Vehicle Stock', 'create', stock.pk)
        messages.success(request, 'Vehicle stock entry added successfully.')
        return redirect('customers:vehicle_stock_detail', pk=stock.pk)
    return render(request, 'customers/vehicle_stock_form.html',
                  {'form': form, 'title': 'Add Vehicle Stock'})


@login_required
@require_module_action('vehicle_master', 'edit')
def vehicle_stock_update(request, pk):
    stock = get_object_or_404(VehicleStock, pk=pk)
    form = VehicleStockForm(request.POST or None, instance=stock)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Vehicle Stock', 'update', pk)
        messages.success(request, 'Vehicle stock updated successfully.')
        return redirect('customers:vehicle_stock_detail', pk=stock.pk)
    return render(request, 'customers/vehicle_stock_form.html',
                  {'form': form, 'title': 'Edit Vehicle Stock'})


# ============================================================
# FEATURE 2 — Vehicle Stock Aging Page
# ============================================================

@login_required
def stock_aging(request):
    from datetime import date, timedelta
    today = date.today()
    aging_30 = VehicleStock.objects.filter(
        stock_status='available',
        purchase_date__lte=today - timedelta(days=30),
        purchase_date__gt=today - timedelta(days=60)
    ).select_related('bike_model', 'branch')
    aging_60 = VehicleStock.objects.filter(
        stock_status='available',
        purchase_date__lte=today - timedelta(days=60),
        purchase_date__gt=today - timedelta(days=90)
    ).select_related('bike_model', 'branch')
    aging_90 = VehicleStock.objects.filter(
        stock_status='available',
        purchase_date__lte=today - timedelta(days=90)
    ).select_related('bike_model', 'branch')

    def days_in_stock(stock):
        if stock.purchase_date:
            return (today - stock.purchase_date).days
        return 0

    aging_90_list = [{'stock': s, 'days': days_in_stock(s)} for s in aging_90]
    return render(request, 'customers/stock_aging.html', {
        'today': today,
        'aging_30': aging_30, 'aging_30_count': aging_30.count(),
        'aging_60': aging_60, 'aging_60_count': aging_60.count(),
        'aging_90_list': aging_90_list, 'aging_90_count': aging_90.count(),
    })


@login_required
@require_POST
@require_module_action('customers', 'delete')
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    # Guard: block if related records exist to prevent silent data loss
    blockers = []
    if customer.vehicles.exists():
        blockers.append('customer vehicles')
    if customer.enquiries.exists():
        blockers.append('sales enquiries')
    if blockers:
        messages.error(
            request,
            f'Cannot delete CUST-{pk}: has linked {", ".join(blockers)}. '
            'Remove or reassign those records first.'
        )
        return redirect('customers:customer_detail', pk=pk)
    customer.delete()
    log_action(request, 'Customer', 'delete', pk)
    messages.success(request, f'Customer CUST-{pk} deleted.')
    return redirect('customers:customer_list')


# ---------------------------------------------------------------------------
# Phase 8c — Vehicle Master Settings
# ---------------------------------------------------------------------------

@login_required
def vehicle_master_settings_list(request):
    objs = VehicleMasterSettings.objects.select_related('vehicle').order_by('-created_at')
    return render(request, 'customers/vehicle_master_settings_list.html', {'objs': objs})


@login_required
def vehicle_master_settings_detail(request, pk):
    obj = get_object_or_404(VehicleMasterSettings.objects.select_related('vehicle', 'service_settings', 'exchange_vehicle_id'), pk=pk)
    return render(request, 'customers/vehicle_master_settings_detail.html', {'obj': obj, 'items': obj.items.select_related('vehicle_name').all()})


@login_required
@require_module_action('customers', 'create')
def vehicle_master_settings_create(request):
    form = VehicleMasterSettingsForm(request.POST or None)
    formset = VehicleMasterSettingsItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        formset.instance = obj
        formset.save()
        log_action(request, 'Vehicle Master Settings', 'create', obj.pk)
        messages.success(request, f'{obj.master_no} created.')
        return redirect('customers:vehicle_master_settings_detail', pk=obj.pk)
    return render(request, 'customers/vehicle_master_settings_form.html', {
        'form': form, 'formset': formset, 'title': 'New Vehicle Master Settings',
    })


@login_required
@require_POST
@require_module_action('customers', 'edit')
def vehicle_master_settings_submit(request, pk):
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    obj = get_object_or_404(VehicleMasterSettings, pk=pk)
    if not user_owns(request.user, obj):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    existing_chassis = set(VehicleStock.objects.values_list('chassis_no', flat=True))
    rows = obj.items.all()
    try:
        obj.submit(request.user)
        log_action(request, 'Vehicle Master Settings', 'update', pk)
        created = [r.chasis_no for r in rows if r.chasis_no not in existing_chassis]
        skipped = [r.chasis_no for r in rows if r.chasis_no in existing_chassis]
        msg = f'{obj.master_no} submitted — {len(created)} vehicle stock row(s) created.'
        if skipped:
            msg += f' Skipped {len(skipped)} duplicate chassis number(s): {", ".join(skipped)}.'
        messages.success(request, msg)
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('customers:vehicle_master_settings_detail', pk=pk)


@login_required
@require_POST
@require_module_action('customers', 'edit')
def vehicle_master_settings_cancel(request, pk):
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    obj = get_object_or_404(VehicleMasterSettings, pk=pk)
    if not user_owns(request.user, obj):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        obj.cancel(request.user)
        log_action(request, 'Vehicle Master Settings', 'update', pk)
        messages.success(request, f'{obj.master_no} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('customers:vehicle_master_settings_detail', pk=pk)
