import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone

from masters.models import Warehouse, Rack, Bin, Supplier
from .models import (
    SparesItem, ItemRackBin, StockLedger,
    SupplierQuote, SupplierQuoteItem,
    PurchaseOrder, PurchaseOrderItem,
    PurchaseInvoice, PurchaseInvoiceItem,
    CounterSale, CounterSaleItem,
    CounterSaleReturn, CounterSaleReturnItem,
    SparesIssueAlteration, SparesIssueAlterationItem,
)
from .forms import (
    SparesItemForm,
    SupplierQuoteForm, SupplierQuoteItemFormSet,
    PurchaseOrderForm, PurchaseOrderItemFormSet,
    PurchaseInvoiceForm, PurchaseInvoiceItemFormSet,
    CounterSaleForm, CounterSaleItemFormSet,
    CounterSaleReturnForm, CounterSaleReturnItemFormSet,
    SparesIssueAlterationForm, SparesIssueAlterationItemFormSet,
)


# -- Dashboard ----------------------------------------------------------------

@login_required
def dashboard(request):
    def safe_count(qs):
        try:
            return qs.count()
        except Exception:
            return 0

    total_items = safe_count(SparesItem.objects.filter(is_active=True))

    try:
        low_stock = SparesItem.objects.filter(
            maintain_stock=True, is_active=True, reorder_level__gt=0
        ).count()
    except Exception:
        low_stock = 0

    today = timezone.localdate()
    counter_sales_today = safe_count(CounterSale.objects.filter(date=today))
    pending_pos = safe_count(PurchaseOrder.objects.filter(status__in=['draft', 'submitted']))
    recent_sales = CounterSale.objects.select_related('godown').order_by('-created_at')[:8]

    return render(request, 'spares/dashboard.html', {
        'total_items': total_items,
        'low_stock': low_stock,
        'counter_sales_today': counter_sales_today,
        'pending_pos': pending_pos,
        'recent_sales': recent_sales,
    })


# -- Items --------------------------------------------------------------------

@login_required
def item_list(request):
    q = request.GET.get('q', '')
    items = SparesItem.objects.select_related('category')
    if q:
        items = items.filter(
            Q(item_name__icontains=q) | Q(item_code__icontains=q) |
            Q(part_number__icontains=q) | Q(hsn_sac__icontains=q)
        )
    return render(request, 'spares/item_list.html', {'items': items, 'q': q})


@login_required
def item_detail(request, pk):
    item = get_object_or_404(SparesItem, pk=pk)
    stock = item.stock.select_related('warehouse', 'rack', 'bin').all()
    return render(request, 'spares/item_detail.html', {'item': item, 'stock': stock})


@login_required
def item_create(request):
    form = SparesItemForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        messages.success(request, f'Item {obj.item_code} created.')
        return redirect('spares:item_detail', pk=obj.pk)
    return render(request, 'spares/item_form.html', {'form': form, 'title': 'New Item'})


@login_required
def item_update(request, pk):
    obj = get_object_or_404(SparesItem, pk=pk)
    form = SparesItemForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Item updated.')
        return redirect('spares:item_detail', pk=pk)
    return render(request, 'spares/item_form.html', {'form': form, 'title': 'Edit Item', 'object': obj})


# -- Stock Report -------------------------------------------------------------

@login_required
def stock_report(request):
    ledger = StockLedger.objects.select_related(
        'item', 'warehouse', 'rack', 'bin'
    ).filter(quantity__gt=0).order_by('warehouse__name', 'item__item_name')
    warehouses = Warehouse.objects.filter(is_active=True)
    selected_wh = request.GET.get('warehouse', '')
    if selected_wh:
        ledger = ledger.filter(warehouse_id=selected_wh)
    return render(request, 'spares/stock_report.html', {
        'ledger': ledger,
        'warehouses': warehouses,
        'selected_wh': selected_wh,
    })


# -- Supplier Quotes ----------------------------------------------------------

@login_required
def quote_list(request):
    quotes = SupplierQuote.objects.select_related('supplier').order_by('-date')
    return render(request, 'spares/quote_list.html', {'quotes': quotes})


@login_required
def quote_detail(request, pk):
    quote = get_object_or_404(SupplierQuote, pk=pk)
    items = quote.items.select_related('item')
    return render(request, 'spares/quote_detail.html', {'quote': quote, 'items': items})


