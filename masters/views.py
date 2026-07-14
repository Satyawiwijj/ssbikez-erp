from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_POST
from accounts.permissions import require_module_action
from .models import (
    SparesCategory, Supplier, Warehouse, Rack, Bin, OrderFormSettings, OrderFormSeries,
    ModelAndPrice, CustomerPrice, DealerPriceList, VehicleFittingSpares,
)
from .forms import (
    SparesCategoryForm, SupplierForm, WarehouseForm, RackForm, BinForm, OrderFormSettingsForm,
    ModelAndPriceForm, CustomerPriceForm, CustomerPriceItemFormSet,
    DealerPriceListForm, DealerPriceItemFormSet,
    VehicleFittingSparesForm, VehicleFittingSpareItemFormSet,
)


# ── Categories ──────────────────────────────────────────────────────────────

@login_required
def category_list(request):
    cats = SparesCategory.objects.all()
    return render(request, 'masters/category_list.html', {'categories': cats})


@login_required
@require_module_action('masters', 'create')
def category_create(request):
    form = SparesCategoryForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Category created.')
        return redirect('masters:category_list')
    return render(request, 'masters/category_form.html', {'form': form, 'title': 'New Category'})


@login_required
@require_module_action('masters', 'edit')
def category_update(request, pk):
    obj = get_object_or_404(SparesCategory, pk=pk)
    form = SparesCategoryForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Category updated.')
        return redirect('masters:category_list')
    return render(request, 'masters/category_form.html', {'form': form, 'title': 'Edit Category', 'object': obj})


# ── Suppliers ────────────────────────────────────────────────────────────────

@login_required
def supplier_list(request):
    suppliers = Supplier.objects.all()
    return render(request, 'masters/supplier_list.html', {'suppliers': suppliers})


