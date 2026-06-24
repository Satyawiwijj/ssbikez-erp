from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.permissions import require_module_action
from .models import SparesCategory, Supplier, Warehouse, Rack, Bin
from .forms import SparesCategoryForm, SupplierForm, WarehouseForm, RackForm, BinForm


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
