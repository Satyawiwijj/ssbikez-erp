import logging

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import DocStatusMixin

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prospect — walk-in leads not yet registered as Customers
# ---------------------------------------------------------------------------

class Prospect(models.Model):
    """A walk-in or inbound lead who is not yet a registered Customer."""
    ENQUIRY_SOURCE_CHOICES = [
        ('walk_in',  'Walk In'),
        ('phone',    'Phone'),
        ('website',  'Website'),
        ('referral', 'Referral'),
        ('social',   'Social Media'),
    ]

    full_name           = models.CharField(max_length=200)
    phone               = models.CharField(max_length=15)
    vehicle_of_interest = models.ForeignKey(
        'customers.BikeModel',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='prospects'
    )
    enquiry_source = models.CharField(
        max_length=50,
        choices=ENQUIRY_SOURCE_CHOICES,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Prospects'

    def __str__(self):
        return f"{self.full_name} ({self.phone})"

    @property
    def display_name(self):
        return self.full_name

    @property
    def display_phone(self):
        return self.phone


# ---------------------------------------------------------------------------
# SalesEnquiry
# ---------------------------------------------------------------------------

class SalesEnquiry(models.Model):
    class Status(models.TextChoices):
        OPEN      = 'open',      'Open'
        FOLLOW_UP = 'follow_up', 'Follow Up'
        CONVERTED = 'converted', 'Converted'
        LOST      = 'lost',      'Lost'

    class EnquirySource(models.TextChoices):
        WALK_IN  = 'walk_in',  'Walk In'
        PHONE    = 'phone',    'Phone'
        WEBSITE  = 'website',  'Website'
        REFERRAL = 'referral', 'Referral'
        SOCIAL   = 'social',   'Social Media'

    # Either customer OR prospect must be set (validated in clean())
    customer        = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='enquiries',
        null=True, blank=True,
    )
    prospect        = models.ForeignKey(
        Prospect,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='enquiries',
    )
    sales_executive = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='enquiries_handled'
    )
    bike_model      = models.ForeignKey(
        'customers.BikeModel',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='enquiries'
    )
    branch          = models.ForeignKey(
        'accounts.Branch',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='enquiries'
    )
    enquiry_source  = models.CharField(
        max_length=50,
        choices=EnquirySource.choices,
        blank=True, null=True
    )
    status          = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    whatsapp_no           = models.CharField(max_length=20, blank=True, default='', verbose_name='WhatsApp No')
    email                 = models.EmailField(blank=True, default='', verbose_name='Email')
    purpose               = models.CharField(max_length=100, blank=True, default='', verbose_name='Purpose')
    expected_purchase_date = models.DateField(null=True, blank=True, verbose_name='Expected Purchase Date')
    # ERP alignment — customer classification
    customer_enquiry_date = models.DateField(null=True, blank=True, verbose_name='Customer Enquiry Date')
    customer_type = models.CharField(
        max_length=50, blank=True, default='', verbose_name='Customer Type',
        choices=[('Individual', 'Individual'), ('Corporate', 'Corporate'), ('Fleet', 'Fleet')]
    )
    gender = models.CharField(
        max_length=20, blank=True, default='', verbose_name='Gender',
        choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')]
    )
    enquiry_type = models.CharField(
        max_length=50, blank=True, default='', verbose_name='Enquiry Type',
        choices=[('New Vehicle', 'New Vehicle'), ('Exchange', 'Exchange'), ('Fleet', 'Fleet'), ('Corporate', 'Corporate')]
    )
    test_ride_taken = models.CharField(
        max_length=10, blank=True, default='', verbose_name='Test Ride Taken',
        choices=[('Yes', 'Yes'), ('No', 'No')]
    )
    payment_type = models.CharField(
        max_length=50, blank=True, default='', verbose_name='Payment Type',
        choices=[('Cash', 'Cash'), ('Finance', 'Finance'), ('Exchange', 'Exchange')]
    )
    customer_interested_in_exchange = models.CharField(
        max_length=10, blank=True, default='', verbose_name='Customer Interested in Exchange',
        choices=[('Yes', 'Yes'), ('No', 'No')]
    )
    source_of_information = models.CharField(max_length=100, blank=True, default='', verbose_name='Source of Information')
    # ERP alignment — address
    address_line1 = models.CharField(max_length=200, blank=True, default='', verbose_name='Address 1')
    address_line2 = models.CharField(max_length=200, blank=True, default='', verbose_name='Address 2')
    address_line3 = models.CharField(max_length=200, blank=True, default='', verbose_name='Address 3')
    address_line4 = models.CharField(max_length=200, blank=True, default='', verbose_name='Address 4')
    district = models.CharField(max_length=100, blank=True, default='', verbose_name='District')
    city     = models.CharField(max_length=100, blank=True, default='', verbose_name='City')
    state    = models.CharField(max_length=100, blank=True, default='', verbose_name='State')
    pincode  = models.CharField(max_length=10, blank=True, default='', verbose_name='Pincode')
    remarks         = models.TextField(blank=True, null=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    # Trade-in pre-assessment -- reference embeds this directly on the enquiry form, gated on
    # customer_interested_in_exchange == 'Yes'. Confirmed live against 'Sales Enquiry Form';
    # there is no ExchangeVehicle record yet at this stage (that only exists 1:1 off a confirmed
    # Sales Order), so this is deliberately its own flat cluster, not a shared model.
    exchange_type                    = models.CharField(max_length=20, blank=True, default='',
        choices=[('Yamaha', 'Yamaha'), ('Competition', 'Competition')])
    exchange_vehicle_model_and_make  = models.CharField(max_length=200, blank=True, default='')
    exchange_year_of_manufacturing   = models.CharField(max_length=10, blank=True, default='')
    exchange_owner_type              = models.CharField(max_length=20, blank=True, default='',
        choices=[('First Owner', 'First Owner'), ('Second Owner', 'Second Owner'), ('Third Owner', 'Third Owner')])
    exchange_valid_insurance         = models.CharField(max_length=5, blank=True, default='',
        choices=[('Yes', 'Yes'), ('No', 'No')])
    exchange_original_rc_available   = models.CharField(max_length=5, blank=True, default='',
        choices=[('Yes', 'Yes'), ('No', 'No')])
    exchange_customer_expected_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    exchange_price_offer_by_dealer   = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Sales Enquiries'

    def __str__(self):
        from customers.models import Customer
        try:
            lead = self.customer or self.prospect
        except (Customer.DoesNotExist, Prospect.DoesNotExist):
            lead = f'#{self.customer_id or self.prospect_id}'
        if lead is None:
            lead = '—'
        return f"ENQ-{self.pk} | {lead} — {self.bike_model or '—'}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.customer and not self.prospect:
            raise ValidationError(
                'Either a Customer or a Prospect must be set on the enquiry.'
            )

    @property
    def lead_name(self):
        if self.customer:
            return self.customer.full_name
        if self.prospect:
            return self.prospect.full_name
        return '—'

    @property
    def lead_phone(self):
        if self.customer:
            return self.customer.phone
        if self.prospect:
            return self.prospect.phone
        return '—'

    @property
    def is_prospect_only(self):
        return bool(self.prospect and not self.customer)


# ---------------------------------------------------------------------------
# SalesAppointment
# ---------------------------------------------------------------------------

class SalesAppointment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        NO_SHOW   = 'no_show',   'No Show'

    class Purpose(models.TextChoices):
        TEST_RIDE      = 'test_ride',      'Test Ride'
        DISCUSSION     = 'discussion',     'Discussion'
        SHOWROOM_VISIT = 'showroom_visit', 'Showroom Visit'
        DELIVERY       = 'delivery',       'Delivery'

    enquiry                 = models.ForeignKey(
        SalesEnquiry,
        on_delete=models.CASCADE,
        related_name='appointments'
    )
    appointment_date        = models.DateTimeField()
    purpose                 = models.CharField(
        max_length=50,
        choices=Purpose.choices,
        blank=True, null=True
    )
    status                  = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED
    )
    # ERP-matched fields
    vehicle_code            = models.CharField(max_length=50, blank=True, default='', verbose_name='Vehicle Code')
    vehicle_name            = models.CharField(max_length=200, blank=True, default='')
    gender                  = models.CharField(max_length=20, blank=True, default='')
    phone_no                = models.CharField(max_length=20, blank=True, default='')
    address                 = models.TextField(blank=True, default='')
    whatsapp_no             = models.CharField(max_length=20, blank=True, default='')
    is_cancelled_postponed  = models.BooleanField(default=False, verbose_name='Appointment Cancel/Postponed')
    cancel_reason           = models.TextField(blank=True, default='', verbose_name='Cancellation / Postpone Reason')
    created_at              = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-appointment_date']
        verbose_name_plural = 'Sales Appointments'

    def __str__(self):
        try:
            lead_name = self.enquiry.lead_name
        except SalesEnquiry.DoesNotExist:
            lead_name = f'#{self.enquiry_id}'
        return f"APT-{self.pk} | {lead_name} on {self.appointment_date:%d %b %Y}"


