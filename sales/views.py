import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.audit import log_action

from .forms import (ExchangeVehicleForm, SalesAppointmentForm, SalesFeedbackForm,
                    SalesEnquiryForm, VehicleDeliveryForm, VehicleSalesOrderForm)
from .models import (ExchangeVehicle, Prospect, SalesAppointment, SalesFeedback,
                     SalesEnquiry, VehicleDelivery, VehicleSalesOrder)


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

    today       = timezone.now().date()
    month_start = today.replace(day=1)

    total_enquiries  = safe_count(SalesEnquiry.objects.all())
    total_orders     = safe_count(VehicleSalesOrder.objects.all())
    open_orders      = safe_count(VehicleSalesOrder.objects.filter(sales_status='booked'))
    total_deliveries = safe_count(VehicleDelivery.objects.all())

    my_enquiries_today  = safe_count(
        SalesEnquiry.objects.filter(created_at__date=today, sales_executive=request.user)
    )
    my_open_enquiries   = safe_count(
        SalesEnquiry.objects.filter(
            status__in=['open', 'follow_up'], sales_executive=request.user
        )
    )
    my_converted_month  = safe_count(
        SalesEnquiry.objects.filter(
            status='converted', sales_executive=request.user,
            created_at__date__gte=month_start
        )
    )
    my_orders_month     = safe_count(
        VehicleSalesOrder.objects.filter(
            sales_executive=request.user, created_at__date__gte=month_start
        )
    )

    # Follow-ups for this executive
    today_followups    = _followups_for_user(request.user, 'today', today)
    overdue_followups  = _followups_for_user(request.user, 'overdue', today)
    upcoming_followups = _followups_for_user(request.user, 'upcoming', today)

    recent_enquiries = list(
        SalesEnquiry.objects
        .select_related('customer', 'prospect', 'bike_model')
        .order_by('-created_at')[:10]
    )
    recent_orders = list(
        VehicleSalesOrder.objects
        .select_related('customer', 'vehicle__bike_model')
        .order_by('-created_at')[:5]
    )

    return render(request, 'sales/dashboard.html', {
        'total_enquiries':    total_enquiries,
        'total_orders':       total_orders,
        'open_orders':        open_orders,
        'total_deliveries':   total_deliveries,
        'my_enquiries_today': my_enquiries_today,
        'my_open_enquiries':  my_open_enquiries,
        'my_converted_month': my_converted_month,
        'my_orders_month':    my_orders_month,
        'today_followups':    today_followups,
        'overdue_followups':  overdue_followups,
        'upcoming_followups': upcoming_followups,
        'recent_enquiries':   recent_enquiries,
        'recent_orders':      recent_orders,
        'today':              today,
    })


def _followups_for_user(user, period, today):
    """Helper: return SalesFeedback queryset filtered by period for given user."""
    base = SalesFeedback.objects.select_related(
        'enquiry__customer', 'enquiry__prospect', 'enquiry__bike_model',
        'enquiry__sales_executive',
    ).filter(enquiry__sales_executive=user)
    if period == 'overdue':
        return base.filter(
            next_followup_date__lt=today,
            enquiry__status__in=['open', 'follow_up'],
        ).order_by('next_followup_date')
    if period == 'today':
        return base.filter(next_followup_date=today).order_by('next_followup_date')
    if period == 'upcoming':
        return base.filter(
            next_followup_date__gt=today,
            next_followup_date__lte=today + datetime.timedelta(days=7),
        ).order_by('next_followup_date')
    return base.none()


# ---------------------------------------------------------------------------
# Follow-Up List (dedicated page)
# ---------------------------------------------------------------------------

@login_required
def follow_up_list(request):
    """Dedicated page: all follow-ups for the logged-in sales executive."""
    today  = timezone.now().date()
    period = request.GET.get('period', 'all')   # overdue | today | upcoming | all

    base = SalesFeedback.objects.select_related(
        'enquiry__customer', 'enquiry__prospect', 'enquiry__bike_model',
    ).filter(enquiry__sales_executive=request.user)

    if period == 'overdue':
        qs = base.filter(
            next_followup_date__lt=today, enquiry__status__in=['open', 'follow_up']
        ).order_by('next_followup_date')
    elif period == 'today':
        qs = base.filter(next_followup_date=today).order_by('next_followup_date')
    elif period == 'upcoming':
        qs = base.filter(
            next_followup_date__gt=today,
            next_followup_date__lte=today + datetime.timedelta(days=7),
        ).order_by('next_followup_date')
    else:
        qs = base.order_by('-next_followup_date')

    overdue_count  = base.filter(
        next_followup_date__lt=today, enquiry__status__in=['open', 'follow_up']
    ).count()
    today_count    = base.filter(next_followup_date=today).count()
    upcoming_count = base.filter(
        next_followup_date__gt=today,
        next_followup_date__lte=today + datetime.timedelta(days=7),
    ).count()

    return render(request, 'sales/follow_up_list.html', {
        'followups':       qs,
        'period':          period,
        'today':           today,
        'overdue_count':   overdue_count,
        'today_count':     today_count,
        'upcoming_count':  upcoming_count,
    })


