from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import (DecimalField, ExpressionWrapper, F, Q, Sum)
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.audit import log_action

from .forms import (CounterSaleForm, CounterSaleItemForm, PurchaseOrderForm,
                    PurchaseOrderItemForm, SparePartForm, SparesCategoryForm,
                    SparesIssueForm, SupplierForm)
from .models import (CounterSale, CounterSaleItem, PurchaseOrder,
                     PurchaseOrderItem, SparePart, SparesCategory,
                     SparesIssue, Supplier)


# ---------------------------------------------------------------------------
# SparesCategory
# ---------------------------------------------------------------------------

@login_required
def category_list(request):
    categories = SparesCategory.objects.all()
    return render(request, 'spares/category_list.html', {'categories': categories})


@login_required
def category_create(request):
    form = SparesCategoryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Category added successfully.')
        return redirect('spares:category_list')
    return render(request, 'spares/category_form.html',
                  {'form': form, 'title': 'Add Category'})


@login_required
def category_update(request, pk):
    category = get_object_or_404(SparesCategory, pk=pk)
    form     = SparesCategoryForm(request.POST or None, instance=category)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Category updated successfully.')
        return redirect('spares:category_list')
    return render(request, 'spares/category_form.html',
                  {'form': form, 'title': 'Edit Category'})


# ---------------------------------------------------------------------------
# SparePart
# ---------------------------------------------------------------------------

@login_required
def part_list(request):
    q               = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '')
    qs = SparePart.objects.select_related('category').all()
    if q:
        qs = qs.filter(
            Q(part_name__icontains=q) | Q(part_number__icontains=q)
        )
    if category_filter:
        qs = qs.filter(category_id=category_filter)
    paginator = Paginator(qs, 25)
    page_obj  = paginator.get_page(request.GET.get('page'))
    return render(request, 'spares/part_list.html', {
        'parts':           page_obj,
        'page_obj':        page_obj,
        'q':               q,
        'category_filter': category_filter,
        'categories':      SparesCategory.objects.all(),
    })


@login_required
def part_detail(request, pk):
    part       = get_object_or_404(SparePart.objects.select_related('category'), pk=pk)
    po_items   = part.purchase_order_items.select_related('purchase_order__supplier').order_by('-created_at')[:10]
    sale_items = part.counter_sale_items.select_related('counter_sale').order_by('-counter_sale__sale_date')[:10]
    issues     = part.issues.select_related('job_card__customer_vehicle__customer', 'issued_by').order_by('-issued_at')[:10]
    return render(request, 'spares/part_detail.html', {
        'part':       part,
        'po_items':   po_items,
        'sale_items': sale_items,
        'issues':     issues,
    })


@login_required
def part_create(request):
    form = SparePartForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        part = form.save()
        log_action(request, 'Spare Part', 'create', part.pk)
        messages.success(request, 'Spare part added successfully.')
        return redirect('spares:part_detail', pk=part.pk)
    return render(request, 'spares/part_form.html',
                  {'form': form, 'title': 'Add Spare Part'})


@login_required
def part_update(request, pk):
    part = get_object_or_404(SparePart, pk=pk)
    form = SparePartForm(request.POST or None, instance=part)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Spare Part', 'update', pk)
        messages.success(request, 'Spare part updated successfully.')
        return redirect('spares:part_detail', pk=part.pk)
    return render(request, 'spares/part_form.html',
                  {'form': form, 'title': 'Edit Spare Part'})


# ---------------------------------------------------------------------------
# Supplier
# ---------------------------------------------------------------------------

@login_required
def supplier_list(request):
    q  = request.GET.get('q', '').strip()
    qs = Supplier.objects.all()
    if q:
        qs = qs.filter(
            Q(supplier_name__icontains=q) |
            Q(phone__icontains=q) |
            Q(email__icontains=q)
        )
    return render(request, 'spares/supplier_list.html', {'suppliers': qs, 'q': q})


@login_required
def supplier_detail(request, pk):
    supplier        = get_object_or_404(Supplier, pk=pk)
    purchase_orders = supplier.purchase_orders.all()
    return render(request, 'spares/supplier_detail.html', {
        'supplier':        supplier,
        'purchase_orders': purchase_orders,
    })


