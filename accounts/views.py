import datetime
import hmac

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth import views as auth_views
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

MAX_FAILED_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES     = 15


def submitted_document_locked(request, detail_url):
    """Render a real page (not a bare error string) when a user tries to
    edit a Submitted document directly. Points them at the document's own
    detail page, where the existing Cancel & Amend action actually lives —
    the previous bare HttpResponseForbidden told the user what to do
    without giving them any way to do it."""
    from django.http import HttpResponseForbidden
    from django.template.loader import render_to_string
    html = render_to_string('accounts/submitted_locked.html', {'detail_url': detail_url}, request=request)
    return HttpResponseForbidden(html)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:home')

    # Form validation always runs first, for every submission, regardless of
    # lockout state -- this keeps response timing identical whether or not an
    # account is locked, closing a timing-based username-enumeration channel.
    form = LoginForm(request, data=request.POST or None)

    if request.method == 'POST' and not form.is_valid():
        submitted_username = (request.POST.get('username') or '').strip()
        failed_user = User.objects.filter(username=submitted_username).first()
        if failed_user:
            now = timezone.now()
            if failed_user.locked_until and failed_user.locked_until <= now:
                # A previous lockout window has already expired -- this failed
                # attempt starts a fresh count, not a continuation of the old one.
                User.objects.filter(pk=failed_user.pk).update(failed_login_attempts=0, locked_until=None)
            # F()-based update so concurrent failed attempts for the same
            # account can't collide into a single lost increment.
            User.objects.filter(pk=failed_user.pk).update(failed_login_attempts=F('failed_login_attempts') + 1)
            failed_user.refresh_from_db(fields=['failed_login_attempts', 'locked_until'])
            if failed_user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS and not failed_user.locked_until:
                User.objects.filter(pk=failed_user.pk).update(
                    locked_until=now + datetime.timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
                )

    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        # Only reveal an active lockout once the submitted credentials are
        # actually correct -- revealing it for a wrong-password guess would
        # let an attacker enumerate which usernames exist and are locked.
        if user.locked_until and user.locked_until > timezone.now():
            messages.error(
                request,
                'Too many failed login attempts. Please try again in a few minutes.'
            )
            return render(request, 'accounts/login.html', {'form': LoginForm(request)})
        if user.failed_login_attempts or user.locked_until:
            user.failed_login_attempts = 0
            user.locked_until = None
            user.save(update_fields=['failed_login_attempts', 'locked_until'])
        next_url = request.GET.get('next', 'accounts:home')

        # Every user — including superusers — must verify an emailed OTP
        # before a session is created.
        OTPVerification.objects.filter(user=user, action='login').delete()
        otp = OTPVerification(user=user, action='login')
        email_sent = otp.generate_otp()

        if not email_sent:
            # Fail closed — never let a user in without proving they received
            # the emailed code.
            otp.delete()
            messages.error(
                request,
                'Could not send the OTP email. Please contact the system '
                'administrator to fix email delivery before logging in.'
            )
            return render(request, 'accounts/login.html', {'form': form})

        request.session['pre_otp_user_id'] = user.pk
        request.session['next_url'] = next_url
        request.session.pop('otp_attempts', None)
        return redirect('accounts:verify_otp')
    return render(request, 'accounts/login.html', {'form': form})


def verify_otp(request):
    user_id = request.session.get('pre_otp_user_id')
    if not user_id:
        return redirect('accounts:login')

    MAX_OTP_ATTEMPTS = 5
    if request.method == 'POST':
        otp_code = request.POST.get('otp_code', '').strip()
        try:
            otp_record = OTPVerification.objects.get(user_id=user_id, action='login', is_verified=False)
            if hmac.compare_digest(otp_record.otp_code, otp_code) and otp_record.expires_at > timezone.now():
                otp_record.is_verified = True
                otp_record.save()

                from django.contrib.auth import get_user_model
                user = get_user_model().objects.get(pk=user_id)
                login(request, user)

                next_url = request.session.pop('next_url', 'accounts:home')
                for key in ('pre_otp_user_id', 'otp_attempts'):
                    request.session.pop(key, None)

                return redirect(next_url)
            else:
                attempts = request.session.get('otp_attempts', 0) + 1
                request.session['otp_attempts'] = attempts
                if attempts >= MAX_OTP_ATTEMPTS:
                    otp_record.delete()
                    for key in ('pre_otp_user_id', 'otp_attempts'):
                        request.session.pop(key, None)
                    messages.error(
                        request,
                        'Too many incorrect attempts. Please log in again to receive a new code.'
                    )
                    return redirect('accounts:login')
                messages.error(request, 'Invalid or expired OTP.')
        except OTPVerification.DoesNotExist:
            messages.error(request, 'No valid OTP request found.')

    return render(request, 'accounts/verify_otp.html')


