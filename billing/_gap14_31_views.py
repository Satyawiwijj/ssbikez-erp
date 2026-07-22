"""GAP 14-31 billing views."""
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.permissions import require_module_action

from .forms import JournalEntryForm, JournalEntryLineFormSet, RefundAdvanceForm
from .models import Invoice, JournalEntry, JournalEntryLine, Payment, RefundAdvance


# --- GAP 16: Payment Reconciliation ----------------------------------------

@login_required
def payment_reconciliation(request):
    today = timezone.now().date()
    start_str = request.GET.get('start') or (today - timedelta(days=7)).isoformat()
    end_str = request.GET.get('end') or today.isoformat()
    try:
        start = datetime.strptime(start_str, '%Y-%m-%d').date()
        end = datetime.strptime(end_str, '%Y-%m-%d').date()
    except ValueError:
        start, end = today - timedelta(days=7), today

    payments = Payment.objects.select_related(
        'invoice__sales_order__customer'
    ).filter(payment_date__date__gte=start, payment_date__date__lte=end)

    method_totals = {}
    for m, label in Payment.Method.choices:
        qs = payments.filter(payment_method=m)
        method_totals[m] = {
            'label': label,
            'total': qs.aggregate(t=Sum('amount'))['t'] or Decimal('0'),
            'count': qs.count(),
        }
    grand_total = payments.aggregate(t=Sum('amount'))['t'] or Decimal('0')
    unreconciled = payments.filter(payment_status=Payment.PaymentStatus.PENDING)

    if request.method == 'POST' and request.POST.get('reconcile'):
        ids = request.POST.getlist('payment_ids')
        # Only reconcile payments that are actually pending AND within the
        # date range/queryset shown on this page — never trust posted ids alone.
        # Saved one-by-one (not a bulk QuerySet.update()) so each Payment's
        # save() hook fires and auto-posts its GL JournalEntry — a bulk
        # .update() bypasses save() entirely and previously left reconciled
        # payments with no General Ledger entry (see billing/tests.py
        # PaymentReconciliationPostsJournalEntryTests).
        n = 0
        for payment in unreconciled.filter(pk__in=ids):
            payment.payment_status = Payment.PaymentStatus.COMPLETED
            payment.save()
            n += 1
        messages.success(request, f'{n} payment(s) marked as completed.')
        return redirect(request.path + f'?start={start_str}&end={end_str}')

    return render(request, 'billing/payment_reconciliation.html', {
        'start': start, 'end': end,
        'payments': payments,
        'method_totals': method_totals,
        'grand_total': grand_total,
        'unreconciled': unreconciled,
    })


# --- GAP 17: Invoice Search ------------------------------------------------

@login_required
def invoice_search(request):
    invoices = Invoice.objects.select_related('sales_order__customer').all()
    q = request.GET.get('q', '').strip()
    start = request.GET.get('start', '').strip()
    end = request.GET.get('end', '').strip()
    amount_min = request.GET.get('amount_min', '').strip()
    amount_max = request.GET.get('amount_max', '').strip()

    if q:
        invoices = invoices.filter(
            Q(invoice_number__icontains=q) |
            Q(sales_order__customer__full_name__icontains=q)
        )
    if start:
        try:
            invoices = invoices.filter(invoice_date__gte=datetime.strptime(start, '%Y-%m-%d').date())
        except ValueError:
            pass
    if end:
        try:
            invoices = invoices.filter(invoice_date__lte=datetime.strptime(end, '%Y-%m-%d').date())
        except ValueError:
            pass
    if amount_min:
        try:
            invoices = invoices.filter(final_amount__gte=Decimal(amount_min))
        except Exception:
            pass
    if amount_max:
        try:
            invoices = invoices.filter(final_amount__lte=Decimal(amount_max))
        except Exception:
            pass

    invoices = invoices[:200]
    return render(request, 'billing/invoice_search.html', {
        'invoices': invoices, 'q': q, 'start': start, 'end': end,
        'amount_min': amount_min, 'amount_max': amount_max,
    })


# --- GAP 18: Refunds & Advances --------------------------------------------

