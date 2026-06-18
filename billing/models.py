from django.db import models


def split_gst(gst_amount):
    """Split a GST amount into (cgst, sgst) using the company's actual rates,
    instead of assuming an even 50/50 split."""
    from decimal import Decimal
    from accounts.models import CompanySettings
    settings_ = CompanySettings.get_instance()
    rate_total = (settings_.cgst_rate or 0) + (settings_.sgst_rate or 0)
    if rate_total:
        cgst = (gst_amount * settings_.cgst_rate / rate_total).quantize(Decimal('0.01'))
        sgst = (gst_amount * settings_.sgst_rate / rate_total).quantize(Decimal('0.01'))
    else:
        cgst = sgst = (gst_amount / Decimal('2')).quantize(Decimal('0.01'))
    return cgst, sgst


class Invoice(models.Model):
    sales_order     = models.OneToOneField(
        'sales.VehicleSalesOrder',
        on_delete=models.PROTECT,
        related_name='invoice'
    )
    invoice_number  = models.CharField(max_length=100, unique=True)
    subtotal        = models.DecimalField(max_digits=10, decimal_places=2)
    gst_amount      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_amount    = models.DecimalField(max_digits=10, decimal_places=2)
    invoice_date    = models.DateField()
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-invoice_date']
        verbose_name_plural = 'Invoices'

    def __str__(self):
        return f"{self.invoice_number} — Rs.{self.final_amount}"


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH   = 'cash',   'Cash'
        CARD   = 'card',   'Card'
        UPI    = 'upi',    'UPI'
        NEFT   = 'neft',   'NEFT'
        CHEQUE = 'cheque', 'Cheque'

    class PaymentStatus(models.TextChoices):
        PENDING   = 'pending',   'Pending'
        COMPLETED = 'completed', 'Completed'
        FAILED    = 'failed',    'Failed'

    invoice               = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name='payments'
    )
    payment_method        = models.CharField(
        max_length=50,
        choices=Method.choices,
        blank=True, null=True
    )
    transaction_reference = models.CharField(max_length=255, blank=True, null=True)
    amount                = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status        = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )
    payment_date          = models.DateTimeField(blank=True, null=True)
    created_at            = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date']
        verbose_name_plural = 'Payments'

    def __str__(self):
        return f"PAY-{self.pk} | {self.invoice.invoice_number} — {self.payment_method} Rs.{self.amount}"


class InsurancePolicy(models.Model):
    sales_order    = models.ForeignKey(
        'sales.VehicleSalesOrder',
        on_delete=models.PROTECT,
        related_name='insurance_policies'
    )
    provider_name  = models.CharField(max_length=255)
    policy_number  = models.CharField(max_length=100, unique=True)
    premium_amount = models.DecimalField(max_digits=10, decimal_places=2)
    start_date     = models.DateField()
    end_date       = models.DateField()
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Insurance Policies'

    def __str__(self):
        return f"{self.policy_number} | {self.provider_name} — Rs.{self.premium_amount}"


class FinanceLoan(models.Model):
    class LoanStatus(models.TextChoices):
        ACTIVE   = 'active',   'Active'
        CLOSED   = 'closed',   'Closed'
        REJECTED = 'rejected', 'Rejected'

    sales_order     = models.OneToOneField(
        'sales.VehicleSalesOrder',
        on_delete=models.PROTECT,
        related_name='loan'
    )
    bank_name       = models.CharField(max_length=100)
    loan_amount     = models.DecimalField(max_digits=10, decimal_places=2)
    interest_rate   = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    tenure_months   = models.IntegerField(null=True, blank=True)
    emi_amount      = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    loan_status     = models.CharField(
        max_length=20,
        choices=LoanStatus.choices,
        default=LoanStatus.ACTIVE
    )
    sanctioned_date = models.DateField(null=True, blank=True)
    first_emi_date  = models.DateField(null=True, blank=True)

    # GAP 29 — Hypothecation workflow
    HP_STATUS_CHOICES = [
        ('not_applicable', 'Not Applicable'),
        ('pending',        'HP Pending'),
        ('submitted',      'Submitted to RTO'),
        ('endorsed',       'HP Endorsed on RC'),
        ('released',       'HP Released'),
    ]
    hp_status            = models.CharField(
        max_length=20, choices=HP_STATUS_CHOICES, default='not_applicable'
    )
    hp_bank_name         = models.CharField(max_length=200, blank=True)
    hp_submission_date   = models.DateField(null=True, blank=True)
    hp_endorsement_date  = models.DateField(null=True, blank=True)
    hp_release_date      = models.DateField(null=True, blank=True)

    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Finance Loans'

    def __str__(self):
        return f"LOAN-{self.pk} | {self.bank_name} — Rs.{self.loan_amount}"

    @property
    def loan_end_date(self):
        """Calculate loan end date from first EMI date + tenure."""
        if self.first_emi_date and self.tenure_months:
            from dateutil.relativedelta import relativedelta
            try:
                return self.first_emi_date + relativedelta(months=self.tenure_months)
            except Exception:
                pass
        return None

    @property
    def total_payable(self):
        """Simple interest estimate of total repayment."""
        from decimal import Decimal
        if self.loan_amount and self.interest_rate and self.tenure_months:
            years    = Decimal(str(self.tenure_months)) / Decimal('12')
            interest = self.loan_amount * (self.interest_rate / Decimal('100')) * years
            return self.loan_amount + interest
        return None


from django.conf import settings


# ---------------------------------------------------------------------------
# GAP 18 — Refunds & Advances
# ---------------------------------------------------------------------------

class RefundAdvance(models.Model):
    class TransactionType(models.TextChoices):
        REFUND  = 'refund',  'Refund'
        ADVANCE = 'advance', 'Advance'

    class Status(models.TextChoices):
        PENDING   = 'pending',   'Pending'
        PROCESSED = 'processed', 'Processed'
        CANCELLED = 'cancelled', 'Cancelled'

    customer            = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT, related_name='refunds_advances'
    )
    transaction_type    = models.CharField(max_length=20, choices=TransactionType.choices)
    amount              = models.DecimalField(max_digits=10, decimal_places=2)
    reference_invoice   = models.ForeignKey(
        Invoice, on_delete=models.SET_NULL, null=True, blank=True
    )
    reason              = models.TextField()
    payment_method      = models.CharField(max_length=50, blank=True)
    status              = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    processed_by        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at          = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type} — Rs.{self.amount} — {self.customer}"


# ---------------------------------------------------------------------------
# GAP 25 — Journal Entries / General Ledger
# ---------------------------------------------------------------------------

class JournalEntry(models.Model):
    class EntryType(models.TextChoices):
        DEBIT  = 'debit',  'Debit'
        CREDIT = 'credit', 'Credit'

    entry_date   = models.DateField()
    description  = models.TextField()
    account_name = models.CharField(max_length=200, db_index=True)
    entry_type   = models.CharField(max_length=10, choices=EntryType.choices)
    amount       = models.DecimalField(max_digits=12, decimal_places=2)
    reference    = models.CharField(max_length=200, blank=True)
    created_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-entry_date', '-created_at']

    def __str__(self):
        return f"JE-{self.pk} | {self.account_name} {self.entry_type} Rs.{self.amount}"
