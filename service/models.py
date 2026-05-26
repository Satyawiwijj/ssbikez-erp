from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum


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
    claim_number    = models.CharField(max_length=100, blank=True)
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
            last = WarrantyClaim.objects.order_by('-id').first()
            num  = (last.id + 1) if last else 1
            self.claim_number = f"WC-{num:05d}"
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
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
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
