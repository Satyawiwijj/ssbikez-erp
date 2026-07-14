from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import Sum

from accounts.models import DocStatusMixin


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

    service_enquiry         = models.ForeignKey(
        ServiceEnquiry,
        on_delete=models.CASCADE,
        related_name='appointments'
    )
    appointment_date        = models.DateTimeField()
    service_type            = models.CharField(
        max_length=100,
        choices=ServiceType.choices,
        blank=True, null=True
    )
    status                  = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED
    )
    # ERP-matched fields
    phone_no                = models.CharField(max_length=20, blank=True, default='')
    whatsapp_no             = models.CharField(max_length=20, blank=True, default='')
    chassis_no              = models.CharField(max_length=50, blank=True, default='', verbose_name='Chassis No')
    vehicle_name            = models.CharField(max_length=200, blank=True, default='')
    is_cancelled_postponed  = models.BooleanField(default=False, verbose_name='Appointment Cancel/Postponed')
    created_at              = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-appointment_date']
        verbose_name_plural = 'Service Appointments'

    def __str__(self):
        return f"SAPT-{self.pk} | {self.service_enquiry.customer_vehicle} on {self.appointment_date:%d %b %Y}"


class JobCard(DocStatusMixin, models.Model):
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
    class Status(models.TextChoices):
        DRAFT  = 'draft',  'Draft'
        ISSUED = 'issued', 'Issued'
        PAID   = 'paid',   'Paid'

    job_card        = models.OneToOneField(
        JobCard,
        on_delete=models.PROTECT,
        related_name='service_invoice'
    )
    invoice_number  = models.CharField(max_length=100, unique=True, blank=True, null=True)
    labor_total     = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    spares_total    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    outwork_total   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal        = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gst_amount      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_amount    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status          = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    invoice_date    = models.DateField(auto_now_add=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Service Invoices'

    def __str__(self):
        return f"SINV-{self.pk} | JC-{self.job_card_id} — Rs.{self.final_amount}"

    def calculate_totals(self):
        """Recalculate all totals from related labor, spares, and outwork."""
        self.labor_total = (
            self.job_card.labor_charges.aggregate(total=Sum('labor_cost'))['total']
            or Decimal('0.00')
        )

        # Spares total is now managed via spares.SparesIssueAlteration; set to 0 here
        self.spares_total = Decimal('0.00')

        self.outwork_total = (
            self.job_card.outwork_entries.aggregate(total=Sum('cost'))['total']
            or Decimal('0.00')
        )

        subtotal       = self.labor_total + self.spares_total + self.outwork_total
        self.subtotal  = subtotal

        # GAP 12: read GST rate from CompanySettings
        gst_rate = Decimal('18')
        try:
            from accounts.models import CompanySettings
            gst_rate = Decimal(str(CompanySettings.get_instance().gst_rate or 18))
        except Exception:
            pass
        self.gst_amount = (subtotal * gst_rate / Decimal('100')).quantize(Decimal('0.01'))

        # GAP 11: auto-apply ServiceDiscountMaster (if no manual discount)
        if (not self.discount_amount) and self.job_card.service_appointment_id:
            try:
                stype = self.job_card.service_appointment.service_type
                if stype:
                    sdm = ServiceDiscountMaster.objects.filter(
                        service_type=stype, is_active=True
                    ).first()
                    if sdm and sdm.discount_percent:
                        self.discount_amount = (
                            subtotal * sdm.discount_percent / Decimal('100')
                        ).quantize(Decimal('0.01'))
            except Exception:
                pass

        self.final_amount = subtotal + self.gst_amount - (self.discount_amount or Decimal('0.00'))
        self.save(update_fields=[
            'labor_total', 'spares_total', 'outwork_total',
            'subtotal', 'gst_amount', 'final_amount', 'discount_amount',
        ])


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


# ---------------------------------------------------------------------------
# Warranty Claim
# ---------------------------------------------------------------------------

class WarrantyClaim(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        APPROVED  = 'approved',  'Approved'
        REJECTED  = 'rejected',  'Rejected'
        SETTLED   = 'settled',   'Settled'

    job_card        = models.ForeignKey(
        JobCard,
        on_delete=models.CASCADE,
        related_name='warranty_claims'
    )
    claim_number    = models.CharField(max_length=100, blank=True, unique=True)
    claim_date      = models.DateField(auto_now_add=True)
    description     = models.TextField()
    claimed_amount  = models.DecimalField(max_digits=10, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status          = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.SUBMITTED
    )
    notes           = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Warranty Claims'

    def save(self, *args, **kwargs):
        if not self.claim_number:
            with transaction.atomic():
                last = WarrantyClaim.objects.select_for_update().order_by('-id').first()
                num  = (last.id + 1) if last else 1
                self.claim_number = f"WC-{num:05d}"
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.claim_number


# ---------------------------------------------------------------------------
# Insurance Estimation
# ---------------------------------------------------------------------------

class InsuranceEstimation(models.Model):
    class Status(models.TextChoices):
        DRAFT    = 'draft',    'Draft'
        SENT     = 'sent',     'Sent to Insurance'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    job_card          = models.ForeignKey(
        JobCard,
        on_delete=models.CASCADE,
        related_name='insurance_estimations'
    )
    insurance_company = models.CharField(max_length=200)
    policy_number     = models.CharField(max_length=100, blank=True)
    estimation_date   = models.DateField(auto_now_add=True)
    labour_estimate   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    spares_estimate   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_estimate    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    approved_amount   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status            = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.DRAFT
    )
    notes             = models.TextField(blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Insurance Estimations'

    def save(self, *args, **kwargs):
        self.total_estimate = (self.labour_estimate or 0) + (self.spares_estimate or 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"IE-{self.pk} | JC-{self.job_card_id}"


# ---------------------------------------------------------------------------
# Service Discount Master
# ---------------------------------------------------------------------------

class ServiceDiscountMaster(models.Model):
    service_type     = models.CharField(max_length=100, unique=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    is_active        = models.BooleanField(default=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['service_type']
        verbose_name_plural = 'Service Discount Master'

    def __str__(self):
        return f"{self.service_type} — {self.discount_percent}%"


# ---------------------------------------------------------------------------
# GAP 14 — Job Card Revisit
# ---------------------------------------------------------------------------

class JobCardRevisit(models.Model):
    job_card          = models.OneToOneField(
        JobCard, on_delete=models.CASCADE, related_name='revisit'
    )
    next_service_km   = models.IntegerField(help_text="Odometer reading for next service")
    next_service_days = models.IntegerField(help_text="Days until next service")
    next_service_date = models.DateField(null=True, blank=True)
    notes             = models.TextField(blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.next_service_days and not self.next_service_date:
            from datetime import timedelta
            base = self.job_card.created_at.date() if self.job_card.created_at else None
            if base:
                self.next_service_date = base + timedelta(days=self.next_service_days)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Revisit JC-{self.job_card_id} at {self.next_service_km}km"


# ---------------------------------------------------------------------------
# GAP 15 — Job Card Service Childs (Sub-tasks)
# ---------------------------------------------------------------------------

class JobCardServiceChild(models.Model):
    class Status(models.TextChoices):
        PENDING     = 'pending',     'Pending'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED   = 'completed',   'Completed'
        SKIPPED     = 'skipped',     'Skipped'

    job_card     = models.ForeignKey(
        JobCard, on_delete=models.CASCADE, related_name='service_childs'
    )
    task_name    = models.CharField(max_length=200)
    description  = models.TextField(blank=True)
    assigned_to  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    status       = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.task_name} — {self.status}"


# ---------------------------------------------------------------------------
# GAP 23 — Customer Call Log
# ---------------------------------------------------------------------------

class CustomerCall(models.Model):
    class Outcome(models.TextChoices):
        INTERESTED     = 'interested',     'Interested'
        NOT_INTERESTED = 'not_interested', 'Not Interested'
        CALLBACK       = 'callback',       'Callback Later'
        NO_ANSWER      = 'no_answer',      'No Answer'
        BOOKED         = 'booked',         'Appointment Booked'

    customer_vehicle = models.ForeignKey(
        'customer_vehicles.CustomerVehicle',
        on_delete=models.CASCADE, related_name='calls'
    )
    called_by       = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    call_date       = models.DateTimeField(auto_now_add=True)
    purpose         = models.CharField(max_length=200)
    notes           = models.TextField(blank=True)
    outcome         = models.CharField(max_length=20, choices=Outcome.choices)
    next_call_date  = models.DateField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-call_date']

    def __str__(self):
        return f"Call-{self.pk} | {self.customer_vehicle} — {self.outcome}"


# ---------------------------------------------------------------------------
# GAP 26 — Insurance Claim
# ---------------------------------------------------------------------------

class InsuranceClaim(models.Model):
    class Status(models.TextChoices):
        SUBMITTED    = 'submitted',    'Submitted'
        UNDER_REVIEW = 'under_review', 'Under Review'
        APPROVED     = 'approved',     'Approved'
        REJECTED     = 'rejected',     'Rejected'
        SETTLED      = 'settled',      'Settled'

    job_card             = models.ForeignKey(
        JobCard, on_delete=models.CASCADE, related_name='insurance_claims'
    )
    insurance_estimation = models.ForeignKey(
        InsuranceEstimation, on_delete=models.SET_NULL, null=True, blank=True
    )
    claim_number      = models.CharField(max_length=100)
    insurance_company = models.CharField(max_length=200)
    policy_number     = models.CharField(max_length=100)
    claim_amount      = models.DecimalField(max_digits=10, decimal_places=2)
    approved_amount   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status            = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SUBMITTED
    )
    settlement_date   = models.DateField(null=True, blank=True)
    notes             = models.TextField(blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"IC-{self.pk} | {self.claim_number}"


# ---------------------------------------------------------------------------
# GAP 30 — Additional Work Approval
# ---------------------------------------------------------------------------

class AdditionalWorkApproval(models.Model):
    class Status(models.TextChoices):
        PENDING  = 'pending',  'Pending Approval'
        SENT     = 'sent',     'Sent to Customer'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    job_card           = models.ForeignKey(
        JobCard, on_delete=models.CASCADE, related_name='additional_approvals'
    )
    description        = models.TextField(help_text="Description of additional work needed")
    estimated_labour   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estimated_spares   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estimated_total    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    customer_response  = models.TextField(blank=True)
    status             = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    sent_at            = models.DateTimeField(null=True, blank=True)
    responded_at       = models.DateTimeField(null=True, blank=True)
    created_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        self.estimated_total = (self.estimated_labour or 0) + (self.estimated_spares or 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"AWA-{self.pk} | JC-{self.job_card_id} — {self.status}"


# ---------------------------------------------------------------------------
# FEATURE 4 — Service Reminder Auto-Generation
# ---------------------------------------------------------------------------

class ServiceReminder(models.Model):
    class Status(models.TextChoices):
        PENDING        = 'pending',        'Pending Call'
        CALLED         = 'called',         'Called'
        BOOKED         = 'booked',         'Appointment Booked'
        NOT_INTERESTED = 'not_interested', 'Not Interested'
        NO_ANSWER      = 'no_answer',      'No Answer'

    REMINDER_TYPE_CHOICES = [
        ('free_service',    'Free Service Due'),
        ('paid_service',    'Paid Service Due'),
        ('insurance_expiry','Insurance Expiry'),
        ('amc_renewal',     'AMC Renewal'),
        ('warranty_expiry', 'Warranty Expiry'),
    ]

    customer_vehicle = models.ForeignKey(
        'customer_vehicles.CustomerVehicle',
        on_delete=models.CASCADE, related_name='service_reminders'
    )
    reminder_date    = models.DateField()
    reminder_type    = models.CharField(max_length=50, choices=REMINDER_TYPE_CHOICES)
    due_km           = models.IntegerField(null=True, blank=True)
    notes            = models.TextField(blank=True)
    status           = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    assigned_to      = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='service_reminders'
    )
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['reminder_date']

    def __str__(self):
        return f"SR-{self.pk} | {self.customer_vehicle} | {self.reminder_type}"


# ---------------------------------------------------------------------------
# ERP Alignment — Vehicle Service Master
# ---------------------------------------------------------------------------

class VehicleServiceMaster(models.Model):
    bike_model   = models.OneToOneField(
        'customers.BikeModel',
        on_delete=models.CASCADE,
        related_name='service_master',
        verbose_name='Vehicle / Bike Model'
    )
    vehicle_code = models.CharField(max_length=50, blank=True, default='', verbose_name='Vehicle Code')

    class Meta:
        verbose_name = 'Vehicle Service Master'

    def __str__(self):
        return f'{self.bike_model.model_name} Service Schedule'


class VehicleServiceSchedule(models.Model):
    SERVICE_TYPES = [
        ('Free Service 1', 'Free Service 1'),
        ('Free Service 2', 'Free Service 2'),
        ('Free Service 3', 'Free Service 3'),
        ('Paid Service', 'Paid Service'),
        ('General Checkup', 'General Checkup'),
    ]
    master             = models.ForeignKey(
        VehicleServiceMaster,
        on_delete=models.CASCADE,
        related_name='schedules'
    )
    service_type       = models.CharField(max_length=100, choices=SERVICE_TYPES, verbose_name='Service Type')
    days_from_purchase = models.IntegerField(verbose_name='Service Days from Purchase')
    km_from_purchase   = models.IntegerField(verbose_name='Service KM from Purchase')

    class Meta:
        ordering = ['days_from_purchase']
        verbose_name = 'Service Schedule'

    def __str__(self):
        return f'{self.master} — {self.service_type}'


# ---------------------------------------------------------------------------
# Phase 2 — Reference-parity workshop stage documents. The reference ERP
# implements each workshop stage as its own separate Submittable document
# linking back to the Job Card (not just a single status field). Submitting
# each stage document advances JobCard.service_status via a post_save signal,
# same pattern as sales.models.on_delivery_created from Phase 1.
# ---------------------------------------------------------------------------

def _advance_job_card_status(job_card, new_status):
    if job_card.service_status != new_status:
        job_card.service_status = new_status
        job_card.save(update_fields=['service_status'])


class WaterWashDone(DocStatusMixin, models.Model):
    job_card        = models.ForeignKey(JobCard, on_delete=models.PROTECT, related_name='water_wash_entries')
    register_number = models.CharField(max_length=50, blank=True)
    vehicle_code    = models.CharField(max_length=100, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Water Wash Done'

    def __str__(self):
        return f"WWD-{self.pk} | JC-{self.job_card_id}"


class BayInCreation(DocStatusMixin, models.Model):
    job_card     = models.ForeignKey(JobCard, on_delete=models.PROTECT, related_name='bay_in_entries')
    mechanic     = models.ForeignKey(
        'masters.Supplier', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='bay_in_entries', help_text='Filtered to supplier_group=Labor'
    )
    vehicle_code = models.CharField(max_length=100, blank=True)
    register_no  = models.CharField(max_length=50, blank=True)
    date_time    = models.DateTimeField()
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Bay In Creation'
        verbose_name_plural = 'Bay In Creations'

    def __str__(self):
        return f"BAYIN-{self.pk} | JC-{self.job_card_id}"


class BayOutCreation(DocStatusMixin, models.Model):
    job_card     = models.ForeignKey(JobCard, on_delete=models.PROTECT, related_name='bay_out_entries')
    mechanic     = models.ForeignKey(
        'masters.Supplier', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='bay_out_entries'
    )
    vehicle_code = models.CharField(max_length=100, blank=True)
    remarks      = models.TextField()
    date_time    = models.DateTimeField()
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Bay Out Creation'
        verbose_name_plural = 'Bay Out Creations'

    def __str__(self):
        return f"BAYOUT-{self.pk} | JC-{self.job_card_id}"


class FinalInspection(DocStatusMixin, models.Model):
    job_card                 = models.ForeignKey(JobCard, on_delete=models.PROTECT, related_name='final_inspections')
    rework                   = models.BooleanField(default=False)
    vehicle_name             = models.CharField(max_length=200, blank=True)
    chasis_number            = models.CharField(max_length=100, blank=True)
    mechanic_name            = models.CharField(max_length=200, blank=True)
    register_number          = models.CharField(max_length=50, blank=True)
    final_inspection_remarks = models.TextField()
    revisit                  = models.BooleanField(default=False)
    created_at               = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Final Inspections'

    def __str__(self):
        return f"FI-{self.pk} | JC-{self.job_card_id}"


class OutworkEntryIssue(DocStatusMixin, models.Model):
    class GatePass(models.TextChoices):
        YES = 'yes', 'Yes'
        NO  = 'no',  'No'

    job_card    = models.ForeignKey(JobCard, on_delete=models.PROTECT, related_name='outwork_issues')
    vendor_name = models.ForeignKey('masters.Supplier', on_delete=models.PROTECT, related_name='outwork_issues')
    godown      = models.ForeignKey('masters.Warehouse', on_delete=models.SET_NULL, null=True, blank=True, related_name='outwork_issues')
    gate_pass   = models.CharField(max_length=5, choices=GatePass.choices, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Outwork Entry Issues'

    def __str__(self):
        return f"OWI-{self.pk} | JC-{self.job_card_id} — {self.vendor_name}"

    @property
    def total_amount(self):
        return self.work_details.aggregate(t=Sum('total_amount'))['t'] or Decimal('0.00')


class OutworkWorkDetail(models.Model):
    outwork_issue = models.ForeignKey(OutworkEntryIssue, on_delete=models.CASCADE, related_name='work_details')
    work_name     = models.CharField(max_length=200, blank=True)
    party         = models.ForeignKey('customers.Customer', on_delete=models.SET_NULL, null=True, blank=True)
    quantity      = models.DecimalField(max_digits=10, decimal_places=2, default=1, blank=True)
    amount        = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    tax           = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True, verbose_name='Tax (%)')
    total_amount  = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    work_type     = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name_plural = 'Outwork Work Details'

    def __str__(self):
        return f"{self.work_name} — Rs.{self.total_amount}"


class OutworkSpareItem(models.Model):
    outwork_issue = models.ForeignKey(OutworkEntryIssue, on_delete=models.CASCADE, related_name='outwork_spares')
    item          = models.ForeignKey('spares.SparesItem', on_delete=models.PROTECT)
    rack          = models.ForeignKey('masters.Rack', on_delete=models.SET_NULL, null=True, blank=True)
    bin           = models.ForeignKey('masters.Bin', on_delete=models.SET_NULL, null=True, blank=True)
    quantity      = models.DecimalField(max_digits=10, decimal_places=3, default=1, blank=True)
    rate          = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    sgst          = models.DecimalField(max_digits=5, decimal_places=2, default=9, blank=True)
    cgst          = models.DecimalField(max_digits=5, decimal_places=2, default=9, blank=True)
    total         = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    class Meta:
        verbose_name_plural = 'Outwork Spare Items'

    def __str__(self):
        return f"{self.item} x {self.quantity}"


class OutworkEntryReturn(DocStatusMixin, models.Model):
    class PaymentType(models.TextChoices):
        ADJUSTMENT = 'adjustment', 'Adjustment'
        CASH       = 'cash',       'Cash'

    outwork_issue     = models.ForeignKey(OutworkEntryIssue, on_delete=models.PROTECT, related_name='returns')
    job_card          = models.ForeignKey(JobCard, on_delete=models.PROTECT, related_name='outwork_returns')
    rework            = models.BooleanField(default=False)
    payment_type      = models.CharField(max_length=20, choices=PaymentType.choices, blank=True)
    supplier          = models.ForeignKey('masters.Supplier', on_delete=models.SET_NULL, null=True, blank=True, related_name='outwork_returns')
    issue_spares_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, blank=True,
        help_text='Snapshot of the linked Outwork Entry Issue spares total, auto-set on save'
    )
    actual_amount     = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    billing_amount    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vendor_spares_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    total             = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, blank=True,
        help_text='issue_spares_amount + actual_amount + billing_amount, matching the reference formula'
    )
    pending_amount    = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Outwork Entry Returns'

    def __str__(self):
        return f"OWR-{self.pk} | JC-{self.job_card_id}"

    def save(self, *args, **kwargs):
        if self.outwork_issue_id:
            self.issue_spares_amount = self.outwork_issue.outwork_spares.aggregate(
                t=Sum('total')
            )['t'] or Decimal('0.00')
        self.total = (self.issue_spares_amount or 0) + (self.actual_amount or 0) + (self.billing_amount or 0)
        super().save(*args, **kwargs)


class OutworkReturnDetail(models.Model):
    outwork_return = models.ForeignKey(OutworkEntryReturn, on_delete=models.CASCADE, related_name='outwork_details')
    work_name      = models.CharField(max_length=200, blank=True)
    quantity       = models.DecimalField(max_digits=10, decimal_places=2, default=1, blank=True)
    amount         = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    class Meta:
        verbose_name_plural = 'Outwork Return Details'

    def __str__(self):
        return f"{self.work_name} — Rs.{self.amount}"


class OutworkReturnSpareItem(models.Model):
    outwork_return = models.ForeignKey(OutworkEntryReturn, on_delete=models.CASCADE, related_name='out_work_issue_spares_list')
    item           = models.ForeignKey('spares.SparesItem', on_delete=models.PROTECT)
    quantity       = models.DecimalField(max_digits=10, decimal_places=3, default=1, blank=True)
    rate           = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    total          = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    class Meta:
        verbose_name_plural = 'Outwork Return Spare Items'

    def __str__(self):
        return f"{self.item} x {self.quantity}"


class LaborChargesAlteration(DocStatusMixin, models.Model):
    job_card      = models.ForeignKey(JobCard, on_delete=models.PROTECT, related_name='labor_alterations')
    labours_name  = models.ForeignKey(
        'masters.Supplier', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='labor_alterations', verbose_name='Labour Name (Spares Used Mechanic)'
    )
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Labor Charges Alterations'

    def __str__(self):
        return f"LCA-{self.pk} | JC-{self.job_card_id}"

    @property
    def total_amount(self):
        return self.labor_details.aggregate(t=Sum('total'))['t'] or Decimal('0.00')


class LaborDetailLine(models.Model):
    alteration      = models.ForeignKey(LaborChargesAlteration, on_delete=models.CASCADE, related_name='labor_details')
    labor_name      = models.ForeignKey('masters.LabourWork', on_delete=models.PROTECT, verbose_name='Labor Work')
    quantity        = models.DecimalField(max_digits=10, decimal_places=2, default=1, blank=True)
    amount          = models.DecimalField(max_digits=10, decimal_places=2)
    sgst            = models.DecimalField(max_digits=5, decimal_places=2, default=9, blank=True)
    cgst            = models.DecimalField(max_digits=5, decimal_places=2, default=9, blank=True)
    total           = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    discount        = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    class Meta:
        verbose_name_plural = 'Labor Detail Lines'

    def __str__(self):
        return f"{self.labor_name} — Rs.{self.total}"


class LaborSpareItem(models.Model):
    alteration = models.ForeignKey(LaborChargesAlteration, on_delete=models.CASCADE, related_name='spares_used')
    item       = models.ForeignKey('spares.SparesItem', on_delete=models.PROTECT)
    quantity   = models.DecimalField(max_digits=10, decimal_places=3, default=1, blank=True)
    rate       = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    total      = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    class Meta:
        verbose_name_plural = 'Labor Spare Items'

    def __str__(self):
        return f"{self.item} x {self.quantity}"


# ---------------------------------------------------------------------------
# Phase 4 — Job Card inspection-checklist child tables (embedded directly in
# Job Card Creation in the reference, not separate stage documents).
# ---------------------------------------------------------------------------

class ComplaintDetail(models.Model):
    class Status(models.TextChoices):
        PENDING   = 'pending',   'Pending'
        COMPLETED = 'completed', 'Completed'

    job_card           = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name='complaint_details')
    customer_complaint = models.ForeignKey('masters.JobcardComplaintMaster', on_delete=models.PROTECT, related_name='+')
    details            = models.TextField(blank=True)
    status              = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    complaint_check_box = models.BooleanField(default=False)
    estimated_amount     = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    class Meta:
        verbose_name_plural = 'Complaint Details'

    def __str__(self):
        return f"{self.customer_complaint} (JC-{self.job_card_id})"


class JobCardSupervisorObservation(models.Model):
    job_card             = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name='supervisor_observations')
    complaint            = models.ForeignKey('masters.JobcardSupervisorObservationMaster', on_delete=models.PROTECT, related_name='+')
    details              = models.TextField(blank=True)
    complaint_check_box  = models.BooleanField(default=False)
    estimated_amount     = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    class Meta:
        verbose_name_plural = 'Job Card Supervisor Observations'

    def __str__(self):
        return f"{self.complaint} (JC-{self.job_card_id})"


class EngineDetailRow(models.Model):
    class Variant(models.TextChoices):
        YES_NO    = 'yes_no',    'Yes/No'
        OK_HI_LOW = 'ok_hi_low', 'OK/High/Low'

    job_card      = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name='engine_details')
    variant       = models.CharField(max_length=20, choices=Variant.choices, default=Variant.YES_NO)
    items         = models.CharField(max_length=200, blank=True)
    yes           = models.BooleanField(default=False)
    no            = models.BooleanField(default=False)
    ok            = models.BooleanField(default=False)
    high          = models.BooleanField(default=False)
    low           = models.BooleanField(default=False)
    area_mention  = models.CharField(max_length=200, blank=True)
    yes_status     = models.CharField(max_length=50, blank=True)
    no_status      = models.CharField(max_length=50, blank=True)
    ok_status      = models.CharField(max_length=50, blank=True)
    high_status    = models.CharField(max_length=50, blank=True)
    low_status     = models.CharField(max_length=50, blank=True)
    mention_status = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name_plural = 'Engine Detail Rows'

    def __str__(self):
        return f"{self.items} (JC-{self.job_card_id})"


class LightDetail(models.Model):
    job_card = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name='light_details')
    items    = models.CharField(max_length=200, blank=True)
    yes      = models.BooleanField(default=False)
    no       = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Light Details'

    def __str__(self):
        return f"{self.items} (JC-{self.job_card_id})"