@login_required
def quote_create(request):
    form = SupplierQuoteForm(request.POST or None)
    formset = SupplierQuoteItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            formset.instance = obj
            formset.save()
            items = obj.items.all()
            obj.total_quantity = sum(i.quantity for i in items)
            obj.total_amount = sum(i.amount for i in items)
            obj.grand_total = obj.total_amount - obj.additional_discount_amount
            obj.save()
        messages.success(request, f'Quote {obj.quote_no} created.')
        return redirect('spares:quote_detail', pk=obj.pk)
    return render(request, 'spares/quote_form.html', {
        'form': form, 'formset': formset, 'title': 'New Supplier Quote'
    })


@login_required
def quote_update(request, pk):
    obj = get_object_or_404(SupplierQuote, pk=pk)
    form = SupplierQuoteForm(request.POST or None, instance=obj)
    formset = SupplierQuoteItemFormSet(request.POST or None, instance=obj, prefix='items')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            form.save()
            formset.save()
            items = obj.items.all()
            obj.total_quantity = sum(i.quantity for i in items)
            obj.total_amount = sum(i.amount for i in items)
            obj.grand_total = obj.total_amount - obj.additional_discount_amount
            obj.save()
        messages.success(request, 'Quote updated.')
        return redirect('spares:quote_detail', pk=pk)
    return render(request, 'spares/quote_form.html', {
        'form': form, 'formset': formset, 'title': 'Edit Quote', 'object': obj
    })


# -- Purchase Orders ----------------------------------------------------------

@login_required
def order_list(request):
    orders = PurchaseOrder.objects.select_related('supplier').order_by('-date')
    return render(request, 'spares/order_list.html', {'orders': orders})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    items = order.items.select_related('item', 'warehouse')
    return render(request, 'spares/order_detail.html', {'order': order, 'items': items})


@login_required
def order_create(request):
    form = PurchaseOrderForm(request.POST or None)
    formset = PurchaseOrderItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            formset.instance = obj
            formset.save()
            items = obj.items.all()
            obj.total_quantity = sum(i.quantity for i in items)
            obj.total_amount = sum(i.amount for i in items)
            obj.grand_total = obj.total_amount
            obj.save()
        messages.success(request, f'PO {obj.po_no} created.')
        return redirect('spares:order_detail', pk=obj.pk)
    return render(request, 'spares/order_form.html', {
        'form': form, 'formset': formset, 'title': 'New Purchase Order'
    })


@login_required
def order_update(request, pk):
    obj = get_object_or_404(PurchaseOrder, pk=pk)
    form = PurchaseOrderForm(request.POST or None, instance=obj)
    formset = PurchaseOrderItemFormSet(request.POST or None, instance=obj, prefix='items')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            form.save()
            formset.save()
            items = obj.items.all()
            obj.total_quantity = sum(i.quantity for i in items)
            obj.total_amount = sum(i.amount for i in items)
            obj.grand_total = obj.total_amount
            obj.save()
        messages.success(request, 'PO updated.')
        return redirect('spares:order_detail', pk=pk)
    return render(request, 'spares/order_form.html', {
        'form': form, 'formset': formset, 'title': 'Edit PO', 'object': obj
    })


# -- Purchase Invoices --------------------------------------------------------

@login_required
def invoice_list(request):
    invoices = PurchaseInvoice.objects.select_related('supplier').order_by('-date')
    return render(request, 'spares/invoice_list.html', {'invoices': invoices})


@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(PurchaseInvoice, pk=pk)
    items = invoice.items.select_related('item', 'warehouse', 'rack', 'bin')
    return render(request, 'spares/invoice_detail.html', {'invoice': invoice, 'items': items})


@login_required
def invoice_create(request):
    form = PurchaseInvoiceForm(request.POST or None)
    formset = PurchaseInvoiceItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            formset.instance = obj
            formset.save()
            all_items = obj.items.all()
            obj.total_quantity = sum(i.quantity for i in all_items)
            obj.total_amount = sum(i.amount for i in all_items)
            obj.total_sgst = sum(i.sgst_amount for i in all_items)
            obj.total_cgst = sum(i.cgst_amount for i in all_items)
            obj.total_taxes = obj.total_sgst + obj.total_cgst
            obj.grand_total = obj.total_amount + obj.total_taxes
            obj.save()
            if obj.status == 'submitted':
                for inv_item in all_items:
                    ledger, _ = StockLedger.objects.get_or_create(
                        item=inv_item.item,
                        warehouse=inv_item.warehouse,
                        rack=inv_item.rack,
                        bin=inv_item.bin,
                        defaults={'quantity': 0}
                    )
                    ledger.quantity += inv_item.quantity
                    ledger.save()
        messages.success(request, f'Invoice {obj.invoice_no} created.')
        return redirect('spares:invoice_detail', pk=obj.pk)
    return render(request, 'spares/invoice_form.html', {
        'form': form, 'formset': formset, 'title': 'New Purchase Invoice'
    })


