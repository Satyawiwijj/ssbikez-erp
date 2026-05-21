import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .audit import log_action
from .forms import (BranchForm, FuelExpenseForm, LoginForm,
                    ProfileUpdateForm, RoleForm, UserCreationForm, UserUpdateForm)
from .models import AuditLog, Branch, FuelExpense, Role, User


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        return redirect(request.GET.get('next', 'accounts:dashboard'))
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('accounts:login')


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    from billing.models import Payment
    from sales.models import SalesAppointment, SalesEnquiry, VehicleSalesOrder
    from service.models import JobCard
    from spares.models import SparePart

    today            = timezone.now().date()
    this_month_start = today.replace(day=1)

    enquiries_today = SalesEnquiry.objects.filter(created_at__date=today).count()

    open_orders = VehicleSalesOrder.objects.filter(sales_status='booked').count()

    active_job_cards = JobCard.objects.exclude(
        service_status__in=['invoiced', 'ready']
    ).count()

    low_stock_count = SparePart.objects.filter(stock_quantity__lt=5).count()

    recent_activity = AuditLog.objects.select_related('user').all()[:10]

    pending_appointments = SalesAppointment.objects.filter(
        appointment_date__date=today,
        status='scheduled',
    ).count()

    monthly_revenue = (
        Payment.objects.filter(
            payment_status='completed',
            payment_date__date__gte=this_month_start,
        ).aggregate(total=Sum('amount'))['total'] or 0
    )

    return render(request, 'accounts/dashboard.html', {
        'user':                 request.user,
        'enquiries_today':      enquiries_today,
        'open_orders':          open_orders,
        'active_job_cards':     active_job_cards,
        'low_stock_count':      low_stock_count,
        'recent_activity':      recent_activity,
        'pending_appointments': pending_appointments,
        'monthly_revenue':      monthly_revenue,
    })


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@login_required
def user_list(request):
    users = User.objects.select_related('role', 'branch').all()
    return render(request, 'accounts/user_list.html', {'users': users})


@login_required
def user_create(request):
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        log_action(request, 'User', 'create', user.pk)
        messages.success(request, 'User created successfully.')
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Create User'})


@login_required
def user_update(request, pk):
    user = get_object_or_404(User, pk=pk)
    form = UserUpdateForm(request.POST or None, instance=user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'User', 'update', pk)
        messages.success(request, 'User updated successfully.')
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Update User'})


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {'profile_user': request.user})


@login_required
def profile_update(request):
    form = ProfileUpdateForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'User', 'update', request.user.pk)
        messages.success(request, 'Profile updated successfully.')
        return redirect('accounts:profile')
    return render(request, 'accounts/profile_form.html', {'form': form, 'title': 'Edit Profile'})


# ---------------------------------------------------------------------------
# Branches
# ---------------------------------------------------------------------------

@login_required
def branch_list(request):
    branches = Branch.objects.all()
    return render(request, 'accounts/branch_list.html', {'branches': branches})


@login_required
def branch_create(request):
    form = BranchForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        branch = form.save()
        log_action(request, 'Branch', 'create', branch.pk)
        messages.success(request, 'Branch created successfully.')
        return redirect('accounts:branch_list')
    return render(request, 'accounts/branch_form.html', {'form': form, 'title': 'Create Branch'})