# ---------------------------------------------------------------------------
# SalesFeedback
# ---------------------------------------------------------------------------

class SalesFeedback(models.Model):
    enquiry            = models.ForeignKey(
        SalesEnquiry,
        on_delete=models.CASCADE,
        related_name='feedback'
    )
    # CRM workflow link — connects Enquiry → Appointment → Feedback
    appointment        = models.ForeignKey(
        SalesAppointment,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='feedback',
        verbose_name='Sales Appointment'
    )
    feedback_notes     = models.TextField(blank=True, null=True)
    next_followup_date = models.DateField(blank=True, null=True, verbose_name='Feed Back Follow Date')
    feed_back_date     = models.DateField(blank=True, null=True, verbose_name='Feedback Date')
    # ERP-matched fields
    vehicle_name       = models.CharField(max_length=200, blank=True, default='', verbose_name='Vehicle Code')
    phone_no           = models.CharField(max_length=20, blank=True, default='')
    created_by         = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sales_feedback_created'
    )
    created_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Sales Feedback'

    def __str__(self):
        return f"Feedback on ENQ-{self.enquiry_id} — {self.created_at:%d %b %Y}"


# ---------------------------------------------------------------------------
# VehicleSalesOrder
# ---------------------------------------------------------------------------

class VehicleSalesOrder(DocStatusMixin, models.Model):
    _amend_reset_number_field = 'order_number'

    def cancel(self, user):
        # Guard: block cancelling an order that already has a submitted
        # Delivery against it -- same class of downstream-reference guard as
        # used_vehicles.UsedVehicleSale.cancel(). Without this, an order could
        # flip to Cancelled (this diff's own sync_sales_status_on_order_cancel
        # signal forces sales_status=Cancelled too) while a live, Submitted
        # VehicleDelivery still points at it -- a contradictory state the
        # used_vehicles equivalent relationship already prevents.
        if self.deliveries.filter(docstatus=self.DocStatus.SUBMITTED).exists():
            raise ValueError(
                'Cannot cancel: a submitted Delivery already exists for this order.'
            )
        super().cancel(user)

    class SalesStatus(models.TextChoices):
        BOOKED    = 'booked',    'Booked'
        INVOICED  = 'invoiced',  'Invoiced'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'

    class FinanceClosing(models.TextChoices):
        YES = 'yes', 'Yes'
        NO  = 'no',  'No'

    class PaymentStatus(models.TextChoices):
        UNPAID    = 'unpaid',    'Unpaid'
        COMPLETED = 'completed', 'Completed'

    enquiry         = models.ForeignKey(
        SalesEnquiry,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='orders'
    )
    customer        = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='sales_orders'
    )
    vehicle         = models.ForeignKey(
        'customers.VehicleStock',
        on_delete=models.PROTECT,
        related_name='sales_orders',
        null=True, blank=True,
    )
    sales_executive = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sales_orders'
    )
    branch          = models.ForeignKey(
        'accounts.Branch',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sales_orders'
    )
    order_number    = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    order_form_series = models.ForeignKey(
        'masters.OrderFormSeries', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sales_orders', verbose_name='Order Form Series',
        help_text='Optional link to a pre-generated Order Form Series number; order_number above remains the working numbering mechanism'
    )
    insurance_name  = models.ForeignKey(
        'masters.Supplier', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='insured_sales_orders', verbose_name='Insurance Name'
    )
    sales_finance   = models.ForeignKey(
        'masters.FinanceCompany', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sales_orders', verbose_name='Sales Finance'
    )
    gst_category    = models.CharField(max_length=30, blank=True)
    delivery_date   = models.DateField(null=True, blank=True, verbose_name='Expected Delivery Date')

    # Special Helmet section
    special_helmet           = models.BooleanField(default=False)
    helmet_name              = models.CharField(max_length=200, blank=True)
    helmet_price             = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    special_helmet_warehouse = models.ForeignKey(
        'masters.Warehouse', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='Special Helmet Warehouse'
    )
    default_helmet           = models.CharField(max_length=200, blank=True)

    # Exchange Vehicle summary (detail record lives on ExchangeVehicle)
    has_vehicle_exchange = models.BooleanField(default=False)
    finance_closing      = models.CharField(max_length=10, choices=FinanceClosing.choices, blank=True)
    exchange_amount      = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    # Temp Charges section
    temp_charges_applied = models.BooleanField(default=False)
    temp_charges         = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    temp_area            = models.CharField(max_length=200, blank=True)

    booking_amount  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount    = models.DecimalField(max_digits=10, decimal_places=2)
    sales_status    = models.CharField(
        max_length=20,
        choices=SalesStatus.choices,
        default=SalesStatus.BOOKED,
        db_index=True,
    )

    # Totals / payment status cluster
    total_qty                             = models.IntegerField(default=0, blank=True)
    invoice_discount                      = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    is_finance_done                       = models.BooleanField(default=False)
    table_charges_total                   = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    delivery_discount                     = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    finance_amount                        = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    advance_payment                       = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, help_text='Rollup of advance_payments lines')
    additional_discount_amount            = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    payment_reference                     = models.CharField(max_length=200, blank=True)
    number_plate_amount                   = models.DecimalField(max_digits=10, decimal_places=2, default=330, blank=True)
    balance_payment                       = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    payment_status                        = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID
    )
    customer_refund                       = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    balance_sales_amount                  = models.IntegerField(default=0, blank=True)

    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Vehicle Sales Orders'

    def __str__(self):
        from customers.models import Customer, VehicleStock
        try:
            cust = self.customer
        except Customer.DoesNotExist:
            cust = f'#{self.customer_id}'
        try:
            veh = self.vehicle
        except VehicleStock.DoesNotExist:
            veh = f'#vehicle_{self.vehicle_id}'
        if veh is None:
            veh = '—'
        return f"{self.order_number or f'ORD-{self.pk}'} | {cust} — {veh}"

    def save(self, *args, **kwargs):
        if not self.gst_category and self.customer_id:
            self.gst_category = self.customer.gst_category
        if not self.order_number:
            with transaction.atomic():
                last = VehicleSalesOrder.objects.select_for_update().order_by('-id').values_list('order_number', flat=True).first()
                next_seq = 1
                if last and last.startswith('ORD-'):
                    try:
                        next_seq = int(last.split('-')[1]) + 1
                    except (IndexError, ValueError):
                        pass
                self.order_number = f'ORD-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    @property
    def current_delivery(self):
        """The active (non-cancelled) delivery, if any — deliveries is a plain
        FK (not O2O) so a cancelled+amended pair can coexist historically."""
        return self.deliveries.exclude(docstatus=DocStatusMixin.DocStatus.CANCELLED).order_by('-created_at').first()

    @property
    def current_invoice(self):
        """The active (non-cancelled) invoice, if any — same reasoning as current_delivery."""
        return self.invoices.exclude(docstatus=DocStatusMixin.DocStatus.CANCELLED).order_by('-created_at').first()

    def recompute_totals(self):
        """Sum VehicleSaleItem.amount across this order's items and persist
        into total_amount. Called after the items formset is saved — see
        sales/views.py order_create/order_update."""
        from accounts.utils import recompute_total_from_items
        self.total_amount = recompute_total_from_items(self, 'items', 'amount')
        self.save(update_fields=['total_amount'])