def logout_view(request):
    logout(request)
    return redirect('accounts:login')


PASSWORD_RESET_REQUEST_COOLDOWN_MINUTES = 2


class RateLimitedPasswordResetView(auth_views.PasswordResetView):
    """
    Django's stock PasswordResetView has no throttling on the request step —
    an unauthenticated caller can trigger unlimited reset emails to any known
    address. Skips the actual send (silently, so the response is identical
    either way and doesn't leak whether a cooldown is active) if this user
    was already sent a reset link within the cooldown window.
    """
    def form_valid(self, form):
        users = list(form.get_users(form.cleaned_data['email']))
        now = timezone.now()
        cooldown = datetime.timedelta(minutes=PASSWORD_RESET_REQUEST_COOLDOWN_MINUTES)

        due_users = [
            u for u in users
            if not u.last_password_reset_request_at
            or (now - u.last_password_reset_request_at) >= cooldown
        ]
        if not due_users:
            # Every matching account is still in cooldown -- redirect to the
            # same success page without sending anything, matching Django's
            # own no-enumeration behavior for a non-matching email.
            return redirect(self.get_success_url())

        User.objects.filter(pk__in=[u.pk for u in due_users]).update(
            last_password_reset_request_at=now
        )
        # PasswordResetForm.save() re-resolves recipients via form.get_users(),
        # which would otherwise re-fetch and email every account matching the
        # address again -- including ones still in cooldown, if the address
        # is shared across more than one account. Scope the send to exactly
        # the due accounts already computed above.
        original_get_users = form.get_users
        form.get_users = lambda email: due_users
        try:
            return super().form_valid(form)
        finally:
            form.get_users = original_get_users


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    import datetime
    from decimal import Decimal
    from billing.models import Payment
    from sales.models import SalesAppointment, SalesEnquiry, SalesFeedback
    from service.models import JobCard, ServiceAppointment as ServiceSvcApt
    from customer_vehicles.models import CustomerVehicle
    try:
        from spares.models import SparesItem
    except ImportError:
        SparesItem = None

    today            = timezone.now().date()
    this_month_start = today.replace(day=1)

    def safe_count(qs):
        try:
            return qs.count()
        except Exception:
            return 0

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
            ).select_related('enquiry__customer', 'enquiry__prospect')
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

    # Insurance expiry data
    try:
        expiry_30     = today + datetime.timedelta(days=30)
        expiry_60     = today + datetime.timedelta(days=60)
        expiring_30   = CustomerVehicle.objects.filter(
            insurance_expiry__lte=expiry_30,
            insurance_expiry__gte=today,
        ).select_related('customer', 'vehicle__bike_model').order_by('insurance_expiry')
        expiring_60   = CustomerVehicle.objects.filter(
            insurance_expiry__lte=expiry_60,
            insurance_expiry__gt=expiry_30,
        ).select_related('customer', 'vehicle__bike_model').order_by('insurance_expiry')
        already_expired = CustomerVehicle.objects.filter(
            insurance_expiry__lt=today,
        ).select_related('customer', 'vehicle__bike_model').order_by('insurance_expiry')
        expiring_insurance_count = expiring_30.count()
    except Exception:
        expiring_30 = []
        expiring_60 = []
        already_expired = []
        expiring_insurance_count = 0

    # Follow-up data for sales executives
    try:
        _fb_base = SalesFeedback.objects.select_related(
            'enquiry__customer', 'enquiry__prospect', 'enquiry__bike_model',
        ).filter(enquiry__sales_executive=request.user)

        todays_followups = list(
            _fb_base.filter(next_followup_date=today).order_by('next_followup_date')
        )
        overdue_followups = list(
            _fb_base.filter(
                next_followup_date__lt=today,
                enquiry__status__in=['open', 'follow_up'],
            ).order_by('next_followup_date')
        )
        upcoming_followups = list(
            _fb_base.filter(
                next_followup_date__gt=today,
                next_followup_date__lte=today + datetime.timedelta(days=7),
            ).order_by('next_followup_date')
        )
    except Exception:
        todays_followups   = []
        overdue_followups  = []
        upcoming_followups = []

    today_appointments_count = len(today_sales_appointments) + len(today_service_appointments)

    # Detect CRE role
    is_cre = (
        request.user.role and
        'cre' in request.user.role.role_name.lower()
    ) if hasattr(request.user, 'role') and request.user.role else False

    # ── FEATURE 10: Enhanced dashboard additions ──────────────────────────
    from customers.models import BikeModel, Customer, VehicleStock

    try:
        from sales.models import TestRideLog as _TRL, SalesTarget as _ST
        todays_test_rides = _TRL.objects.filter(
            start_time__date=today, status='out'
        ).count()
        target_this_month = _ST.objects.filter(
            month=today.month, year=today.year,
            sales_executive=request.user
        ).first()
    except Exception:
        todays_test_rides = 0
        target_this_month = None

    try:
        from sales.models import PDIChecklist as _PDI, VehicleSalesOrder as _VSO
        pending_pdi = _VSO.objects.filter(
            sales_status='booked'
        ).exclude(pdi_checklist__isnull=False).count()
        open_orders = _VSO.objects.filter(sales_status='booked').count()
    except Exception:
        pending_pdi = 0
        open_orders = 0

    try:
        vehicles_aging_90 = VehicleStock.objects.filter(
            stock_status='available',
            purchase_date__lte=today - datetime.timedelta(days=90)
        ).count()
        aging_30_count = VehicleStock.objects.filter(
            stock_status='available',
            purchase_date__lte=today - datetime.timedelta(days=30),
            purchase_date__gt=today - datetime.timedelta(days=60)
        ).count()
        aging_60_count = VehicleStock.objects.filter(
            stock_status='available',
            purchase_date__lte=today - datetime.timedelta(days=60),
            purchase_date__gt=today - datetime.timedelta(days=90)
        ).count()
        aging_90_plus = VehicleStock.objects.filter(
            stock_status='available',
            purchase_date__lte=today - datetime.timedelta(days=90)
        ).select_related('bike_model', 'branch')
    except Exception:
        vehicles_aging_90 = aging_30_count = aging_60_count = 0
        aging_90_plus = []

    try:
        from service.models import ServiceReminder as _SR
        pending_reminders = _SR.objects.filter(
            reminder_date=today, status='pending'
        ).count()
    except Exception:
        pending_reminders = 0

    # ── Home Page Structure: "Your Shortcuts" setup checklist ─────────────
    # New installs land on an empty dashboard with nothing to act on, which
    # is what the client's review report flagged as "incomplete" — the real
    # gap was that no master data existed yet, not missing features. This
    # surfaces the master-data setup steps (and their live counts) so a new
    # branch knows what to create first, and hides itself once done.
    try:
        from masters.models import Supplier
        branch_count   = Branch.objects.count()
        bike_model_count = BikeModel.objects.count()
        vehicle_stock_count = VehicleStock.objects.count()
        supplier_count = Supplier.objects.count()
        customer_count = Customer.objects.count()
        setup_steps = [
            {'label': 'Add a Branch',        'count': branch_count,       'url': 'accounts:branch_create'},
            {'label': 'Add a Bike Model',     'count': bike_model_count,   'url': 'customers:bike_model_create'},
            {'label': 'Add Vehicle Stock',    'count': vehicle_stock_count,'url': 'customers:vehicle_stock_create'},
            {'label': 'Add a Supplier',       'count': supplier_count,     'url': 'masters:supplier_create'},
            {'label': 'Add a Customer',       'count': customer_count,     'url': 'customers:customer_create'},
        ]
        setup_incomplete = any(step['count'] == 0 for step in setup_steps)
    except Exception:
        setup_steps = []
        setup_incomplete = False

    return render(request, 'accounts/dashboard.html', {
        'user':                        request.user,
        'enquiries_today':             today_enquiries,
        'monthly_revenue':             month_revenue,
        'active_job_cards':            open_job_cards,
        'low_stock_count':             low_stock_items,
        'pending_appointments':        today_appointments_count,
        'today_sales_appointments':    today_sales_appointments,
        'today_service_appointments':  today_service_appointments,
        'today_appointments_count':    today_appointments_count,
        'recent_audit_logs':           recent_audit_logs,
        'recent_activity':             recent_audit_logs,
        # Insurance
        'expiring_insurance_count':    expiring_insurance_count,
        'expiring_30':                 expiring_30,
        'expiring_60':                 expiring_60,
        'already_expired':             already_expired,
        'is_cre':                      is_cre,
        # Follow-ups
        'todays_followups':            todays_followups,
        'overdue_followups':           overdue_followups,
        'upcoming_followups':          upcoming_followups,
        'today':                       today,
        # Feature 10 extras
        'todays_test_rides':           todays_test_rides,
        'open_orders':                 open_orders,
        'pending_pdi':                 pending_pdi,
        'vehicles_aging_90':           vehicles_aging_90,
        'aging_30_count':              aging_30_count,
        'aging_60_count':              aging_60_count,
        'aging_90_plus':               aging_90_plus,
        'aging_90_count':              vehicles_aging_90,
        'pending_reminders':           pending_reminders,
        'target_this_month':           target_this_month,
    })


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

