from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.audit import log_action
from service.models import JobCard
from vas.models import AMCPackage, ProtectionPlusPackage, RSAPackage

from .forms import CustomerVehicleForm
from .models import CustomerVehicle


@login_required
def customervehicle_list(request):
    q = request.GET.get('q', '').strip()
    qs = CustomerVehicle.objects.select_related(
        'customer', 'vehicle__bike_model'
    ).all()
    if q:
        qs = qs.filter(
            Q(customer__full_name__icontains=q) |
            Q(customer__phone__icontains=q) |
            Q(registration_no__icontains=q)
        )
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'customer_vehicles/customervehicle_list.html',
                  {'customer_vehicles': page_obj, 'page_obj': page_obj, 'q': q})


@login_required
def customervehicle_detail(request, pk):
    from decimal import Decimal
    cv = get_object_or_404(
        CustomerVehicle.objects.select_related('customer', 'vehicle__bike_model', 'vehicle__branch'),
        pk=pk
    )
    job_cards     = list(JobCard.objects.filter(customer_vehicle=cv).select_related('service_advisor', 'branch').order_by('-created_at'))
    amc_packages  = list(AMCPackage.objects.filter(customer_vehicle=cv))
    rsa_packages  = list(RSAPackage.objects.filter(customer_vehicle=cv))
    protection_plus = list(ProtectionPlusPackage.objects.filter(customer_vehicle=cv))

    # Financials from related sales order
    from sales.models import VehicleSalesOrder
    from billing.models import Invoice, FinanceLoan, InsurancePolicy, Payment
    from django.db.models import Sum

    sales_order = VehicleSalesOrder.objects.filter(vehicle=cv.vehicle).select_related('customer').first()
    invoice     = None
    loan        = None
    policies    = []
    payments    = []
    total_paid  = Decimal('0')
    balance     = Decimal('0')

    if sales_order:
        invoice = sales_order.current_invoice
        try:
            loan = sales_order.loan
        except Exception:
            loan = None
        policies = list(sales_order.insurance_policies.all())
        if invoice:
            payments   = list(invoice.payments.filter(payment_status='completed').order_by('payment_date'))
            total_paid = sum((p.amount for p in payments), Decimal('0'))
            balance    = invoice.final_amount - total_paid

    from django.utils import timezone
    return render(request, 'customer_vehicles/customervehicle_detail.html', {
        'cv':              cv,
        'job_cards':       job_cards,
        'amc_packages':    amc_packages,
        'rsa_packages':    rsa_packages,
        'protection_plus': protection_plus,
        'sales_order':     sales_order,
        'invoice':         invoice,
        'loan':            loan,
        'policies':        policies,
        'payments':        payments,
        'total_paid':      total_paid,
        'balance':         balance,
        'today':           timezone.now().date(),
    })


@login_required
def customervehicle_create(request):
    form = CustomerVehicleForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cv = form.save()
        log_action(request, 'Customer Vehicle', 'create', cv.pk)
        messages.success(request, 'Customer vehicle added successfully.')
        return redirect('customer_vehicles:customervehicle_detail', pk=cv.pk)
    return render(request, 'customer_vehicles/customervehicle_form.html',
                  {'form': form, 'title': 'Add Customer Vehicle'})


@login_required
def customervehicle_update(request, pk):
    cv   = get_object_or_404(CustomerVehicle, pk=pk)
    form = CustomerVehicleForm(request.POST or None, instance=cv)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Customer Vehicle', 'update', pk)
        messages.success(request, 'Customer vehicle updated successfully.')
        return redirect('customer_vehicles:customervehicle_detail', pk=cv.pk)
    return render(request, 'customer_vehicles/customervehicle_form.html',
                  {'form': form, 'title': 'Edit Customer Vehicle'})
