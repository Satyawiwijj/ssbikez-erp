import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.audit import log_action
from accounts.permissions import require_module_action

from .forms import (CallLogFormSet, ExchangeVehicleForm, FeedbackItemFormSet,
                    HistoryFormSet, SalesAppointmentForm, SalesFeedbackForm,
                    SalesEnquiryForm, VehicleDeliveryForm, VehicleSalesOrderForm)
from .models import (ExchangeVehicle, Prospect, SalesAppointment, SalesFeedback,
                     SalesEnquiry, SalesEnquiryCallLog, SalesEnquiryHistory,
                     VehicleDelivery, VehicleSalesOrder)


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
    from django.db.models import Exists, OuterRef
    deliveries = VehicleDelivery.objects.select_related(
        'sales_order__customer', 'delivered_by'
    ).order_by('-delivery_date')
    missing_deliveries = VehicleSalesOrder.objects.filter(
        sales_status='delivered'
    ).exclude(
        Exists(VehicleDelivery.objects.filter(sales_order=OuterRef('pk')))
    ).select_related('customer', 'vehicle__bike_model', 'sales_executive').order_by('-created_at')
    return render(request, 'sales/delivery_list.html', {
        'deliveries': deliveries,
        'missing_deliveries': missing_deliveries,
    })


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
    q = request.GET.get('q', '').strip()
    feedbacks = SalesFeedback.objects.select_related(
        'enquiry__customer', 'enquiry__prospect', 'created_by'
    ).order_by('-created_at')
    if q:
        feedbacks = feedbacks.filter(
            Q(enquiry__customer__full_name__icontains=q) |
            Q(enquiry__customer__phone__icontains=q) |
            Q(enquiry__prospect__full_name__icontains=q) |
            Q(enquiry__prospect__phone__icontains=q) |
            Q(feedback_notes__icontains=q)
        )
    return render(request, 'sales/feedback_list.html', {'feedbacks': feedbacks, 'q': q})


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

    call_logs = enquiry.call_logs.order_by('-created_at')
    histories = enquiry.histories.order_by('-update_date')

    return render(request, 'sales/enquiry_detail.html', {
        'enquiry':        enquiry,
        'appointments':   appointments,
        'feedback_list':  feedback_list,
        'order':          order,
        'today':          today,
        'latest_fb':      latest_fb,
        'followup_delta': followup_delta,
        'call_logs':      call_logs,
        'histories':      histories,
    })


@login_required
@require_module_action('sales', 'create')
def enquiry_create(request):
    form              = SalesEnquiryForm(request.POST or None)
    calllog_formset   = CallLogFormSet(request.POST or None, prefix='calllogs')
    history_formset   = HistoryFormSet(request.POST or None, prefix='histories')
    if request.method == 'POST':
        if form.is_valid() and calllog_formset.is_valid() and history_formset.is_valid():
            enquiry = form.save()
            if not enquiry.sales_executive_id:
                enquiry.sales_executive = request.user
                enquiry.save(update_fields=['sales_executive'])
            calllog_formset.instance = enquiry
            calllog_formset.save()
            history_formset.instance = enquiry
            history_formset.save()
            log_action(request, 'Sales Enquiry', 'create', enquiry.pk)
            messages.success(request, 'Enquiry created successfully.')
            return redirect('sales:enquiry_detail', pk=enquiry.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'sales/enquiry_form.html', {
        'form': form,
        'calllog_formset': calllog_formset,
        'history_formset': history_formset,
        'title': 'New Enquiry',
    })