_USER_MGMT_ROLES = {'Managing Director', 'Sales Manager'}
_SETTINGS_MGMT_ROLES = {'Managing Director'}


def _can_manage_settings(user):
    if user.is_superuser:
        return True
    role_name = getattr(getattr(user, 'role', None), 'role_name', '')
    return role_name in _SETTINGS_MGMT_ROLES


def _can_manage_users(user):
    if user.is_superuser:
        return True
    role_name = getattr(getattr(user, 'role', None), 'role_name', '')
    return role_name in _USER_MGMT_ROLES

@login_required
def user_list(request):
    if not _can_manage_users(request.user):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    users = User.objects.select_related('role', 'branch').all()
    return render(request, 'accounts/user_list.html', {'users': users})


@login_required
def user_create(request):
    if not _can_manage_users(request.user):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        log_action(request, 'User', 'create', user.pk)
        messages.success(request, 'User created successfully.')
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Create User'})


@login_required
def user_update(request, pk):
    if not _can_manage_users(request.user):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    user = get_object_or_404(User, pk=pk)
    form = UserUpdateForm(request.POST or None, instance=user)
    if not _can_manage_settings(request.user):
        # Only Managing Director / superuser may change role or activation —
        # a user-management role (e.g. Sales Manager) could otherwise
        # promote themselves or anyone else to a more privileged role.
        form.fields.pop('role', None)
        form.fields.pop('is_active', None)
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
    if not _can_manage_settings(request.user):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    branches = Branch.objects.all()
    return render(request, 'accounts/branch_list.html', {'branches': branches})


