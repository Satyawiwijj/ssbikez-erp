from django.db import models


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
        default=PaymentStatus.PENDING
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

    sales_order   = models.OneToOneField(
        'sales.VehicleSalesOrder',
        on_delete=models.PROTECT,
        related_name='loan'
    )
    bank_name     = models.CharField(max_length=100)
    loan_amount   = models.DecimalField(max_digits=10, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    tenure_months = models.IntegerField(null=True, blank=True)
    emi_amount    = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    loan_status   = models.CharField(
        max_length=20,
        choices=LoanStatus.choices,
        default=LoanStatus.ACTIVE
    )
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Finance Loans'

    def __str__(self):
        return f"LOAN-{self.pk} | {self.bank_name} — Rs.{self.loan_amount}"