@login_required
@require_module_action('sales', 'edit')
def enquiry_update(request, pk):
    from accounts.permissions import user_owns
    enquiry           = get_object_or_404(SalesEnquiry, pk=pk)
    if not user_owns(request.user, enquiry):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    form              = SalesEnquiryForm(request.POST or None, instance=enquiry)
    calllog_formset   = CallLogFormSet(request.POST or None, instance=enquiry, prefix='calllogs')
    history_formset   = HistoryFormSet(request.POST or None, instance=enquiry, prefix='histories')
    if request.method == 'POST':
        if form.is_valid() and calllog_formset.is_valid() and history_formset.is_valid():
            form.save()
            calllog_formset.save()
            history_formset.save()
            log_action(request, 'Sales Enquiry', 'update', pk)
            messages.success(request, 'Enquiry updated successfully.')
            return redirect('sales:enquiry_detail', pk=enquiry.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'sales/enquiry_form.html', {
        'form': form,
        'calllog_formset': calllog_formset,
        'history_formset': history_formset,
        'title': 'Edit Enquiry',
    })


@login_required
@require_POST
@require_module_action('sales', 'edit')
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
@require_module_action('sales', 'create')
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
@require_module_action('sales', 'edit')
def appointment_update(request, pk):
    from accounts.permissions import user_owns
    apt  = get_object_or_404(SalesAppointment, pk=pk)
    if not user_owns(request.user, apt.enquiry):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
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
@require_module_action('sales', 'edit')
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
@require_module_action('sales', 'create')
def feedback_create(request):
    initial    = {}
    enquiry_pk = request.GET.get('enquiry')
    apt_pk     = request.GET.get('appointment')
    if enquiry_pk:
        initial['enquiry'] = enquiry_pk
    if apt_pk:
        initial['appointment'] = apt_pk
    form            = SalesFeedbackForm(request.POST or None, initial=initial)
    fb_item_formset = FeedbackItemFormSet(request.POST or None, prefix='feedback_items')
    if request.method == 'POST':
        if form.is_valid() and fb_item_formset.is_valid():
            fb = form.save(commit=False)
            if not fb.created_by_id:
                fb.created_by = request.user
            fb.save()
            fb_item_formset.instance = fb
            fb_item_formset.save()
            log_action(request, 'Sales Feedback', 'create', fb.pk)
            messages.success(request, 'Feedback recorded successfully.')
            return redirect('sales:enquiry_detail', pk=fb.enquiry_id)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'sales/feedback_form.html', {
        'form': form,
        'fb_item_formset': fb_item_formset,
        'title': 'Add Feedback',
    })