# -- Counter Sales ------------------------------------------------------------

@login_required
def counter_sale_list(request):
    sales = CounterSale.objects.select_related('godown').order_by('-date')
    return render(request, 'spares/counter_sale_list.html', {'sales': sales})


@login_required
def counter_sale_detail(request, pk):
    sale = get_object_or_404(CounterSale, pk=pk)
    items = sale.items.select_related('item', 'rack', 'bin')
    return render(request, 'spares/counter_sale_detail.html', {'sale': sale, 'items': items})


@login_required
def counter_sale_create(request):
    form = CounterSaleForm(request.POST or None)
    formset = CounterSaleItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            formset.instance = obj
            formset.save()
            all_items = obj.items.all()
            obj.total_qty = sum(i.quantity for i in all_items)
            obj.total_amount = sum(i.total for i in all_items) - obj.discount_amount
            obj.save()
        messages.success(request, f'Counter sale {obj.sale_no} created.')
        return redirect('spares:counter_sale_detail', pk=obj.pk)
    return render(request, 'spares/counter_sale_form.html', {
        'form': form, 'formset': formset, 'title': 'New Counter Sale'
    })


# -- Counter Returns ----------------------------------------------------------

@login_required
def counter_return_list(request):
    returns = CounterSaleReturn.objects.select_related('original_sale').order_by('-return_date')
    return render(request, 'spares/counter_return_list.html', {'returns': returns})


@login_required
def counter_return_detail(request, pk):
    ret = get_object_or_404(CounterSaleReturn, pk=pk)
    items = ret.items.select_related('item')
    return render(request, 'spares/counter_return_detail.html', {'ret': ret, 'items': items})


@login_required
def counter_return_create(request):
    form = CounterSaleReturnForm(request.POST or None)
    formset = CounterSaleReturnItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            formset.instance = obj
            formset.save()
            all_items = obj.items.all()
            obj.total_amount = sum(i.amount for i in all_items)
            obj.save()
        messages.success(request, f'Return {obj.return_no} created.')
        return redirect('spares:counter_return_detail', pk=obj.pk)
    return render(request, 'spares/counter_return_form.html', {
        'form': form, 'formset': formset, 'title': 'New Counter Return'
    })


# -- Issue Alterations --------------------------------------------------------

@login_required
def issue_alteration_list(request):
    alterations = SparesIssueAlteration.objects.select_related('godown').order_by('-date')
    return render(request, 'spares/issue_alteration_list.html', {'alterations': alterations})


@login_required
def issue_alteration_detail(request, pk):
    alteration = get_object_or_404(SparesIssueAlteration, pk=pk)
    items = alteration.items.select_related('item', 'rack', 'bin')
    return render(request, 'spares/issue_alteration_detail.html', {
        'alteration': alteration, 'items': items
    })


@login_required
def issue_alteration_create(request):
    form = SparesIssueAlterationForm(request.POST or None)
    formset = SparesIssueAlterationItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            formset.instance = obj
            formset.save()
            all_items = obj.items.all()
            obj.spares_total = sum(i.total for i in all_items)
            obj.total = obj.spares_total + obj.labour_total + obj.outwork_total
            obj.updated_total = obj.total - obj.discount
            obj.save()
        messages.success(request, f'Issue alteration SIA-{obj.pk:05d} created.')
        return redirect('spares:issue_alteration_detail', pk=obj.pk)
    return render(request, 'spares/issue_alteration_form.html', {
        'form': form, 'formset': formset, 'title': 'New Issue Alteration'
    })


# -- AJAX ---------------------------------------------------------------------

@login_required
def ajax_item_details(request):
    item_id = request.GET.get('item_id')
    if not item_id:
        return JsonResponse({'error': 'No item_id'}, status=400)
    try:
        item = SparesItem.objects.get(pk=item_id)
        return JsonResponse({
            'rate': float(item.standard_selling_rate),
            'mrp': float(item.mrp),
            'sgst': float(item.sgst),
            'cgst': float(item.cgst),
            'uom': item.uom,
            'hsn': item.hsn_sac,
        })
    except SparesItem.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)


@login_required
def ajax_rack_bins(request):
    rack_id = request.GET.get('rack_id')
    if not rack_id:
        return JsonResponse({'bins': []})
    bins = list(Bin.objects.filter(rack_id=rack_id).values('id', 'name'))
    return JsonResponse({'bins': bins})