@login_required
def branch_update(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    form   = BranchForm(request.POST or None, instance=branch)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Branch', 'update', pk)
        messages.success(request, 'Branch updated successfully.')
        return redirect('accounts:branch_list')
    return render(request, 'accounts/branch_form.html', {'form': form, 'title': 'Edit Branch'})


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

@login_required
def role_list(request):
    roles = Role.objects.all()
    return render(request, 'accounts/role_list.html', {'roles': roles})


# ---------------------------------------------------------------------------
# FuelExpense
# ---------------------------------------------------------------------------

@login_required
def fuel_expense_list(request):
    q  = request.GET.get('q', '').strip()
    qs = FuelExpense.objects.select_related('vehicle__bike_model', 'created_by').all()
    if q:
        qs = qs.filter(
            Q(voucher_number__icontains=q) |
            Q(vehicle__chassis_no__icontains=q)
        )
    return render(request, 'accounts/fuel_expense_list.html', {'expenses': qs, 'q': q})


@login_required
def fuel_expense_create(request):
    form = FuelExpenseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        exp = form.save()
        log_action(request, 'Fuel Expense', 'create', exp.pk)
        messages.success(request, 'Fuel expense recorded successfully.')
        return redirect('accounts:fuel_expense_list')
    return render(request, 'accounts/fuel_expense_form.html',
                  {'form': form, 'title': 'Add Fuel Expense'})


@login_required
def fuel_expense_update(request, pk):
    expense = get_object_or_404(FuelExpense, pk=pk)
    form    = FuelExpenseForm(request.POST or None, instance=expense)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Fuel Expense', 'update', pk)
        messages.success(request, 'Fuel expense updated successfully.')
        return redirect('accounts:fuel_expense_list')
    return render(request, 'accounts/fuel_expense_form.html',
                  {'form': form, 'title': 'Edit Fuel Expense'})


# ---------------------------------------------------------------------------
# Password Change
# ---------------------------------------------------------------------------

@login_required
def password_change(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        update_session_auth_hash(request, form.user)
        log_action(request, 'User', 'update', request.user.pk)
        messages.success(request, 'Your password was updated successfully.')
        return redirect('accounts:dashboard')
    return render(request, 'accounts/password_change.html', {'form': form})


# ---------------------------------------------------------------------------
# Global Search
# ---------------------------------------------------------------------------

@login_required
def global_search(request):
    from billing.models import Invoice
    from customers.models import Customer, VehicleStock
    from sales.models import SalesEnquiry, VehicleSalesOrder
    from service.models import JobCard
    from spares.models import SparePart

    q       = request.GET.get('q', '').strip()
    results = {}

    if q:
        results['customers'] = list(
            Customer.objects.filter(
                Q(full_name__icontains=q) | Q(phone__icontains=q)
            )[:5]
        )

        results['vehicle_stock'] = list(
            VehicleStock.objects.select_related('bike_model').filter(
                Q(chassis_no__icontains=q) | Q(engine_no__icontains=q)
            )[:5]
        )

        results['enquiries'] = list(
            SalesEnquiry.objects.select_related('customer').filter(
                Q(customer__full_name__icontains=q) |
                Q(customer__phone__icontains=q)
            )[:5]
        )

        results['orders'] = list(
            VehicleSalesOrder.objects.select_related('customer').filter(
                Q(customer__full_name__icontains=q) |
                Q(customer__phone__icontains=q)
            )[:5]
        )

        results['job_cards'] = list(
            JobCard.objects.select_related(
                'customer_vehicle__customer',
                'customer_vehicle__vehicle__bike_model',
            ).filter(
                Q(customer_vehicle__registration_no__icontains=q) |
                Q(customer_vehicle__customer__full_name__icontains=q)
            )[:5]
        )

        results['spare_parts'] = list(
            SparePart.objects.filter(
                Q(part_name__icontains=q) | Q(part_number__icontains=q)
            )[:5]
        )

    total = sum(len(v) for v in results.values())

    return render(request, 'accounts/search_results.html', {
        'q':       q,
        'results': results,
        'total':   total,
    })


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

@login_required
def sales_report(request):
    from sales.models import SalesEnquiry, VehicleSalesOrder

    today             = timezone.now().date()
    this_month_start  = today.replace(day=1)
    last_month_end    = this_month_start - datetime.timedelta(days=1)
    last_month_start  = last_month_end.replace(day=1)
    six_months_ago    = today - datetime.timedelta(days=180)

    enquiries_this_month = SalesEnquiry.objects.filter(
        created_at__date__gte=this_month_start
    ).count()
    enquiries_last_month = SalesEnquiry.objects.filter(
        created_at__date__gte=last_month_start,
        created_at__date__lte=last_month_end,
    ).count()

    total_enquiries = SalesEnquiry.objects.count()
    converted       = SalesEnquiry.objects.filter(status='converted').count()
    conversion_rate = round(converted / total_enquiries * 100, 1) if total_enquiries else 0

    top_models = list(
        SalesEnquiry.objects
        .filter(bike_model__isnull=False)
        .values('bike_model__brand', 'bike_model__model_name')
        .annotate(count=Count('id'))
        .order_by('-count')[:8]
    )

    source_breakdown = list(
        SalesEnquiry.objects
        .values('enquiry_source')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    monthly_trend = list(
        SalesEnquiry.objects
        .filter(created_at__date__gte=six_months_ago)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    max_trend = max((m['count'] for m in monthly_trend), default=1) or 1

    open_orders = VehicleSalesOrder.objects.filter(sales_status='booked').count()

    return render(request, 'accounts/reports/sales_report.html', {
        'enquiries_this_month': enquiries_this_month,
        'enquiries_last_month': enquiries_last_month,
        'total_enquiries':      total_enquiries,
        'converted':            converted,
        'conversion_rate':      conversion_rate,
        'top_models':           top_models,
        'source_breakdown':     source_breakdown,
        'monthly_trend':        monthly_trend,
        'max_trend':            max_trend,
        'open_orders':          open_orders,
    })


@login_required
def spares_report(request):
    from spares.models import CounterSale, PurchaseOrder, SparePart, SparesIssue

    today            = timezone.now().date()
    this_month_start = today.replace(day=1)

    parts_qs          = SparePart.objects.all()
    total_parts       = parts_qs.count()
    total_stock_value = (
        parts_qs.filter(mrp__isnull=False)
        .aggregate(val=Sum(F('mrp') * F('stock_quantity')))['val'] or 0
    )

    low_stock_count = parts_qs.filter(stock_quantity__lt=5).count()
    low_stock       = list(parts_qs.filter(stock_quantity__lt=5).order_by('stock_quantity')[:10])

    top_issued = list(
        SparesIssue.objects
        .values('spare_part__part_name')
        .annotate(total_qty=Sum('quantity_issued'))
        .order_by('-total_qty')[:10]
    )
    max_issued = max((p['total_qty'] for p in top_issued), default=1) or 1

    po_summary = list(
        PurchaseOrder.objects
        .values('status')
        .annotate(count=Count('id'), total=Sum('total_amount'))
        .order_by('status')
    )

    cs_qs    = CounterSale.objects.filter(sale_date__gte=this_month_start)
    cs_count = cs_qs.count()
    cs_total = cs_qs.aggregate(t=Sum('total_amount'))['t'] or 0

    return render(request, 'accounts/reports/spares_report.html', {
        'total_parts':       total_parts,
        'total_stock_value': total_stock_value,
        'low_stock_count':   low_stock_count,
        'low_stock':         low_stock,
        'top_issued':        top_issued,
        'max_issued':        max_issued,
        'po_summary':        po_summary,
        'cs_count':          cs_count,
        'cs_total':          cs_total,
    })


@login_required
def service_report(request):
    from service.models import BayAssignment, JobCard, LaborCharge

    today            = timezone.now().date()
    this_month_start = today.replace(day=1)

    status_counts = list(
        JobCard.objects
        .values('service_status')
        .annotate(count=Count('id'))
        .order_by('service_status')
    )
    total_jc      = JobCard.objects.count()
    active_jc     = JobCard.objects.exclude(service_status='invoiced').count()
    this_month_jc = JobCard.objects.filter(created_at__date__gte=this_month_start).count()

    top_labor = list(
        LaborCharge.objects
        .values('service_name')
        .annotate(count=Count('id'), total_cost=Sum('labor_cost'))
        .order_by('-count')[:10]
    )
    max_labor = max((l['count'] for l in top_labor), default=1) or 1

    bay_stats = list(
        BayAssignment.objects
        .filter(created_at__date__gte=this_month_start)
        .values('bay__bay_name')
        .annotate(count=Count('id'))
        .order_by('-count')[:8]
    )
    max_bay = max((b['count'] for b in bay_stats), default=1) or 1

    return render(request, 'accounts/reports/service_report.html', {
        'status_counts': status_counts,
        'total_jc':      total_jc,
        'active_jc':     active_jc,
        'this_month_jc': this_month_jc,
        'top_labor':     top_labor,
        'max_labor':     max_labor,
        'bay_stats':     bay_stats,
        'max_bay':       max_bay,
    })