# ---------------------------------------------------------------------------
# VehicleDelivery
# ---------------------------------------------------------------------------

class VehicleDelivery(DocStatusMixin, models.Model):
    class PaymentStatus(models.TextChoices):
        UNPAID    = 'unpaid',    'Unpaid'
        COMPLETED = 'completed', 'Completed'

    # A plain ForeignKey (not OneToOne): docstatus/amend means an order can
    # accumulate a cancelled delivery + its amended replacement over time.
    # Use VehicleSalesOrder.current_delivery for "the active one".
    sales_order   = models.ForeignKey(
        VehicleSalesOrder,
        on_delete=models.PROTECT,
        related_name='deliveries'
    )
    delivery_date = models.DateField()
    delivered_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='vehicle_deliveries'
    )
    remarks       = models.TextField(blank=True, null=True)
    # Delivery checklist
    checklist_insurance   = models.BooleanField(default=False, verbose_name='Insurance Policy Handed Over')
    checklist_rc_book     = models.BooleanField(default=False, verbose_name='RC Book / Temp Reg Handed Over')
    checklist_warranty    = models.BooleanField(default=False, verbose_name='Warranty Card Handed Over')
    checklist_toolkit     = models.BooleanField(default=False, verbose_name='Toolkit & Owner Manual Handed Over')
    checklist_accessories = models.BooleanField(default=False, verbose_name='Accessories Fitted & Verified')
    issue_gate_pass       = models.BooleanField(default=False, verbose_name='Issue Gate Pass')

    # Approval workflow — Manager then Finance, gates submission
    manager_approval_requested = models.BooleanField(default=False)
    manager_approved           = models.BooleanField(default=False)
    finance_approved           = models.BooleanField(default=False)

    # On-delivery petrol offer
    offer_petrol   = models.BooleanField(default=False)
    petrol_type    = models.CharField(max_length=50, blank=True)
    petrol_litre   = models.DecimalField(max_digits=6, decimal_places=2, default=0, blank=True)
    petrol_amount  = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    bunk_name      = models.ForeignKey(
        'masters.BunkName', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )

    # Totals / status
    total_quantity                    = models.IntegerField(default=0, blank=True)
    invoice_discount                  = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    table_charges_total                = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    finance_amount                     = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    additional_discount                = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    total_amount                       = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    sales_order_additional_discount    = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    pending_amount                     = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    advance_amount                     = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    refund_amount                      = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    payment_status                     = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID
    )

    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-delivery_date']
        verbose_name_plural = 'Vehicle Deliveries'

    def __str__(self):
        return f"DELIVERY-{self.pk} | ORD-{self.sales_order_id} on {self.delivery_date}"


# ---------------------------------------------------------------------------
# Vehicle Delivery child tables
# ---------------------------------------------------------------------------

class DeliveryNoteItem(models.Model):
    class WarrantyRSAAMC(models.TextChoices):
        WARRANTY = 'warranty', 'Warranty'
        RSA      = 'rsa',      'RSA'
        AMC      = 'amc',      'AMC'
        NONE     = 'none',     'None'

    delivery         = models.ForeignKey(VehicleDelivery, on_delete=models.CASCADE, related_name='items')
    item_code        = models.CharField(max_length=100, blank=True)
    warranty_rsa_amc = models.CharField(max_length=20, choices=WarrantyRSAAMC.choices, default=WarrantyRSAAMC.NONE)
    rate             = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    actual_amount    = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Delivery Note Items'

    def __str__(self):
        return f"{self.item_code} — Rs.{self.actual_amount}"