@login_required
def branch_create(request):
    if not _can_manage_settings(request.user):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    form = BranchForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        branch = form.save()
        log_action(request, 'Branch', 'create', branch.pk)
        messages.success(request, 'Branch created successfully.')
        return redirect('accounts:branch_list')
    return render(request, 'accounts/branch_form.html', {'form': form, 'title': 'Create Branch'})


@login_required
def branch_update(request, pk):
    if not _can_manage_settings(request.user):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
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

def home(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    return render(request, 'accounts/home.html')


@login_required
def role_list(request):
    if not _can_manage_settings(request.user):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    roles = Role.objects.all()
    return render(request, 'accounts/role_list.html', {'roles': roles})


@login_required
def role_create(request):
    if not _can_manage_settings(request.user):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    form = RoleForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        role = form.save()
        log_action(request, 'Role', 'create', role.pk)
        messages.success(request, 'Role created.')
        return redirect('accounts:role_list')
    return render(request, 'accounts/role_form.html', {'form': form, 'title': 'Create Role'})


@login_required
def role_update(request, pk):
    if not _can_manage_settings(request.user):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    role = get_object_or_404(Role, pk=pk)
    form = RoleForm(request.POST or None, instance=role)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Role', 'update', pk)
        messages.success(request, 'Role updated.')
        return redirect('accounts:role_list')
    return render(request, 'accounts/role_form.html', {'form': form, 'title': 'Edit Role'})


# ---------------------------------------------------------------------------
# ModulePermission — page/module-level access per role
# ---------------------------------------------------------------------------

@login_required
def module_access_list(request):
    if not _can_manage_settings(request.user):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    roles = Role.objects.all()
    return render(request, 'accounts/module_access_list.html', {'roles': roles})


_MODULE_ACTIONS = ('can_view', 'can_create', 'can_edit', 'can_delete')


@login_required
def module_access_edit(request, role_pk):
    from .models import MODULE_CHOICES, ModulePermission
    if not _can_manage_settings(request.user):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')

    role = get_object_or_404(Role, pk=role_pk)
    overrides = {mp.module: mp for mp in role.module_permissions.all()}

    if request.method == 'POST':
        for key, _label in MODULE_CHOICES:
            defaults = {
                action: request.POST.get(f'module_{key}_{action}') == 'on'
                for action in _MODULE_ACTIONS
            }
            ModulePermission.objects.update_or_create(
                role=role, module=key, defaults=defaults
            )
        log_action(request, 'ModulePermission', 'update', role.pk)
        messages.success(request, f'Module access updated for {role.role_name}.')
        return redirect('accounts:module_access_list')

    rows = []
    for key, label in MODULE_CHOICES:
        existing = overrides.get(key)
        rows.append({
            'key': key, 'label': label,
            'can_view':   existing.can_view if existing else True,
            'can_create': existing.can_create if existing else True,
            'can_edit':   existing.can_edit if existing else True,
            'can_delete': existing.can_delete if existing else True,
        })
    return render(request, 'accounts/module_access_edit.html', {'role': role, 'rows': rows})


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
        exp = form.save(commit=False)
        exp.created_by = request.user
        exp.save()
        log_action(request, 'Fuel Expense', 'create', exp.pk)
        messages.success(request, 'Fuel expense recorded successfully.')
        return redirect('accounts:fuel_expense_list')
    return render(request, 'accounts/fuel_expense_form.html',
                  {'form': form, 'title': 'Add Fuel Expense'})


@login_required
def fuel_expense_update(request, pk):
    from accounts.permissions import user_owns
    expense = get_object_or_404(FuelExpense, pk=pk)
    if not user_owns(request.user, expense):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
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
    from customer_vehicles.models import CustomerVehicle
    from sales.models import SalesEnquiry, VehicleSalesOrder
    from service.models import JobCard
    try:
        from spares.models import SparesItem
    except ImportError:
        SparesItem = None

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

        results['customer_vehicles'] = list(
            CustomerVehicle.objects.select_related('customer', 'vehicle__bike_model').filter(
                Q(registration_no__icontains=q)
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

        if SparesItem:
            results['spare_parts'] = list(
                SparesItem.objects.filter(
                    Q(item_name__icontains=q) | Q(part_number__icontains=q) | Q(item_code__icontains=q)
                ).annotate(total_stock=Sum('stock__quantity'))[:5]
            )
        else:
            results['spare_parts'] = []

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
    from spares.models import CounterSale, PurchaseOrder, SparesItem, StockLedger

    today            = timezone.now().date()
    this_month_start = today.replace(day=1)

    parts_qs          = SparesItem.objects.filter(is_active=True)
    total_parts       = parts_qs.count()
    total_stock_value = (
        parts_qs.filter(mrp__isnull=False)
        .aggregate(val=Sum(F('mrp') * F('opening_stock')))['val'] or 0
    )

    low_stock_entries = StockLedger.objects.filter(quantity__lte=0)
    low_stock_count   = low_stock_entries.count()
    low_stock         = list(low_stock_entries.select_related('item').order_by('quantity')[:10])

    top_issued = []
    max_issued = 1

    po_summary = list(
        PurchaseOrder.objects
        .values('status')
        .annotate(count=Count('id'), total=Sum('total_amount'))
        .order_by('status')
    )

    cs_qs    = CounterSale.objects.filter(date__gte=this_month_start)
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


# ---------------------------------------------------------------------------
# FIX 6 — Insurance Expiry List
# ---------------------------------------------------------------------------

@login_required
def insurance_expiry_list(request):
    from customer_vehicles.models import CustomerVehicle

    today     = timezone.now().date()
    expiry_30 = today + datetime.timedelta(days=30)
    expiry_60 = today + datetime.timedelta(days=60)

    base = CustomerVehicle.objects.select_related(
        'customer', 'vehicle__bike_model'
    )

    already_expired = base.filter(insurance_expiry__lt=today).order_by('insurance_expiry')
    expiring_30_qs  = base.filter(
        insurance_expiry__gte=today, insurance_expiry__lte=expiry_30
    ).order_by('insurance_expiry')
    expiring_60_qs  = base.filter(
        insurance_expiry__gt=expiry_30, insurance_expiry__lte=expiry_60
    ).order_by('insurance_expiry')

    return render(request, 'accounts/insurance_expiry.html', {
        'already_expired':  already_expired,
        'expiring_30':      expiring_30_qs,
        'expiring_60':      expiring_60_qs,
        'today':            today,
    })


# ---------------------------------------------------------------------------
# Company Settings (singleton)
# ---------------------------------------------------------------------------

@login_required
def company_settings(request):
    if not _can_manage_settings(request.user):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    from .forms import CompanySettingsForm
    from .models import CompanySettings as CS
    instance = CS.get_instance()
    form = CompanySettingsForm(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request, 'Company Settings', 'update', instance.pk)
        messages.success(request, 'Company settings saved successfully.')
        return redirect('accounts:company_settings')
    return render(request, 'accounts/company_settings.html', {
        'form':    form,
        'company': instance,
    })


# ---------------------------------------------------------------------------
# Phase 8d — Discount Percentage Master & Ledger Creation Date Master
# (both singletons, combined on one settings page)
# ---------------------------------------------------------------------------

@login_required
def admin_settings(request):
    if not _can_manage_settings(request.user):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 — Access Denied</h1>')
    from .forms import DiscountPercentageMasterForm, LedgerCreationDateMasterForm
    from .models import DiscountPercentageMaster, LedgerCreationDateMaster
    discount_instance = DiscountPercentageMaster.get_instance()
    ledger_instance = LedgerCreationDateMaster.get_instance()
    is_discount_save = request.method == 'POST' and 'save_discount' in request.POST
    is_ledger_save = request.method == 'POST' and 'save_ledger' in request.POST
    discount_form = DiscountPercentageMasterForm(
        request.POST if is_discount_save else None, instance=discount_instance, prefix='discount',
    )
    ledger_form = LedgerCreationDateMasterForm(
        request.POST if is_ledger_save else None, instance=ledger_instance, prefix='ledger',
    )
    if is_discount_save and discount_form.is_valid():
        discount_form.save()
        log_action(request, 'Discount Percentage Master', 'update', discount_instance.pk)
        messages.success(request, 'Discount Percentage Master saved.')
        return redirect('accounts:admin_settings')
    if is_ledger_save and ledger_form.is_valid():
        ledger_form.save()
        log_action(request, 'Ledger Creation Date Master', 'update', ledger_instance.pk)
        messages.success(request, 'Ledger Creation Date Master saved.')
        return redirect('accounts:admin_settings')
    return render(request, 'accounts/admin_settings.html', {
        'discount_form': discount_form, 'ledger_form': ledger_form,
    })


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

from django.http import JsonResponse


@login_required
def notification_list(request):
    from .models import Notification
    from .notifications import generate_notifications
    generate_notifications(request.user)
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:50]
    # Mark all as read if ?mark_read=1
    if request.GET.get('mark_read'):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return redirect('accounts:notification_list')
    return render(request, 'accounts/notification_list.html', {
        'notifications': notifications,
    })


@login_required
def notification_count(request):
    from .models import Notification
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})


