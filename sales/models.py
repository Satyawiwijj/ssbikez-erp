from django.conf import settings
from django.db import models


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

    customer        = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='enquiries'
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
    remarks         = models.TextField(blank=True, null=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Sales Enquiries'

    def __str__(self):
        return f"ENQ-{self.pk} | {self.customer} — {self.bike_model}"


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

    enquiry          = models.ForeignKey(
        SalesEnquiry,
        on_delete=models.CASCADE,
        related_name='appointments'
    )
    appointment_date = models.DateTimeField()
    purpose          = models.CharField(
        max_length=50,
        choices=Purpose.choices,
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
        verbose_name_plural = 'Sales Appointments'

    def __str__(self):
        return f"APT-{self.pk} | {self.enquiry.customer} on {self.appointment_date:%d %b %Y}"


class SalesFeedback(models.Model):
    enquiry            = models.ForeignKey(
        SalesEnquiry,
        on_delete=models.CASCADE,
        related_name='feedback'
    )
    feedback_notes     = models.TextField(blank=True, null=True)
    next_followup_date = models.DateField(blank=True, null=True)
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
        related_name='sales_orders'
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
        return f"ORD-{self.pk} | {self.customer} — {self.vehicle}"


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
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-delivery_date']
        verbose_name_plural = 'Vehicle Deliveries'

    def __str__(self):
        return f"DELIVERY-{self.pk} | ORD-{self.sales_order_id} on {self.delivery_date}"


class ExchangeVehicle(models.Model):
    sales_order       = models.OneToOneField(
        VehicleSalesOrder,
        on_delete=models.CASCADE,
        related_name='exchange_vehicle'
    )
    old_vehicle_model = models.CharField(max_length=100, blank=True, null=True)
    registration_no   = models.CharField(max_length=50, blank=True, null=True)
    valuation_amount  = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Exchange Vehicles'

    def __str__(self):
        return f"Exchange for ORD-{self.sales_order_id} — {self.old_vehicle_model}"