# ---------------------------------------------------------------------------
# GAP 13: Bulk Insert (CSV)
# ---------------------------------------------------------------------------

@login_required
def bulk_insert(request):
    import csv
    from io import TextIOWrapper, StringIO
    from decimal import Decimal, InvalidOperation

    results = None
    if request.method == 'POST' and request.FILES.get('file'):
        f = request.FILES['file']
        name = (f.name or '').lower()
        rows = []
        errors = []
        imported = []
        try:
            if name.endswith('.csv') or name.endswith('.txt'):
                text = TextIOWrapper(f.file, encoding='utf-8-sig', errors='ignore')
                reader = csv.DictReader(text)
                rows = list(reader)
            elif name.endswith('.xlsx') or name.endswith('.xls'):
                try:
                    from openpyxl import load_workbook
                    wb = load_workbook(f, read_only=True, data_only=True)
                    ws = wb.active
                    headers = None
                    for r in ws.iter_rows(values_only=True):
                        if headers is None:
                            headers = [str(c).strip() if c is not None else '' for c in r]
                            continue
                        if all(c is None for c in r):
                            continue
                        rows.append({headers[i]: r[i] for i in range(len(headers))})
                except ImportError:
                    errors.append({'row': 0, 'error': 'openpyxl not installed; please upload CSV.'})
            else:
                errors.append({'row': 0, 'error': 'Unsupported file type. Use .csv or .xlsx'})
        except Exception as exc:
            errors.append({'row': 0, 'error': f'Could not read file: {exc}'})

        def D(v, default='0'):
            if v in (None, ''):
                return Decimal(default)
            try:
                return Decimal(str(v).strip())
            except (InvalidOperation, ValueError):
                return Decimal(default)

        for idx, row in enumerate(rows, start=2):
            try:
                row = {(k or '').strip().lower(): v for k, v in row.items()}
                name_v = (row.get('item_name') or '').strip()
                if not name_v:
                    errors.append({'row': idx, 'error': 'item_name is required'})
                    continue
                part_no = (row.get('part_number') or '').strip()
                hsn = (row.get('hsn_sac') or '').strip()
                category = (row.get('category') or '').strip()

                item = SparesItem(
                    item_name=name_v,
                    part_number=part_no,
                    hsn_sac=hsn,
                    mrp=D(row.get('mrp')),
                    standard_selling_rate=D(row.get('selling_rate')),
                    sgst=D(row.get('sgst'), '9'),
                    cgst=D(row.get('cgst'), '9'),
                    reorder_level=D(row.get('reorder_level')),
                )
                item.save()
                if category:
                    try:
                        from masters.models import SparesCategory
                        cat, _ = SparesCategory.objects.get_or_create(name=category)
                        item.category = cat
                        item.save(update_fields=['category'])
                    except Exception:
                        pass
                imported.append({'row': idx, 'item_code': item.item_code, 'name': item.item_name})
            except Exception as exc:
                errors.append({'row': idx, 'error': str(exc)})

        results = {
            'total': len(rows),
            'imported': imported,
            'errors': errors,
            'imported_count': len(imported),
            'error_count': len(errors),
        }
        if imported:
            messages.success(request, f"{len(imported)} items imported successfully.")
        if errors:
            messages.warning(request, f"{len(errors)} rows had errors.")

    return render(request, 'spares/bulk_insert.html', {'results': results})


# ---------------------------------------------------------------------------
# GAP 21 — PO Used Qty Report
# ---------------------------------------------------------------------------

@login_required
def po_used_qty_report(request):
    from .models import (CounterSaleItem, PurchaseOrder, PurchaseOrderItem,
                         SparesIssueAlterationItem)

    rows = []
    for poi in PurchaseOrderItem.objects.select_related('order__supplier', 'item').order_by('-order__date'):
        item_id = poi.item_id
        ordered = poi.quantity or 0
        used_in_service = SparesIssueAlterationItem.objects.filter(
            item_id=item_id
        ).aggregate(t=Sum('quantity'))['t'] or 0
        sold_counter = CounterSaleItem.objects.filter(
            item_id=item_id
        ).aggregate(t=Sum('quantity'))['t'] or 0
        consumed = (used_in_service or 0) + (sold_counter or 0)
        remaining = (ordered or 0) - consumed
        rows.append({
            'po_no': poi.order.po_no,
            'supplier': poi.order.supplier.name if poi.order.supplier else '—',
            'item': poi.item,
            'ordered': ordered,
            'used_service': used_in_service,
            'sold_counter': sold_counter,
            'remaining': remaining,
        })
    return render(request, 'spares/po_used_qty_report.html', {'rows': rows})