class DeliveryNoteAdvancePayment(models.Model):
    delivery        = models.ForeignKey(VehicleDelivery, on_delete=models.CASCADE, related_name='advance_payments')
    mode_of_payment = models.CharField(max_length=100, blank=True)
    date            = models.DateField()
    amount          = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    to_account      = models.CharField(max_length=200, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'Delivery Note Advance Payments'

    def __str__(self):
        return f"{self.mode_of_payment} — Rs.{self.amount} on {self.date}"


class DeliveryNotePaymentEntry(models.Model):
    delivery        = models.ForeignKey(VehicleDelivery, on_delete=models.CASCADE, related_name='payment_entries')
    date            = models.DateField()
    amount          = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    mode_of_payment = models.CharField(max_length=100, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'Delivery Note Payment Entries'

    def __str__(self):
        return f"{self.mode_of_payment} — Rs.{self.amount} on {self.date}"


# ---------------------------------------------------------------------------
# ExchangeVehicle
# ---------------------------------------------------------------------------

class ExchangeVehicle(models.Model):
    class VehicleCategory(models.TextChoices):
        MOTORCYCLE = 'motorcycle', 'Motorcycle'
        SCOOTER    = 'scooter',    'Scooter'
        MOPED      = 'moped',      'Moped'
        OTHER      = 'other',      'Other'

    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID    = 'paid',    'Paid'

    sales_order       = models.OneToOneField(
        VehicleSalesOrder,
        on_delete=models.CASCADE,
        related_name='exchange_vehicle'
    )
    old_vehicle_model = models.CharField(max_length=100, blank=True, null=True)
    registration_no   = models.CharField(max_length=50, blank=True, null=True)
    valuation_amount  = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # RC handover tracking — customer must physically hand over the old
    # vehicle's RC book as part of the trade-in.
    rc_handed_over    = models.BooleanField(default=False, verbose_name='RC Book Handed Over')
    rc_handover_date  = models.DateField(null=True, blank=True, verbose_name='RC Handover Date')

    manufacturing_company = models.CharField(max_length=100, blank=True, verbose_name='Manufacturing Company')
    colour                = models.CharField(max_length=50, blank=True, verbose_name='Colour')
    engine_no             = models.CharField(max_length=50, blank=True, verbose_name='Engine Number')
    chassis_no            = models.CharField(max_length=50, blank=True, verbose_name='Chassis No')
    year_of_make          = models.PositiveIntegerField(null=True, blank=True, verbose_name='Year of Make')
    hp_endorsement        = models.BooleanField(default=False, verbose_name='HP Endorsement')
    sub_group             = models.CharField(max_length=100, blank=True, verbose_name='Sub Group')
    vehicle_category      = models.CharField(
        max_length=20, choices=VehicleCategory.choices, blank=True, verbose_name='Vehicle Category'
    )
    target_warehouse      = models.ForeignKey(
        'masters.Warehouse', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='exchange_vehicles', verbose_name='Target Warehouse'
    )
    insurance_valid_upto  = models.DateField(null=True, blank=True, verbose_name='Insurance Valid Upto')
    payment_status        = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING,
        verbose_name='Payment Status'
    )

    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Exchange Vehicles'

    def __str__(self):
        return f"Exchange for ORD-{self.sales_order_id} — {self.old_vehicle_model}"


# ---------------------------------------------------------------------------
# Phase 13 -- Dealer sub-module: reselling a traded-in vehicle onward to a
# wholesale dealer, once it's already in used-vehicle stock. Lives alongside
# ExchangeVehicle above since this is the same domain's downstream workflow.
# ---------------------------------------------------------------------------

class Dealer(models.Model):
    """Reference: 'Dealer' master (non-submittable, autoname field:dealer_name)."""
    class GstCategory(models.TextChoices):
        UNREGISTERED       = 'unregistered',        'Unregistered'
        REGISTERED_REGULAR = 'registered_regular',   'Registered Regular'

    dealer_name    = models.CharField(max_length=200, unique=True)
    gstin          = models.CharField(max_length=20, blank=True)
    mobile_number  = models.CharField(max_length=20)
    gst_category   = models.CharField(max_length=20, choices=GstCategory.choices, blank=True)
    warehouse      = models.ForeignKey('masters.Warehouse', on_delete=models.PROTECT, related_name='dealers')
    email          = models.EmailField(blank=True)
    branch         = models.ForeignKey('accounts.Branch', on_delete=models.PROTECT, related_name='dealers', verbose_name='Area')
    address_type   = models.CharField(max_length=100, blank=True)
    address_line1  = models.CharField(max_length=200, blank=True)
    state          = models.CharField(max_length=100, blank=True)
    country        = models.CharField(max_length=100, blank=True)
    citytown       = models.CharField(max_length=100, blank=True, verbose_name='City/Town')
    pincode        = models.CharField(max_length=10, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.dealer_name

    class Meta:
        ordering = ['dealer_name']
        verbose_name_plural = 'Dealers'


YES_NO_CHOICES = [('', '—'), ('yes', 'Yes'), ('no', 'No')]


class ExchangeVehicleDealer(DocStatusMixin, models.Model):
    """Reference: 'Exchange Vehicle Dealer' -- transfers a batch of traded-in vehicles from our
    stock to a wholesale dealer. The header also carries a full duplicate single-vehicle field
    set in the reference (manufacturing_company/chasis_no/model/colour/year_of_making/remarks/
    a Customer-Link party_name) -- confirmed live to be the exact same "header duplicates the
    child table" Frappe artifact already resolved for RTOPayment/RegpayCreation in Phase 9a;
    dropped here for the same reason, only the batch child table is built."""
    _amend_reset_number_field = 'transfer_no'

    transfer_no        = models.CharField(max_length=50, unique=True, blank=True, editable=False)
    date                = models.DateField()
    from_warehouse      = models.ForeignKey('masters.Warehouse', on_delete=models.PROTECT, related_name='exchange_vehicle_dealer_transfers_out')
    to_warehouse        = models.ForeignKey('masters.Warehouse', on_delete=models.PROTECT, related_name='exchange_vehicle_dealer_transfers_in')
    dealer              = models.ForeignKey(Dealer, on_delete=models.PROTECT, related_name='vehicle_transfers')
    branch              = models.ForeignKey('accounts.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='exchange_vehicle_dealer_transfers')
    hp_endorsement      = models.BooleanField(default=False, help_text='Confirmed live as a batch-level field with no per-vehicle child equivalent')
    insurance_received  = models.BooleanField(default=False, help_text='Confirmed live as a batch-level field with no per-vehicle child equivalent')
    created_at          = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.transfer_no:
            with transaction.atomic():
                last = ExchangeVehicleDealer.objects.select_for_update().order_by('-id').values_list('transfer_no', flat=True).first()
                next_seq = 1
                if last:
                    try:
                        next_seq = int(last.rsplit('-', 1)[-1]) + 1
                    except ValueError:
                        pass
                self.transfer_no = f'EX-VEH-DEALER-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.transfer_no

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Exchange Vehicle Dealer Transfers'


class ExchangeVehicleDealerItem(models.Model):
    transfer            = models.ForeignKey(ExchangeVehicleDealer, on_delete=models.CASCADE, related_name='vehicle_details')
    vehicle_name         = models.CharField(max_length=200, blank=True,
                                             help_text="Reference links to 'Exchange Master Used Vehicle Names' -- confirmed 0 records, "
                                                        'no real Django master needed -- free text instead')
    engine_number         = models.CharField(max_length=100, blank=True)
    registration_number   = models.ForeignKey('used_vehicles.UsedVehicleRegisterNo', on_delete=models.PROTECT, null=True, blank=True, related_name='dealer_transfer_items')
    party_name            = models.CharField(max_length=200, blank=True,
                                              help_text="Reference types this row's own field as free text (Data), not a Link -- preserved as-is")
    rc_book_received      = models.CharField(max_length=5, choices=YES_NO_CHOICES, blank=True)
    rc_book_number        = models.CharField(max_length=100, blank=True)
    noc                   = models.CharField(max_length=5, choices=YES_NO_CHOICES, blank=True, verbose_name='NOC')
    to_received            = models.CharField(max_length=5, choices=YES_NO_CHOICES, blank=True, verbose_name='T.O Received')
    vehicle_amount         = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    color                  = models.CharField(max_length=50, blank=True,
                                               help_text='Reference links to Product Color; no Django master exists anywhere -- free text instead')
    vehicle_value          = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    vehicle_code           = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.vehicle_code} — {self.registration_number or '—'}"

    class Meta:
        verbose_name_plural = 'Exchange Vehicle Dealer Items'


@receiver(post_save, sender=ExchangeVehicleDealer)
def on_exchange_vehicle_dealer_submitted(sender, instance, **kwargs):
    if instance.docstatus != ExchangeVehicleDealer.DocStatus.SUBMITTED:
        return
    for row in instance.vehicle_details.select_related('registration_number').all():
        if row.registration_number_id and row.registration_number.stock_status != row.registration_number.StockStatus.SOLD:
            row.registration_number.stock_status = row.registration_number.StockStatus.SOLD
            row.registration_number.save(update_fields=['stock_status'])


class ExchangeDealerPayment(DocStatusMixin, models.Model):
    """Reference: 'Exchange Dealer Payment' -- paying the dealer for an already-transferred
    batch. No stock side effect of its own -- the vehicle already left stock on
    ExchangeVehicleDealer submit; this is purely a payment record."""
    class PaymentMode(models.TextChoices):
        CASH   = 'cash',   'Cash'
        CREDIT = 'credit', 'Credit'

    _amend_reset_number_field = 'payment_no'

    payment_no            = models.CharField(max_length=50, unique=True, blank=True, editable=False)
    date                   = models.DateField()
    dealer                  = models.ForeignKey(Dealer, on_delete=models.PROTECT, related_name='payments')
    exchange_vehicle_dealer = models.ForeignKey(ExchangeVehicleDealer, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    branch                  = models.ForeignKey('accounts.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='exchange_dealer_payments')
    payment_mode             = models.CharField(max_length=10, choices=PaymentMode.choices, blank=True, verbose_name='Pay Type')
    total_amount              = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    pending_amount             = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    payment_status              = models.CharField(max_length=30, blank=True,
                                                     help_text="Reference types this as free text (Data), not a Select -- preserved as-is")
    created_at                   = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.payment_no:
            with transaction.atomic():
                last = ExchangeDealerPayment.objects.select_for_update().order_by('-id').values_list('payment_no', flat=True).first()
                next_seq = 1
                if last:
                    try:
                        next_seq = int(last.rsplit('-', 1)[-1]) + 1
                    except ValueError:
                        pass
                self.payment_no = f'EX-DEALER-PAY-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.payment_no

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Exchange Dealer Payments'


class ExchangeDealerPaymentItem(models.Model):
    payment            = models.ForeignKey(ExchangeDealerPayment, on_delete=models.CASCADE, related_name='vehicle_details')
    register_number     = models.ForeignKey('used_vehicles.UsedVehicleRegisterNo', on_delete=models.PROTECT, related_name='dealer_payment_items')
    vehicle_name          = models.CharField(max_length=200, blank=True)
    vehicle_amount         = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                                  validators=[MinValueValidator(0)],
                                                  help_text='Reference types this as free text (Data) but the header total_amount '
                                                             'clearly sums it -- built as a real Decimal, same "fix an obviously '
                                                             'mistyped reference field" call made elsewhere this session')
    allow_permission        = models.BooleanField(default=False)
    date                     = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.register_number} — Rs.{self.vehicle_amount}"

    class Meta:
        verbose_name_plural = 'Exchange Dealer Payment Items'


class DealerRCHandOver(DocStatusMixin, models.Model):
    """Reference: 'Dealer RC Hand Over' -- RC-book handover tracking to the dealer, per vehicle,
    in batch. No stock side effect -- purely an RC-paperwork tracking document."""
    _amend_reset_number_field = 'handover_no'

    handover_no  = models.CharField(max_length=50, unique=True, blank=True, editable=False)
    dealer        = models.ForeignKey(Dealer, on_delete=models.PROTECT, related_name='rc_hand_overs')
    created_at     = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.handover_no:
            with transaction.atomic():
                last = DealerRCHandOver.objects.select_for_update().order_by('-id').values_list('handover_no', flat=True).first()
                next_seq = 1
                if last:
                    try:
                        next_seq = int(last.rsplit('-', 1)[-1]) + 1
                    except ValueError:
                        pass
                self.handover_no = f'Dealer-RC-HAND-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.handover_no

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Dealer RC Hand Overs'


class DealerRCHandOverItem(models.Model):
    handover              = models.ForeignKey(DealerRCHandOver, on_delete=models.CASCADE, related_name='items')
    register_number        = models.ForeignKey('used_vehicles.UsedVehicleRegisterNo', on_delete=models.PROTECT, related_name='dealer_rc_handover_items')
    noc                      = models.CharField(max_length=5, choices=YES_NO_CHOICES, blank=True, verbose_name='NOC')
    to_received               = models.CharField(max_length=5, choices=YES_NO_CHOICES, blank=True, verbose_name='T.O. Received')
    rc_book_received           = models.CharField(max_length=5, choices=YES_NO_CHOICES, blank=True)
    vehicle_received             = models.CharField(max_length=5, choices=YES_NO_CHOICES, blank=True)
    rc_book_number                = models.CharField(max_length=100, blank=True)
    date                            = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.register_number} — {self.handover.handover_no}"

    class Meta:
        verbose_name_plural = 'Dealer RC Hand Over Items'


# ---------------------------------------------------------------------------
# VehicleAllotment — formal chassis/engine assignment to an order
# ---------------------------------------------------------------------------

class VehicleAllotment(models.Model):
    sales_order    = models.OneToOneField(
        VehicleSalesOrder,
        on_delete=models.CASCADE,
        related_name='allotment'
    )
    vehicle        = models.ForeignKey(
        'customers.VehicleStock',
        on_delete=models.PROTECT,
        related_name='allotments'
    )
    allotted_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='vehicle_allotments'
    )
    allotment_date = models.DateField(auto_now_add=True)
    notes          = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Vehicle Allotments'

    def __str__(self):
        return f"Allot-{self.pk} | ORD-{self.sales_order_id}"

    def save(self, *args, **kwargs):
        # Mark the allotted vehicle as reserved
        try:
            from customers.models import VehicleStock
            VehicleStock.objects.filter(pk=self.vehicle_id).exclude(
                stock_status='sold'
            ).update(stock_status='reserved')
        except Exception as exc:
            logger.error("VehicleAllotment.save() failed to reserve vehicle %s for allotment %s: %s",
                         self.vehicle_id, self.pk, exc)
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# VehicleFitting — accessories / add-ons attached at time of sale
# ---------------------------------------------------------------------------

