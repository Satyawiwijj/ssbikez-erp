from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class DocStatusMixin(models.Model):
    """
    Frappe-style draft/submitted/cancelled lifecycle for documents that need
    it (Sales Order, Delivery, Invoice, ...). Submitted documents are locked
    for editing; cancelling opens the door to an amended (new draft) copy
    that carries an `amended_from` trail back to the cancelled original.
    """
    class DocStatus(models.IntegerChoices):
        DRAFT     = 0, 'Draft'
        SUBMITTED = 1, 'Submitted'
        CANCELLED = 2, 'Cancelled'

    docstatus = models.PositiveSmallIntegerField(
        choices=DocStatus.choices, default=DocStatus.DRAFT, db_index=True
    )
    amended_from = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='amendments'
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )

    class Meta:
        abstract = True

    @property
    def is_draft(self):
        return self.docstatus == self.DocStatus.DRAFT

    @property
    def is_submitted(self):
        return self.docstatus == self.DocStatus.SUBMITTED

    @property
    def is_cancelled(self):
        return self.docstatus == self.DocStatus.CANCELLED

    def submit(self, user):
        from django.utils import timezone
        if self.docstatus != self.DocStatus.DRAFT:
            raise ValueError('Only a Draft document can be submitted.')
        self.docstatus = self.DocStatus.SUBMITTED
        self.submitted_at = timezone.now()
        self.submitted_by = user
        self.save()

    def cancel(self, user):
        from django.utils import timezone
        if self.docstatus != self.DocStatus.SUBMITTED:
            raise ValueError('Only a Submitted document can be cancelled.')
        self.docstatus = self.DocStatus.CANCELLED
        self.cancelled_at = timezone.now()
        self.cancelled_by = user
        self.save()

    # Subclasses with an auto-generated unique "number" field (e.g. order_number,
    # populated only `if not self.<field>` in save()) should set this so the
    # amended copy gets a fresh number instead of colliding with the original.
    _amend_reset_number_field = None

    def amend(self):
        """Create and return a new Draft copy linked back via amended_from."""
        import copy
        if self.docstatus != self.DocStatus.CANCELLED:
            raise ValueError('Only a Cancelled document can be amended.')
        new = copy.copy(self)
        new.pk = None
        new.id = None
        new._state.adding = True
        new.docstatus = self.DocStatus.DRAFT
        new.amended_from = self
        new.submitted_at = new.submitted_by = None
        new.cancelled_at = new.cancelled_by = None
        if self._amend_reset_number_field:
            setattr(new, self._amend_reset_number_field, '')
        new.save()
        return new


