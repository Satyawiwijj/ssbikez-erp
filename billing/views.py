from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from accounts.audit import log_action
from accounts.permissions import require_module_action

from django.views.decorators.http import require_POST

from .forms import (FinanceLoanForm, InsurancePolicyForm, InvoiceForm,
                    InvoiceItemFormSet, PaymentForm)
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
    q = request.GET.get('q', '').strip()
    qs = FinanceLoan.objects.select_related('sales_order__customer').order_by('-created_at')
    if q:
        qs = qs.filter(
            Q(bank_name__icontains=q) |
            Q(sales_order__customer__full_name__icontains=q) |
            Q(sales_order__customer__phone__icontains=q)
        )
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'billing/loan_list.html', {'loans': page_obj, 'page_obj': page_obj, 'q': q})


@login_required
def invoice_list(request):
    q  = request.GET.get('q', '').strip()
    qs = Invoice.objects.select_related('sales_order__customer').all()
    if q:
        qs = qs.filter(
            Q(invoice_number__icontains=q) |
            Q(sales_order__customer__full_name__icontains=q)
        )
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'billing/invoice_list.html', {'invoices': page_obj, 'page_obj': page_obj, 'q': q})


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
    from .models import split_gst
    cgst_amount, sgst_amount = split_gst(invoice.gst_amount)
    return render(request, 'billing/invoice_detail.html', {
        'invoice':     invoice,
        'payments':    payments,
        'total_paid':  total_paid,
        'balance':     balance,
        'cgst_amount': cgst_amount,
        'sgst_amount': sgst_amount,
    })


@login_required
@require_module_action('finance', 'create')
def invoice_create(request):
    initial = {}
    if request.GET.get('order'):
        initial['sales_order'] = request.GET['order']
    form = InvoiceForm(request.POST or None, initial=initial)
    items_formset = InvoiceItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST':
        if form.is_valid() and items_formset.is_valid():
            invoice = form.save()
            items_formset.instance = invoice
            items_formset.save()
            log_action(request, 'Invoice', 'create', invoice.pk)
            messages.success(request, 'Invoice created successfully.')
            return redirect('billing:invoice_detail', pk=invoice.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'billing/invoice_form.html', {
        'form': form, 'title': 'Create Invoice', 'items_formset': items_formset,
    })


@login_required
@require_module_action('finance', 'edit')
def invoice_update(request, pk):
    # No ownership field exists on Invoice/Payment/Loan/InsurancePolicy —
    # "who owns a billing record" is a product decision (sales exec? branch?
    # cashier?), not something to invent here. Protected only by the
    # namespace-level role gate (RolePermissionMiddleware) for now.
    invoice = get_object_or_404(Invoice, pk=pk)
    if invoice.docstatus != Invoice.DocStatus.DRAFT:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Submitted documents cannot be edited. Cancel and amend instead.</h1>')
    form = InvoiceForm(request.POST or None, instance=invoice)
    items_formset = InvoiceItemFormSet(request.POST or None, instance=invoice, prefix='items')
    if request.method == 'POST':
        if form.is_valid() and items_formset.is_valid():
            form.save()
            items_formset.save()
            log_action(request, 'Invoice', 'update', pk)
            messages.success(request, 'Invoice updated successfully.')
            return redirect('billing:invoice_detail', pk=invoice.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'billing/invoice_form.html', {
        'form': form, 'title': 'Edit Invoice', 'items_formset': items_formset,
    })


@login_required
@require_POST
@require_module_action('finance', 'edit')
def invoice_md_approve(request, pk):
    from accounts.permissions import user_is_manager
    from django.utils import timezone
    invoice = get_object_or_404(Invoice, pk=pk)
    if not user_is_manager(request.user):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    invoice.md_approved = True
    invoice.md_approved_by = request.user
    invoice.md_approved_at = timezone.now()
    invoice.save(update_fields=['md_approved', 'md_approved_by', 'md_approved_at'])
    log_action(request, 'Invoice', 'update', pk)
    messages.success(request, 'MD approval recorded.')
    return redirect('billing:invoice_detail', pk=pk)


@login_required
@require_POST
@require_module_action('finance', 'edit')
def invoice_md_reject(request, pk):
    from accounts.permissions import user_is_manager
    invoice = get_object_or_404(Invoice, pk=pk)
    if not user_is_manager(request.user):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    invoice.md_approved = False
    invoice.md_approved_by = None
    invoice.md_approved_at = None
    invoice.save(update_fields=['md_approved', 'md_approved_by', 'md_approved_at'])
    log_action(request, 'Invoice', 'update', pk)
    messages.success(request, 'MD approval rejected.')
    return redirect('billing:invoice_detail', pk=pk)


