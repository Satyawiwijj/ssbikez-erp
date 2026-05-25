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


from .models import OTPVerification
from django.utils import timezone

def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:home')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        # Create OTP
        OTPVerification.objects.filter(user=user, action='login').delete()
        otp = OTPVerification(user=user, action='login')
        otp.generate_otp()
        request.session['pre_otp_user_id'] = user.pk
        request.session['next_url'] = request.GET.get('next', 'accounts:dashboard')
        return redirect('accounts:verify_otp')
    return render(request, 'accounts/login.html', {'form': form})

def verify_otp(request):
    user_id = request.session.get('pre_otp_user_id')
    if not user_id:
        return redirect('accounts:login')
    
    if request.method == 'POST':
        otp_code = request.POST.get('otp_code', '').strip()
        try:
            otp_record = OTPVerification.objects.get(user_id=user_id, action='login', is_verified=False)
            if otp_record.otp_code == otp_code and otp_record.expires_at > timezone.now():
                otp_record.is_verified = True
                otp_record.save()
                
                # Fetch user and login
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(pk=user_id)
                login(request, user)
                
                # Cleanup session
                del request.session['pre_otp_user_id']
                next_url = request.session.pop('next_url', 'accounts:dashboard')
                return redirect(next_url)
            else:
                messages.error(request, "Invalid or expired OTP.")
        except OTPVerification.DoesNotExist:
            messages.error(request, "No valid OTP request found.")
            
    return render(request, 'accounts/verify_otp.html')



def logout_view(request):
    logout(request)
    return redirect('accounts:login')


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    import datetime
    from decimal import Decimal
    from billing.models import Payment
    from sales.models import SalesAppointment, SalesEnquiry
    from service.models import JobCard, ServiceAppointment as ServiceSvcApt
    from customer_vehicles.models import CustomerVehicle
    try:
        from spares.models import SparesItem
    except ImportError:
        SparesItem = None

    today = timezone.now().date()
    this_month_start = today.replace(day=1)

    def safe_count(qs):
        try:
            return qs.count()
        except Exception:
            return 0

    def safe_qs(qs, limit=10):
        try:
            return list(qs[:limit])
        except Exception:
            return []

    def safe_sum(qs, field):
        try:
            result = qs.aggregate(total=Sum(field))['total']
            return result if result is not None else Decimal('0')
        except Exception:
            return Decimal('0')

    try:
        today_enquiries = SalesEnquiry.objects.filter(created_at__date=today).count()
    except Exception:
        today_enquiries = 0

    try:
        month_revenue = Payment.objects.filter(
            payment_status='completed',
            payment_date__month=today.month,
            payment_date__year=today.year,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    except Exception:
        month_revenue = Decimal('0')

    try:
        open_job_cards = JobCard.objects.exclude(service_status__in=['invoiced']).count()
    except Exception:
        open_job_cards = 0

    try:
        low_stock_items = SparesItem.objects.filter(
            maintain_stock=True, is_active=True, reorder_level__gt=0
        ).count() if SparesItem else 0
    except Exception:
        low_stock_items = 0

    try:
        today_sales_appointments = list(
            SalesAppointment.objects.filter(
                appointment_date__date=today, status='scheduled'
            ).select_related('enquiry__customer')
        )
    except Exception:
        today_sales_appointments = []

    try:
        today_service_appointments = list(
            ServiceSvcApt.objects.filter(
                appointment_date__date=today, status='scheduled'
            ).select_related('service_enquiry__customer_vehicle__customer')
        )
    except Exception:
        today_service_appointments = []

    try:
        recent_audit_logs = list(
            AuditLog.objects.select_related('user').order_by('-created_at')[:5]
        )
    except Exception:
        recent_audit_logs = []

    try:
        expiry_limit = today + datetime.timedelta(days=30)
        expiring_insurance_count = CustomerVehicle.objects.filter(
            insurance_expiry__lte=expiry_limit,
            insurance_expiry__gte=today,
        ).count()
    except Exception:
        expiring_insurance_count = 0

    today_appointments_count = len(today_sales_appointments) + len(today_service_appointments)

    return render(request, 'accounts/dashboard.html', {
        'user':                        request.user,
        # canonical names used by template
        'enquiries_today':             today_enquiries,
        'monthly_revenue':             month_revenue,
        'active_job_cards':            open_job_cards,
        'low_stock_count':             low_stock_items,
        'pending_appointments':        today_appointments_count,
        # extra detail lists
        'today_sales_appointments':    today_sales_appointments,
        'today_service_appointments':  today_service_appointments,
        'today_appointments_count':    today_appointments_count,
        'recent_audit_logs':           recent_audit_logs,
        'recent_activity':             recent_audit_logs,
        'expiring_insurance_count':    expiring_insurance_count,
    })

# ---------------------------------------------------------------------------
# Account Settings
# ---------------------------------------------------------------------------

@login_required
def profile_update(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            log_action(request.user, "Updated profile")
            messages.success(request, "Profile updated successfully.")
            return redirect('accounts:profile_update')
    else:
        form = ProfileUpdateForm(instance=request.user)
    return render(request, 'accounts/profile_update.html', {'form': form})

@login_required
def password_change(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            log_action(user, "Changed password")
            messages.success(request, "Your password was successfully updated!")
            return redirect('accounts:profile_update')
        else:
            messages.error(request, "Please correct the error below.")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'accounts/password_change.html', {'form': form})


# ---------------------------------------------------------------------------
# User Management
# ---------------------------------------------------------------------------

@login_required
def user_list(request):
    if not request.user.has_perm('accounts.view_user'):
        messages.error(request, "Permission denied.")
        return redirect('accounts:dashboard')
    q = request.GET.get('q', '')
    qs = User.objects.all().order_by('-date_joined')
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q) | Q(first_name__icontains=q))
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/user_list.html', {'page_obj': page_obj, 'q': q})