@login_required
def refund_advance_list(request):
    items = RefundAdvance.objects.select_related('customer').all()[:300]
    return render(request, 'billing/refund_advance_list.html', {'items': items})


@login_required
@require_module_action('finance', 'create')
def refund_advance_create(request):
    form = RefundAdvanceForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.processed_by = request.user
        obj.save()
        messages.success(request, 'Refund/Advance recorded.')
        return redirect('billing:refund_advance_list')
    return render(request, 'billing/refund_advance_form.html', {'form': form})


@login_required
def refund_advance_detail(request, pk):
    obj = get_object_or_404(RefundAdvance.objects.select_related('customer'), pk=pk)
    return render(request, 'billing/refund_advance_detail.html', {'obj': obj})


# --- GAP 25: Journal & General Ledger --------------------------------------

@login_required
def journal_entry_list(request):
    entries = JournalEntry.objects.prefetch_related('lines')
    start = request.GET.get('start', '').strip()
    end = request.GET.get('end', '').strip()
    if start:
        try:
            entries = entries.filter(entry_date__gte=datetime.strptime(start, '%Y-%m-%d').date())
        except ValueError:
            pass
    if end:
        try:
            entries = entries.filter(entry_date__lte=datetime.strptime(end, '%Y-%m-%d').date())
        except ValueError:
            pass
    entries = entries[:300]
    return render(request, 'billing/journal_entry_list.html',
                  {'entries': entries, 'start': start, 'end': end})


@login_required
def journal_entry_detail(request, pk):
    entry = get_object_or_404(JournalEntry.objects.prefetch_related('lines'), pk=pk)
    return render(request, 'billing/journal_entry_detail.html', {'entry': entry})


@login_required
@require_module_action('finance', 'create')
def journal_entry_create(request):
    from django.db import transaction
    form = JournalEntryForm(request.POST or None)
    formset = JournalEntryLineFormSet(request.POST or None, prefix='lines')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        total_debit  = sum((f.cleaned_data.get('debit') or Decimal('0'))
                            for f in formset.forms if not f.cleaned_data.get('DELETE'))
        total_credit = sum((f.cleaned_data.get('credit') or Decimal('0'))
                            for f in formset.forms if not f.cleaned_data.get('DELETE'))
        if total_debit != total_credit:
            messages.error(
                request,
                f'Journal entry is not balanced — total debit (₹{total_debit}) '
                f'must equal total credit (₹{total_credit}).'
            )
        elif total_debit == 0:
            messages.error(request, 'Add at least one debit and one credit line.')
        else:
            with transaction.atomic():
                obj = form.save(commit=False)
                obj.created_by = request.user
                obj.save()
                formset.instance = obj
                formset.save()
            messages.success(request, 'Journal entry created.')
            return redirect('billing:journal_entry_list')
    return render(request, 'billing/journal_entry_form.html', {'form': form, 'formset': formset})


@login_required
@require_module_action('finance', 'view')
def general_ledger(request):
    lines = JournalEntryLine.objects.select_related('entry').order_by('account', 'entry__entry_date')

    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    account_filter = request.GET.get('account', '').strip()

    if from_date:
        lines = lines.filter(entry__entry_date__gte=from_date)
    if to_date:
        lines = lines.filter(entry__entry_date__lte=to_date)
    if account_filter:
        lines = lines.filter(account=account_filter)

    accounts = {}
    for line in lines:
        a = accounts.setdefault(line.account, {
            'name': line.account, 'debit': Decimal('0'),
            'credit': Decimal('0'), 'entries': [],
        })
        a['debit']  += line.debit
        a['credit'] += line.credit
        a['entries'].append(line)
    for a in accounts.values():
        a['balance'] = a['debit'] - a['credit']
    accounts_list = sorted(accounts.values(), key=lambda x: x['name'])

    all_accounts = list(
        JournalEntryLine.objects.order_by('account').values_list('account', flat=True).distinct()
    )

    return render(request, 'billing/general_ledger.html', {
        'accounts': accounts_list,
        'all_accounts': all_accounts,
        'from_date': from_date or '',
        'to_date': to_date or '',
        'selected_account': account_filter,
    })