# ============================================================
# FEATURE 6 — GST Return Report
# ============================================================

@login_required
def gst_report(request):
    from billing.models import Invoice, Payment
    from service.models import ServiceInvoice
    from spares.models import CounterSale
    from django.db.models import Sum
    import calendar as _cal
    from django.utils import timezone as _tz
    today = _tz.now().date()

    month = int(request.GET.get('month', today.month))
    year  = int(request.GET.get('year',  today.year))

    vehicle_invoices = Invoice.objects.filter(
        invoice_date__month=month, invoice_date__year=year
    ).select_related('sales_order__customer', 'sales_order__vehicle__bike_model')

    service_invoices = ServiceInvoice.objects.filter(
        created_at__month=month, created_at__year=year
    ).select_related('job_card__customer_vehicle__customer')

    counter_sales = CounterSale.objects.filter(
        date__month=month, date__year=year, status='submitted'
    )

    vehicle_taxable = vehicle_invoices.aggregate(t=Sum('subtotal'))['t'] or 0
    vehicle_gst     = vehicle_invoices.aggregate(t=Sum('gst_amount'))['t'] or 0

    from accounts.models import CompanySettings as _CS
    context = {
        'month': month, 'year': year,
        'month_name': _cal.month_name[month],
        'vehicle_invoices': vehicle_invoices,
        'service_invoices': service_invoices,
        'counter_sales': counter_sales,
        'vehicle_taxable': vehicle_taxable,
        'vehicle_gst': vehicle_gst,
        'company': _CS.get_instance(),
    }
    return render(request, 'accounts/gst_report.html', context)