@login_required
def user_create(request):
    if not request.user.has_perm('accounts.add_user'):
        messages.error(request, "Permission denied.")
        return redirect('accounts:user_list')
    if request.method == 'POST':
        form = UserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            log_action(request.user, f"Created user {user.username}")
            messages.success(request, "User created successfully.")
            return redirect('accounts:user_list')
    else:
        form = UserCreationForm()
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Create User'})

@login_required
def user_update(request, pk):
    if not request.user.has_perm('accounts.change_user'):
        messages.error(request, "Permission denied.")
        return redirect('accounts:user_list')
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, request.FILES, instance=user_obj)
        if form.is_valid():
            form.save()
            log_action(request.user, f"Updated user {user_obj.username}")
            messages.success(request, "User updated successfully.")
            return redirect('accounts:user_list')
    else:
        form = UserUpdateForm(instance=user_obj)
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Update User'})


# ---------------------------------------------------------------------------
# Branch Management
# ---------------------------------------------------------------------------

@login_required
def branch_list(request):
    if not request.user.has_perm('accounts.view_branch'):
        messages.error(request, "Permission denied.")
        return redirect('accounts:dashboard')
    qs = Branch.objects.all().order_by('name')
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/branch_list.html', {'page_obj': page_obj})

@login_required
def branch_create(request):
    if not request.user.has_perm('accounts.add_branch'):
        messages.error(request, "Permission denied.")
        return redirect('accounts:branch_list')
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            branch = form.save()
            log_action(request.user, f"Created branch {branch.name}")
            messages.success(request, "Branch created successfully.")
            return redirect('accounts:branch_list')
    else:
        form = BranchForm()
    return render(request, 'accounts/branch_form.html', {'form': form, 'title': 'Create Branch'})

@login_required
def branch_update(request, pk):
    if not request.user.has_perm('accounts.change_branch'):
        messages.error(request, "Permission denied.")
        return redirect('accounts:branch_list')
    branch = get_object_or_404(Branch, pk=pk)
    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            log_action(request.user, f"Updated branch {branch.name}")
            messages.success(request, "Branch updated successfully.")
            return redirect('accounts:branch_list')
    else:
        form = BranchForm(instance=branch)
    return render(request, 'accounts/branch_form.html', {'form': form, 'title': 'Update Branch'})