@login_required
@require_POST
@require_module_action('finance', 'edit')
def invoice_submit(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if invoice.md_approval_requested and not invoice.md_approved:
        messages.error(request, 'MD approval is required before submitting this invoice.')
        return redirect('billing:invoice_detail', pk=pk)
    try:
        invoice.submit(request.user)
        log_action(request, 'Invoice', 'update', pk)
        messages.success(request, f'{invoice.invoice_number} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('billing:invoice_detail', pk=pk)


@login_required
@require_POST
@require_module_action('finance', 'edit')
def invoice_cancel(request, pk):
    from accounts.permissions import user_is_manager
    invoice = get_object_or_404(Invoice, pk=pk)
    if not user_is_manager(request.user):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        invoice.cancel(request.user)
        log_action(request, 'Invoice', 'update', pk)
        messages.success(request, f'{invoice.invoice_number} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('billing:invoice_detail', pk=pk)


@login_required
@require_POST
@require_module_action('finance', 'create')
def invoice_amend(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    try:
        # invoice_number is unique — the amended copy needs a fresh one
        original_number = invoice.invoice_number
        new_invoice = invoice.amend()
        new_invoice.invoice_number = f'{original_number}-AMD-{new_invoice.pk}'
        new_invoice.save(update_fields=['invoice_number'])
        for item in invoice.items.all():
            item.pk = None
            item.invoice = new_invoice
            item.save()
        log_action(request, 'Invoice', 'create', new_invoice.pk)
        messages.success(request, f'Amended as {new_invoice.invoice_number}.')
        return redirect('billing:invoice_detail', pk=new_invoice.pk)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('billing:invoice_detail', pk=pk)


@login_required
@require_module_action('finance', 'create')
def payment_create(request):
    from django.utils import timezone
    initial = {'payment_date': timezone.now().date()}
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
@require_module_action('finance', 'edit')
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


# ---------------------------------------------------------------------------
# GAP 3: Daily Collection Report
# ---------------------------------------------------------------------------

@login_required
def daily_collection_report(request):
    from datetime import datetime, date as _date
    from django.utils import timezone

    date_str = request.GET.get('date') or ''
    if date_str:
        try:
            report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            report_date = timezone.now().date()
    else:
        report_date = timezone.now().date()

    # Vehicle invoice payments for this date
    payments = Payment.objects.select_related('invoice__sales_order__customer').filter(
        payment_status=Payment.PaymentStatus.COMPLETED,
        payment_date__date=report_date,
    ).order_by('payment_date')

    # Aggregate by method
    method_totals = {}
    for m, label in Payment.Method.choices:
        method_totals[m] = {
            'label': label,
            'total': payments.filter(payment_method=m).aggregate(t=Sum('amount'))['t'] or Decimal('0'),
            'count': payments.filter(payment_method=m).count(),
        }
    vehicle_total = payments.aggregate(t=Sum('amount'))['t'] or Decimal('0')

    # Service invoices issued on this date
    service_invoices = []
    service_total = Decimal('0')
    try:
        from service.models import ServiceInvoice
        service_invoices = ServiceInvoice.objects.select_related(
            'job_card__customer_vehicle__customer'
        ).filter(invoice_date=report_date).order_by('-created_at')
        service_total = service_invoices.aggregate(t=Sum('final_amount'))['t'] or Decimal('0')
    except Exception:
        pass

    # Counter sales on this date
    counter_sales = []
    counter_total = Decimal('0')
    try:
        from spares.models import CounterSale
        counter_sales = CounterSale.objects.filter(date=report_date).order_by('-created_at')
        counter_total = counter_sales.aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
    except Exception:
        pass

    grand_total = vehicle_total + service_total + counter_total

    return render(request, 'billing/daily_collection_report.html', {
        'report_date':     report_date,
        'payments':        payments,
        'method_totals':   method_totals,
        'vehicle_total':   vehicle_total,
        'service_invoices': service_invoices,
        'service_total':   service_total,
        'counter_sales':   counter_sales,
        'counter_total':   counter_total,
        'grand_total':     grand_total,
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
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'billing/insurance_policy_list.html', {'policies': page_obj, 'page_obj': page_obj, 'q': q})


@login_required
def insurance_policy_detail(request, pk):
    policy = get_object_or_404(
        InsurancePolicy.objects.select_related('sales_order__customer'), pk=pk
    )
    return render(request, 'billing/insurance_policy_detail.html', {'policy': policy})


@login_required
@require_module_action('finance', 'create')
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
@require_module_action('finance', 'edit')
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
@require_module_action('finance', 'create')
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
@require_module_action('finance', 'edit')
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

# GAP 14-31 views
from billing._gap14_31_views import *  # noqa: E402,F401,F403