# ---------------------------------------------------------------------------
# All Appointments list
# ---------------------------------------------------------------------------

@login_required
def all_appointments(request):
    q  = request.GET.get('q', '').strip()
    qs = SalesAppointment.objects.select_related(
        'enquiry__customer', 'enquiry__prospect'
    ).order_by('-appointment_date')
    if q:
        qs = qs.filter(
            Q(enquiry__customer__full_name__icontains=q) |
            Q(enquiry__customer__phone__icontains=q) |
            Q(enquiry__prospect__full_name__icontains=q) |
            Q(enquiry__prospect__phone__icontains=q)
        )
    return render(request, 'sales/appointment_list.html', {'appointments': qs, 'q': q})


# ---------------------------------------------------------------------------
# Delivery list
# ---------------------------------------------------------------------------

@login_required
def delivery_list(request):
    deliveries = VehicleDelivery.objects.select_related(
        'sales_order__customer', 'delivered_by'
    ).order_by('-delivery_date')
    return render(request, 'sales/delivery_list.html', {'deliveries': deliveries})


# ---------------------------------------------------------------------------
# Exchange list
# ---------------------------------------------------------------------------

@login_required
def exchange_list(request):
    exchanges = ExchangeVehicle.objects.select_related(
        'sales_order__customer'
    ).order_by('-created_at')
    return render(request, 'sales/exchange_list.html', {'exchanges': exchanges})


# ---------------------------------------------------------------------------
# Feedback all
# ---------------------------------------------------------------------------

@login_required
def feedback_all(request):
    feedbacks = SalesFeedback.objects.select_related(
        'enquiry__customer', 'enquiry__prospect', 'created_by'
    ).order_by('-created_at')
    return render(request, 'sales/feedback_list.html', {'feedbacks': feedbacks})


# ---------------------------------------------------------------------------
# SalesEnquiry
# ---------------------------------------------------------------------------

