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
        null=True, blank=True,   # nullable — single-branch works without it
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
