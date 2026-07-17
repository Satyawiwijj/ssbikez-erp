from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from accounts.models import DocStatusMixin


def split_gst(gst_amount, customer=None):
    """Split a GST amount into (cgst, sgst, igst).

    Interstate-aware: if `customer` is given and its `.state` is set and
    differs (case-insensitively) from `CompanySettings.state`, this is an
    interstate sale — the whole `gst_amount` goes to IGST and CGST/SGST are
    both zero. Otherwise (customer is None, customer.state is blank, or it
    matches the company's state) this is the pre-existing intrastate
    behaviour: split across CGST/SGST using the company's actual rates
    instead of assuming an even 50/50 split.

    `customer` is optional and defaults to None so existing callers that
    haven't been updated yet keep getting the old intrastate-only behaviour
    (backward compatible) rather than breaking outright — but every call
    site in this codebase has been updated to pass the customer through.
    """
    from decimal import Decimal
    from accounts.models import CompanySettings
    settings_ = CompanySettings.get_instance()

    if customer is not None:
        customer_state = (getattr(customer, 'state', '') or '').strip()
        company_state  = (settings_.state or '').strip()
        if customer_state and company_state and customer_state.lower() != company_state.lower():
            igst = gst_amount.quantize(Decimal('0.01'))
            return Decimal('0.00'), Decimal('0.00'), igst

    rate_total = (settings_.cgst_rate or 0) + (settings_.sgst_rate or 0)
    if rate_total:
        cgst = (gst_amount * settings_.cgst_rate / rate_total).quantize(Decimal('0.01'))
        sgst = (gst_amount * settings_.sgst_rate / rate_total).quantize(Decimal('0.01'))
    else:
        cgst = sgst = (gst_amount / Decimal('2')).quantize(Decimal('0.01'))
    return cgst, sgst, Decimal('0.00')


class Invoice(DocStatusMixin, models.Model):
    class PaymentType(models.TextChoices):
        CASH   = 'cash',   'Cash'
        BANK   = 'bank',   'Bank'

    class Status(models.TextChoices):
        UNPAID = 'unpaid', 'Unpaid'
        PAID   = 'paid',   'Paid'

    # A plain ForeignKey (not OneToOne): docstatus/amend means an order can
    # accumulate a cancelled invoice + its amended replacement over time.
    # Use VehicleSalesOrder.current_invoice for "the active one".
    sales_order     = models.ForeignKey(
        'sales.VehicleSalesOrder',
        on_delete=models.PROTECT,
        related_name='invoices'
    )
    invoice_number  = models.CharField(max_length=100, unique=True)
    subtotal        = models.DecimalField(max_digits=10, decimal_places=2)
    gst_amount      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gst_category    = models.CharField(max_length=30, blank=True, help_text='Snapshot at issue time')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    final_amount    = models.DecimalField(max_digits=10, decimal_places=2)
    invoice_date    = models.DateField()
    payment_type    = models.CharField(max_length=10, choices=PaymentType.choices, blank=True)
    payment_due_date = models.DateField(null=True, blank=True)

    # MD approval workflow — a separate gate from the delivery-stage
    # Manager/Finance approval on VehicleDelivery
    md_approval_requested = models.BooleanField(default=False)
    md_approved           = models.BooleanField(default=False)
    md_approved_by        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    md_approved_at        = models.DateTimeField(null=True, blank=True)

    # Totals cluster
    total_quantity              = models.IntegerField(default=0, blank=True)
    finance_amount               = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    actual_refund_amount         = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    customer_refund_amount       = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    delivery_discount            = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, validators=[MinValueValidator(0)])
    sales_order_discount_amount  = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, validators=[MinValueValidator(0)])
    refund_from_account          = models.CharField(max_length=200, blank=True)
    exchange_vehicle_amount      = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    number_plate_amount          = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    advance_amount               = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    balance_payment              = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    status                       = models.CharField(max_length=10, choices=Status.choices, default=Status.UNPAID)

    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-invoice_date']
        verbose_name_plural = 'Invoices'

    def __str__(self):
        return f"{self.invoice_number} — Rs.{self.final_amount}"

    def submit(self, user):
        """Draft -> Submitted, then auto-post the sales-recognition entry to
        the General Ledger. GL posting only happens on a *real* submit
        (never for Draft/Cancelled invoices) because DocStatusMixin.submit()
        itself raises ValueError unless docstatus is currently Draft."""
        super().submit(user)
        self.post_journal_entry(user)

    def post_journal_entry(self, user=None):
        """Auto-create the balanced JournalEntry for this invoice:
        Dr Accounts Receivable / Cr Sales Revenue, both for final_amount.

        Idempotency guard mirrors VASStockMovement's source_* OneToOneField
        pattern in vas/models.py: JournalEntry.source_invoice is a OneToOne
        back-reference, so `hasattr(self, 'journal_entry')` is True once a
        line has been posted for this invoice, and a second call is a no-op.
        Simplification: this posts subtotal/GST as a single lump sum against
        two accounts rather than breaking GST out into its own GL line(s) —
        deliberately kept simple per the brief.
        """
        if hasattr(self, 'journal_entry'):
            return self.journal_entry
        entry = JournalEntry.objects.create(
            entry_date=self.invoice_date,
            description=f'Auto-posted on submit: Sales Invoice {self.invoice_number}',
            reference=self.invoice_number,
            reference_doctype='billing.Invoice',
            reference_docname=str(self.pk),
            created_by=user,
            source_invoice=self,
        )
        JournalEntryLine.objects.create(entry=entry, account='Accounts Receivable', debit=self.final_amount)
        JournalEntryLine.objects.create(entry=entry, account='Sales Revenue', credit=self.final_amount)
        return entry


