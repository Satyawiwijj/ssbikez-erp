from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from accounts.audit import log_action

from .forms import FinanceLoanForm, InsurancePolicyForm, InvoiceForm, PaymentForm
from .models import FinanceLoan, InsurancePolicy, Invoice, Payment


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    def safe_count(qs):
        try:
            return qs.count()
        except Exception:
            return 0

    total_invoices = safe_count(Invoice.objects.all())
    total_revenue  = Invoice.objects.aggregate(t=Sum('final_amount'))['t'] or 0
    total_loans    = safe_count(FinanceLoan.objects.all())
    total_policies = safe_count(InsurancePolicy.objects.all())
    recent_invoices = Invoice.objects.select_related('sales_order__customer').order_by('-invoice_date')[:10]

    return render(request, 'billing/dashboard.html', {
        'total_invoices': total_invoices,
        'total_revenue':  total_revenue,
        'total_loans':    total_loans,
        'total_policies': total_policies,
        'recent_invoices': recent_invoices,
    })


# ---------------------------------------------------------------------------
# FinanceLoan list
# ---------------------------------------------------------------------------

@login_required
def loan_list(request):
    loans = FinanceLoan.objects.select_related('sales_order__customer').order_by('-created_at')
    return render(request, 'billing/loan_list.html', {'loans': loans})


@login_required
def invoice_list(request):
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
    invoice    = get_object_or_404(
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
    initial = {}
    if request.GET.get('order'):
        initial['sales_order'] = request.GET['order']
    form = InvoiceForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        invoice = form.save()
        log_action(request, 'Invoice', 'create', invoice.pk)
        messages.success(request, 'Invoice created successfully.')
        return redirect('billing:invoice_detail', pk=invoice.pk)
    return render(request, 'billing/invoice_form.html', {'form': form, 'title': 'Create Invoice'})


@login_required
def invoice_update(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    form    = InvoiceForm(request.POST or None, instance=invoice)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Invoice', 'update', pk)
        messages.success(request, 'Invoice updated successfully.')
        return redirect('billing:invoice_detail', pk=invoice.pk)
    return render(request, 'billing/invoice_form.html', {'form': form, 'title': 'Edit Invoice'})


@login_required
def payment_create(request):
    initial = {}
    if request.GET.get('invoice'):
        initial['invoice'] = request.GET['invoice']
    form = PaymentForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        payment = form.save()
        log_action(request, 'Payment', 'create', payment.pk)
        messages.success(request, 'Payment recorded successfully.')
        return redirect('billing:invoice_detail', pk=payment.invoice_id)
    return render(request, 'billing/payment_form.html', {'form': form, 'title': 'Add Payment'})


@login_required
def payment_update(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    form    = PaymentForm(request.POST or None, instance=payment)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Payment', 'update', pk)
        messages.success(request, 'Payment updated successfully.')
        return redirect('billing:invoice_detail', pk=payment.invoice_id)
    return render(request, 'billing/payment_form.html', {'form': form, 'title': 'Edit Payment'})


@login_required
def payment_list(request, invoice_pk):
    invoice  = get_object_or_404(Invoice, pk=invoice_pk)
    payments = invoice.payments.all()
    return render(request, 'billing/invoice_detail.html', {
        'invoice':  invoice,
        'payments': payments,
    })


@login_required
def insurance_policy_list(request):
    q  = request.GET.get('q', '').strip()
    qs = InsurancePolicy.objects.select_related('sales_order__customer').all()
    if q:
        qs = qs.filter(
            Q(policy_number__icontains=q) |
            Q(provider_name__icontains=q) |
            Q(sales_order__customer__full_name__icontains=q)
        )
    return render(request, 'billing/insurance_policy_list.html', {'policies': qs, 'q': q})


@login_required
def insurance_policy_detail(request, pk):
    policy = get_object_or_404(
        InsurancePolicy.objects.select_related('sales_order__customer'), pk=pk
    )
    return render(request, 'billing/insurance_policy_detail.html', {'policy': policy})


@login_required
def insurance_policy_create(request):
    initial = {}
    if request.GET.get('order'):
        initial['sales_order'] = request.GET['order']
    form = InsurancePolicyForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        policy = form.save()
        log_action(request, 'Insurance Policy', 'create', policy.pk)
        messages.success(request, 'Insurance policy added successfully.')
        return redirect('billing:insurance_policy_detail', pk=policy.pk)
    return render(request, 'billing/insurance_policy_form.html',
                  {'form': form, 'title': 'Add Insurance Policy'})


@login_required
def insurance_policy_update(request, pk):
    policy = get_object_or_404(InsurancePolicy, pk=pk)
    form   = InsurancePolicyForm(request.POST or None, instance=policy)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Insurance Policy', 'update', pk)
        messages.success(request, 'Insurance policy updated successfully.')
        return redirect('billing:insurance_policy_detail', pk=policy.pk)
    return render(request, 'billing/insurance_policy_form.html',
                  {'form': form, 'title': 'Edit Insurance Policy'})


@login_required
def loan_create(request):
    initial = {}
    if request.GET.get('order'):
        initial['sales_order'] = request.GET['order']
    form = FinanceLoanForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        loan = form.save()
        log_action(request, 'Finance Loan', 'create', loan.pk)
        messages.success(request, 'Finance loan added successfully.')
        return redirect('billing:loan_detail', pk=loan.pk)
    return render(request, 'billing/loan_form.html', {'form': form, 'title': 'Add Finance Loan'})


@login_required
def loan_update(request, pk):
    loan = get_object_or_404(FinanceLoan, pk=pk)
    form = FinanceLoanForm(request.POST or None, instance=loan)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Finance Loan', 'update', pk)
        messages.success(request, 'Finance loan updated successfully.')
        return redirect('billing:loan_detail', pk=loan.pk)
    return render(request, 'billing/loan_form.html', {'form': form, 'title': 'Edit Finance Loan'})


@login_required
def loan_detail(request, pk):
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