@login_required
def feedback_list(request, enquiry_pk):
    from django.utils import timezone
    enquiry       = get_object_or_404(SalesEnquiry, pk=enquiry_pk)
    feedback_list = enquiry.feedback.select_related('created_by').all()
    return render(request, 'sales/enquiry_detail.html', {
        'enquiry':       enquiry,
        'feedback_list': feedback_list,
        'today':         timezone.now().date(),
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
    from billing.models import Invoice, InsurancePolicy
    from rto.models import RTORegistration

    invoice   = Invoice.objects.filter(sales_order=order).first()
    rto_reg   = RTORegistration.objects.filter(sales_order=order).first()
    insurance = InsurancePolicy.objects.filter(sales_order=order).first()
    delivery  = VehicleDelivery.objects.filter(sales_order=order).first()
    loan      = getattr(order, 'loan',             None)
    exchange  = getattr(order, 'exchange_vehicle', None)
    policies  = order.insurance_policies.all()
    return render(request, 'sales/order_detail.html', {
        'order':     order,
        'invoice':   invoice,
        'loan':      loan,
        'exchange':  exchange,
        'rto':       rto_reg,    # keep key 'rto' so existing template sections work
        'delivery':  delivery,
        'policies':  policies,
        'insurance': insurance,  # single policy for the Documents hub
    })


@login_required
@require_module_action('sales', 'create')
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

    from accounts.permissions import user_is_manager
    is_manager = user_is_manager(request.user)

    form = VehicleSalesOrderForm(request.POST or None, initial=initial)
    if not is_manager:
        form.fields.pop('sales_executive', None)
    if request.method == 'POST' and form.is_valid():
        order = form.save(commit=False)
        if not is_manager:
            order.sales_executive = request.user
        order.save()
        log_action(request, 'Sales Order', 'create', order.pk)
        messages.success(request, 'Sales order created successfully.')
        return redirect('sales:order_detail', pk=order.pk)
    if request.method == 'POST':
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'sales/order_form.html', {'form': form, 'title': 'Create Sales Order'})


@login_required
@require_module_action('sales', 'edit')
def order_update(request, pk):
    from accounts.permissions import user_is_manager, user_owns
    order = get_object_or_404(VehicleSalesOrder, pk=pk)
    if not user_owns(request.user, order):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    form  = VehicleSalesOrderForm(request.POST or None, instance=order)
    if not user_is_manager(request.user):
        form.fields.pop('sales_executive', None)
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
@require_module_action('sales', 'create')
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
@require_module_action('sales', 'edit')
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
@require_module_action('sales', 'create')
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
@require_module_action('sales', 'edit')
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
@require_module_action('sales', 'create')
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
@require_module_action('sales', 'create')
def fitting_create(request, order_pk):
    from .forms import VehicleFittingFormSet
    order = get_object_or_404(VehicleSalesOrder, pk=order_pk)
    formset = VehicleFittingFormSet(request.POST or None, instance=order, prefix='fittings')
    if request.method == 'POST' and formset.is_valid():
        formset.save()
        log_action(request, 'Vehicle Fitting', 'update', order.pk)
        messages.success(request, 'Fittings saved successfully.')
        return redirect('sales:order_detail', pk=order.pk)
    return render(request, 'sales/fitting_form.html', {
        'formset': formset, 'order': order, 'title': 'Add / Edit Fittings',
    })


@login_required
@require_module_action('sales', 'delete')
def fitting_delete(request, pk):
    from .models import VehicleFitting
    fit = get_object_or_404(VehicleFitting, pk=pk)
    order_id = fit.sales_order_id
    if request.method == 'POST':
        fit.delete()
        log_action(request, 'Vehicle Fitting', 'delete', pk)
        messages.success(request, 'Fitting removed.')
    return redirect('sales:order_detail', pk=order_id)


# ============================================================
# FEATURE 1 — Sales Target Tracking
# ============================================================
from .models import SalesTarget, TestRideLog, PDIChecklist
from .forms import SalesTargetForm, TestRideLogForm, PDIChecklistForm


@login_required
def target_list(request):
    from django.utils import timezone as _tz
    today = _tz.now().date()
    targets = SalesTarget.objects.filter(
        month=today.month, year=today.year
    ).select_related('sales_executive')
    return render(request, 'sales/target_list.html', {
        'targets': targets, 'month': today.month, 'year': today.year,
    })


@login_required
@require_module_action('sales', 'create')
def target_create(request):
    from django.utils import timezone as _tz
    from accounts.permissions import user_is_manager
    is_manager = user_is_manager(request.user)
    today = _tz.now().date()
    if request.method == 'POST':
        form = SalesTargetForm(request.POST)
        if not is_manager:
            form.fields.pop('sales_executive', None)
        if form.is_valid():
            target = form.save(commit=False)
            if not is_manager:
                target.sales_executive = request.user
            target.created_by = request.user
            target.save()
            messages.success(request, 'Sales target set successfully.')
            return redirect('sales:target_list')
    else:
        form = SalesTargetForm(initial={'month': today.month, 'year': today.year})
        if not is_manager:
            form.fields.pop('sales_executive', None)
    return render(request, 'sales/target_form.html', {'form': form, 'title': 'Set Sales Target'})


@login_required
def target_detail(request, pk):
    from accounts.permissions import user_owns
    target = get_object_or_404(SalesTarget, pk=pk)
    if not user_owns(request.user, target):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    return render(request, 'sales/target_detail.html', {'target': target})


@login_required
def leaderboard(request):
    from django.utils import timezone as _tz
    from django.db.models import Count, Sum
    today = _tz.now().date()
    from accounts.models import User as _AuthUser
    execs = _AuthUser.objects.filter(
        role__role_name='Sales Executive'
    ).annotate(
        month_enquiries=Count(
            'enquiries_handled',
            filter=Q(enquiries_handled__created_at__month=today.month,
                     enquiries_handled__created_at__year=today.year)
        ),
        month_conversions=Count(
            'sales_orders',
            filter=Q(sales_orders__created_at__month=today.month,
                     sales_orders__created_at__year=today.year)
        ),
        month_revenue=Sum(
            'sales_orders__total_amount',
            filter=Q(sales_orders__created_at__month=today.month,
                     sales_orders__created_at__year=today.year)
        )
    ).order_by('-month_conversions', '-month_revenue')

    leaderboard_data = []
    for i, exec_user in enumerate(execs, 1):
        target = SalesTarget.objects.filter(
            sales_executive=exec_user, month=today.month, year=today.year
        ).first()
        month_enquiries = exec_user.month_enquiries or 0
        month_conversions = exec_user.month_conversions or 0
        conversion_percent = (
            round(month_conversions / month_enquiries * 100, 1) if month_enquiries else 0
        )
        leaderboard_data.append({
            'rank': i, 'user': exec_user, 'target': target,
            'month_enquiries': month_enquiries,
            'month_conversions': month_conversions,
            'month_revenue': exec_user.month_revenue or 0,
            'conversion_percent': conversion_percent,
        })
    return render(request, 'sales/leaderboard.html', {
        'leaderboard': leaderboard_data, 'month': today.month, 'year': today.year,
    })


# ============================================================
# FEATURE 3 — Test Ride Log
# ============================================================

@login_required
def test_ride_list(request):
    rides = TestRideLog.objects.select_related(
        'enquiry', 'vehicle__bike_model', 'accompanied_by'
    ).order_by('-created_at')
    scheduled_appointments = SalesAppointment.objects.filter(
        purpose='test_ride'
    ).select_related(
        'enquiry__customer', 'enquiry__prospect', 'enquiry__bike_model'
    ).order_by('-appointment_date')
    return render(request, 'sales/test_ride_list.html', {
        'rides': rides,
        'scheduled_appointments': scheduled_appointments,
    })


@login_required
@require_module_action('sales', 'create')
def test_ride_create(request):
    enquiry_id = request.GET.get('enquiry')
    initial = {}
    if enquiry_id:
        enq = get_object_or_404(SalesEnquiry, pk=enquiry_id)
        initial['enquiry'] = enq
    if request.method == 'POST':
        form = TestRideLogForm(request.POST)
        if form.is_valid():
            ride = form.save(commit=False)
            ride.created_by = request.user
            ride.save()
            messages.success(request, f'Test ride TR-{ride.pk} logged.')
            return redirect('sales:test_ride_list')
    else:
        form = TestRideLogForm(initial=initial)
    return render(request, 'sales/test_ride_form.html', {'form': form, 'title': 'Log Test Ride'})


@login_required
@require_POST
def test_ride_return(request, pk):
    from django.utils import timezone as _tz
    ride = get_object_or_404(TestRideLog, pk=pk)
    ride.end_time = _tz.now()
    ride.status = 'returned'
    end_odo = request.POST.get('end_odometer')
    if end_odo:
        try:
            ride.end_odometer = int(end_odo)
        except ValueError:
            pass
    ride.save()
    messages.success(request, f'Vehicle returned for TR-{ride.pk}.')
    return redirect('sales:test_ride_list')


# ============================================================
# FEATURE 5 — PDI Checklist
# ============================================================

@login_required
@require_module_action('sales', 'create')
def pdi_create(request, pk):
    order = get_object_or_404(VehicleSalesOrder, pk=pk)
    if hasattr(order, 'pdi_checklist'):
        return redirect('sales:pdi_detail', pk=order.pdi_checklist.pk)
    if request.method == 'POST':
        form = PDIChecklistForm(request.POST)
        if form.is_valid():
            pdi = form.save(commit=False)
            pdi.sales_order = order
            pdi.inspected_by = request.user
            pdi.save()
            messages.success(request, 'PDI checklist saved.')
            return redirect('sales:pdi_detail', pk=pdi.pk)
    else:
        form = PDIChecklistForm()
    return render(request, 'sales/pdi_form.html', {
        'form': form, 'order': order, 'title': f'PDI - Order {order.pk}'
    })


@login_required
def pdi_detail(request, pk):
    pdi = get_object_or_404(PDIChecklist, pk=pk)
    return render(request, 'sales/pdi_detail.html', {'pdi': pdi})


@login_required
@require_POST
def pdi_approve(request, pk):
    pdi = get_object_or_404(PDIChecklist, pk=pk)
    pdi.is_approved = True
    pdi.approved_by = request.user
    pdi.save()
    messages.success(request, 'PDI approved.')
    return redirect('sales:pdi_detail', pk=pdi.pk)


# ============================================================
# FEATURE 9 — Profit Per Vehicle Sale
# ============================================================

@login_required
def sale_profit_report(request):
    from django.utils import timezone as _tz
    from django.db.models import Sum
    today = _tz.now().date()
    month = int(request.GET.get('month', today.month))
    year  = int(request.GET.get('year',  today.year))

    orders = VehicleSalesOrder.objects.filter(
        created_at__month=month, created_at__year=year
    ).select_related('customer', 'vehicle__bike_model', 'sales_executive')

    profit_data = []
    for order in orders:
        cost_price = 0
        if order.vehicle and order.vehicle.bike_model:
            bm = order.vehicle.bike_model
            cost_price = bm.dealer_cost_price or bm.ex_showroom_price or 0
        selling_price = order.total_amount or 0
        discount      = order.discount_amount or 0
        fittings_rev  = order.fittings.aggregate(t=Sum('cost'))['t'] or 0
        gross_profit  = selling_price - cost_price - discount
        margin_pct    = round(float(gross_profit) / float(selling_price) * 100, 1) if selling_price else 0
        profit_data.append({
            'order': order, 'cost_price': cost_price,
            'selling_price': selling_price, 'discount': discount,
            'fittings_revenue': fittings_rev,
            'gross_profit': gross_profit, 'margin_pct': margin_pct,
        })

    context = {
        'month': month, 'year': year,
        'profit_data': profit_data,
        'total_revenue': sum(d['selling_price'] for d in profit_data),
        'total_profit':  sum(d['gross_profit']  for d in profit_data),
    }
    return render(request, 'sales/profit_report.html', context)


# ---------------------------------------------------------------------------
# API: Enquiry info for JS auto-fill in appointment/feedback forms
# ---------------------------------------------------------------------------

@login_required
def enquiry_info_api(request, pk):
    from django.http import JsonResponse
    enq = get_object_or_404(SalesEnquiry, pk=pk)
    return JsonResponse({
        'name':       enq.lead_name,
        'phone':      enq.lead_phone,
        'bike_model': str(enq.bike_model) if enq.bike_model else '',
    })


# ---------------------------------------------------------------------------
# Appointment detail view
# ---------------------------------------------------------------------------

@login_required
def appointment_detail(request, pk):
    apt = get_object_or_404(SalesAppointment, pk=pk)
    return render(request, 'sales/appointment_detail.html', {
        'appointment': apt,
        'title': f'Appointment APT-{apt.pk}',
    })


# ---------------------------------------------------------------------------
# Call Log and History add views (lightweight separate-page forms)
# ---------------------------------------------------------------------------

@login_required
def calllog_add(request, enquiry_pk):
    from .forms import CallLogForm
    enquiry = get_object_or_404(SalesEnquiry, pk=enquiry_pk)
    form = CallLogForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cl = form.save(commit=False)
        cl.enquiry = enquiry
        cl.save()
        messages.success(request, 'Call log saved.')
        return redirect('sales:enquiry_detail', pk=enquiry_pk)
    return render(request, 'sales/calllog_form.html', {
        'form': form, 'enquiry': enquiry, 'title': 'Add Call Log',
    })


@login_required
def history_add(request, enquiry_pk):
    from .forms import HistoryForm
    enquiry = get_object_or_404(SalesEnquiry, pk=enquiry_pk)
    form = HistoryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        hist = form.save(commit=False)
        hist.enquiry = enquiry
        hist.save()
        messages.success(request, 'History entry saved.')
        return redirect('sales:enquiry_detail', pk=enquiry_pk)
    return render(request, 'sales/history_form.html', {
        'form': form, 'enquiry': enquiry, 'title': 'Add History Entry',
    })


# ---------------------------------------------------------------------------
# Delete views — Issue 11
# ---------------------------------------------------------------------------

@login_required
@require_POST
@require_module_action('sales', 'delete')
def enquiry_delete(request, pk):
    from django.db.models import ProtectedError
    from accounts.permissions import user_owns
    enq = get_object_or_404(SalesEnquiry, pk=pk)
    if not user_owns(request.user, enq):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    if enq.appointments.exists():
        messages.error(request, f'Cannot delete ENQ-{pk}: it has linked appointments.')
        return redirect('sales:enquiry_detail', pk=pk)
    if enq.feedback.exists():
        messages.error(request, f'Cannot delete ENQ-{pk}: it has linked feedback records.')
        return redirect('sales:enquiry_detail', pk=pk)
    try:
        enq.delete()
        log_action(request, 'SalesEnquiry', 'delete', pk)
        messages.success(request, f'Enquiry ENQ-{pk} deleted.')
    except ProtectedError:
        messages.error(request, f'Cannot delete ENQ-{pk}: linked records exist.')
    return redirect('sales:enquiry_list')


@login_required
@require_POST
@require_module_action('sales', 'delete')
def appointment_delete(request, pk):
    from accounts.permissions import user_owns
    apt = get_object_or_404(SalesAppointment, pk=pk)
    if not user_owns(request.user, apt.enquiry):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    apt.delete()
    log_action(request, 'SalesAppointment', 'delete', pk)
    messages.success(request, f'Appointment APT-{pk} deleted.')
    return redirect('sales:all_appointments')


@login_required
@require_POST
@require_module_action('sales', 'delete')
def feedback_delete(request, pk):
    from accounts.permissions import user_owns
    fb = get_object_or_404(SalesFeedback, pk=pk)
    if not user_owns(request.user, fb):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    fb.delete()
    log_action(request, 'SalesFeedback', 'delete', pk)
    messages.success(request, 'Feedback record deleted.')
    return redirect('sales:feedback_all')


@login_required
@require_POST
@require_module_action('sales', 'delete')
def order_delete(request, pk):
    from django.db.models import ProtectedError
    from accounts.permissions import user_owns
    order = get_object_or_404(VehicleSalesOrder, pk=pk)
    if not user_owns(request.user, order):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    if order.sales_status != 'cancelled':
        messages.error(
            request,
            f'Cannot delete ORD-{pk}: status is "{order.get_sales_status_display()}". '
            'Only Cancelled orders can be deleted.'
        )
        return redirect('sales:order_detail', pk=pk)
    try:
        order.delete()
        log_action(request, 'VehicleSalesOrder', 'delete', pk)
        messages.success(request, f'Order ORD-{pk} deleted.')
    except ProtectedError:
        messages.error(request, f'Cannot delete ORD-{pk}: billing or delivery records exist.')
    return redirect('sales:order_list')