class InvoiceItem(models.Model):
    """Priced line items on the invoice — matches reference "Items" table."""
    invoice   = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    item_code = models.CharField(max_length=100, blank=True)
    rate      = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, validators=[MinValueValidator(0)])
    discount  = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, validators=[MinValueValidator(0)])
    total     = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        if self.discount and self.rate and self.discount > self.rate:
            raise ValidationError({'discount': 'Discount cannot exceed the rate.'})

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Invoice Items'

    def __str__(self):
        return f"{self.item_code} — Rs.{self.total}"

    def save(self, *args, **kwargs):
        # Defensive guard: rate/discount are blank=True DecimalFields with no
        # null=True (so the DB column is NOT NULL), so a partially-filled
        # invoice item row can reach here with either set to None
        # (form-level clean_rate/clean_discount on InvoiceItemLineForm should
        # already coerce blank -> 0, but guard here too in case any other
        # caller constructs/saves an InvoiceItem directly with None).
        if self.rate is None:
            self.rate = 0
        if self.discount is None:
            self.discount = 0
        self.total = self.rate - self.discount
        super().save(*args, **kwargs)


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

    def save(self, *args, **kwargs):
        # Same is_new-then-super().save()-then-post-effects shape as
        # VASStockMovement.save() in vas/models.py.
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and self.payment_status == self.PaymentStatus.COMPLETED:
            self.post_journal_entry()

    def post_journal_entry(self):
        """Auto-create the balanced JournalEntry for this completed payment:
        Dr Cash/Bank / Cr Accounts Receivable, both for `amount`.

        Only fires for a Payment created already-COMPLETED (per the brief:
        "on Payment create ... a completed payment"). A Payment that starts
        Pending and is later marked Completed via the payment_reconciliation
        bulk queryset .update() (billing/_gap14_31_views.py) does NOT go
        through save() and so is NOT auto-posted -- a known gap, noted in
        the report rather than silently patched over.

        Account choice: 'Cash' for the Cash method, 'Bank' for every other
        (electronic/instrument) method -- Card/UPI/NEFT/Cheque/blank -- since
        none of those are physical cash into the till.

        Idempotency guard: same source_* OneToOneField pattern as Invoice
        (and as VASStockMovement in vas/models.py) via JournalEntry.source_payment.
        """
        if hasattr(self, 'journal_entry'):
            return self.journal_entry
        from django.utils import timezone
        entry_date = timezone.now().date()
        if self.payment_date:
            if hasattr(self.payment_date, 'date'):
                # A real datetime (the normal case via form-validated input).
                entry_date = self.payment_date.date()
            else:
                # payment_date arrived as a plain string/date -- e.g. a direct
                # Payment.objects.create(payment_date='2026-08-01', ...) call
                # that bypassed form validation's datetime coercion.
                from django.utils.dateparse import parse_date, parse_datetime
                parsed = parse_datetime(str(self.payment_date)) or parse_date(str(self.payment_date))
                if parsed:
                    entry_date = parsed.date() if hasattr(parsed, 'date') else parsed
        account = 'Cash' if self.payment_method == self.Method.CASH else 'Bank'
        entry = JournalEntry.objects.create(
            entry_date=entry_date,
            description=f'Auto-posted on payment: {self.invoice.invoice_number}',
            reference=self.transaction_reference or f'PAY-{self.pk}',
            reference_doctype='billing.Payment',
            reference_docname=str(self.pk),
            source_payment=self,
        )
        JournalEntryLine.objects.create(entry=entry, account=account, debit=self.amount)
        JournalEntryLine.objects.create(entry=entry, account='Accounts Receivable', credit=self.amount)
        return entry


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
    """
    Double-entry journal voucher — a header with one or more JournalEntryLine
    rows (account + debit/credit). Total debit must equal total credit
    across the lines (see clean()), matching standard double-entry
    accounting and the reference ERP's Journal Entry document.
    """
    entry_date          = models.DateField()
    description         = models.TextField()
    reference            = models.CharField(max_length=200, blank=True)
    is_vehicle_purchase = models.BooleanField(default=False, verbose_name='Vehicle Purchase')
    company_gstin       = models.CharField(max_length=20, blank=True, verbose_name='Company GSTIN')
    reference_doctype   = models.CharField(max_length=100, blank=True)
    reference_docname   = models.CharField(max_length=100, blank=True)
    reference_number    = models.CharField(max_length=100, blank=True)
    reference_date      = models.DateField(null=True, blank=True)
    number_plate_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    multi_currency      = models.BooleanField(default=False)
    created_by          = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    # Idempotency links for auto-posted entries -- same OneToOneField
    # "source_*" pattern VASStockMovement uses in vas/models.py
    # (source_invoice_item / source_amc_package / ...) to guarantee a given
    # source document posts at most one GL entry. NULL for manually-created
    # journal entries (journal_entry_create view), which don't set these.
    source_invoice      = models.OneToOneField(
        'Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entry'
    )
    source_payment       = models.OneToOneField(
        'Payment', on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entry'
    )
    created_at          = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-entry_date', '-created_at']
        verbose_name_plural = 'Journal Entries'

    @property
    def total_debit(self):
        from decimal import Decimal
        return self.lines.aggregate(t=models.Sum('debit'))['t'] or Decimal('0')

    @property
    def total_credit(self):
        from decimal import Decimal
        return self.lines.aggregate(t=models.Sum('credit'))['t'] or Decimal('0')

    @property
    def is_balanced(self):
        return self.total_debit == self.total_credit

    def __str__(self):
        return f"JE-{self.pk} | {self.entry_date} | Dr/Cr Rs.{self.total_debit}"


class JournalEntryLine(models.Model):
    entry      = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account    = models.CharField(max_length=200, db_index=True)
    party_type = models.CharField(max_length=100, blank=True)
    party      = models.CharField(max_length=200, blank=True)
    debit      = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit     = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ['pk']

    def __str__(self):
        return f"{self.account} | Dr {self.debit} / Cr {self.credit}"
