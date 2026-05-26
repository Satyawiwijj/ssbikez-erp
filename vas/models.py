from django.db import models


class AMCPackage(models.Model):
    class Status(models.TextChoices):
        ACTIVE    = 'active',    'Active'
        EXPIRED   = 'expired',   'Expired'
        CANCELLED = 'cancelled', 'Cancelled'

    customer_vehicle = models.ForeignKey(
        'customer_vehicles.CustomerVehicle',
        on_delete=models.PROTECT,
        related_name='amc_packages'
    )
    package_name     = models.CharField(max_length=100)
    start_date       = models.DateField(blank=True, null=True)
    end_date         = models.DateField(blank=True, null=True)
    amount           = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status           = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'AMC Packages'

    def __str__(self):
        return f"AMC-{self.pk} | {self.customer_vehicle} — {self.package_name}"


class RSAPackage(models.Model):
    class Status(models.TextChoices):
        ACTIVE    = 'active',    'Active'
        EXPIRED   = 'expired',   'Expired'
        CANCELLED = 'cancelled', 'Cancelled'

    customer_vehicle = models.ForeignKey(
        'customer_vehicles.CustomerVehicle',
        on_delete=models.PROTECT,
        related_name='rsa_packages'
    )
    provider_name    = models.CharField(max_length=100, blank=True, null=True)
    start_date       = models.DateField(blank=True, null=True)
    end_date         = models.DateField(blank=True, null=True)
    amount           = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status           = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'RSA Packages'

    def __str__(self):
        return f"RSA-{self.pk} | {self.customer_vehicle} — {self.provider_name}"


class ProtectionPlusPackage(models.Model):
    class Status(models.TextChoices):
        ACTIVE    = 'active',    'Active'
        EXPIRED   = 'expired',   'Expired'
        CANCELLED = 'cancelled', 'Cancelled'

    customer_vehicle = models.ForeignKey(
        'customer_vehicles.CustomerVehicle',
        on_delete=models.PROTECT,
        related_name='protection_plus_packages'
    )
    package_name     = models.CharField(max_length=100, blank=True, null=True)
    provider_name    = models.CharField(max_length=100, blank=True, null=True)
    start_date       = models.DateField(blank=True, null=True)
    end_date         = models.DateField(blank=True, null=True)
    amount           = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status           = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Protection Plus Packages'

    def __str__(self):
        return f"PP-{self.pk} | {self.customer_vehicle} — {self.package_name}"
