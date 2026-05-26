from django.contrib.auth.models import AbstractUser
from django.db import models


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
        return f"{self.action_name} by {self.user} on {self.module_name} #{self.record_id}"

import random
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
        
        self.otp_code = f"{random.randint(100000, 999999)}"
        self.expires_at = timezone.now() + timezone.timedelta(minutes=10)
        self.save()
        
        subject = 'Your SSBikez ERP Login OTP'
        message = f'Hello {self.user.first_name or self.user.username},\n\nYour OTP for login is: {self.otp_code}\n\nThis code is valid for the next 10 minutes.\n\nThank you,\nSSBikez ERP Team'
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@ssbikez.com')
        recipient_list = [self.user.email]
        
        try:
            send_mail(subject, message, from_email, recipient_list, fail_silently=False)
            print(f"--- OTP email dispatched to {self.user.email} ---")
        except Exception as e:
            print(f"Failed to send email: {e}")
            # Fallback print for local dev if email fails
            print(f"--- FALLBACK MOCK OTP for {self.user.email} is {self.otp_code} ---")

    class Meta:
        ordering = ['-created_at']