# ---------------------------------------------------------------------------
# Role Management
# ---------------------------------------------------------------------------

@login_required
def role_list(request):
    if not request.user.has_perm('accounts.view_role'):
        messages.error(request, "Permission denied.")
        return redirect('accounts:dashboard')
    qs = Role.objects.all().order_by('name')
    return render(request, 'accounts/role_list.html', {'roles': qs})

@login_required
def role_create(request):
    if not request.user.has_perm('accounts.add_role'):
        messages.error(request, "Permission denied.")
        return redirect('accounts:role_list')
    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            role = form.save()
            log_action(request.user, f"Created role {role.name}")
            messages.success(request, "Role created successfully.")
            return redirect('accounts:role_list')
    else:
        form = RoleForm()
    return render(request, 'accounts/role_form.html', {'form': form, 'title': 'Create Role'})

@login_required
def role_update(request, pk):
    if not request.user.has_perm('accounts.change_role'):
        messages.error(request, "Permission denied.")
        return redirect('accounts:role_list')
    role = get_object_or_404(Role, pk=pk)
    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            form.save()
            log_action(request.user, f"Updated role {role.name}")
            messages.success(request, "Role updated successfully.")
            return redirect('accounts:role_list')
    else:
        form = RoleForm(instance=role)
    return render(request, 'accounts/role_form.html', {'form': form, 'title': 'Update Role'})


# ---------------------------------------------------------------------------
# Fuel Expenses
# ---------------------------------------------------------------------------

@login_required
def fuel_expense_list(request):
    if not request.user.has_perm('accounts.view_fuelexpense'):
        messages.error(request, "Permission denied.")
        return redirect('accounts:dashboard')
    qs = FuelExpense.objects.all().order_by('-date')
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/fuel_expense_list.html', {'page_obj': page_obj})

@login_required
def fuel_expense_create(request):
    if not request.user.has_perm('accounts.add_fuelexpense'):
        messages.error(request, "Permission denied.")
        return redirect('accounts:fuel_expense_list')
    if request.method == 'POST':
        form = FuelExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.added_by = request.user
            expense.save()
            log_action(request.user, f"Added fuel expense of Rs. {expense.amount}")
            messages.success(request, "Fuel expense added.")
            return redirect('accounts:fuel_expense_list')
    else:
        form = FuelExpenseForm()
    return render(request, 'accounts/fuel_expense_form.html', {'form': form, 'title': 'Add Fuel Expense'})

@login_required
def fuel_expense_update(request, pk):
    if not request.user.has_perm('accounts.change_fuelexpense'):
        messages.error(request, "Permission denied.")
        return redirect('accounts:fuel_expense_list')
    expense = get_object_or_404(FuelExpense, pk=pk)
    if request.method == 'POST':
        form = FuelExpenseForm(request.POST, request.FILES, instance=expense)
        if form.is_valid():
            form.save()
            log_action(request.user, f"Updated fuel expense #{expense.pk}")
            messages.success(request, "Fuel expense updated.")
            return redirect('accounts:fuel_expense_list')
    else:
        form = FuelExpenseForm(instance=expense)
    return render(request, 'accounts/fuel_expense_form.html', {'form': form, 'title': 'Update Fuel Expense'})


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------

@login_required
def audit_log_list(request):
    if not request.user.is_superuser:
        messages.error(request, "Permission denied. Only admins can view audit logs.")
        return redirect('accounts:dashboard')
    qs = AuditLog.objects.select_related('user').order_by('-created_at')
    # Filter by user
    user_id = request.GET.get('user')
    if user_id:
        qs = qs.filter(user_id=user_id)
    # Filter by date range
    d_from = request.GET.get('date_from')
    d_to = request.GET.get('date_to')
    if d_from:
        qs = qs.filter(created_at__gte=d_from)
    if d_to:
        qs = qs.filter(created_at__lte=d_to)
        
    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get('page'))
    users = User.objects.filter(is_active=True)
    return render(request, 'accounts/audit_log_list.html', {
        'page_obj': page_obj,
        'users': users,
        'selected_user': user_id,
        'date_from': d_from,
        'date_to': d_to
    })