class Branch(models.Model):
    branch_name = models.CharField(max_length=100)
    address     = models.TextField(blank=True, null=True)
    phone       = models.CharField(max_length=15, blank=True, null=True)
    gstin       = models.CharField(max_length=20, blank=True, null=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['branch_name']
        verbose_name_plural = 'Branches'

    def __str__(self):
        return self.branch_name


class Role(models.Model):
    role_name   = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['role_name']
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.role_name


class User(AbstractUser):
    """
    Custom user model — replaces Django's default User.
    AUTH_USER_MODEL = 'accounts.User' must be in settings.py
    before the very first migration.
    """
    class Status(models.TextChoices):
        ACTIVE   = 'active',   'Active'
        INACTIVE = 'inactive', 'Inactive'

    role   = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='users'
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='users'
    )
    phone  = models.CharField(max_length=15, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until           = models.DateTimeField(null=True, blank=True)
    last_password_reset_request_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['first_name', 'last_name']
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"


class CompanySettings(models.Model):
    """Singleton model storing company-wide configuration."""
    company_name  = models.CharField(max_length=200, default='SS Bikez')
    tagline       = models.CharField(max_length=200, blank=True, default='Motorcycle Dealership')
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city          = models.CharField(max_length=100, blank=True)
    state         = models.CharField(max_length=100, blank=True)
    pincode       = models.CharField(max_length=10, blank=True)
    phone         = models.CharField(max_length=20, blank=True)
    email         = models.EmailField(blank=True)
    gstin         = models.CharField(max_length=20, blank=True)
    pan_number    = models.CharField(max_length=20, blank=True)
    logo_url      = models.URLField(blank=True)
    gst_rate      = models.DecimalField(max_digits=5, decimal_places=2, default=18)
    cgst_rate     = models.DecimalField(max_digits=5, decimal_places=2, default=9)
    sgst_rate     = models.DecimalField(max_digits=5, decimal_places=2, default=9)
    # IGST applies instead of CGST+SGST for interstate sales (customer.state
    # != CompanySettings.state). Defaults to cgst_rate + sgst_rate (9+9) so a
    # freshly-migrated singleton stays consistent with the existing rates
    # rather than silently being 0.
    igst_rate     = models.DecimalField(max_digits=5, decimal_places=2, default=18)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Company Settings'
        verbose_name_plural = 'Company Settings'

    def __str__(self):
        return self.company_name

    def save(self, *args, **kwargs):
        # Force singleton: always pk=1
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class DiscountPercentageMaster(models.Model):
    """Reference: 'Discount Percentage Master' (workspace label 'Service
    Invoice Discount Percentage') -- singleton via pk=1, same pattern as
    CompanySettings.get_instance(). No current consumer -- LaborChargesAlteration/
    OutworkEntryReturn/SparesIssueAlteration don't auto-apply a global discount
    today (flagged, not wired this phase)."""
    labor_charge_discount            = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    out_work_return_discount         = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    spares_issue_alteration_discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        verbose_name        = 'Discount Percentage Master'
        verbose_name_plural = 'Discount Percentage Master'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'Discount Percentage Master'


class LedgerCreationDateMaster(models.Model):
    """Reference: 'Ledger Creation Date Master' (workspace label 'Voucher
    Creation Date Master') -- singleton via pk=1. No current consumer -- the
    reference's 'Ledger Creation' doctype this gates hasn't been built in
    Django yet (flagged, not wired this phase)."""
    allowed_days = models.IntegerField(default=0)

    class Meta:
        verbose_name        = 'Ledger Creation Date Master'
        verbose_name_plural = 'Ledger Creation Date Master'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'Ledger Creation Date Master'


class FuelExpense(models.Model):
    vehicle        = models.ForeignKey(
        'customers.VehicleStock',
        on_delete=models.PROTECT,
        related_name='fuel_expenses'
    )
    amount         = models.DecimalField(max_digits=10, decimal_places=2)
    fuel_date      = models.DateField()
    voucher_number = models.CharField(max_length=100, blank=True, null=True)
    remarks        = models.TextField(blank=True, null=True)
    created_by     = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='fuel_expenses_created'
    )
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fuel_date']
        verbose_name_plural = 'Fuel Expenses'

    def __str__(self):
        return f"FUEL-{self.pk} | {self.vehicle} — Rs.{self.amount} on {self.fuel_date}"


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = 'create', 'Create'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'
        VIEW   = 'view',   'View'

    user        = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs'
    )
    module_name = models.CharField(max_length=100)
    action_name = models.CharField(max_length=100, choices=Action.choices)
    record_id   = models.IntegerField(null=True, blank=True)
    ip_address  = models.CharField(max_length=100, blank=True, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        return f"{self.action_name} by {self.user or 'a deleted user'} on {self.module_name} #{self.record_id}"

import secrets
from django.utils import timezone

class OTPVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    otp_code = models.CharField(max_length=6)
    action = models.CharField(max_length=100) # e.g. "discount_approval"
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_otp(self):
        from django.core.mail import send_mail
        from django.conf import settings

        self.otp_code = f"{100000 + secrets.randbelow(900000)}"
        self.expires_at = timezone.now() + timezone.timedelta(minutes=10)
        self.save()

        subject = 'Your SSBikez ERP Login OTP'
        message = (
            f'Hello {self.user.first_name or self.user.username},\n\n'
            f'Your OTP for login is: {self.otp_code}\n\n'
            f'This code is valid for the next 10 minutes.\n\nSSBikez ERP Team'
        )
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@ssbikez.com')
        recipient_list = [self.user.email]

        try:
            send_mail(subject, message, from_email, recipient_list, fail_silently=False)
            print(f"--- OTP email dispatched to {self.user.email} ---")
            return True
        except Exception as e:
            # Never log the actual OTP code -- it's a 2FA secret. The caller
            # already fails closed (deletes this record, blocks the login)
            # when email dispatch fails, so there's no legitimate need for
            # the code to appear anywhere outside the sent email itself.
            print(f"Failed to send OTP email to {self.user.email}: {e}")
            return False

    class Meta:
        ordering = ['-created_at']


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

class Notification(models.Model):
    class Level(models.TextChoices):
        INFO    = 'info',    'Info'
        WARNING = 'warning', 'Warning'
        ERROR   = 'error',   'Error'

    user       = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True, blank=True,
    )
    title      = models.CharField(max_length=200)
    message    = models.TextField(blank=True)
    level      = models.CharField(max_length=20, choices=Level.choices, default=Level.INFO)
    is_read    = models.BooleanField(default=False)
    link       = models.CharField(max_length=500, blank=True, help_text='Optional URL to navigate to')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"[{self.level}] {self.title}"


# ---------------------------------------------------------------------------
# ModulePermission — page/module-level access on top of role permissions
# ---------------------------------------------------------------------------

MODULE_CHOICES = (
    ('sales',          'Sales'),
    ('customers',      'Customers'),
    ('finance',        'Finance / Billing'),
    ('rto',            'RTO'),
    ('service',        'Service'),
    ('spares',         'Spares'),
    ('vas',            'Value Added Services'),
    ('vehicle_master', 'Vehicle Master'),
    ('masters',        'Masters'),
    ('used_vehicles',  'Used Vehicles'),
    ('reports',        'Reports'),
    ('admin',          'Admin'),
)


class ModulePermission(models.Model):
    """
    Per-role override for module-level access, at Create/Read(Display)/
    Edit/Delete granularity — matches the reference ERP's per-role
    permission matrix (Display / Edit / Create / Delete checkboxes per
    module).

    A role's base access comes from accounts.permissions.ROLE_PERMISSIONS.
    A row here narrows that further: any flag set to False here blocks that
    action for that role even if the role would otherwise have it. Absence
    of a row, or an absent flag, means "use the role default" (allowed).
    """
    role        = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='module_permissions')
    module      = models.CharField(max_length=30, choices=MODULE_CHOICES)
    can_view    = models.BooleanField(default=True, verbose_name='Display')
    can_create  = models.BooleanField(default=True, verbose_name='Create')
    can_edit    = models.BooleanField(default=True, verbose_name='Edit')
    can_delete  = models.BooleanField(default=True, verbose_name='Delete')
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('role', 'module')
        ordering = ['role__role_name', 'module']
        verbose_name_plural = 'Module Permissions'

    def __str__(self):
        flags = ', '.join(
            label for label, val in (
                ('Display', self.can_view), ('Create', self.can_create),
                ('Edit', self.can_edit), ('Delete', self.can_delete),
            ) if val
        ) or 'No access'
        return f"{self.role} — {self.get_module_display()}: {flags}"
