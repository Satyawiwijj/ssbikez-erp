from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.audit import log_action

from .forms import (ExchangeVehicleForm, SalesAppointmentForm, SalesFeedbackForm,
                    SalesEnquiryForm, VehicleDeliveryForm, VehicleSalesOrderForm)
from .models import (ExchangeVehicle, SalesAppointment, SalesFeedback,
                     SalesEnquiry, VehicleDelivery, VehicleSalesOrder)


# ---------------------------------------------------------------------------
# SalesEnquiry
# ---------------------------------------------------------------------------

@login_required
def enquiry_list(request):
    q             = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    qs = SalesEnquiry.objects.select_related(
        'customer', 'bike_model', 'sales_executive', 'branch'
    ).all()
    if q:
        qs = qs.filter(
            Q(customer__full_name__icontains=q) | Q(customer__phone__icontains=q)
        )
    if status_filter:
        qs = qs.filter(status=status_filter)
    paginator = Paginator(qs, 25)
    page_obj  = paginator.get_page(request.GET.get('page'))
    return render(request, 'sales/enquiry_list.html', {
        'enquiries':      page_obj,
        'page_obj':       page_obj,
        'q':              q,
        'status_filter':  status_filter,
        'status_choices': SalesEnquiry.Status.choices,
    })


@login_required
def enquiry_detail(request, pk):
    enquiry       = get_object_or_404(
        SalesEnquiry.objects.select_related('customer', 'bike_model', 'sales_executive', 'branch'),
        pk=pk
    )
    appointments  = enquiry.appointments.all()
    feedback_list = enquiry.feedback.select_related('created_by').all()
    order         = enquiry.orders.first()
    return render(request, 'sales/enquiry_detail.html', {
        'enquiry':       enquiry,
        'appointments':  appointments,
        'feedback_list': feedback_list,
        'order':         order,
    })


@login_required
def enquiry_create(request):
    form = SalesEnquiryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        enquiry = form.save()
        log_action(request, 'Sales Enquiry', 'create', enquiry.pk)
        messages.success(request, 'Enquiry created successfully.')
        return redirect('sales:enquiry_detail', pk=enquiry.pk)
    return render(request, 'sales/enquiry_form.html', {'form': form, 'title': 'New Enquiry'})


@login_required
def enquiry_update(request, pk):
    enquiry = get_object_or_404(SalesEnquiry, pk=pk)
    form    = SalesEnquiryForm(request.POST or None, instance=enquiry)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Sales Enquiry', 'update', pk)
        messages.success(request, 'Enquiry updated successfully.')
        return redirect('sales:enquiry_detail', pk=enquiry.pk)
    return render(request, 'sales/enquiry_form.html', {'form': form, 'title': 'Edit Enquiry'})


@login_required
@require_POST
def enquiry_status_update(request, pk):
    enquiry    = get_object_or_404(SalesEnquiry, pk=pk)
    new_status = request.POST.get('status')
    if new_status in dict(SalesEnquiry.Status.choices):
        enquiry.status = new_status
        enquiry.save(update_fields=['status'])
        log_action(request, 'Sales Enquiry', 'update', pk)
        messages.success(request, f'Enquiry status updated to {enquiry.get_status_display()}.')
    return redirect('sales:enquiry_detail', pk=enquiry.pk)


# ---------------------------------------------------------------------------
# SalesAppointment
# ---------------------------------------------------------------------------

@login_required
def appointment_list(request, enquiry_pk):
    enquiry      = get_object_or_404(SalesEnquiry, pk=enquiry_pk)
    appointments = enquiry.appointments.all()
    return render(request, 'sales/enquiry_detail.html', {
        'enquiry':      enquiry,
        'appointments': appointments,
    })


@login_required
def appointment_create(request):
    initial    = {}
    enquiry_pk = request.GET.get('enquiry')
    if enquiry_pk:
        initial['enquiry'] = enquiry_pk
    form = SalesAppointmentForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        apt = form.save()
        log_action(request, 'Sales Appointment', 'create', apt.pk)
        messages.success(request, 'Appointment scheduled successfully.')
        return redirect('sales:enquiry_detail', pk=apt.enquiry_id)
    return render(request, 'sales/appointment_form.html',
                  {'form': form, 'title': 'Add Appointment'})


@login_required
def appointment_update(request, pk):
    apt  = get_object_or_404(SalesAppointment, pk=pk)
    form = SalesAppointmentForm(request.POST or None, instance=apt)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Sales Appointment', 'update', pk)
        messages.success(request, 'Appointment updated successfully.')
        return redirect('sales:enquiry_detail', pk=apt.enquiry_id)
    return render(request, 'sales/appointment_form.html',
                  {'form': form, 'title': 'Edit Appointment'})


@login_required
@require_POST
def appointment_cancel(request, pk):
    apt        = get_object_or_404(SalesAppointment, pk=pk)
    apt.status = SalesAppointment.Status.CANCELLED
    apt.save(update_fields=['status'])
    log_action(request, 'Sales Appointment', 'update', pk)
    messages.success(request, 'Appointment cancelled.')
    return redirect('sales:enquiry_detail', pk=apt.enquiry_id)


# ---------------------------------------------------------------------------
# SalesFeedback
# ---------------------------------------------------------------------------

