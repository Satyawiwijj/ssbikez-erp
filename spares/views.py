from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import (DecimalField, ExpressionWrapper, F, Q, Sum)
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

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
    # context: categories — all SparesCategory instances
    categories = SparesCategory.objects.all()
    return render(request, 'spares/category_list.html', {'categories': categories})


@login_required
def category_create(request):
    # context: form — SparesCategoryForm; title — str
    form = SparesCategoryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('spares:category_list')
    return render(request, 'spares/category_form.html',
                  {'form': form, 'title': 'Add Category'})


@login_required
def category_update(request, pk):
    # context: form — SparesCategoryForm; title — str
    category = get_object_or_404(SparesCategory, pk=pk)
    form     = SparesCategoryForm(request.POST or None, instance=category)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('spares:category_list')
    return render(request, 'spares/category_form.html',
                  {'form': form, 'title': 'Edit Category'})


# ---------------------------------------------------------------------------
# SparePart
# ---------------------------------------------------------------------------

@login_required
def part_list(request):
    # context: parts — filtered queryset; q — search string;
    #          category_filter — pk or ''; categories — all SparesCategory
    q               = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '')
    qs = SparePart.objects.select_related('category').all()
    if q:
        qs = qs.filter(
            Q(part_name__icontains=q) | Q(part_number__icontains=q)
        )
    if category_filter:
        qs = qs.filter(category_id=category_filter)
    return render(request, 'spares/part_list.html', {
        'parts':           qs,
        'q':               q,
        'category_filter': category_filter,
        'categories':      SparesCategory.objects.all(),
    })


@login_required
def part_detail(request, pk):
    # context: part — SparePart; po_items — recent PurchaseOrderItems (last 10);
    #          sale_items — recent CounterSaleItems (last 10);
    #          issues — recent SparesIssues (last 10)
    part      = get_object_or_404(SparePart.objects.select_related('category'), pk=pk)
    po_items  = part.purchase_order_items.select_related('purchase_order__supplier').order_by('-created_at')[:10]
    sale_items = part.counter_sale_items.select_related('counter_sale').order_by('-counter_sale__sale_date')[:10]
    issues    = part.issues.select_related('job_card__customer_vehicle__customer', 'issued_by').order_by('-issued_at')[:10]
    return render(request, 'spares/part_detail.html', {
        'part':       part,
        'po_items':   po_items,
        'sale_items': sale_items,
        'issues':     issues,
    })


@login_required
def part_create(request):
    # context: form — SparePartForm; title — str
    form = SparePartForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        part = form.save()
        return redirect('spares:part_detail', pk=part.pk)
    return render(request, 'spares/part_form.html',
                  {'form': form, 'title': 'Add Spare Part'})


@login_required
def part_update(request, pk):
    # context: form — SparePartForm; title — str
    part = get_object_or_404(SparePart, pk=pk)
    form = SparePartForm(request.POST or None, instance=part)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('spares:part_detail', pk=part.pk)
    return render(request, 'spares/part_form.html',
                  {'form': form, 'title': 'Edit Spare Part'})


# ---------------------------------------------------------------------------
# Supplier
# ---------------------------------------------------------------------------

@login_required
def supplier_list(request):
    # context: suppliers — filtered queryset; q — search string
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
    # context: supplier — Supplier; purchase_orders — all POs for this supplier
    supplier       = get_object_or_404(Supplier, pk=pk)
    purchase_orders = supplier.purchase_orders.all()
    return render(request, 'spares/supplier_detail.html', {
        'supplier':       supplier,
        'purchase_orders': purchase_orders,
    })


@login_required
def supplier_create(request):
    # context: form — SupplierForm; title — str
    form = SupplierForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        supplier = form.save()
        return redirect('spares:supplier_detail', pk=supplier.pk)
    return render(request, 'spares/supplier_form.html',
                  {'form': form, 'title': 'Add Supplier'})


@login_required
def supplier_update(request, pk):
    # context: form — SupplierForm; title — str
    supplier = get_object_or_404(Supplier, pk=pk)
    form     = SupplierForm(request.POST or None, instance=supplier)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('spares:supplier_detail', pk=supplier.pk)
    return render(request, 'spares/supplier_form.html',
                  {'form': form, 'title': 'Edit Supplier'})


# ---------------------------------------------------------------------------
# PurchaseOrder
# ---------------------------------------------------------------------------

@login_required
def po_list(request):
    # context: purchase_orders — filtered queryset; status_filter — active tab;
    #          status_choices — list
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
    # context: po — PurchaseOrder; items — PurchaseOrderItems; total — Decimal
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
    # context: form — PurchaseOrderForm; title — str
    form = PurchaseOrderForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        po = form.save()
        return redirect('spares:po_detail', pk=po.pk)
    return render(request, 'spares/po_form.html',
                  {'form': form, 'title': 'New Purchase Order'})


@login_required
def po_update(request, pk):
    # context: form — PurchaseOrderForm; title — str
    po   = get_object_or_404(PurchaseOrder, pk=pk)
    form = PurchaseOrderForm(request.POST or None, instance=po)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('spares:po_detail', pk=po.pk)
    return render(request, 'spares/po_form.html',
                  {'form': form, 'title': 'Edit Purchase Order'})