class ChasisDetailRow(models.Model):
    class Variant(models.TextChoices):
        YES_NO       = 'yes_no',       'Yes/No'
        GOOD_BAD_NA  = 'good_bad_na',  'Good/Bad/NA'
        OK_HI_LOW    = 'ok_hi_low',    'OK/High/Low'

    job_card   = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name='chasis_details')
    variant    = models.CharField(max_length=20, choices=Variant.choices, default=Variant.YES_NO)
    items      = models.CharField(max_length=200, blank=True)
    yes        = models.BooleanField(default=False)
    no         = models.BooleanField(default=False)
    ok         = models.BooleanField(default=False)
    high       = models.BooleanField(default=False)
    low        = models.BooleanField(default=False)
    good       = models.BooleanField(default=False)
    bad        = models.BooleanField(default=False)
    na         = models.BooleanField(default=False)
    yes_status  = models.IntegerField(default=0, blank=True)
    no_status   = models.IntegerField(default=0, blank=True)
    good_status = models.IntegerField(default=0, blank=True)
    bad_status  = models.IntegerField(default=0, blank=True)
    na_status   = models.IntegerField(default=0, blank=True)
    ok_status   = models.IntegerField(default=0, blank=True)
    high_status = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Chasis Detail Rows'

    def __str__(self):
        return f"{self.items} (JC-{self.job_card_id})"


