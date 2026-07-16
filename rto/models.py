from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import DocStatusMixin


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

    rto          = models.OneToOneField(
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


class RCBook(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CREATED = 'created', 'Created'
        ISSUED  = 'issued',  'Issued to Customer'

    rto_registration = models.OneToOneField(
        RTORegistration,
        on_delete=models.CASCADE,
        related_name='rc_book'
    )
    rc_number     = models.CharField(max_length=100, blank=True)
    issue_date    = models.DateField(null=True, blank=True)
    issued_to     = models.CharField(max_length=200, blank=True)
    # GAP 29 — HP endorsement on RC
    hp_endorsed   = models.BooleanField(default=False)
    hp_bank_name  = models.CharField(max_length=200, blank=True)
    status     = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'RC Books'

    def __str__(self):
        return f"RC-{self.pk} | {self.rc_number or 'Pending'}"


# ---------------------------------------------------------------------------
# GAP 19 — RegPay (Registration Payment)
# ---------------------------------------------------------------------------

class RegPayment(models.Model):
    rto_registration = models.ForeignKey(
        RTORegistration, on_delete=models.CASCADE, related_name='reg_payments'
    )
    payment_type   = models.CharField(max_length=100)
    amount         = models.DecimalField(max_digits=10, decimal_places=2)
    receipt_number = models.CharField(max_length=100, blank=True)
    payment_date   = models.DateField()
    notes          = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"RegPay-{self.pk} | Rs.{self.amount}"


# ---------------------------------------------------------------------------
# GAP 20 — RTO Income
# ---------------------------------------------------------------------------

class RTOIncome(models.Model):
    rto_registration = models.ForeignKey(
        RTORegistration, on_delete=models.CASCADE, related_name='income_entries'
    )
    income_type     = models.CharField(max_length=100)
    amount          = models.DecimalField(max_digits=10, decimal_places=2)
    collected_from  = models.CharField(max_length=200, blank=True)
    date            = models.DateField()
    notes           = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"RTOIncome-{self.pk} | Rs.{self.amount}"


# ---------------------------------------------------------------------------
# Phase 6 — New-vehicle RTO masters
# ---------------------------------------------------------------------------

class RegistrationArea(models.Model):
    name       = models.CharField(max_length=200, unique=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Registration Areas'


class RegPayBaseAmount(models.Model):
    """Reference: 'RegPay Base Amount' -- government registration-fee base
    amount per vehicle model, driving RegpayCreation's fee calculation."""
    vehicle    = models.ForeignKey('customers.BikeModel', on_delete=models.PROTECT, related_name='regpay_base_amounts')
    amount     = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vehicle} — Rs.{self.amount}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'RegPay Base Amounts'


class RegisterNumberMaster(models.Model):
    """Reference: 'Register Number Master' -- pool of RTO-issued registration
    numbers available for assignment via RegistrationNoCreation."""
    register_number = models.CharField(max_length=50, unique=True)
    is_used         = models.BooleanField(default=False)
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.register_number

    class Meta:
        ordering = ['register_number']
        verbose_name_plural = 'Register Number Master'


# ---------------------------------------------------------------------------
# RC Hand Over -- new-vehicle pre-delivery RC/NOC/T.O./HP-endorsement checklist
# ---------------------------------------------------------------------------

class RCHandOver(DocStatusMixin, models.Model):
    class YesNo(models.TextChoices):
        YES = 'yes', 'Yes'
        NO  = 'no',  'No'

    sales_order      = models.ForeignKey('sales.VehicleSalesOrder', on_delete=models.PROTECT, related_name='rc_hand_overs')
    rc_book_received = models.CharField(max_length=5, choices=YesNo.choices, blank=True)
    noc              = models.CharField(max_length=5, choices=YesNo.choices, blank=True)
    # Reference spec: 3-state Select (blank/Yes/No), same as rc_book_received/noc above --
    # a plain BooleanField can never be made "required" in a ModelForm (Django always forces
    # required=False for BooleanField, since an unchecked checkbox posts nothing), so it had
    # no way to distinguish "not yet answered" from "answered No". Converted to match.
    vehicle_received = models.CharField(max_length=5, choices=YesNo.choices, blank=True)
    year_of_make     = models.PositiveIntegerField(null=True, blank=True)
    hp_endorsement   = models.BooleanField(default=False)
    to_received      = models.BooleanField(default=False, verbose_name='T.O. Received')
    rc_book_number   = models.CharField(max_length=100, blank=True, help_text="Only meaningful when RC Book Received = Yes")
    created_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"RCH-{self.pk} | {self.sales_order}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'RC Hand Overs'


# ---------------------------------------------------------------------------
# Form 20 + Registration No -- stage documents feeding RTORegistration's
# form20_number/registration_number snapshot fields.
# ---------------------------------------------------------------------------

class Form20Creation(DocStatusMixin, models.Model):
    sales_order      = models.ForeignKey('sales.VehicleSalesOrder', on_delete=models.PROTECT, related_name='form20_creations')
    registration_area = models.ForeignKey(RegistrationArea, on_delete=models.SET_NULL, null=True, blank=True, related_name='form20_creations')
    engine_no        = models.CharField(max_length=100, blank=True)
    frame_no         = models.CharField(max_length=100, blank=True)
    application_no   = models.CharField(max_length=100, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"FORM20-{self.pk} | {self.sales_order}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Form 20 Creations'


class RegistrationNoCreation(DocStatusMixin, models.Model):
    class Status(models.TextChoices):
        OPEN   = 'open',   'Open'
        CLOSED = 'closed', 'Closed'

    sales_order       = models.ForeignKey('sales.VehicleSalesOrder', on_delete=models.PROTECT, related_name='registration_no_creations')
    form20            = models.ForeignKey(Form20Creation, on_delete=models.SET_NULL, null=True, blank=True, related_name='registration_no_creations')
    registration_area = models.ForeignKey(RegistrationArea, on_delete=models.SET_NULL, null=True, blank=True, related_name='registration_no_creations')
    reg_no            = models.CharField(max_length=50, blank=True, verbose_name='Vehicle No')
    frame_no          = models.CharField(max_length=100, blank=True)
    engine_no         = models.CharField(max_length=100, blank=True)
    status            = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    remark            = models.CharField(max_length=255, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"REGNO-{self.pk} | {self.reg_no or self.sales_order}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Registration No Creations'


@receiver(post_save, sender=Form20Creation)
def on_form20_submitted(sender, instance, **kwargs):
    if instance.docstatus != Form20Creation.DocStatus.SUBMITTED:
        return
    rto = RTORegistration.objects.filter(sales_order=instance.sales_order).first()
    if rto and rto.form20_number != instance.application_no:
        rto.form20_number = instance.application_no
        rto.save(update_fields=['form20_number'])


@receiver(post_save, sender=RegistrationNoCreation)
def on_registration_no_submitted(sender, instance, **kwargs):
    if instance.docstatus != RegistrationNoCreation.DocStatus.SUBMITTED:
        return
    rto = RTORegistration.objects.filter(sales_order=instance.sales_order).first()
    if rto and rto.registration_number != instance.reg_no:
        rto.registration_number = instance.reg_no
        rto.save(update_fields=['registration_number'])


# ---------------------------------------------------------------------------
# RTOPayment -- collapses reference's 'RTO Income Creation' + 'RTO Expenses
# Creation' (near-identical shape, differing only by money-flow direction).
# ---------------------------------------------------------------------------

class RTOPayment(DocStatusMixin, models.Model):
    """Reference: 'RTO Income Creation' + 'RTO Expenses Creation' -- both are
    header-plus-multi-row-party BATCH documents (one payment run can cover
    several vehicles at once), confirmed live against the reference server's
    'RTO Income Party'/'RTO Expense Party' child tables. Phase 6 originally
    built this as one-row-per-vehicle; Phase 9a restructures it into a real
    header + RTOPaymentItem child table to match."""
    class Direction(models.TextChoices):
        INCOME  = 'income',  'Income (from Customer)'
        EXPENSE = 'expense', 'Expense (to Agent)'

    class PayType(models.TextChoices):
        CASH = 'cash', 'Cash'
        BANK = 'bank', 'Bank'

    class AgentType(models.TextChoices):
        PAYMENT_TO_AGENT = 'payment_to_agent', 'Payment to Agent'
        SUB_DEALER       = 'sub_dealer_rto',   'RTO done by Sub Dealer'

    class PaymentStatus(models.TextChoices):
        UNPAID = 'unpaid', 'Unpaid'
        PAID   = 'paid',   'Paid'

    direction      = models.CharField(max_length=10, choices=Direction.choices)
    pay_type       = models.CharField(max_length=10, choices=PayType.choices, blank=True)
    cash_account   = models.CharField(max_length=200, blank=True)
    bank_name      = models.CharField(max_length=200, blank=True)
    agent_type     = models.CharField(max_length=20, choices=AgentType.choices, blank=True, help_text='Expense direction only')
    agent          = models.ForeignKey('masters.Supplier', on_delete=models.SET_NULL, null=True, blank=True, related_name='rto_payments')
    reference_no   = models.CharField(max_length=100, blank=True)
    reference_date = models.DateField(null=True, blank=True)
    total_amount   = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, help_text='Sum of item row totals')
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"RTOPAY-{self.pk} | {self.get_direction_display()} — Rs.{self.total_amount}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'RTO Payments'


class RTOPaymentItem(models.Model):
    """Reference: 'RTO Income Party' / 'RTO Expense Party' child row -- one
    vehicle/customer per row within a single RTOPayment batch."""
    payment        = models.ForeignKey(RTOPayment, on_delete=models.CASCADE, related_name='items')
    sales_order    = models.ForeignKey('sales.VehicleSalesOrder', on_delete=models.PROTECT, related_name='rto_payment_items')
    branch         = models.ForeignKey('accounts.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='rto_payment_items')
    flag_amount    = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    fine_amount    = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    license_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    total_amount   = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    def save(self, *args, **kwargs):
        self.total_amount = (self.flag_amount or 0) + (self.fine_amount or 0) + (self.license_amount or 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.payment} | {self.sales_order}"

    class Meta:
        verbose_name_plural = 'RTO Payment Items'


class RegpayCreation(DocStatusMixin, models.Model):
    """Reference: 'Regpay Creation' -- header-plus-multi-row-party BATCH
    document ('Reg Pay Party' child table), confirmed live. Phase 6 originally
    built this as one-row-per-vehicle with vehicle_type on the header; Phase
    9a restructures it into a real header + RegpayCreationItem child table,
    moving vehicle_type onto each row per the reference's actual placement."""
    registration_area   = models.ForeignKey(RegistrationArea, on_delete=models.SET_NULL, null=True, blank=True, related_name='regpay_creations')
    supplier            = models.ForeignKey('masters.Supplier', on_delete=models.SET_NULL, null=True, blank=True, related_name='regpay_creations')
    transaction_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    total_amount        = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, help_text='Sum of item row amounts')
    pending_amount      = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    payment_status      = models.CharField(
        max_length=20,
        choices=[('unpaid', 'Unpaid'), ('paid', 'Paid')],
        default='unpaid',
    )
    created_at            = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"REGPAY-{self.pk}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Regpay Creations'


class RegpayCreationItem(models.Model):
    """Reference: 'Reg Pay Party' child row -- one vehicle/customer per row
    within a single Regpay Creation batch."""
    regpay               = models.ForeignKey(RegpayCreation, on_delete=models.CASCADE, related_name='items')
    sales_order          = models.ForeignKey('sales.VehicleSalesOrder', on_delete=models.PROTECT, related_name='regpay_creation_items')
    vehicle_type         = models.ForeignKey(RegPayBaseAmount, on_delete=models.PROTECT, related_name='regpay_creation_items', verbose_name='Vehicle Type (Base Amount)')
    profit               = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    amount_from_customer = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    amount               = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    def save(self, *args, **kwargs):
        self.amount = (self.profit or 0) + (self.amount_from_customer or 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.regpay} | {self.sales_order}"

    class Meta:
        verbose_name_plural = 'Regpay Creation Items'


# ---------------------------------------------------------------------------
# Number Plate 3-stage flow: Order -> Receipt/Payment -> Issue
# ---------------------------------------------------------------------------

class NumberOrderEntryCreation(DocStatusMixin, models.Model):
    sales_order      = models.ForeignKey('sales.VehicleSalesOrder', on_delete=models.PROTECT, related_name='number_order_entries')
    agent            = models.ForeignKey('masters.Supplier', on_delete=models.PROTECT, related_name='number_order_entries')
    registration_area = models.ForeignKey(RegistrationArea, on_delete=models.SET_NULL, null=True, blank=True, related_name='number_order_entries')
    application_type = models.CharField(max_length=20, default='NB')
    chassis_no       = models.CharField(max_length=100, blank=True)
    engine_no        = models.CharField(max_length=100, blank=True)
    re_order         = models.BooleanField(default=False)
    created_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"NUMORD-{self.pk} | {self.sales_order}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Number Order Entry Creations'


class NumberReceiptEntryCreation(DocStatusMixin, models.Model):
    class PaymentType(models.TextChoices):
        CASH = 'cash', 'Cash'

    order_entry  = models.ForeignKey(NumberOrderEntryCreation, on_delete=models.PROTECT, related_name='receipt_entries')
    agent        = models.ForeignKey('masters.Supplier', on_delete=models.PROTECT, related_name='number_receipt_entries')
    payment_type = models.CharField(max_length=10, choices=PaymentType.choices, blank=True)
    rate         = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, validators=[MinValueValidator(0)])
    cgst         = models.DecimalField(max_digits=5, decimal_places=2, default=9, blank=True, validators=[MinValueValidator(0)])
    sgst         = models.DecimalField(max_digits=5, decimal_places=2, default=9, blank=True, validators=[MinValueValidator(0)])
    total        = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        rate = self.rate or 0
        self.total = rate + (rate * (self.cgst or 0) / 100) + (rate * (self.sgst or 0) / 100)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"NUMREC-{self.pk} | {self.order_entry}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Number Receipt Entry Creations'


class NumberPlateIssue(DocStatusMixin, models.Model):
    class IssueType(models.TextChoices):
        CUSTOMER   = 'customer',   'Issue to Customer'
        SUB_DEALER = 'sub_dealer', 'Issue to Sub Dealers'
        BRANCH     = 'branch',     'Issue to Branch'

    receipt_entry       = models.ForeignKey(NumberReceiptEntryCreation, on_delete=models.PROTECT, related_name='plate_issues')
    issue_type          = models.CharField(max_length=20, choices=IssueType.choices, default=IssueType.CUSTOMER)
    sub_dealer_name      = models.ForeignKey('masters.Supplier', on_delete=models.SET_NULL, null=True, blank=True, related_name='number_plate_issues_as_sub_dealer', help_text='Only when Issue Type = Sub Dealer')
    transfer_to_branch   = models.ForeignKey('accounts.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='number_plate_issues', help_text='Only when Issue Type = Branch')
    is_frame            = models.BooleanField(default=False, verbose_name='Is Frame (spares-stock-backed physical plate)')
    frame               = models.ForeignKey('spares.SparesItem', on_delete=models.SET_NULL, null=True, blank=True, related_name='number_plate_issues')
    warehouse           = models.ForeignKey('masters.Warehouse', on_delete=models.SET_NULL, null=True, blank=True, related_name='number_plate_issues')
    rack                = models.ForeignKey('masters.Rack', on_delete=models.SET_NULL, null=True, blank=True, related_name='number_plate_issues')
    bin                 = models.ForeignKey('masters.Bin', on_delete=models.SET_NULL, null=True, blank=True, related_name='number_plate_issues')
    frame_amount        = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    created_at          = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"NUMISS-{self.pk} | {self.receipt_entry}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Number Plate Issues'


# ---------------------------------------------------------------------------
# RC Book Creation / Issue -- split of the existing flat RCBook model into
# the reference's two real lifecycle stages.
# ---------------------------------------------------------------------------

class RCBookCreation(DocStatusMixin, models.Model):
    rto_registration  = models.ForeignKey(RTORegistration, on_delete=models.PROTECT, related_name='rc_book_creations')
    agent             = models.ForeignKey('masters.Supplier', on_delete=models.SET_NULL, null=True, blank=True, related_name='rc_book_creations')
    registration_area = models.ForeignKey(RegistrationArea, on_delete=models.SET_NULL, null=True, blank=True, related_name='rc_book_creations')
    post_by_rto       = models.BooleanField(default=False)
    rc_number         = models.CharField(max_length=100, blank=True, verbose_name='Vehicle Number')
    created_at        = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"RCBC-{self.pk} | {self.rto_registration}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'RC Book Creations'


class RCBookIssue(DocStatusMixin, models.Model):
    class IssueType(models.TextChoices):
        CUSTOMER   = 'customer',   'Issue to Customer'
        BRANCH     = 'branch',     'Issue to Branch'
        SUB_DEALER = 'sub_dealer', 'Issue to Sub Dealers'

    rc_book_creation = models.ForeignKey(RCBookCreation, on_delete=models.PROTECT, related_name='issues')
    issue_type       = models.CharField(max_length=20, choices=IssueType.choices, default=IssueType.CUSTOMER)
    from_branch       = models.ForeignKey('accounts.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='rc_book_issues_from')
    to_branch         = models.ForeignKey('accounts.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='rc_book_issues_to')
    sub_dealer_name   = models.ForeignKey('masters.Supplier', on_delete=models.SET_NULL, null=True, blank=True, related_name='rc_book_issues')
    created_at        = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"RCBI-{self.pk} | {self.rc_book_creation}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'RC Book Issues'


class RCBookIssueItem(models.Model):
    """Collapses the reference's 'RC Issue Child' / 'Ex RC Issue Child' (two
    near-identical item tables differing only by an exchange-vehicle FK) into
    one child model with a nullable exchange_vehicle FK."""
    rc_book_issue     = models.ForeignKey(RCBookIssue, on_delete=models.CASCADE, related_name='items')
    exchange_vehicle  = models.ForeignKey('sales.ExchangeVehicle', on_delete=models.SET_NULL, null=True, blank=True, related_name='rc_book_issue_items')
    vehicle_number    = models.CharField(max_length=50, blank=True)
    party_name        = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.vehicle_number} — {self.party_name}"

    class Meta:
        verbose_name_plural = 'RC Book Issue Items'
