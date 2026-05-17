from django.db import models


class RTORegistration(models.Model):
    class RegistrationStatus(models.TextChoices):
        PENDING    = 'pending',    'Pending'
        SUBMITTED  = 'submitted',  'Submitted'
        REGISTERED = 'registered', 'Registered'

    sales_order         = models.OneToOneField(
        'sales.VehicleSalesOrder',
        on_delete=models.PROTECT,
        related_name='rto_registration'
    )
    form20_number       = models.CharField(max_length=100, blank=True, null=True)
    registration_number = models.CharField(max_length=100, blank=True, null=True)
    rto_charges         = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    registration_status = models.CharField(
        max_length=20,
        choices=RegistrationStatus.choices,
        default=RegistrationStatus.PENDING
    )
    created_at          = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'RTO Registrations'

    def __str__(self):
        return f"RTO-{self.pk} | {self.registration_number or 'Pending'}"


class NumberPlateOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ORDERED = 'ordered', 'Ordered'
        ISSUED  = 'issued',  'Issued'

    rto         = models.OneToOneField(
        RTORegistration,
        on_delete=models.PROTECT,
        related_name='number_plate_order'
    )
    plate_number = models.CharField(max_length=50, blank=True, null=True)
    vendor_name  = models.CharField(max_length=100, blank=True, null=True)
    issue_date   = models.DateField(blank=True, null=True)
    status       = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Number Plate Orders'

    def __str__(self):
        return f"PLATE-{self.pk} | {self.plate_number or 'Unassigned'}"