# ---- Submit signals: advance JobCard.service_status per reference workflow ----

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=WaterWashDone)
def on_water_wash_submitted(sender, instance, **kwargs):
    if instance.docstatus == WaterWashDone.DocStatus.SUBMITTED:
        _advance_job_card_status(instance.job_card, JobCard.ServiceStatus.WATER_WASH)


@receiver(post_save, sender=BayInCreation)
def on_bay_in_submitted(sender, instance, **kwargs):
    if instance.docstatus == BayInCreation.DocStatus.SUBMITTED:
        _advance_job_card_status(instance.job_card, JobCard.ServiceStatus.IN_BAY)


@receiver(post_save, sender=BayOutCreation)
def on_bay_out_submitted(sender, instance, **kwargs):
    if instance.docstatus == BayOutCreation.DocStatus.SUBMITTED:
        _advance_job_card_status(instance.job_card, JobCard.ServiceStatus.IN_PROGRESS)


@receiver(post_save, sender=OutworkEntryIssue)
def on_outwork_issue_submitted(sender, instance, **kwargs):
    if instance.docstatus == OutworkEntryIssue.DocStatus.SUBMITTED:
        _advance_job_card_status(instance.job_card, JobCard.ServiceStatus.OUTWORK)


@receiver(post_save, sender=OutworkEntryReturn)
def on_outwork_return_submitted(sender, instance, **kwargs):
    if instance.docstatus == OutworkEntryReturn.DocStatus.SUBMITTED and not instance.rework:
        _advance_job_card_status(instance.job_card, JobCard.ServiceStatus.FINAL_INSPECTION)


@receiver(post_save, sender=FinalInspection)
def on_final_inspection_submitted(sender, instance, **kwargs):
    if instance.docstatus == FinalInspection.DocStatus.SUBMITTED:
        status = JobCard.ServiceStatus.FINAL_INSPECTION if instance.rework else JobCard.ServiceStatus.READY
        _advance_job_card_status(instance.job_card, status)