class VehicleFitting(models.Model):
    sales_order  = models.ForeignKey(
        VehicleSalesOrder,
        on_delete=models.CASCADE,
        related_name='fittings'
    )
    item_code    = models.CharField(max_length=100, blank=True)
    fitting_name = models.CharField(max_length=200, verbose_name='Item Name')
    description  = models.TextField(blank=True)
    quantity     = models.DecimalField(max_digits=10, decimal_places=2, default=1, blank=True, verbose_name='Quantity Count')
    rate         = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, verbose_name='Item Rate')
    cost         = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, verbose_name='Item Amount')
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Vehicle Fittings'

    def __str__(self):
        return f"{self.fitting_name} — Rs.{self.cost}"

    def save(self, *args, **kwargs):
        if self.rate:
            self.cost = self.quantity * self.rate
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# AdditionalVehicleFitting — a second, structurally-separate fittings table,
# matching the reference ERP's distinct "Additional Vehicle Fittings" grid
# (kept separate from VehicleFitting/"Fittings Table" for exact parity even
# though the two are near-identical in shape).
# ---------------------------------------------------------------------------

class AdditionalVehicleFitting(models.Model):
    sales_order = models.ForeignKey(
        VehicleSalesOrder,
        on_delete=models.CASCADE,
        related_name='additional_fittings'
    )
    item_code   = models.CharField(max_length=100, blank=True)
    item_name   = models.CharField(max_length=200)
    quantity    = models.DecimalField(max_digits=10, decimal_places=2, default=1, blank=True, verbose_name='QTY')
    rate        = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    total       = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Additional Vehicle Fittings'

    def __str__(self):
        return f"{self.item_name} — Rs.{self.total}"

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.rate
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# VehicleSaleItem — priced line items sold alongside the vehicle (matches
# reference "Items" table — distinct from the vehicle itself and from
# Fittings/Additional Fittings).
# ---------------------------------------------------------------------------

