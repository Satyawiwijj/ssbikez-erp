from django.conf import settings
from django.db import models


class ServiceEnquiry(models.Model):
    class Status(models.TextChoices):
        OPEN      = 'open',      'Open'
        SCHEDULED = 'scheduled', 'Scheduled'
        CLOSED    = 'closed',    'Closed'

    customer_vehicle  = models.ForeignKey(
        'customer_vehicles.CustomerVehicle',
        on_delete=models.PROTECT,
        related_name='service_enquiries'
    )
    created_by        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='service_enquiries_created'
    )
    issue_description = models.TextField(blank=True, null=True)
    status            = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN
    )
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Service Enquiries'

    def __str__(self):
        return f"SENQ-{self.pk} | {self.customer_vehicle}"


class ServiceAppointment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        NO_SHOW   = 'no_show',   'No Show'

    class ServiceType(models.TextChoices):
        FREE_SERVICE = 'free_service', 'Free Service'
        PAID_SERVICE = 'paid_service', 'Paid Service'
        ACCIDENTAL   = 'accidental',   'Accidental Repair'
        GENERAL      = 'general',      'General'

    service_enquiry  = models.ForeignKey(
        ServiceEnquiry,
        on_delete=models.CASCADE,
        related_name='appointments'
    )
    appointment_date = models.DateTimeField()
    service_type     = models.CharField(
        max_length=100,
        choices=ServiceType.choices,
        blank=True, null=True
    )
    status           = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED
    )
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-appointment_date']
        verbose_name_plural = 'Service Appointments'

    def __str__(self):
        return f"SAPT-{self.pk} | {self.service_enquiry.customer_vehicle} on {self.appointment_date:%d %b %Y}"


class JobCard(models.Model):
    class ServiceStatus(models.TextChoices):
        PENDING          = 'pending',          'Pending'
        WATER_WASH       = 'water_wash',       'Water Wash'
        IN_BAY           = 'in_bay',           'In Bay'
        IN_PROGRESS      = 'in_progress',      'In Progress'
        OUTWORK          = 'outwork',          'Outwork'
        FINAL_INSPECTION = 'final_inspection', 'Final Inspection'
        READY            = 'ready',            'Ready'
        INVOICED         = 'invoiced',         'Invoiced'

    customer_vehicle    = models.ForeignKey(
        'customer_vehicles.CustomerVehicle',
        on_delete=models.PROTECT,
        related_name='job_cards'
    )
    service_appointment = models.ForeignKey(
        ServiceAppointment,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='job_cards'
    )
    service_advisor     = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='job_cards_as_advisor'
    )
    floor_supervisor    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='job_cards_as_supervisor'
    )
    branch              = models.ForeignKey(
        'accounts.Branch',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='job_cards'
    )
    odometer_reading    = models.IntegerField(null=True, blank=True)
    problem_description = models.TextField(blank=True, null=True)
    service_status      = models.CharField(
        max_length=30,
        choices=ServiceStatus.choices,
        default=ServiceStatus.PENDING,
        db_index=True,
    )
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Job Cards'

    def __str__(self):
        return f"JC-{self.pk} | {self.customer_vehicle} — {self.service_status}"


class ServiceBay(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        OCCUPIED  = 'occupied',  'Occupied'

    bay_name   = models.CharField(max_length=100)
    status     = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['bay_name']
        verbose_name_plural = 'Service Bays'

    def __str__(self):
        return f"{self.bay_name} ({self.status})"


class BayAssignment(models.Model):
    class AssignmentStatus(models.TextChoices):
        ACTIVE    = 'active',    'Active'
        COMPLETED = 'completed', 'Completed'

    job_card          = models.ForeignKey(
        JobCard,
        on_delete=models.CASCADE,
        related_name='bay_assignments'
    )
    bay               = models.ForeignKey(
        ServiceBay,
        on_delete=models.PROTECT,
        related_name='assignments'
    )
    mechanic          = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='bay_assignments'
    )
    start_time        = models.DateTimeField(blank=True, null=True)
    end_time          = models.DateTimeField(blank=True, null=True)
    assignment_status = models.CharField(
        max_length=20,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.ACTIVE
    )
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Bay Assignments'

    def __str__(self):
        return f"BAY-{self.pk} | JC-{self.job_card_id} in {self.bay}"


class ServiceInvoice(models.Model):
    job_card        = models.OneToOneField(
        JobCard,
        on_delete=models.PROTECT,
        related_name='service_invoice'
    )
    subtotal        = models.DecimalField(max_digits=10, decimal_places=2)
    gst_amount      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_amount    = models.DecimalField(max_digits=10, decimal_places=2)
    invoice_date    = models.DateField()
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-invoice_date']
        verbose_name_plural = 'Service Invoices'

    def __str__(self):
        return f"SINV-{self.pk} | JC-{self.job_card_id} — Rs.{self.final_amount}"


class LaborCharge(models.Model):
    job_card     = models.ForeignKey(
        JobCard,
        on_delete=models.CASCADE,
        related_name='labor_charges'
    )
    service_name = models.CharField(max_length=255)
    labor_cost   = models.DecimalField(max_digits=10, decimal_places=2)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['service_name']
        verbose_name_plural = 'Labor Charges'

    def __str__(self):
        return f"{self.service_name} — Rs.{self.labor_cost} (JC-{self.job_card_id})"


class OutworkEntry(models.Model):
    class Status(models.TextChoices):
        ISSUED   = 'issued',   'Issued'
        RETURNED = 'returned', 'Returned'

    job_card         = models.ForeignKey(
        JobCard,
        on_delete=models.CASCADE,
        related_name='outwork_entries'
    )
    vendor_name      = models.CharField(max_length=255)
    work_description = models.TextField()
    issued_at        = models.DateTimeField(auto_now_add=True)
    returned_at      = models.DateTimeField(null=True, blank=True)
    cost             = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status           = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ISSUED
    )
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-issued_at']
        verbose_name_plural = 'Outwork Entries'

    def __str__(self):
        return f"Outwork-{self.pk} | JC-{self.job_card_id} — {self.vendor_name}"
