from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from .forms import FinanceLoanForm, InvoiceForm, PaymentForm
from .models import FinanceLoan, Invoice, Payment


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------

@login_required
def invoice_list(request):
    # context: invoices — filtered queryset; q — search string
    q  = request.GET.get('q', '').strip()
    qs = Invoice.objects.select_related('sales_order__customer').all()
    if q:
        qs = qs.filter(
            Q(invoice_number__icontains=q) |
            Q(sales_order__customer__full_name__icontains=q)
        )
    return render(request, 'billing/invoice_list.html', {'invoices': qs, 'q': q})


@login_required
def invoice_detail(request, pk):
    # context: invoice — Invoice; payments — completed Payment queryset;
    #          total_paid — Decimal; balance — Decimal
    invoice  = get_object_or_404(
        Invoice.objects.select_related('sales_order__customer'), pk=pk
    )
    payments   = invoice.payments.all()
    total_paid = payments.filter(
        payment_status=Payment.PaymentStatus.COMPLETED
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    balance    = invoice.final_amount - total_paid
    return render(request, 'billing/invoice_detail.html', {
        'invoice':    invoice,
        'payments':   payments,
        'total_paid': total_paid,
        'balance':    balance,
    })


@login_required
def invoice_create(request):
    # context: form — InvoiceForm; title — str
    # Pre-fills sales_order from GET ?order=<pk>
    initial = {}
    if request.GET.get('order'):
        initial['sales_order'] = request.GET['order']
    form = InvoiceForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        invoice = form.save()
        return redirect('billing:invoice_detail', pk=invoice.pk)
    return render(request, 'billing/invoice_form.html', {'form': form, 'title': 'Create Invoice'})


@login_required
def invoice_update(request, pk):
    # context: form — InvoiceForm; title — str
    invoice = get_object_or_404(Invoice, pk=pk)
    form    = InvoiceForm(request.POST or None, instance=invoice)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('billing:invoice_detail', pk=invoice.pk)
    return render(request, 'billing/invoice_form.html', {'form': form, 'title': 'Edit Invoice'})


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------

@login_required
def payment_create(request):
    # context: form — PaymentForm; title — str
    # Pre-fills invoice from GET ?invoice=<pk>
    initial = {}
    if request.GET.get('invoice'):
        initial['invoice'] = request.GET['invoice']
    form = PaymentForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        payment = form.save()
        return redirect('billing:invoice_detail', pk=payment.invoice_id)
    return render(request, 'billing/payment_form.html', {'form': form, 'title': 'Add Payment'})


@login_required
def payment_update(request, pk):
    # context: form — PaymentForm; title — str
    payment = get_object_or_404(Payment, pk=pk)
    form    = PaymentForm(request.POST or None, instance=payment)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('billing:invoice_detail', pk=payment.invoice_id)
    return render(request, 'billing/payment_form.html', {'form': form, 'title': 'Edit Payment'})


@login_required
def payment_list(request, invoice_pk):
    # context: invoice — Invoice; payments — related Payment queryset
    invoice  = get_object_or_404(Invoice, pk=invoice_pk)
    payments = invoice.payments.all()
    return render(request, 'billing/invoice_detail.html', {
        'invoice':  invoice,
        'payments': payments,
    })


# ---------------------------------------------------------------------------
# FinanceLoan
# ---------------------------------------------------------------------------

@login_required
def loan_create(request):
    # context: form — FinanceLoanForm; title — str
    # Pre-fills sales_order from GET ?order=<pk>
    initial = {}
    if request.GET.get('order'):
        initial['sales_order'] = request.GET['order']
    form = FinanceLoanForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        loan = form.save()
        return redirect('billing:loan_detail', pk=loan.pk)
    return render(request, 'billing/loan_form.html', {'form': form, 'title': 'Add Finance Loan'})


@login_required
def loan_update(request, pk):
    # context: form — FinanceLoanForm; title — str
    loan = get_object_or_404(FinanceLoan, pk=pk)
    form = FinanceLoanForm(request.POST or None, instance=loan)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('billing:loan_detail', pk=loan.pk)
    return render(request, 'billing/loan_form.html', {'form': form, 'title': 'Edit Finance Loan'})


@login_required
def loan_detail(request, pk):
    # context: loan — FinanceLoan; total_repayment — Decimal or None
    # total_repayment = loan_amount + simple interest estimate when rate & tenure available
    loan = get_object_or_404(FinanceLoan.objects.select_related('sales_order__customer'), pk=pk)
    total_repayment = None
    if loan.interest_rate is not None and loan.tenure_months:
        years           = Decimal(str(loan.tenure_months)) / Decimal('12')
        interest        = loan.loan_amount * (loan.interest_rate / Decimal('100')) * years
        total_repayment = loan.loan_amount + interest
    return render(request, 'billing/loan_detail.html', {
        'loan':            loan,
        'total_repayment': total_repayment,
    })
