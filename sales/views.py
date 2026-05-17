from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import (ExchangeVehicleForm, SalesAppointmentForm,
                    SalesFeedbackForm, SalesEnquiryForm, VehicleSalesOrderForm)
from .models import (ExchangeVehicle, SalesAppointment, SalesFeedback,
                     SalesEnquiry, VehicleSalesOrder)


# ---------------------------------------------------------------------------
# SalesEnquiry
# ---------------------------------------------------------------------------

@login_required
def enquiry_list(request):
    # context: enquiries — filtered queryset; q — search string; status_filter — active tab
    q             = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    qs = SalesEnquiry.objects.select_related('customer', 'bike_model', 'sales_executive').all()
    if q:
        qs = qs.filter(
            Q(customer__full_name__icontains=q) | Q(customer__phone__icontains=q)
        )
    if status_filter:
        qs = qs.filter(status=status_filter)
    return render(request, 'sales/enquiry_list.html', {
        'enquiries':     qs,
        'q':             q,
        'status_filter': status_filter,
        'status_choices': SalesEnquiry.Status.choices,
    })


@login_required
def enquiry_detail(request, pk):
    # context: enquiry — SalesEnquiry; appointments — related apt queryset;
    #          feedback_list — related feedback queryset; order — VehicleSalesOrder or None
    enquiry      = get_object_or_404(
        SalesEnquiry.objects.select_related('customer', 'bike_model', 'sales_executive', 'branch'),
        pk=pk
    )
    appointments  = enquiry.appointments.all()
    feedback_list = enquiry.feedback.select_related('created_by').all()
    order         = enquiry.orders.first()
    return render(request, 'sales/enquiry_detail.html', {
        'enquiry':      enquiry,
        'appointments': appointments,
        'feedback_list': feedback_list,
        'order':        order,
    })


@login_required
def enquiry_create(request):
    # context: form — SalesEnquiryForm; title — str
    form = SalesEnquiryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        enquiry = form.save()
        return redirect('sales:enquiry_detail', pk=enquiry.pk)
    return render(request, 'sales/enquiry_form.html', {'form': form, 'title': 'New Enquiry'})


@login_required
def enquiry_update(request, pk):
    # context: form — SalesEnquiryForm; title — str
    enquiry = get_object_or_404(SalesEnquiry, pk=pk)
    form    = SalesEnquiryForm(request.POST or None, instance=enquiry)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('sales:enquiry_detail', pk=enquiry.pk)
    return render(request, 'sales/enquiry_form.html', {'form': form, 'title': 'Edit Enquiry'})


@login_required
@require_POST
def enquiry_status_update(request, pk):
    # POST only — updates status field only, redirects back to detail
    enquiry = get_object_or_404(SalesEnquiry, pk=pk)
    new_status = request.POST.get('status')
    if new_status in dict(SalesEnquiry.Status.choices):
        enquiry.status = new_status
        enquiry.save(update_fields=['status'])
    return redirect('sales:enquiry_detail', pk=enquiry.pk)


# ---------------------------------------------------------------------------
# SalesAppointment
# ---------------------------------------------------------------------------

@login_required
def appointment_list(request, enquiry_pk):
    # context: enquiry — SalesEnquiry; appointments — related queryset
    enquiry      = get_object_or_404(SalesEnquiry, pk=enquiry_pk)
    appointments = enquiry.appointments.all()
    return render(request, 'sales/enquiry_detail.html', {
        'enquiry':      enquiry,
        'appointments': appointments,
    })


@login_required
def appointment_create(request):
    # context: form — SalesAppointmentForm; title — str
    # Pre-fills enquiry from GET ?enquiry=<pk>
    initial = {}
    enquiry_pk = request.GET.get('enquiry')
    if enquiry_pk:
        initial['enquiry'] = enquiry_pk
    form = SalesAppointmentForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        apt = form.save()
        return redirect('sales:enquiry_detail', pk=apt.enquiry_id)
    return render(request, 'sales/appointment_form.html',
                  {'form': form, 'title': 'Add Appointment'})


@login_required
def appointment_update(request, pk):
    # context: form — SalesAppointmentForm; title — str
    apt  = get_object_or_404(SalesAppointment, pk=pk)
    form = SalesAppointmentForm(request.POST or None, instance=apt)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('sales:enquiry_detail', pk=apt.enquiry_id)
    return render(request, 'sales/appointment_form.html',
                  {'form': form, 'title': 'Edit Appointment'})


@login_required
@require_POST
def appointment_cancel(request, pk):
    # POST only — sets appointment status to cancelled
    apt        = get_object_or_404(SalesAppointment, pk=pk)
    apt.status = SalesAppointment.Status.CANCELLED
    apt.save(update_fields=['status'])
    return redirect('sales:enquiry_detail', pk=apt.enquiry_id)