@login_required
def supplier_create(request):
    form = SupplierForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        supplier = form.save()
        log_action(request, 'Supplier', 'create', supplier.pk)
        messages.success(request, 'Supplier added successfully.')
        return redirect('spares:supplier_detail', pk=supplier.pk)
    return render(request, 'spares/supplier_form.html',
                  {'form': form, 'title': 'Add Supplier'})


@login_required
def supplier_update(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    form     = SupplierForm(request.POST or None, instance=supplier)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Supplier', 'update', pk)
        messages.success(request, 'Supplier updated successfully.')
        return redirect('spares:supplier_detail', pk=supplier.pk)
    return render(request, 'spares/supplier_form.html',
                  {'form': form, 'title': 'Edit Supplier'})


# ---------------------------------------------------------------------------
# PurchaseOrder
# ---------------------------------------------------------------------------

@login_required
def po_list(request):
    status_filter = request.GET.get('status', '')
    qs = PurchaseOrder.objects.select_related('supplier').all()
    if status_filter:
        qs = qs.filter(status=status_filter)
    return render(request, 'spares/po_list.html', {
        'purchase_orders': qs,
        'status_filter':   status_filter,
        'status_choices':  PurchaseOrder.Status.choices,
    })


@login_required
def po_detail(request, pk):
    po    = get_object_or_404(PurchaseOrder.objects.select_related('supplier'), pk=pk)
    items = po.items.select_related('spare_part').all()
    total = items.aggregate(
        total=Sum(ExpressionWrapper(F('quantity') * F('price'),
                  output_field=DecimalField()))
    )['total'] or Decimal('0.00')
    return render(request, 'spares/po_detail.html', {
        'po':    po,
        'items': items,
        'total': total,
    })


@login_required
def po_create(request):
    form = PurchaseOrderForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        po = form.save()
        log_action(request, 'Purchase Order', 'create', po.pk)
        messages.success(request, 'Purchase order created successfully.')
        return redirect('spares:po_detail', pk=po.pk)
    return render(request, 'spares/po_form.html',
                  {'form': form, 'title': 'New Purchase Order'})


@login_required
def po_update(request, pk):
    po   = get_object_or_404(PurchaseOrder, pk=pk)
    form = PurchaseOrderForm(request.POST or None, instance=po)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Purchase Order', 'update', pk)
        messages.success(request, 'Purchase order updated successfully.')
        return redirect('spares:po_detail', pk=po.pk)
    return render(request, 'spares/po_form.html',
                  {'form': form, 'title': 'Edit Purchase Order'})


@login_required
@require_POST
def po_status_update(request, pk):
    po         = get_object_or_404(PurchaseOrder, pk=pk)
    new_status = request.POST.get('status')
    if new_status in dict(PurchaseOrder.Status.choices):
        po.status = new_status
        po.save(update_fields=['status'])
        log_action(request, 'Purchase Order', 'update', pk)
        messages.success(request, f'PO status updated to {po.get_status_display()}.')
    return redirect('spares:po_detail', pk=po.pk)


# ---------------------------------------------------------------------------
# PurchaseOrderItem
# ---------------------------------------------------------------------------

@login_required
def po_item_create(request):
    initial = {}
    if request.GET.get('po'):
        initial['purchase_order'] = request.GET['po']
    form = PurchaseOrderItemForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        item = form.save()
        messages.success(request, 'Item added to purchase order.')
        return redirect('spares:po_detail', pk=item.purchase_order_id)
    return render(request, 'spares/po_item_form.html',
                  {'form': form, 'title': 'Add Item'})


@login_required
def po_item_update(request, pk):
    item = get_object_or_404(PurchaseOrderItem, pk=pk)
    form = PurchaseOrderItemForm(request.POST or None, instance=item)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Purchase order item updated successfully.')
        return redirect('spares:po_detail', pk=item.purchase_order_id)
    return render(request, 'spares/po_item_form.html',
                  {'form': form, 'title': 'Edit Item'})


@login_required
@require_POST
def po_item_delete(request, pk):
    item  = get_object_or_404(PurchaseOrderItem, pk=pk)
    po_pk = item.purchase_order_id
    item.delete()
    messages.success(request, 'Item removed from purchase order.')
    return redirect('spares:po_detail', pk=po_pk)


# ---------------------------------------------------------------------------
# CounterSale
# ---------------------------------------------------------------------------

@login_required
def counter_sale_list(request):
    q  = request.GET.get('q', '').strip()
    qs = CounterSale.objects.select_related('customer', 'branch', 'created_by').all()
    if q:
        qs = qs.filter(
            Q(invoice_number__icontains=q) |
            Q(customer__full_name__icontains=q)
        )
    paginator = Paginator(qs, 25)
    page_obj  = paginator.get_page(request.GET.get('page'))
    return render(request, 'spares/counter_sale_list.html', {
        'counter_sales': page_obj,
        'page_obj':      page_obj,
        'q':             q,
    })


@login_required
def counter_sale_detail(request, pk):
    sale  = get_object_or_404(
        CounterSale.objects.select_related('customer', 'branch', 'created_by'),
        pk=pk,
    )
    items = sale.items.select_related('spare_part').all()
    total = items.aggregate(total=Sum('total_price'))['total'] or Decimal('0.00')
    return render(request, 'spares/counter_sale_detail.html', {
        'sale':  sale,
        'items': items,
        'total': total,
    })


@login_required
def counter_sale_create(request):
    form = CounterSaleForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        sale = form.save()
        log_action(request, 'Counter Sale', 'create', sale.pk)
        messages.success(request, 'Counter sale created successfully.')
        return redirect('spares:counter_sale_detail', pk=sale.pk)
    return render(request, 'spares/counter_sale_form.html',
                  {'form': form, 'title': 'New Counter Sale'})


@login_required
def counter_sale_update(request, pk):
    sale = get_object_or_404(CounterSale, pk=pk)
    form = CounterSaleForm(request.POST or None, instance=sale)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Counter Sale', 'update', pk)
        messages.success(request, 'Counter sale updated successfully.')
        return redirect('spares:counter_sale_detail', pk=sale.pk)
    return render(request, 'spares/counter_sale_form.html',
                  {'form': form, 'title': 'Edit Counter Sale'})


# ---------------------------------------------------------------------------
# CounterSaleItem
# ---------------------------------------------------------------------------

@login_required
def counter_sale_item_create(request):
    initial = {}
    if request.GET.get('cs'):
        initial['counter_sale'] = request.GET['cs']
    form = CounterSaleItemForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        item = form.save()
        messages.success(request, 'Item added to counter sale.')
        return redirect('spares:counter_sale_detail', pk=item.counter_sale_id)
    return render(request, 'spares/counter_sale_item_form.html',
                  {'form': form, 'title': 'Add Sale Item'})


@login_required
@require_POST
def counter_sale_item_delete(request, pk):
    item    = get_object_or_404(CounterSaleItem, pk=pk)
    sale_pk = item.counter_sale_id
    item.delete()
    messages.success(request, 'Item removed from counter sale.')
    return redirect('spares:counter_sale_detail', pk=sale_pk)


# ---------------------------------------------------------------------------
# SparesIssue
# ---------------------------------------------------------------------------

@login_required
def issue_list(request):
    jobcard_filter = request.GET.get('jobcard', '')
    qs = SparesIssue.objects.select_related(
        'spare_part', 'job_card__customer_vehicle__customer', 'issued_by'
    ).all()
    if jobcard_filter:
        qs = qs.filter(job_card_id=jobcard_filter)
    return render(request, 'spares/spares_issue_list.html', {
        'issues':         qs,
        'jobcard_filter': jobcard_filter,
    })


@login_required
def issue_create(request):
    initial = {}
    if request.GET.get('jobcard'):
        initial['job_card'] = request.GET['jobcard']
    form = SparesIssueForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        issue = form.save()
        log_action(request, 'Spares Issue', 'create', issue.pk)
        messages.success(request, 'Spare part issued successfully.')
        return redirect('service:jobcard_detail', pk=issue.job_card_id)
    return render(request, 'spares/spares_issue_form.html',
                  {'form': form, 'title': 'Issue Spare Part'})


@login_required
def issue_update(request, pk):
    issue = get_object_or_404(SparesIssue, pk=pk)
    form  = SparesIssueForm(request.POST or None, instance=issue)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Spares Issue', 'update', pk)
        messages.success(request, 'Spares issue updated successfully.')
        return redirect('service:jobcard_detail', pk=issue.job_card_id)
    return render(request, 'spares/spares_issue_form.html',
                  {'form': form, 'title': 'Update Spares Issue'})