@login_required
@require_POST
def po_status_update(request, pk):
    # POST only — updates status field only
    po         = get_object_or_404(PurchaseOrder, pk=pk)
    new_status = request.POST.get('status')
    if new_status in dict(PurchaseOrder.Status.choices):
        po.status = new_status
        po.save(update_fields=['status'])
    return redirect('spares:po_detail', pk=po.pk)


# ---------------------------------------------------------------------------
# PurchaseOrderItem
# ---------------------------------------------------------------------------

@login_required
def po_item_create(request):
    # context: form — PurchaseOrderItemForm; title — str
    # Pre-fills purchase_order from GET ?po=<pk>
    initial = {}
    if request.GET.get('po'):
        initial['purchase_order'] = request.GET['po']
    form = PurchaseOrderItemForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        item = form.save()
        return redirect('spares:po_detail', pk=item.purchase_order_id)
    return render(request, 'spares/po_item_form.html',
                  {'form': form, 'title': 'Add Item'})


@login_required
def po_item_update(request, pk):
    # context: form — PurchaseOrderItemForm; title — str
    item = get_object_or_404(PurchaseOrderItem, pk=pk)
    form = PurchaseOrderItemForm(request.POST or None, instance=item)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('spares:po_detail', pk=item.purchase_order_id)
    return render(request, 'spares/po_item_form.html',
                  {'form': form, 'title': 'Edit Item'})


@login_required
@require_POST
def po_item_delete(request, pk):
    # POST only — deletes a PurchaseOrderItem
    item  = get_object_or_404(PurchaseOrderItem, pk=pk)
    po_pk = item.purchase_order_id
    item.delete()
    return redirect('spares:po_detail', pk=po_pk)


# ---------------------------------------------------------------------------
# CounterSale
# ---------------------------------------------------------------------------

@login_required
def counter_sale_list(request):
    # context: counter_sales — filtered queryset; q — search string
    q  = request.GET.get('q', '').strip()
    qs = CounterSale.objects.select_related('customer', 'branch', 'created_by').all()
    if q:
        qs = qs.filter(
            Q(invoice_number__icontains=q) |
            Q(customer__full_name__icontains=q)
        )
    return render(request, 'spares/counter_sale_list.html',
                  {'counter_sales': qs, 'q': q})


@login_required
def counter_sale_detail(request, pk):
    # context: sale — CounterSale; items — CounterSaleItems; total — Decimal
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
    # context: form — CounterSaleForm; title — str
    form = CounterSaleForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        sale = form.save()
        return redirect('spares:counter_sale_detail', pk=sale.pk)
    return render(request, 'spares/counter_sale_form.html',
                  {'form': form, 'title': 'New Counter Sale'})


@login_required
def counter_sale_update(request, pk):
    # context: form — CounterSaleForm; title — str
    sale = get_object_or_404(CounterSale, pk=pk)
    form = CounterSaleForm(request.POST or None, instance=sale)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('spares:counter_sale_detail', pk=sale.pk)
    return render(request, 'spares/counter_sale_form.html',
                  {'form': form, 'title': 'Edit Counter Sale'})


# ---------------------------------------------------------------------------
# CounterSaleItem
# ---------------------------------------------------------------------------

@login_required
def counter_sale_item_create(request):
    # context: form — CounterSaleItemForm; title — str
    # Pre-fills counter_sale from GET ?cs=<pk>
    initial = {}
    if request.GET.get('cs'):
        initial['counter_sale'] = request.GET['cs']
    form = CounterSaleItemForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        item = form.save()
        return redirect('spares:counter_sale_detail', pk=item.counter_sale_id)
    return render(request, 'spares/counter_sale_item_form.html',
                  {'form': form, 'title': 'Add Sale Item'})


@login_required
@require_POST
def counter_sale_item_delete(request, pk):
    # POST only — deletes a CounterSaleItem
    item    = get_object_or_404(CounterSaleItem, pk=pk)
    sale_pk = item.counter_sale_id
    item.delete()
    return redirect('spares:counter_sale_detail', pk=sale_pk)


# ---------------------------------------------------------------------------
# SparesIssue
# ---------------------------------------------------------------------------

@login_required
def issue_list(request):
    # context: issues — filtered queryset; jobcard_filter — pk or ''
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
    # context: form — SparesIssueForm; title — str
    # Pre-fills job_card from GET ?jobcard=<pk>
    initial = {}
    if request.GET.get('jobcard'):
        initial['job_card'] = request.GET['jobcard']
    form = SparesIssueForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        issue = form.save()
        return redirect('service:jobcard_detail', pk=issue.job_card_id)
    return render(request, 'spares/spares_issue_form.html',
                  {'form': form, 'title': 'Issue Spare Part'})


@login_required
def issue_update(request, pk):
    # context: form — SparesIssueForm; title — str
    issue = get_object_or_404(SparesIssue, pk=pk)
    form  = SparesIssueForm(request.POST or None, instance=issue)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('service:jobcard_detail', pk=issue.job_card_id)
    return render(request, 'spares/spares_issue_form.html',
                  {'form': form, 'title': 'Update Spares Issue'})