class VehicleSaleItem(models.Model):
    sales_order = models.ForeignKey(
        VehicleSalesOrder,
        on_delete=models.CASCADE,
        related_name='items'
    )
    item_name   = models.CharField(max_length=200)
    rate        = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, validators=[MinValueValidator(0)])
    quantity    = models.DecimalField(max_digits=10, decimal_places=2, default=1, blank=True, validators=[MinValueValidator(0)])
    amount      = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Vehicle Sale Items'

    def __str__(self):
        return f"{self.item_name} — Rs.{self.amount}"

    def save(self, *args, **kwargs):
        self.amount = self.quantity * self.rate
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# SalesOrderAdvancePayment — matches reference "Advance Payment Details"
# ---------------------------------------------------------------------------

class SalesOrderAdvancePayment(models.Model):
    sales_order      = models.ForeignKey(
        VehicleSalesOrder,
        on_delete=models.CASCADE,
        related_name='advance_payments'
    )
    mode_of_payment  = models.CharField(max_length=100, blank=True)
    draft_type       = models.CharField(max_length=100, blank=True, verbose_name='Draft/Bank Type')
    date             = models.DateField()
    amount           = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    to_account       = models.CharField(max_length=200, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'Sales Order Advance Payments'

    def __str__(self):
        return f"{self.mode_of_payment} — Rs.{self.amount} on {self.date}"


# ---------------------------------------------------------------------------
# FEATURE 1 — Sales Target Tracking
# ---------------------------------------------------------------------------

class SalesTarget(models.Model):
    sales_executive  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='sales_targets'
    )
    month            = models.IntegerField()
    year             = models.IntegerField()
    target_enquiries  = models.IntegerField(default=0)
    target_test_rides = models.IntegerField(default=0)
    target_conversions = models.IntegerField(default=0)
    target_revenue   = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_by       = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='targets_created'
    )
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['sales_executive', 'month', 'year']
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.sales_executive.get_full_name()} — {self.month}/{self.year}"

    @property
    def actual_enquiries(self):
        return SalesEnquiry.objects.filter(
            sales_executive=self.sales_executive,
            created_at__month=self.month,
            created_at__year=self.year
        ).count()

    @property
    def actual_conversions(self):
        return VehicleSalesOrder.objects.filter(
            sales_executive=self.sales_executive,
            created_at__month=self.month,
            created_at__year=self.year
        ).count()

    @property
    def actual_revenue(self):
        from django.db.models import Sum
        result = VehicleSalesOrder.objects.filter(
            sales_executive=self.sales_executive,
            created_at__month=self.month,
            created_at__year=self.year
        ).aggregate(total=Sum('total_amount'))['total']
        return result or 0

    @property
    def conversion_percent(self):
        if self.actual_enquiries == 0:
            return 0.0
        return round(self.actual_conversions / self.actual_enquiries * 100, 1)

    @property
    def revenue_achievement_percent(self) -> float:
        if not self.target_revenue or self.target_revenue == 0:
            return 0.0
        return round(float(self.actual_revenue) / float(self.target_revenue) * 100, 1)

    @property
    def overall_achievement_percent(self) -> float:
        scores = []
        if self.target_enquiries > 0:
            scores.append(min(100, self.actual_enquiries / self.target_enquiries * 100))
        if self.target_conversions > 0:
            scores.append(min(100, self.actual_conversions / self.target_conversions * 100))
        if self.target_revenue and self.target_revenue > 0:
            scores.append(min(100, float(self.actual_revenue or 0) / float(self.target_revenue) * 100))
        if not scores:
            return 0.0
        return round(sum(scores) / len(scores), 1)


