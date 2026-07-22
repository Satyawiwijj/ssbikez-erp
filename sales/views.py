import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.audit import log_action
from accounts.models import DocStatusMixin
from accounts.permissions import require_module_action

from .forms import (AdditionalVehicleFittingFormSet, CallLogFormSet,
                    DeliveryNoteAdvancePaymentFormSet, DeliveryNoteItemFormSet,
                    DeliveryNotePaymentEntryFormSet, ExchangeVehicleForm,
                    FeedbackItemFormSet, HistoryFormSet, SalesAppointmentForm,
                    SalesFeedbackForm, SalesEnquiryForm,
                    SalesOrderAdvancePaymentFormSet, VehicleDeliveryForm,
                    VehicleSalesOrderForm, VehicleSaleItemFormSet,
                    DealerForm, ExchangeVehicleDealerForm, ExchangeVehicleDealerItemFormSet,
                    ExchangeDealerPaymentForm, ExchangeDealerPaymentItemFormSet,
                    DealerRCHandOverForm, DealerRCHandOverItemFormSet)
from .models import (ExchangeVehicle, Prospect, SalesAppointment, SalesFeedback,
                     SalesEnquiry, SalesEnquiryCallLog, SalesEnquiryHistory,
                     VehicleDelivery, VehicleSalesOrder,
                     Dealer, ExchangeVehicleDealer, ExchangeDealerPayment, DealerRCHandOver)


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
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    enquiry    = get_object_or_404(SalesEnquiry, pk=pk)
    if not user_owns(request.user, enquiry):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
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
    from accounts.permissions import user_owns
    apt = get_object_or_404(SalesAppointment, pk=pk)
    if not user_owns(request.user, apt.enquiry):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
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
    from billing.models import InsurancePolicy
    from rto.models import RTORegistration

    invoice   = order.current_invoice
    rto_reg   = RTORegistration.objects.filter(sales_order=order).first()
    insurance = InsurancePolicy.objects.filter(sales_order=order).first()
    delivery  = order.current_delivery
    loan      = getattr(order, 'loan',             None)
    exchange  = getattr(order, 'exchange_vehicle', None)
    policies  = order.insurance_policies.all()
    active_invoices = order.invoices.exclude(
        docstatus=DocStatusMixin.DocStatus.CANCELLED
    ).order_by('-created_at')
    return render(request, 'sales/order_detail.html', {
        'order':                order,
        'invoice':              invoice,
        'active_invoices':      active_invoices,
        'total_invoiced_amount': order.total_invoiced_amount,
        'active_invoice_count':  order.active_invoice_count,
        'loan':                 loan,
        'exchange':             exchange,
        'rto':                  rto_reg,    # keep key 'rto' so existing template sections work
        'delivery':             delivery,
        'policies':             policies,
        'insurance':            insurance,  # single policy for the Documents hub
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
                # No DB writes here — a GET request must stay side-effect-free.
                # The Customer is auto-created from the Prospect only on actual
                # save, in VehicleSalesOrderForm.clean() below. Just surface a
                # heads-up to the user so the blank Customer field makes sense.
                messages.info(
                    request,
                    f'This enquiry has Prospect "{enquiry.prospect.full_name}" but no '
                    'linked Customer yet. A Customer record will be auto-created from '
                    'the prospect when you save this order.'
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
    items_formset      = VehicleSaleItemFormSet(request.POST or None, prefix='items')
    fittings2_formset  = AdditionalVehicleFittingFormSet(request.POST or None, prefix='additional_fittings')
    advance_formset    = SalesOrderAdvancePaymentFormSet(request.POST or None, prefix='advance_payments')
    if request.method == 'POST':
        if (form.is_valid() and items_formset.is_valid()
                and fittings2_formset.is_valid() and advance_formset.is_valid()):
            order = form.save(commit=False)
            if not is_manager:
                order.sales_executive = request.user
            order.save()
            items_formset.instance = order
            items_formset.save()
            order.recompute_totals()
            fittings2_formset.instance = order
            fittings2_formset.save()
            advance_formset.instance = order
            advance_formset.save()
            log_action(request, 'Sales Order', 'create', order.pk)
            messages.success(request, 'Sales order created successfully.')
            return redirect('sales:order_detail', pk=order.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'sales/order_form.html', {
        'form': form, 'title': 'Create Sales Order',
        'items_formset': items_formset,
        'fittings2_formset': fittings2_formset,
        'advance_formset': advance_formset,
    })


@login_required
@require_module_action('sales', 'edit')
def order_update(request, pk):
    from accounts.permissions import user_is_manager, user_owns
    order = get_object_or_404(VehicleSalesOrder, pk=pk)
    if not user_owns(request.user, order):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    if order.docstatus != VehicleSalesOrder.DocStatus.DRAFT:
        from accounts.views import submitted_document_locked
        return submitted_document_locked(request, reverse('sales:order_detail', args=[order.pk]))
    form  = VehicleSalesOrderForm(request.POST or None, instance=order)
    if not user_is_manager(request.user):
        form.fields.pop('sales_executive', None)
    items_formset      = VehicleSaleItemFormSet(request.POST or None, instance=order, prefix='items')
    fittings2_formset  = AdditionalVehicleFittingFormSet(request.POST or None, instance=order, prefix='additional_fittings')
    advance_formset    = SalesOrderAdvancePaymentFormSet(request.POST or None, instance=order, prefix='advance_payments')
    if request.method == 'POST':
        if (form.is_valid() and items_formset.is_valid()
                and fittings2_formset.is_valid() and advance_formset.is_valid()):
            form.save()
            items_formset.save()
            order.recompute_totals()
            fittings2_formset.save()
            advance_formset.save()
            log_action(request, 'Sales Order', 'update', pk)
            messages.success(request, 'Sales order updated successfully.')
            return redirect('sales:order_detail', pk=order.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'sales/order_form.html', {
        'form': form, 'title': 'Edit Sales Order',
        'items_formset': items_formset,
        'fittings2_formset': fittings2_formset,
        'advance_formset': advance_formset,
    })


@login_required
@require_POST
@require_module_action('sales', 'edit')
def order_submit(request, pk):
    from accounts.permissions import user_owns
    order = get_object_or_404(VehicleSalesOrder, pk=pk)
    if not user_owns(request.user, order):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        order.submit(request.user)
        log_action(request, 'Sales Order', 'update', pk)
        messages.success(request, f'{order.order_number} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('sales:order_detail', pk=pk)


@login_required
@require_POST
@require_module_action('sales', 'edit')
def order_cancel(request, pk):
    from accounts.permissions import user_is_manager
    order = get_object_or_404(VehicleSalesOrder, pk=pk)
    if not user_is_manager(request.user):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        order.cancel(request.user)
        log_action(request, 'Sales Order', 'update', pk)
        messages.success(request, f'{order.order_number} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('sales:order_detail', pk=pk)


@login_required
@require_POST
@require_module_action('sales', 'create')
def order_amend(request, pk):
    from accounts.permissions import user_owns
    order = get_object_or_404(VehicleSalesOrder, pk=pk)
    if not user_owns(request.user, order):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        new_order = order.amend()
        for fitting in order.fittings.all():
            fitting.pk = None
            fitting.sales_order = new_order
            fitting.save()
        for fitting in order.additional_fittings.all():
            fitting.pk = None
            fitting.sales_order = new_order
            fitting.save()
        for item in order.items.all():
            item.pk = None
            item.sales_order = new_order
            item.save()
        for adv in order.advance_payments.all():
            adv.pk = None
            adv.sales_order = new_order
            adv.save()
        log_action(request, 'Sales Order', 'create', new_order.pk)
        messages.success(request, f'Amended as {new_order.order_number}.')
        return redirect('sales:order_detail', pk=new_order.pk)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('sales:order_detail', pk=pk)


# ---------------------------------------------------------------------------
# VehicleDelivery
# ---------------------------------------------------------------------------

@login_required
@require_module_action('sales', 'create')
def delivery_create(request):
    from accounts.permissions import user_owns
    initial = {}
    if request.GET.get('order'):
        initial['sales_order'] = request.GET['order']
    order_id = request.POST.get('sales_order') or request.GET.get('order')
    if order_id:
        order = get_object_or_404(VehicleSalesOrder, pk=order_id)
        if not user_owns(request.user, order):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
        if order.docstatus != VehicleSalesOrder.DocStatus.SUBMITTED:
            messages.error(
                request,
                f'Cannot create a delivery against '
                f'{order.order_number or f"ORD-{order.pk}"}: the order must be '
                f'Submitted first (currently {order.get_docstatus_display()}).'
            )
            return redirect('sales:order_detail', pk=order.pk)
    form = VehicleDeliveryForm(request.POST or None, initial=initial)
    items_formset   = DeliveryNoteItemFormSet(request.POST or None, prefix='delivery_items')
    advance_formset = DeliveryNoteAdvancePaymentFormSet(request.POST or None, prefix='delivery_advance')
    payment_formset = DeliveryNotePaymentEntryFormSet(request.POST or None, prefix='delivery_payments')
    if request.method == 'POST':
        if (form.is_valid() and items_formset.is_valid()
                and advance_formset.is_valid() and payment_formset.is_valid()):
            delivery = form.save()
            items_formset.instance = delivery
            items_formset.save()
            delivery.recompute_totals()
            advance_formset.instance = delivery
            advance_formset.save()
            payment_formset.instance = delivery
            payment_formset.save()
            log_action(request, 'Vehicle Delivery', 'create', delivery.pk)
            messages.success(request, 'Delivery recorded. Customer vehicle record auto-created on submit.')
            return redirect('sales:order_detail', pk=delivery.sales_order_id)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'sales/delivery_form.html', {
        'form': form, 'title': 'Record Vehicle Delivery',
        'items_formset': items_formset,
        'advance_formset': advance_formset,
        'payment_formset': payment_formset,
    })


@login_required
@require_module_action('sales', 'edit')
def delivery_update(request, pk):
    from accounts.permissions import user_owns
    delivery = get_object_or_404(VehicleDelivery, pk=pk)
    if not user_owns(request.user, delivery.sales_order):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    if delivery.docstatus != VehicleDelivery.DocStatus.DRAFT:
        from accounts.views import submitted_document_locked
        return submitted_document_locked(request, reverse('sales:order_detail', args=[delivery.sales_order_id]))
    form = VehicleDeliveryForm(request.POST or None, instance=delivery)
    items_formset   = DeliveryNoteItemFormSet(request.POST or None, instance=delivery, prefix='delivery_items')
    advance_formset = DeliveryNoteAdvancePaymentFormSet(request.POST or None, instance=delivery, prefix='delivery_advance')
    payment_formset = DeliveryNotePaymentEntryFormSet(request.POST or None, instance=delivery, prefix='delivery_payments')
    if request.method == 'POST':
        if (form.is_valid() and items_formset.is_valid()
                and advance_formset.is_valid() and payment_formset.is_valid()):
            form.save()
            items_formset.save()
            delivery.recompute_totals()
            advance_formset.save()
            payment_formset.save()
            log_action(request, 'Vehicle Delivery', 'update', pk)
            messages.success(request, 'Delivery updated successfully.')
            return redirect('sales:order_detail', pk=delivery.sales_order_id)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'sales/delivery_form.html', {
        'form': form, 'title': 'Edit Vehicle Delivery',
        'items_formset': items_formset,
        'advance_formset': advance_formset,
        'payment_formset': payment_formset,
    })


@login_required
@require_POST
@require_module_action('sales', 'edit')
def delivery_submit(request, pk):
    from accounts.permissions import user_owns
    delivery = get_object_or_404(VehicleDelivery, pk=pk)
    if not user_owns(request.user, delivery.sales_order):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    if not (delivery.manager_approved and delivery.finance_approved):
        messages.error(request, 'Manager and Finance approval are both required before submitting.')
        return redirect('sales:delivery_detail', pk=pk)
    try:
        delivery.submit(request.user)
        log_action(request, 'Vehicle Delivery', 'update', pk)
        messages.success(request, 'Delivery submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('sales:delivery_detail', pk=pk)


@login_required
@require_POST
@require_module_action('sales', 'edit')
def delivery_cancel(request, pk):
    from accounts.permissions import user_is_manager
    delivery = get_object_or_404(VehicleDelivery, pk=pk)
    if not user_is_manager(request.user):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        delivery.cancel(request.user)
        log_action(request, 'Vehicle Delivery', 'update', pk)
        messages.success(request, 'Delivery cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('sales:delivery_detail', pk=pk)


@login_required
@require_POST
@require_module_action('sales', 'create')
def delivery_amend(request, pk):
    from accounts.permissions import user_owns
    delivery = get_object_or_404(VehicleDelivery, pk=pk)
    if not user_owns(request.user, delivery.sales_order):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    try:
        new_delivery = delivery.amend()
        for item in delivery.items.all():
            item.pk = None
            item.delivery = new_delivery
            item.save()
        for adv in delivery.advance_payments.all():
            adv.pk = None
            adv.delivery = new_delivery
            adv.save()
        for pay in delivery.payment_entries.all():
            pay.pk = None
            pay.delivery = new_delivery
            pay.save()
        log_action(request, 'Vehicle Delivery', 'create', new_delivery.pk)
        messages.success(request, 'Delivery amended.')
        return redirect('sales:delivery_detail', pk=new_delivery.pk)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('sales:delivery_detail', pk=pk)


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
    from accounts.permissions import user_owns
    initial = {}
    if request.GET.get('sales_order'):
        initial['sales_order'] = request.GET['sales_order']
    order_id = request.POST.get('sales_order') or request.GET.get('sales_order')
    if order_id:
        order = get_object_or_404(VehicleSalesOrder, pk=order_id)
        if not user_owns(request.user, order):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
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
    from accounts.permissions import user_owns
    exchange = get_object_or_404(ExchangeVehicle, pk=pk)
    if not user_owns(request.user, exchange.sales_order):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
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
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    order = get_object_or_404(VehicleSalesOrder, pk=order_pk)
    if not user_owns(request.user, order):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
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
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    order = get_object_or_404(VehicleSalesOrder, pk=order_pk)
    if not user_owns(request.user, order):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    if order.docstatus != VehicleSalesOrder.DocStatus.DRAFT:
        from accounts.views import submitted_document_locked
        return submitted_document_locked(request, reverse('sales:order_detail', args=[order.pk]))
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
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    fit = get_object_or_404(VehicleFitting, pk=pk)
    order_id = fit.sales_order_id
    if not user_owns(request.user, fit.sales_order):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    if fit.sales_order.docstatus != VehicleSalesOrder.DocStatus.DRAFT:
        from accounts.views import submitted_document_locked
        return submitted_document_locked(request, reverse('sales:order_detail', args=[order_id]))
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
@require_module_action('sales', 'edit')
def test_ride_return(request, pk):
    from django.utils import timezone as _tz
    from accounts.permissions import user_owns
    ride = get_object_or_404(TestRideLog, pk=pk)
    if not user_owns(request.user, ride):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
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
@require_module_action('sales', 'edit')
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
    ).select_related('customer', 'vehicle__bike_model', 'sales_executive').annotate(
        fittings_rev_total=Sum('fittings__cost')
    )

    profit_data = []
    for order in orders:
        cost_price = 0
        if order.vehicle and order.vehicle.bike_model:
            bm = order.vehicle.bike_model
            cost_price = bm.dealer_cost_price or bm.ex_showroom_price or 0
        selling_price = order.total_amount or 0
        discount      = order.discount_amount or 0
        fittings_rev  = order.fittings_rev_total or 0
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
    address_parts = [p for p in [
        enq.address_line1, enq.address_line2, enq.address_line3, enq.address_line4,
        enq.city, enq.district, enq.state, enq.pincode,
    ] if p]
    return JsonResponse({
        'name':        enq.lead_name,
        'phone':       enq.lead_phone,
        'bike_model':  str(enq.bike_model) if enq.bike_model else '',
        'gender':      enq.gender,
        'address':     ', '.join(address_parts),
        'whatsapp_no': enq.whatsapp_no,
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
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    enquiry = get_object_or_404(SalesEnquiry, pk=enquiry_pk)
    if not user_owns(request.user, enquiry):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
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
    from accounts.permissions import user_owns
    from django.http import HttpResponseForbidden
    enquiry = get_object_or_404(SalesEnquiry, pk=enquiry_pk)
    if not user_owns(request.user, enquiry):
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
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


# ---------------------------------------------------------------------------
# Phase 13 -- Dealer sub-module
# ---------------------------------------------------------------------------

@login_required
def dealer_list(request):
    dealers = Dealer.objects.all()
    return render(request, 'sales/dealer_list.html', {'dealers': dealers})


@login_required
def dealer_detail(request, pk):
    dealer = get_object_or_404(Dealer, pk=pk)
    return render(request, 'sales/dealer_detail.html', {'dealer': dealer})


@login_required
@require_module_action('sales', 'create')
def dealer_create(request):
    form = DealerForm(request.POST or None)
    if form.is_valid():
        obj = form.save()
        log_action(request, 'Dealer', 'create', obj.pk)
        messages.success(request, f'{obj} created.')
        return redirect('sales:dealer_list')
    return render(request, 'sales/dealer_form.html', {'form': form, 'title': 'New Dealer'})


# ---- Exchange Vehicle Dealer ----

@login_required
def exchange_vehicle_dealer_list(request):
    transfers = ExchangeVehicleDealer.objects.select_related('dealer', 'from_warehouse', 'to_warehouse').all()
    return render(request, 'sales/exchange_vehicle_dealer_list.html', {'transfers': transfers})


@login_required
@require_module_action('sales', 'create')
def exchange_vehicle_dealer_create(request):
    form = ExchangeVehicleDealerForm(request.POST or None)
    formset = ExchangeVehicleDealerItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST':
        if form.is_valid() and formset.is_valid():
            obj = form.save()
            formset.instance = obj
            formset.save()
            log_action(request, 'Exchange Vehicle Dealer', 'create', obj.pk)
            messages.success(request, f'{obj} created.')
            return redirect('sales:exchange_vehicle_dealer_detail', pk=obj.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'sales/exchange_vehicle_dealer_form.html', {
        'form': form, 'formset': formset, 'title': 'New Exchange Vehicle Dealer Transfer',
    })


@login_required
def exchange_vehicle_dealer_detail(request, pk):
    obj = get_object_or_404(ExchangeVehicleDealer, pk=pk)
    return render(request, 'sales/exchange_vehicle_dealer_detail.html', {
        'obj': obj, 'items': obj.vehicle_details.select_related('registration_number').all(),
    })


@login_required
@require_POST
@require_module_action('sales', 'edit')
def exchange_vehicle_dealer_submit(request, pk):
    obj = get_object_or_404(ExchangeVehicleDealer, pk=pk)
    try:
        obj.submit(request.user)
        log_action(request, 'Exchange Vehicle Dealer', 'update', pk)
        messages.success(request, f'{obj} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('sales:exchange_vehicle_dealer_detail', pk=pk)


@login_required
@require_POST
@require_module_action('sales', 'edit')
def exchange_vehicle_dealer_cancel(request, pk):
    obj = get_object_or_404(ExchangeVehicleDealer, pk=pk)
    try:
        obj.cancel(request.user)
        log_action(request, 'Exchange Vehicle Dealer', 'update', pk)
        messages.success(request, f'{obj} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('sales:exchange_vehicle_dealer_detail', pk=pk)


@login_required
@require_POST
@require_module_action('sales', 'edit')
def exchange_vehicle_dealer_amend(request, pk):
    obj = get_object_or_404(ExchangeVehicleDealer, pk=pk)
    try:
        new_obj = obj.amend()
        for item in obj.vehicle_details.all():
            item.pk = None
            item.transfer = new_obj
            item.save()
        log_action(request, 'Exchange Vehicle Dealer', 'create', new_obj.pk)
        messages.success(request, f'Amended as {new_obj}.')
        return redirect('sales:exchange_vehicle_dealer_detail', pk=new_obj.pk)
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('sales:exchange_vehicle_dealer_detail', pk=pk)


# ---- Exchange Dealer Payment ----

@login_required
def exchange_dealer_payment_list(request):
    payments = ExchangeDealerPayment.objects.select_related('dealer', 'exchange_vehicle_dealer').all()
    return render(request, 'sales/exchange_dealer_payment_list.html', {'payments': payments})


@login_required
@require_module_action('sales', 'create')
def exchange_dealer_payment_create(request):
    from django.db.models import Sum
    initial = {}
    if request.GET.get('transfer'):
        transfer = get_object_or_404(ExchangeVehicleDealer, pk=request.GET['transfer'])
        initial['exchange_vehicle_dealer'] = transfer.pk
        initial['dealer'] = transfer.dealer_id
    form = ExchangeDealerPaymentForm(request.POST or None, initial=initial)
    formset = ExchangeDealerPaymentItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST':
        if form.is_valid() and formset.is_valid():
            obj = form.save()
            formset.instance = obj
            formset.save()
            obj.total_amount = obj.vehicle_details.aggregate(t=Sum('vehicle_amount'))['t'] or 0
            obj.save(update_fields=['total_amount'])
            log_action(request, 'Exchange Dealer Payment', 'create', obj.pk)
            messages.success(request, f'{obj} created.')
            return redirect('sales:exchange_dealer_payment_detail', pk=obj.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'sales/exchange_dealer_payment_form.html', {
        'form': form, 'formset': formset, 'title': 'New Exchange Dealer Payment',
    })


@login_required
def exchange_dealer_payment_detail(request, pk):
    obj = get_object_or_404(ExchangeDealerPayment, pk=pk)
    return render(request, 'sales/exchange_dealer_payment_detail.html', {
        'obj': obj, 'items': obj.vehicle_details.select_related('register_number').all(),
    })


@login_required
@require_POST
@require_module_action('sales', 'edit')
def exchange_dealer_payment_submit(request, pk):
    obj = get_object_or_404(ExchangeDealerPayment, pk=pk)
    try:
        obj.submit(request.user)
        log_action(request, 'Exchange Dealer Payment', 'update', pk)
        messages.success(request, f'{obj} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('sales:exchange_dealer_payment_detail', pk=pk)


@login_required
@require_POST
@require_module_action('sales', 'edit')
def exchange_dealer_payment_cancel(request, pk):
    obj = get_object_or_404(ExchangeDealerPayment, pk=pk)
    try:
        obj.cancel(request.user)
        log_action(request, 'Exchange Dealer Payment', 'update', pk)
        messages.success(request, f'{obj} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('sales:exchange_dealer_payment_detail', pk=pk)


@login_required
@require_POST
@require_module_action('sales', 'edit')
def exchange_dealer_payment_amend(request, pk):
    obj = get_object_or_404(ExchangeDealerPayment, pk=pk)
    try:
        new_obj = obj.amend()
        for item in obj.vehicle_details.all():
            item.pk = None
            item.payment = new_obj
            item.save()
        log_action(request, 'Exchange Dealer Payment', 'create', new_obj.pk)
        messages.success(request, f'Amended as {new_obj}.')
        return redirect('sales:exchange_dealer_payment_detail', pk=new_obj.pk)
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('sales:exchange_dealer_payment_detail', pk=pk)


# ---- Dealer RC Hand Over ----

@login_required
def dealer_rc_handover_list(request):
    handovers = DealerRCHandOver.objects.select_related('dealer').all()
    return render(request, 'sales/dealer_rc_handover_list.html', {'handovers': handovers})


@login_required
@require_module_action('sales', 'create')
def dealer_rc_handover_create(request):
    form = DealerRCHandOverForm(request.POST or None)
    formset = DealerRCHandOverItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST':
        if form.is_valid() and formset.is_valid():
            obj = form.save()
            formset.instance = obj
            formset.save()
            log_action(request, 'Dealer RC Hand Over', 'create', obj.pk)
            messages.success(request, f'{obj} created.')
            return redirect('sales:dealer_rc_handover_detail', pk=obj.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'sales/dealer_rc_handover_form.html', {
        'form': form, 'formset': formset, 'title': 'New Dealer RC Hand Over',
    })


@login_required
def dealer_rc_handover_detail(request, pk):
    obj = get_object_or_404(DealerRCHandOver, pk=pk)
    return render(request, 'sales/dealer_rc_handover_detail.html', {
        'obj': obj, 'items': obj.items.select_related('register_number').all(),
    })


@login_required
@require_POST
@require_module_action('sales', 'edit')
def dealer_rc_handover_submit(request, pk):
    obj = get_object_or_404(DealerRCHandOver, pk=pk)
    try:
        obj.submit(request.user)
        log_action(request, 'Dealer RC Hand Over', 'update', pk)
        messages.success(request, f'{obj} submitted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('sales:dealer_rc_handover_detail', pk=pk)


@login_required
@require_POST
@require_module_action('sales', 'edit')
def dealer_rc_handover_cancel(request, pk):
    obj = get_object_or_404(DealerRCHandOver, pk=pk)
    try:
        obj.cancel(request.user)
        log_action(request, 'Dealer RC Hand Over', 'update', pk)
        messages.success(request, f'{obj} cancelled.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('sales:dealer_rc_handover_detail', pk=pk)


@login_required
@require_POST
@require_module_action('sales', 'edit')
def dealer_rc_handover_amend(request, pk):
    obj = get_object_or_404(DealerRCHandOver, pk=pk)
    try:
        new_obj = obj.amend()
        for item in obj.items.all():
            item.pk = None
            item.handover = new_obj
            item.save()
        log_action(request, 'Dealer RC Hand Over', 'create', new_obj.pk)
        messages.success(request, f'Amended as {new_obj}.')
        return redirect('sales:dealer_rc_handover_detail', pk=new_obj.pk)
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('sales:dealer_rc_handover_detail', pk=pk)