@login_required
def enquiry_list(request):
    q             = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    qs = SalesEnquiry.objects.select_related(
        'customer', 'prospect', 'bike_model', 'sales_executive', 'branch'
    ).all()
    if q:
        qs = qs.filter(
            Q(customer__full_name__icontains=q) |
            Q(customer__phone__icontains=q) |
            Q(prospect__full_name__icontains=q) |
            Q(prospect__phone__icontains=q)
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
    enquiry = get_object_or_404(
        SalesEnquiry.objects.select_related(
            'customer', 'prospect', 'bike_model', 'sales_executive', 'branch'
        ),
        pk=pk,
    )
    appointments  = enquiry.appointments.all()
    feedback_list = enquiry.feedback.select_related('created_by').order_by('created_at')
    order         = enquiry.orders.first()
    today         = timezone.now().date()

    # Days until next follow-up (from latest feedback)
    latest_fb = enquiry.feedback.filter(next_followup_date__isnull=False).order_by('-created_at').first()
    followup_delta = None
    if latest_fb and latest_fb.next_followup_date:
        followup_delta = (latest_fb.next_followup_date - today).days

    return render(request, 'sales/enquiry_detail.html', {
        'enquiry':        enquiry,
        'appointments':   appointments,
        'feedback_list':  feedback_list,
        'order':          order,
        'today':          today,
        'latest_fb':      latest_fb,
        'followup_delta': followup_delta,
    })


@login_required
def enquiry_create(request):
    form = SalesEnquiryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        enquiry = form.save()
        log_action(request, 'Sales Enquiry', 'create', enquiry.pk)
        messages.success(request, 'Enquiry created successfully.')
        return redirect('sales:enquiry_detail', pk=enquiry.pk)
    if request.method == 'POST':
        messages.error(request, 'Please correct the errors below.')
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
        messages.success(request, f'Status updated to {enquiry.get_status_display()}.')
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
    if request.method == 'POST':
        messages.error(request, 'Please correct the errors below.')
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
    if request.method == 'POST':
        messages.error(request, 'Please correct the errors below.')
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
    if request.method == 'POST':
        messages.error(request, 'Please correct the errors below.')
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
        pk=pk,
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
    initial  = {}
    enquiry  = None

    enquiry_pk = request.GET.get('enquiry')
    if request.GET.get('customer'):
        initial['customer'] = request.GET['customer']
    if enquiry_pk:
        initial['enquiry'] = enquiry_pk
        try:
            enquiry = SalesEnquiry.objects.select_related(
                'customer', 'prospect'
            ).get(pk=enquiry_pk)
            if enquiry.customer_id:
                initial['customer'] = enquiry.customer_id
            elif enquiry.prospect:
                # Auto-create Customer from Prospect so the order can be saved
                from customers.models import Customer
                customer, _ = Customer.objects.get_or_create(
                    phone=enquiry.prospect.phone,
                    defaults={'full_name': enquiry.prospect.full_name}
                )
                # Link back to enquiry
                SalesEnquiry.objects.filter(pk=enquiry.pk).update(customer=customer)
                enquiry.customer = customer
                initial['customer'] = customer.pk
                messages.info(
                    request,
                    f'Customer "{customer.full_name}" auto-created from prospect record.'
                )
        except SalesEnquiry.DoesNotExist:
            pass

    # Pre-fill sales executive with the logged-in user
    if 'sales_executive' not in initial:
        initial['sales_executive'] = request.user.pk

    form = VehicleSalesOrderForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        order = form.save()
        log_action(request, 'Sales Order', 'create', order.pk)
        messages.success(request, 'Sales order created successfully.')
        return redirect('sales:order_detail', pk=order.pk)
    if request.method == 'POST':
        messages.error(request, 'Please correct the errors below.')
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
        messages.success(request, 'Delivery recorded. Customer vehicle record auto-created.')
        return redirect('sales:order_detail', pk=delivery.sales_order_id)
    if request.method == 'POST':
        messages.error(request, 'Please correct the errors below.')
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
    if request.method == 'POST':
        messages.error(request, 'Please correct the errors below.')
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


# ---------------------------------------------------------------------------
# VehicleAllotment
# ---------------------------------------------------------------------------

@login_required
def allotment_create(request, order_pk):
    from .forms import VehicleAllotmentForm
    from .models import VehicleAllotment
    order = get_object_or_404(VehicleSalesOrder, pk=order_pk)
    initial = {'sales_order': order.pk, 'vehicle': order.vehicle_id}
    instance = VehicleAllotment.objects.filter(sales_order=order).first()
    form = VehicleAllotmentForm(request.POST or None, instance=instance, initial=initial)
    if request.method == 'POST' and form.is_valid():
        allot = form.save(commit=False)
        if not allot.allotted_by_id:
            allot.allotted_by = request.user
        allot.save()
        log_action(request, 'Vehicle Allotment', 'create' if not instance else 'update', allot.pk)
        messages.success(request, 'Vehicle allotted successfully.')
        return redirect('sales:order_detail', pk=order.pk)
    return render(request, 'sales/allotment_form.html', {
        'form': form, 'order': order,
        'title': 'Allot Vehicle' if not instance else 'Update Allotment',
    })


# ---------------------------------------------------------------------------
# VehicleFitting
# ---------------------------------------------------------------------------

@login_required
def fitting_create(request, order_pk):
    from .forms import VehicleFittingForm
    order = get_object_or_404(VehicleSalesOrder, pk=order_pk)
    initial = {'sales_order': order.pk}
    form = VehicleFittingForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        fitting = form.save()
        log_action(request, 'Vehicle Fitting', 'create', fitting.pk)
        messages.success(request, 'Fitting added successfully.')
        return redirect('sales:order_detail', pk=order.pk)
    return render(request, 'sales/fitting_form.html', {
        'form': form, 'order': order, 'title': 'Add Fitting',
    })


@login_required
def fitting_delete(request, pk):
    from .models import VehicleFitting
    fit = get_object_or_404(VehicleFitting, pk=pk)
    order_id = fit.sales_order_id
    if request.method == 'POST':
        fit.delete()
        log_action(request, 'Vehicle Fitting', 'delete', pk)
        messages.success(request, 'Fitting removed.')
    return redirect('sales:order_detail', pk=order_id)