# ---------------------------------------------------------------------------
# FEATURE 3 — Test Ride Log
# ---------------------------------------------------------------------------

class TestRideLog(models.Model):
    class Status(models.TextChoices):
        OUT       = 'out',       'Vehicle Out'
        RETURNED  = 'returned',  'Vehicle Returned'
        CANCELLED = 'cancelled', 'Cancelled'

    enquiry          = models.ForeignKey(
        SalesEnquiry, on_delete=models.CASCADE, related_name='test_rides'
    )
    vehicle          = models.ForeignKey(
        'customers.VehicleStock', on_delete=models.PROTECT, related_name='test_rides'
    )
    rider_name       = models.CharField(max_length=200)
    rider_phone      = models.CharField(max_length=15)
    license_number   = models.CharField(max_length=50)
    accompanied_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='test_rides_accompanied'
    )
    start_time       = models.DateTimeField()
    end_time         = models.DateTimeField(null=True, blank=True)
    start_odometer   = models.IntegerField(default=0)
    end_odometer     = models.IntegerField(null=True, blank=True)
    status           = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OUT
    )
    feedback_after_ride = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    created_by       = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='test_rides_created'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"TR-{self.pk} | {self.rider_name} | {self.vehicle}"

    @property
    def duration_minutes(self):
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds() / 60)
        return None


# ---------------------------------------------------------------------------
# FEATURE 5 — PDI Checklist (Pre-Delivery Inspection)
# ---------------------------------------------------------------------------

class PDIChecklist(models.Model):
    sales_order     = models.OneToOneField(
        VehicleSalesOrder, on_delete=models.CASCADE, related_name='pdi_checklist'
    )
    inspected_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    inspection_date = models.DateField(auto_now_add=True)

    # Engine and Mechanical
    engine_oil_level    = models.BooleanField(default=False)
    coolant_level       = models.BooleanField(default=False)
    brake_fluid_level   = models.BooleanField(default=False)
    chain_tension       = models.BooleanField(default=False)
    chain_lubrication   = models.BooleanField(default=False)
    tyre_pressure_front = models.BooleanField(default=False)
    tyre_pressure_rear  = models.BooleanField(default=False)
    brake_front_working = models.BooleanField(default=False)
    brake_rear_working  = models.BooleanField(default=False)
    clutch_adjustment   = models.BooleanField(default=False)
    throttle_smooth     = models.BooleanField(default=False)

    # Electrical
    battery_voltage      = models.BooleanField(default=False)
    headlight_working    = models.BooleanField(default=False)
    taillight_working    = models.BooleanField(default=False)
    indicators_working   = models.BooleanField(default=False)
    horn_working         = models.BooleanField(default=False)
    speedometer_working  = models.BooleanField(default=False)
    kill_switch_working  = models.BooleanField(default=False)

    # Body and Aesthetics
    paint_no_scratches   = models.BooleanField(default=False)
    all_panels_fitted    = models.BooleanField(default=False)
    mirrors_adjusted     = models.BooleanField(default=False)
    seat_firm            = models.BooleanField(default=False)
    toolkit_present      = models.BooleanField(default=False)
    owners_manual_present = models.BooleanField(default=False)

    # Documents
    invoice_ready        = models.BooleanField(default=False)
    insurance_done       = models.BooleanField(default=False)
    form20_submitted     = models.BooleanField(default=False)
    temporary_registration = models.BooleanField(default=False)

    overall_remarks = models.TextField(blank=True)
    is_approved     = models.BooleanField(default=False)
    approved_by     = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pdi_approvals'
    )

    class Meta:
        verbose_name = 'PDI Checklist'

    def __str__(self):
        return f"PDI-{self.pk} | Order {self.sales_order_id}"

    @property
    def mechanical_score(self):
        fields = ['engine_oil_level','coolant_level','brake_fluid_level','chain_tension',
                  'chain_lubrication','tyre_pressure_front','tyre_pressure_rear',
                  'brake_front_working','brake_rear_working','clutch_adjustment','throttle_smooth']
        passed = sum(1 for f in fields if getattr(self, f))
        return f"{passed}/{len(fields)}"

    @property
    def electrical_score(self):
        fields = ['battery_voltage','headlight_working','taillight_working','indicators_working',
                  'horn_working','speedometer_working','kill_switch_working']
        passed = sum(1 for f in fields if getattr(self, f))
        return f"{passed}/{len(fields)}"

    @property
    def all_critical_passed(self):
        critical = ['engine_oil_level','brake_front_working','brake_rear_working',
                    'tyre_pressure_front','tyre_pressure_rear','headlight_working',
                    'invoice_ready','insurance_done']
        return all(getattr(self, f) for f in critical)


# ---------------------------------------------------------------------------
# ERP Alignment — SalesEnquiry child tables
# ---------------------------------------------------------------------------

