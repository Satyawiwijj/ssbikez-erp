import logging

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

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

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Sales Enquiries'

    def __str__(self):
        from customers.models import Customer
        try:
            lead = self.customer or self.prospect
        except (Customer.DoesNotExist, Prospect.DoesNotExist):
            lead = f'#{self.customer_id or self.prospect_id}'
        return f"ENQ-{self.pk} | {lead} — {self.bike_model}"

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

class VehicleSalesOrder(models.Model):
    class SalesStatus(models.TextChoices):
        BOOKED    = 'booked',    'Booked'
        INVOICED  = 'invoiced',  'Invoiced'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'

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
    booking_amount  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount    = models.DecimalField(max_digits=10, decimal_places=2)
    sales_status    = models.CharField(
        max_length=20,
        choices=SalesStatus.choices,
        default=SalesStatus.BOOKED,
        db_index=True,
    )
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
        return f"ORD-{self.pk} | {cust} — {veh}"


# ---------------------------------------------------------------------------
# VehicleDelivery
# ---------------------------------------------------------------------------

class VehicleDelivery(models.Model):
    sales_order   = models.OneToOneField(
        VehicleSalesOrder,
        on_delete=models.PROTECT,
        related_name='delivery'
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
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-delivery_date']
        verbose_name_plural = 'Vehicle Deliveries'

    def __str__(self):
        return f"DELIVERY-{self.pk} | ORD-{self.sales_order_id} on {self.delivery_date}"


# ---------------------------------------------------------------------------
# ExchangeVehicle
# ---------------------------------------------------------------------------

class ExchangeVehicle(models.Model):
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
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Exchange Vehicles'

    def __str__(self):
        return f"Exchange for ORD-{self.sales_order_id} — {self.old_vehicle_model}"


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
        except Exception:
            pass
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
    fitting_name = models.CharField(max_length=200)
    description  = models.TextField(blank=True)
    cost         = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Vehicle Fittings'

    def __str__(self):
        return f"{self.fitting_name} — Rs.{self.cost}"


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
    """When a VehicleDelivery is recorded, mark the sales order as delivered."""
    if not created:
        return
    order = instance.sales_order
    if order.sales_status != VehicleSalesOrder.SalesStatus.DELIVERED:
        # Use .save() so the VehicleSalesOrder post_save signal fires
        order.sales_status = VehicleSalesOrder.SalesStatus.DELIVERED
        order.save(update_fields=['sales_status'])


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