@login_required
def supplier_detail(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    return render(request, 'masters/supplier_detail.html', {'supplier': supplier})


@login_required
@require_module_action('masters', 'create')
def supplier_create(request):
    form = SupplierForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        messages.success(request, 'Supplier created.')
        return redirect('masters:supplier_list')
    return render(request, 'masters/supplier_form.html', {'form': form, 'title': 'New Supplier'})


@login_required
@require_module_action('masters', 'edit')
def supplier_update(request, pk):
    obj = get_object_or_404(Supplier, pk=pk)
    form = SupplierForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Supplier updated.')
        return redirect('masters:supplier_detail', pk=pk)
    return render(request, 'masters/supplier_form.html', {'form': form, 'title': 'Edit Supplier', 'object': obj})


# ── Warehouses ───────────────────────────────────────────────────────────────

@login_required
def warehouse_list(request):
    warehouses = Warehouse.objects.all()
    return render(request, 'masters/warehouse_list.html', {'warehouses': warehouses})


@login_required
@require_module_action('masters', 'create')
def warehouse_create(request):
    form = WarehouseForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Warehouse created.')
        return redirect('masters:warehouse_list')
    return render(request, 'masters/warehouse_form.html', {'form': form, 'title': 'New Warehouse'})


@login_required
@require_module_action('masters', 'edit')
def warehouse_update(request, pk):
    obj = get_object_or_404(Warehouse, pk=pk)
    form = WarehouseForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Warehouse updated.')
        return redirect('masters:warehouse_list')
    return render(request, 'masters/warehouse_form.html', {'form': form, 'title': 'Edit Warehouse', 'object': obj})


# ── Racks ─────────────────────────────────────────────────────────────────────

@login_required
def rack_list(request):
    racks = Rack.objects.select_related('warehouse').all()
    return render(request, 'masters/rack_list.html', {'racks': racks})


@login_required
@require_module_action('masters', 'create')
def rack_create(request):
    form = RackForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Rack created.')
        return redirect('masters:rack_list')
    return render(request, 'masters/rack_form.html', {'form': form, 'title': 'New Rack'})


@login_required
@require_module_action('masters', 'edit')
def rack_update(request, pk):
    obj = get_object_or_404(Rack, pk=pk)
    form = RackForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Rack updated.')
        return redirect('masters:rack_list')
    return render(request, 'masters/rack_form.html', {'form': form, 'title': 'Edit Rack', 'object': obj})


# ── Bins ──────────────────────────────────────────────────────────────────────

@login_required
def bin_list(request):
    bins = Bin.objects.select_related('rack__warehouse').all()
    return render(request, 'masters/bin_list.html', {'bins': bins})


@login_required
@require_module_action('masters', 'create')
def bin_create(request):
    form = BinForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Bin created.')
        return redirect('masters:bin_list')
    return render(request, 'masters/bin_form.html', {'form': form, 'title': 'New Bin'})


@login_required
@require_module_action('masters', 'edit')
def bin_update(request, pk):
    obj = get_object_or_404(Bin, pk=pk)
    form = BinForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Bin updated.')
        return redirect('masters:bin_list')
    return render(request, 'masters/bin_form.html', {'form': form, 'title': 'Edit Bin', 'object': obj})


# ── Phase 8a — Order Form Settings & Order Form Series ──────────────────────

@login_required
def order_form_settings(request):
    instance = OrderFormSettings.get_instance()
    form = OrderFormSettingsForm(request.POST or None, instance=instance)
    if request.method == 'POST' and 'save_settings' in request.POST and form.is_valid():
        form.save()
        messages.success(request, 'Order Form Settings saved.')
        return redirect('masters:order_form_settings')
    return render(request, 'masters/order_form_settings.html', {'form': form, 'settings': instance})


@login_required
@require_POST
@require_module_action('masters', 'create')
def order_form_settings_generate(request):
    instance = OrderFormSettings.get_instance()
    if instance.new_vehicle:
        series_type = 'new_vehicle'
    elif instance.used_vehicle:
        series_type = 'used_vehicle'
    else:
        messages.error(request, 'Check either New Vehicle or Used Vehicle before generating.')
        return redirect('masters:order_form_settings')

    if not instance.branch_id or not instance.prefix or not instance.count:
        messages.error(request, 'Branch, Prefix and Count are required to generate a series.')
        return redirect('masters:order_form_settings')

    last = OrderFormSeries.objects.filter(
        branch=instance.branch, series_type=series_type, order_form_no__startswith=instance.prefix
    ).order_by('-order_form_no').values_list('order_form_no', flat=True).first()
    next_seq = 1
    if last:
        try:
            next_seq = int(last[len(instance.prefix):]) + 1
        except ValueError:
            pass

    from_no = next_seq
    to_no = from_no + instance.count - 1
    with transaction.atomic():
        for n in range(from_no, to_no + 1):
            OrderFormSeries.objects.create(
                order_form_no=f'{instance.prefix}{n:0{instance.digits}d}',
                order_form_count=n,
                branch=instance.branch,
                status='unused',
                series_type=series_type,
                docstatus=OrderFormSeries.DocStatus.SUBMITTED,
                created_by=request.user,
            )
        instance.from_no = to_no + 1
        instance.to_no = to_no + instance.count
        instance.save()
    messages.success(request, f'Generated {instance.count} Order Form Series numbers ({instance.prefix}{from_no:0{instance.digits}d} — {instance.prefix}{to_no:0{instance.digits}d}).')
    return redirect('masters:order_form_series_list')


@login_required
def order_form_series_list(request):
    objs = OrderFormSeries.objects.select_related('branch').order_by('-order_form_no')
    return render(request, 'masters/order_form_series_list.html', {'objs': objs})


@login_required
def order_form_series_detail(request, pk):
    obj = get_object_or_404(OrderFormSeries.objects.select_related('branch'), pk=pk)
    return render(request, 'masters/order_form_series_detail.html', {'obj': obj})


@login_required
@require_POST
@require_module_action('masters', 'edit')
def order_form_series_cancel(request, pk):
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    obj = get_object_or_404(OrderFormSeries, pk=pk)
    if not user_owns(request.user, obj):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        obj.cancel(request.user)
        messages.success(request, f'{obj.order_form_no} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('masters:order_form_series_detail', pk=pk)


# ── Phase 8b — Model and Price ───────────────────────────────────────────────

@login_required
def model_and_price_list(request):
    objs = ModelAndPrice.objects.select_related('model_code').all()
    return render(request, 'masters/model_and_price_list.html', {'objs': objs})


@login_required
def model_and_price_detail(request, pk):
    obj = get_object_or_404(ModelAndPrice.objects.select_related('model_code'), pk=pk)
    return render(request, 'masters/model_and_price_detail.html', {'obj': obj})


@login_required
@require_module_action('masters', 'create')
def model_and_price_create(request):
    form = ModelAndPriceForm(request.POST or None)
    if form.is_valid():
        obj = form.save()
        messages.success(request, f'{obj.price_no} created.')
        return redirect('masters:model_and_price_detail', pk=obj.pk)
    return render(request, 'masters/model_and_price_form.html', {'form': form, 'title': 'New Model and Price'})


@login_required
@require_module_action('masters', 'edit')
def model_and_price_update(request, pk):
    obj = get_object_or_404(ModelAndPrice, pk=pk)
    form = ModelAndPriceForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, f'{obj.price_no} updated.')
        return redirect('masters:model_and_price_detail', pk=pk)
    return render(request, 'masters/model_and_price_form.html', {'form': form, 'title': 'Edit Model and Price', 'object': obj})


# ── Phase 8b — Customer Price ────────────────────────────────────────────────

@login_required
def customer_price_list(request):
    objs = CustomerPrice.objects.select_related('model_code', 'branch').all()
    return render(request, 'masters/customer_price_list.html', {'objs': objs})


@login_required
def customer_price_detail(request, pk):
    obj = get_object_or_404(CustomerPrice.objects.select_related('model_code', 'branch'), pk=pk)
    return render(request, 'masters/customer_price_detail.html', {'obj': obj, 'items': obj.items.all()})


@login_required
@require_module_action('masters', 'create')
def customer_price_create(request):
    form = CustomerPriceForm(request.POST or None)
    formset = CustomerPriceItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        obj = form.save()
        formset.instance = obj
        formset.save()
        obj.total = sum((i.amount for i in obj.items.all()), start=0)
        obj.save()
        messages.success(request, f'{obj.id_name} created.')
        return redirect('masters:customer_price_detail', pk=obj.pk)
    return render(request, 'masters/customer_price_form.html', {'form': form, 'formset': formset, 'title': 'New Customer Price'})


@login_required
@require_module_action('masters', 'edit')
def customer_price_update(request, pk):
    obj = get_object_or_404(CustomerPrice, pk=pk)
    form = CustomerPriceForm(request.POST or None, instance=obj)
    formset = CustomerPriceItemFormSet(request.POST or None, instance=obj, prefix='items')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        form.save()
        formset.save()
        obj.total = sum((i.amount for i in obj.items.all()), start=0)
        obj.save()
        messages.success(request, f'{obj.id_name} updated.')
        return redirect('masters:customer_price_detail', pk=pk)
    return render(request, 'masters/customer_price_form.html', {'form': form, 'formset': formset, 'title': 'Edit Customer Price', 'object': obj})


# ── Phase 8b — Dealer Price List ─────────────────────────────────────────────

@login_required
def dealer_price_list_list(request):
    objs = DealerPriceList.objects.select_related('dealer_name', 'model_code').all()
    return render(request, 'masters/dealer_price_list_list.html', {'objs': objs})


@login_required
def dealer_price_list_detail(request, pk):
    obj = get_object_or_404(DealerPriceList.objects.select_related('dealer_name', 'model_code'), pk=pk)
    return render(request, 'masters/dealer_price_list_detail.html', {'obj': obj, 'items': obj.items.all()})


@login_required
@require_module_action('masters', 'create')
def dealer_price_list_create(request):
    form = DealerPriceListForm(request.POST or None)
    formset = DealerPriceItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        obj = form.save()
        formset.instance = obj
        formset.save()
        obj.total_amount = sum((i.amount for i in obj.items.all()), start=0)
        obj.save()
        messages.success(request, f'{obj.id_name} created.')
        return redirect('masters:dealer_price_list_detail', pk=obj.pk)
    return render(request, 'masters/dealer_price_list_form.html', {'form': form, 'formset': formset, 'title': 'New Dealer Price List'})


@login_required
@require_module_action('masters', 'edit')
def dealer_price_list_update(request, pk):
    obj = get_object_or_404(DealerPriceList, pk=pk)
    form = DealerPriceListForm(request.POST or None, instance=obj)
    formset = DealerPriceItemFormSet(request.POST or None, instance=obj, prefix='items')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        form.save()
        formset.save()
        obj.total_amount = sum((i.amount for i in obj.items.all()), start=0)
        obj.save()
        messages.success(request, f'{obj.id_name} updated.')
        return redirect('masters:dealer_price_list_detail', pk=pk)
    return render(request, 'masters/dealer_price_list_form.html', {'form': form, 'formset': formset, 'title': 'Edit Dealer Price List', 'object': obj})


# ── Phase 8c — Vehicle Fitting Spares (Vehicle Service Master already exists
#    in service/views.py — not duplicated) ───────────────────────────────────

@login_required
def vehicle_fitting_spares_list(request):
    objs = VehicleFittingSpares.objects.select_related('vehicle', 'branch').all()
    return render(request, 'masters/vehicle_fitting_spares_list.html', {'objs': objs})


@login_required
def vehicle_fitting_spares_detail(request, pk):
    obj = get_object_or_404(VehicleFittingSpares.objects.select_related('vehicle', 'branch'), pk=pk)
    return render(request, 'masters/vehicle_fitting_spares_detail.html', {'obj': obj, 'items': obj.items.select_related('item').all()})


@login_required
@require_module_action('masters', 'create')
def vehicle_fitting_spares_create(request):
    form = VehicleFittingSparesForm(request.POST or None)
    formset = VehicleFittingSpareItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        obj = form.save()
        formset.instance = obj
        formset.save()
        obj.total_amount = sum((i.total for i in obj.items.all()), start=0)
        obj.save()
        messages.success(request, f'Fitting Spares for {obj.vehicle} created.')
        return redirect('masters:vehicle_fitting_spares_detail', pk=obj.pk)
    return render(request, 'masters/vehicle_fitting_spares_form.html', {'form': form, 'formset': formset, 'title': 'New Vehicle Fitting Spares'})


@login_required
@require_module_action('masters', 'edit')
def vehicle_fitting_spares_update(request, pk):
    obj = get_object_or_404(VehicleFittingSpares, pk=pk)
    form = VehicleFittingSparesForm(request.POST or None, instance=obj)
    formset = VehicleFittingSpareItemFormSet(request.POST or None, instance=obj, prefix='items')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        form.save()
        formset.save()
        obj.total_amount = sum((i.total for i in obj.items.all()), start=0)
        obj.save()
        messages.success(request, f'Fitting Spares for {obj.vehicle} updated.')
        return redirect('masters:vehicle_fitting_spares_detail', pk=pk)
    return render(request, 'masters/vehicle_fitting_spares_form.html', {'form': form, 'formset': formset, 'title': 'Edit Vehicle Fitting Spares', 'object': obj})