class SalesEnquiryCallLog(models.Model):
    enquiry    = models.ForeignKey(SalesEnquiry, on_delete=models.CASCADE, related_name='call_logs')
    unique_id  = models.CharField(max_length=100, blank=True, default='', verbose_name='Unique ID')
    call_from  = models.CharField(max_length=200, blank=True, default='', verbose_name='Call From')
    bill_sec   = models.IntegerField(default=0, verbose_name='Bill Sec')
    start_time = models.DateTimeField(null=True, blank=True, verbose_name='Start Time')
    audio_url  = models.URLField(blank=True, default='', verbose_name='Audio URL')
    notes      = models.TextField(blank=True, default='', verbose_name='Notes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Call Log'

    def __str__(self):
        return f"CallLog-{self.pk} | ENQ-{self.enquiry_id}"


class SalesEnquiryHistory(models.Model):
    STATUS_CHOICES = [
        ('Open', 'Open'), ('Follow Up', 'Follow Up'), ('Converted', 'Converted'),
        ('Lost', 'Lost'), ('Hot', 'Hot'), ('Warm', 'Warm'), ('Cold', 'Cold'),
    ]
    enquiry     = models.ForeignKey(SalesEnquiry, on_delete=models.CASCADE, related_name='histories')
    update_date = models.DateField(verbose_name='Update Date')
    remarks     = models.TextField(verbose_name='Remarks')
    status      = models.CharField(max_length=50, choices=STATUS_CHOICES, verbose_name='Status')

    class Meta:
        ordering = ['-update_date']
        verbose_name = 'Enquiry History'

    def __str__(self):
        return f"History-{self.pk} | ENQ-{self.enquiry_id} {self.status}"


class SalesFeedbackItem(models.Model):
    FEEDBACK_TYPE_CHOICES = [
        ('Product', 'Product'), ('Price', 'Price'), ('Service', 'Service'),
        ('Competitor', 'Competitor'), ('Finance', 'Finance'), ('Other', 'Other'),
    ]
    feedback      = models.ForeignKey(SalesFeedback, on_delete=models.CASCADE, related_name='feedback_items')
    points        = models.CharField(max_length=500, verbose_name='Points')
    feedback_type = models.CharField(max_length=100, blank=True, default='', choices=FEEDBACK_TYPE_CHOICES, verbose_name='Type')
    response      = models.TextField(blank=True, default='', verbose_name='Response')
    rating        = models.IntegerField(null=True, blank=True, choices=[(i, str(i)) for i in range(1, 6)], verbose_name='Rating')

    class Meta:
        ordering = ['id']
        verbose_name = 'Feedback Item'

    def __str__(self):
        return f"FBItem-{self.pk} | {self.points[:40]}"


# ---------------------------------------------------------------------------
# FIX 3 — Signals: auto-create CustomerVehicle on delivery
# ---------------------------------------------------------------------------

@receiver(post_save, sender=VehicleDelivery)
def on_delivery_created(sender, instance, created, **kwargs):
    """When a VehicleDelivery is submitted (docstatus flips to Submitted), mark
    the sales order as delivered. Gated on docstatus, not just row creation,
    since deliveries are now created as Draft first and submitted separately."""
    if instance.docstatus != VehicleDelivery.DocStatus.SUBMITTED:
        return
    order = instance.sales_order
    if order.sales_status != VehicleSalesOrder.SalesStatus.DELIVERED:
        # Use .save() so the VehicleSalesOrder post_save signal fires
        order.sales_status = VehicleSalesOrder.SalesStatus.DELIVERED
        order.save(update_fields=['sales_status'])


@receiver(post_save, sender=VehicleDelivery)
def on_delivery_cancelled(sender, instance, created, **kwargs):
    """When a VehicleDelivery is cancelled, revert the linked Sales Order's
    sales_status back off 'Delivered' — otherwise the order is stuck showing
    'Delivered' even though the delivery that put it there no longer stands.
    Reverts to 'Invoiced' if the order has an active invoice, else 'Booked'
    (mirrors the forward transitions already driven by current_invoice /
    current_delivery elsewhere on this model)."""
    if instance.docstatus != VehicleDelivery.DocStatus.CANCELLED:
        return
    order = instance.sales_order
    if order.sales_status != VehicleSalesOrder.SalesStatus.DELIVERED:
        return
    if order.current_delivery is not None:
        # Another non-cancelled delivery (e.g. an amended replacement)
        # already exists for this order — leave sales_status as Delivered.
        return
    if order.current_invoice is not None:
        order.sales_status = VehicleSalesOrder.SalesStatus.INVOICED
    else:
        order.sales_status = VehicleSalesOrder.SalesStatus.BOOKED
    order.save(update_fields=['sales_status'])


@receiver(post_save, sender=VehicleSalesOrder)
def sync_sales_status_on_order_cancel(sender, instance, created, **kwargs):
    """Keep sales_status in lockstep when an order's docstatus is cancelled —
    otherwise the order can end up in a stale sales_status (e.g. still
    'Booked') alongside a Cancelled docstatus, showing contradictory badges
    on the order detail page. Uses .update() (not instance.save()) so this
    doesn't recurse back into post_save."""
    if instance.docstatus != VehicleSalesOrder.DocStatus.CANCELLED:
        return
    if instance.sales_status == VehicleSalesOrder.SalesStatus.CANCELLED:
        return
    VehicleSalesOrder.objects.filter(pk=instance.pk).update(
        sales_status=VehicleSalesOrder.SalesStatus.CANCELLED
    )


@receiver(post_save, sender=VehicleSalesOrder)
def auto_create_customer_vehicle(sender, instance, created, update_fields, **kwargs):
    """When a VehicleSalesOrder status changes to delivered, auto-create CustomerVehicle."""
    # Skip if this save didn't touch sales_status
    if update_fields is not None and 'sales_status' not in update_fields:
        return
    if instance.sales_status != VehicleSalesOrder.SalesStatus.DELIVERED:
        return
    if not instance.vehicle_id:
        return

    try:
        from customer_vehicles.models import CustomerVehicle
        CustomerVehicle.objects.get_or_create(
            customer=instance.customer,
            vehicle=instance.vehicle,
            defaults={'purchase_date': instance.created_at.date()},
        )
        # Mark vehicle stock as sold (avoid triggering VehicleStock signal chain by using .update())
        from customers.models import VehicleStock
        VehicleStock.objects.filter(
            pk=instance.vehicle_id,
        ).exclude(stock_status='sold').update(stock_status='sold')

        # Mark enquiry as converted
        if instance.enquiry_id:
            SalesEnquiry.objects.filter(
                pk=instance.enquiry_id,
                status__in=[SalesEnquiry.Status.OPEN, SalesEnquiry.Status.FOLLOW_UP]
            ).update(status=SalesEnquiry.Status.CONVERTED)

    except Exception as exc:
        logger.error("auto_create_customer_vehicle failed for order %s: %s", instance.pk, exc)