@login_required
def feedback_create(request):
    initial    = {}
    enquiry_pk = request.GET.get('enquiry')
    if enquiry_pk:
        initial['enquiry'] = enquiry_pk
    form = SalesFeedbackForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        fb = form.save()
        log_action(request, 'Sales Feedback', 'create', fb.pk)
        messages.success(request, 'Feedback recorded successfully.')
        return redirect('sales:enquiry_detail', pk=fb.enquiry_id)
    return render(request, 'sales/feedback_form.html',
                  {'form': form, 'title': 'Add Feedback'})


@login_required
def feedback_list(request, enquiry_pk):
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
    q             = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    qs = VehicleSalesOrder.objects.select_related(
        'customer', 'vehicle__bike_model', 'sales_executive', 'branch'
    ).all()
    if q:
        qs = qs.filter(
            Q(customer__full_name__icontains=q) | Q(customer__phone__icontains=q)
        )
    if status_filter:
        qs = qs.filter(sales_status=status_filter)
    paginator = Paginator(qs, 25)
    page_obj  = paginator.get_page(request.GET.get('page'))
    return render(request, 'sales/order_list.html', {
        'orders':         page_obj,
        'page_obj':       page_obj,
        'q':              q,
        'status_filter':  status_filter,
        'status_choices': VehicleSalesOrder.SalesStatus.choices,
    })


@login_required
def order_detail(request, pk):
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
    delivery = getattr(order, 'delivery',         None)
    policies = order.insurance_policies.all()
    return render(request, 'sales/order_detail.html', {
        'order':    order,
        'invoice':  invoice,
        'loan':     loan,
        'exchange': exchange,
        'rto':      rto,
        'delivery': delivery,
        'policies': policies,
    })


@login_required
def order_create(request):
    initial = {}
    if request.GET.get('customer'):
        initial['customer'] = request.GET['customer']
    if request.GET.get('enquiry'):
        initial['enquiry'] = request.GET['enquiry']
    form = VehicleSalesOrderForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        order = form.save()
        log_action(request, 'Sales Order', 'create', order.pk)
        messages.success(request, 'Sales order created successfully.')
        return redirect('sales:order_detail', pk=order.pk)
    return render(request, 'sales/order_form.html', {'form': form, 'title': 'Create Sales Order'})


@login_required
def order_update(request, pk):
    order = get_object_or_404(VehicleSalesOrder, pk=pk)
    form  = VehicleSalesOrderForm(request.POST or None, instance=order)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Sales Order', 'update', pk)
        messages.success(request, 'Sales order updated successfully.')
        return redirect('sales:order_detail', pk=order.pk)
    return render(request, 'sales/order_form.html', {'form': form, 'title': 'Edit Sales Order'})


# ---------------------------------------------------------------------------
# VehicleDelivery
# ---------------------------------------------------------------------------

@login_required
def delivery_create(request):
    initial = {}
    if request.GET.get('order'):
        initial['sales_order'] = request.GET['order']
    form = VehicleDeliveryForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        delivery = form.save()
        log_action(request, 'Vehicle Delivery', 'create', delivery.pk)
        messages.success(request, 'Delivery recorded successfully.')
        return redirect('sales:order_detail', pk=delivery.sales_order_id)
    return render(request, 'sales/delivery_form.html',
                  {'form': form, 'title': 'Record Vehicle Delivery'})


@login_required
def delivery_update(request, pk):
    delivery = get_object_or_404(VehicleDelivery, pk=pk)
    form     = VehicleDeliveryForm(request.POST or None, instance=delivery)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Vehicle Delivery', 'update', pk)
        messages.success(request, 'Delivery updated successfully.')
        return redirect('sales:order_detail', pk=delivery.sales_order_id)
    return render(request, 'sales/delivery_form.html',
                  {'form': form, 'title': 'Edit Vehicle Delivery'})


@login_required
def delivery_detail(request, pk):
    delivery = get_object_or_404(
        VehicleDelivery.objects.select_related('sales_order__customer', 'delivered_by'), pk=pk
    )
    return render(request, 'sales/delivery_detail.html', {'delivery': delivery})


# ---------------------------------------------------------------------------
# ExchangeVehicle
# ---------------------------------------------------------------------------

@login_required
def exchange_create(request):
    initial = {}
    if request.GET.get('sales_order'):
        initial['sales_order'] = request.GET['sales_order']
    form = ExchangeVehicleForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        exchange = form.save()
        log_action(request, 'Exchange Vehicle', 'create', exchange.pk)
        messages.success(request, 'Exchange vehicle recorded successfully.')
        return redirect('sales:order_detail', pk=exchange.sales_order_id)
    return render(request, 'sales/exchange_form.html',
                  {'form': form, 'title': 'Add Exchange Vehicle'})


@login_required
def exchange_update(request, pk):
    exchange = get_object_or_404(ExchangeVehicle, pk=pk)
    form     = ExchangeVehicleForm(request.POST or None, instance=exchange)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Exchange Vehicle', 'update', pk)
        messages.success(request, 'Exchange vehicle updated successfully.')
        return redirect('sales:order_detail', pk=exchange.sales_order_id)
    return render(request, 'sales/exchange_form.html',
                  {'form': form, 'title': 'Edit Exchange Vehicle'})