# ---------------------------------------------------------------------------
# SalesFeedback
# ---------------------------------------------------------------------------

@login_required
def feedback_create(request):
    # context: form — SalesFeedbackForm; title — str
    # Pre-fills enquiry from GET ?enquiry=<pk>
    initial = {}
    enquiry_pk = request.GET.get('enquiry')
    if enquiry_pk:
        initial['enquiry'] = enquiry_pk
    form = SalesFeedbackForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        fb = form.save()
        return redirect('sales:enquiry_detail', pk=fb.enquiry_id)
    return render(request, 'sales/feedback_form.html',
                  {'form': form, 'title': 'Add Feedback'})


@login_required
def feedback_list(request, enquiry_pk):
    # context: enquiry — SalesEnquiry; feedback_list — related feedback queryset
    enquiry       = get_object_or_404(SalesEnquiry, pk=enquiry_pk)
    feedback_list = enquiry.feedback.select_related('created_by').all()
    return render(request, 'sales/enquiry_detail.html', {
        'enquiry':       enquiry,
        'feedback_list': feedback_list,
    })


# ---------------------------------------------------------------------------
# VehicleSalesOrder
# ---------------------------------------------------------------------------

@login_required
def order_list(request):
    # context: orders — filtered queryset; q — search string; status_filter — active filter
    q             = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    qs = VehicleSalesOrder.objects.select_related(
        'customer', 'vehicle__bike_model', 'sales_executive'
    ).all()
    if q:
        qs = qs.filter(
            Q(customer__full_name__icontains=q) | Q(customer__phone__icontains=q)
        )
    if status_filter:
        qs = qs.filter(sales_status=status_filter)
    return render(request, 'sales/order_list.html', {
        'orders':         qs,
        'q':              q,
        'status_filter':  status_filter,
        'status_choices': VehicleSalesOrder.SalesStatus.choices,
    })


@login_required
def order_detail(request, pk):
    # context: order — VehicleSalesOrder; invoice — Invoice or None;
    #          loan — FinanceLoan or None; exchange — ExchangeVehicle or None;
    #          rto — RTORegistration or None
    order = get_object_or_404(
        VehicleSalesOrder.objects.select_related(
            'customer', 'vehicle__bike_model', 'sales_executive', 'branch', 'enquiry'
        ),
        pk=pk
    )
    invoice  = getattr(order, 'invoice',          None)
    loan     = getattr(order, 'loan',             None)
    exchange = getattr(order, 'exchange_vehicle', None)
    rto      = getattr(order, 'rto_registration', None)
    return render(request, 'sales/order_detail.html', {
        'order':   order,
        'invoice': invoice,
        'loan':    loan,
        'exchange': exchange,
        'rto':     rto,
    })


@login_required
def order_create(request):
    # context: form — VehicleSalesOrderForm; title — str
    # Pre-fills customer and enquiry from GET params ?customer=<pk>&enquiry=<pk>
    initial = {}
    if request.GET.get('customer'):
        initial['customer'] = request.GET['customer']
    if request.GET.get('enquiry'):
        initial['enquiry'] = request.GET['enquiry']
    form = VehicleSalesOrderForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        order = form.save()
        return redirect('sales:order_detail', pk=order.pk)
    return render(request, 'sales/order_form.html', {'form': form, 'title': 'Create Sales Order'})


@login_required
def order_update(request, pk):
    # context: form — VehicleSalesOrderForm; title — str
    order = get_object_or_404(VehicleSalesOrder, pk=pk)
    form  = VehicleSalesOrderForm(request.POST or None, instance=order)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('sales:order_detail', pk=order.pk)
    return render(request, 'sales/order_form.html', {'form': form, 'title': 'Edit Sales Order'})


# ---------------------------------------------------------------------------
# ExchangeVehicle
# ---------------------------------------------------------------------------

@login_required
def exchange_create(request):
    # context: form — ExchangeVehicleForm; title — str
    # Pre-fills sales_order from GET ?sales_order=<pk>
    initial = {}
    if request.GET.get('sales_order'):
        initial['sales_order'] = request.GET['sales_order']
    form = ExchangeVehicleForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        exchange = form.save()
        return redirect('sales:order_detail', pk=exchange.sales_order_id)
    return render(request, 'sales/exchange_form.html',
                  {'form': form, 'title': 'Add Exchange Vehicle'})


@login_required
def exchange_update(request, pk):
    # context: form — ExchangeVehicleForm; title — str
    exchange = get_object_or_404(ExchangeVehicle, pk=pk)
    form     = ExchangeVehicleForm(request.POST or None, instance=exchange)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('sales:order_detail', pk=exchange.sales_order_id)
    return render(request, 'sales/exchange_form.html',
                  {'form': form, 'title': 'Edit Exchange Vehicle'})
