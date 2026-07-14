from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from accounts.models import DocStatusMixin


# ---------------------------------------------------------------------------
# Type masters (kept in-app -- used only within the VAS domain)
# ---------------------------------------------------------------------------

class AMCType(models.Model):
    """Reference: 'AMC Types'."""
    code                    = models.CharField(max_length=50, unique=True)
    name                    = models.CharField(max_length=200)
    amc_validity_days       = models.IntegerField(default=0, blank=True)
    amc_amount              = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    hsn_code                = models.CharField(max_length=20, blank=True)
    ss_bikes                = models.BooleanField(default=True, verbose_name='SS Bikes')
    yamaha                  = models.BooleanField(default=False)
    deactivate_amc          = models.BooleanField(default=False)
    vehicle_type            = models.CharField(max_length=100, blank=True, help_text='Reference: Vehicle Type link; no Django master exists for this yet, kept as a snapshot label')
    no_of_service           = models.IntegerField(default=0, blank=True)
    water_wash_count_free   = models.IntegerField(default=0, blank=True)
    service_interval_days   = models.IntegerField(default=0, blank=True)
    grace_days              = models.IntegerField(default=0, blank=True)
    is_active               = models.BooleanField(default=True)
    created_at              = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} — {self.name}"

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'AMC Types'


class RSAType(models.Model):
    """Reference: 'RSA Types'."""
    code       = models.CharField(max_length=50, unique=True)
    name       = models.CharField(max_length=200)
    rsa_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    hsn_code   = models.CharField(max_length=20, blank=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} — {self.name}"

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'RSA Types'


class WarrantyType(models.Model):
    """Reference: 'Warranty Type' (Protection Plus)."""
    code       = models.CharField(max_length=50, unique=True)
    name       = models.CharField(max_length=200)
    hsn_code   = models.CharField(max_length=20, blank=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} — {self.name}"

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Warranty Types'


# ---------------------------------------------------------------------------
# Sale-side documents (submittable, one per vehicle sold)
# ---------------------------------------------------------------------------

class AMCPackage(DocStatusMixin, models.Model):
    class Status(models.TextChoices):
        ACTIVE    = 'active',    'Active'
        EXPIRED   = 'expired',   'Expired'
        CANCELLED = 'cancelled', 'Cancelled'

    customer_vehicle      = models.ForeignKey(
        'customer_vehicles.CustomerVehicle',
        on_delete=models.PROTECT,
        related_name='amc_packages'
    )
    amc_type               = models.ForeignKey(AMCType, on_delete=models.PROTECT, related_name='packages', null=True, blank=True)
    sales_order            = models.ForeignKey('sales.VehicleSalesOrder', on_delete=models.SET_NULL, null=True, blank=True, related_name='amc_packages')
    invoice                = models.ForeignKey('billing.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='amc_packages')
    start_date             = models.DateField(blank=True, null=True)
    end_date               = models.DateField(blank=True, null=True)
    amount                 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    gst_amount              = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    without_gst_amount      = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    vehicle_number          = models.CharField(max_length=50, blank=True)
    chasis_number           = models.CharField(max_length=100, blank=True)
    ss_bikes                = models.BooleanField(default=True, verbose_name='SS Bikes')
    yamaha                  = models.BooleanField(default=False)
    no_of_service           = models.IntegerField(default=0, blank=True)
    water_wash_count_free   = models.IntegerField(default=0, blank=True)
    service_interval        = models.IntegerField(default=0, blank=True)
    grace_days              = models.IntegerField(default=0, blank=True)
    vehicle_group           = models.CharField(max_length=100, blank=True)
    status                  = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    created_at              = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.amc_type_id and not self.pk:
            # snapshot the type's service-schedule config at sale time
            self.no_of_service = self.no_of_service or self.amc_type.no_of_service
            self.water_wash_count_free = self.water_wash_count_free or self.amc_type.water_wash_count_free
            self.service_interval = self.service_interval or self.amc_type.service_interval_days
            self.grace_days = self.grace_days or self.amc_type.grace_days
            self.vehicle_group = self.vehicle_group or self.amc_type.vehicle_type
        super().save(*args, **kwargs)

    def submit(self, user):
        VASStockLedger.get_or_create_for(amc_type=self.amc_type)
        with transaction.atomic():
            ledger = VASStockLedger.objects.select_for_update().get(amc_type=self.amc_type)
            if ledger.current_stock <= 0:
                raise ValueError(f"{self.amc_type} doesn't have stock.")
            super().submit(user)

    def amend(self):
        # amend() shallow-copies every field including `invoice` -- an amended draft must get
        # its own fresh auto-invoice on resubmit, not silently inherit the cancelled original's.
        new = super().amend()
        new.invoice = None
        new.save(update_fields=['invoice'])
        return new

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'AMC Packages'

    def __str__(self):
        return f"AMC-{self.pk} | {self.customer_vehicle} — {self.amc_type}"


class RSAPackage(DocStatusMixin, models.Model):
    class Status(models.TextChoices):
        ACTIVE    = 'active',    'Active'
        EXPIRED   = 'expired',   'Expired'
        CANCELLED = 'cancelled', 'Cancelled'

    customer_vehicle = models.ForeignKey(
        'customer_vehicles.CustomerVehicle',
        on_delete=models.PROTECT,
        related_name='rsa_packages'
    )
    rsa_type         = models.ForeignKey(RSAType, on_delete=models.PROTECT, related_name='packages', null=True, blank=True)
    sales_order      = models.ForeignKey('sales.VehicleSalesOrder', on_delete=models.SET_NULL, null=True, blank=True, related_name='rsa_packages')
    invoice          = models.ForeignKey('billing.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='rsa_packages')
    rsa_portal_no    = models.CharField(max_length=100, blank=True, verbose_name='RSA Portal No')
    start_date       = models.DateField(blank=True, null=True)
    end_date         = models.DateField(blank=True, null=True)
    amount           = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    gst_amount        = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    without_gst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    status           = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    created_at       = models.DateTimeField(auto_now_add=True)

    def submit(self, user):
        VASStockLedger.get_or_create_for(rsa_type=self.rsa_type)
        with transaction.atomic():
            ledger = VASStockLedger.objects.select_for_update().get(rsa_type=self.rsa_type)
            if ledger.current_stock <= 0:
                raise ValueError(f"{self.rsa_type} doesn't have stock.")
            super().submit(user)

    def amend(self):
        new = super().amend()
        new.invoice = None
        new.save(update_fields=['invoice'])
        return new

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'RSA Packages'

    def __str__(self):
        return f"RSA-{self.pk} | {self.customer_vehicle} — {self.rsa_type}"


class ProtectionPlusPackage(DocStatusMixin, models.Model):
    class Status(models.TextChoices):
        ACTIVE    = 'active',    'Active'
        EXPIRED   = 'expired',   'Expired'
        CANCELLED = 'cancelled', 'Cancelled'

    customer_vehicle = models.ForeignKey(
        'customer_vehicles.CustomerVehicle',
        on_delete=models.PROTECT,
        related_name='protection_plus_packages'
    )
    warranty_type    = models.ForeignKey(WarrantyType, on_delete=models.PROTECT, related_name='packages', null=True, blank=True)
    sales_order      = models.ForeignKey('sales.VehicleSalesOrder', on_delete=models.SET_NULL, null=True, blank=True, related_name='protection_plus_packages')
    invoice          = models.ForeignKey('billing.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='protection_plus_packages')
    start_date       = models.DateField(blank=True, null=True)
    end_date         = models.DateField(blank=True, null=True)
    amount           = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    gst_amount        = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    without_gst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    status           = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    created_at       = models.DateTimeField(auto_now_add=True)

    def submit(self, user):
        VASStockLedger.get_or_create_for(warranty_type=self.warranty_type)
        with transaction.atomic():
            ledger = VASStockLedger.objects.select_for_update().get(warranty_type=self.warranty_type)
            if ledger.current_stock <= 0:
                raise ValueError(f"{self.warranty_type} doesn't have stock.")
            super().submit(user)

    def amend(self):
        new = super().amend()
        new.invoice = None
        new.save(update_fields=['invoice'])
        return new

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Protection Plus Packages'

    def __str__(self):
        return f"PP-{self.pk} | {self.customer_vehicle} — {self.warranty_type}"


# ---------------------------------------------------------------------------
# Stock ledger -- shared across AMC/RSA/Warranty via a triple-nullable-FK
# discriminator (same precedent as spares.SparesIssueAlteration's dual-FK).
# Replaces the reference's 3 parallel "X Stock" doctypes + their "Add X Stock"
# Single-doctype purchase-entry screens (which have no real record identity of
# their own -- creating a VASStockMovement row IS the "add stock" action).
# ---------------------------------------------------------------------------

class VASStockLedger(models.Model):
    amc_type      = models.OneToOneField(AMCType, on_delete=models.CASCADE, null=True, blank=True, related_name='stock_ledger')
    rsa_type      = models.OneToOneField(RSAType, on_delete=models.CASCADE, null=True, blank=True, related_name='stock_ledger')
    warranty_type = models.OneToOneField(WarrantyType, on_delete=models.CASCADE, null=True, blank=True, related_name='stock_ledger')
    current_stock = models.IntegerField(default=0)
    created_at    = models.DateTimeField(auto_now_add=True)

    def clean(self):
        set_count = sum(bool(x) for x in [self.amc_type_id, self.rsa_type_id, self.warranty_type_id])
        if set_count != 1:
            raise ValidationError('Set exactly one of AMC Type / RSA Type / Warranty Type, not both or neither.')

    @property
    def plan_type(self):
        return self.amc_type or self.rsa_type or self.warranty_type

    def __str__(self):
        return f"VAS Stock — {self.plan_type} ({self.current_stock})"

    class Meta:
        verbose_name_plural = 'VAS Stock Ledgers'

    @classmethod
    def get_or_create_for(cls, *, amc_type=None, rsa_type=None, warranty_type=None):
        if amc_type is not None:
            ledger, _ = cls.objects.get_or_create(amc_type=amc_type)
        elif rsa_type is not None:
            ledger, _ = cls.objects.get_or_create(rsa_type=rsa_type)
        elif warranty_type is not None:
            ledger, _ = cls.objects.get_or_create(warranty_type=warranty_type)
        else:
            raise ValidationError('One of amc_type / rsa_type / warranty_type is required.')
        return ledger


class VASStockMovement(models.Model):
    class MovementType(models.TextChoices):
        PURCHASE   = 'purchase',   'Purchase'
        SALE       = 'sale',       'Sale'
        ADJUSTMENT = 'adjustment', 'Adjustment'

    ledger              = models.ForeignKey(VASStockLedger, on_delete=models.CASCADE, related_name='movements')
    date                = models.DateField()
    branch              = models.ForeignKey('accounts.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='vas_stock_movements')
    supplier            = models.ForeignKey('masters.Supplier', on_delete=models.SET_NULL, null=True, blank=True, related_name='vas_stock_movements')
    movement_type       = models.CharField(max_length=20, choices=MovementType.choices, default=MovementType.PURCHASE)
    quantity            = models.IntegerField(help_text='Positive for purchase/adjustment-in, negative for sale/adjustment-out')
    updated_quantity    = models.IntegerField(null=True, blank=True, help_text='Running balance after this movement')
    # Idempotency links -- ensure each source document posts at most one movement.
    source_invoice_item = models.OneToOneField('VASSupplierInvoiceItem', on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_movement')
    source_amc_package  = models.OneToOneField(AMCPackage, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_movement')
    source_rsa_package  = models.OneToOneField(RSAPackage, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_movement')
    source_pp_package   = models.OneToOneField(ProtectionPlusPackage, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_movement')
    created_at          = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            # F()-based atomic increment, not a plain-Python read-then-overwrite --
            # the previous code read self.ledger.current_stock in memory and wrote
            # it straight back, which loses concurrent updates under a race.
            VASStockLedger.objects.filter(pk=self.ledger_id).update(
                current_stock=F('current_stock') + self.quantity
            )
            new_stock = VASStockLedger.objects.filter(pk=self.ledger_id).values_list(
                'current_stock', flat=True
            ).first()
            VASStockMovement.objects.filter(pk=self.pk).update(updated_quantity=new_stock)
            self.updated_quantity = new_stock

    def __str__(self):
        return f"{self.ledger.plan_type} {self.get_movement_type_display()} {self.quantity:+d}"

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name_plural = 'VAS Stock Movements'


# ---------------------------------------------------------------------------
# RSA Creation -- RSA-only extra ordering step (reference-confirmed asymmetry:
# AMC and Warranty have no equivalent order-to-supplier document).
# ---------------------------------------------------------------------------

class RSACreation(DocStatusMixin, models.Model):
    rsa_type      = models.ForeignKey(RSAType, on_delete=models.PROTECT, related_name='rsa_creations')
    rsa_amount    = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    supplier      = models.ForeignKey('masters.Supplier', on_delete=models.PROTECT, related_name='rsa_creations')
    expected_date = models.DateField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"RSA-CRE-{self.pk} | {self.rsa_type} — {self.supplier}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'RSA Creations'


# ---------------------------------------------------------------------------
# Supplier invoices -- shared across AMC/RSA/Warranty (replaces the 3
# parallel "X Invoice" doctypes).
# ---------------------------------------------------------------------------

class VASSupplierInvoice(DocStatusMixin, models.Model):
    class PaymentType(models.TextChoices):
        ADJUSTMENT = 'adjustment', 'Adjustment'
        CASH       = 'cash',       'Cash'

    class PaymentStatus(models.TextChoices):
        UNPAID = 'unpaid', 'Unpaid'
        PAID   = 'paid',   'Paid'

    _amend_reset_number_field = 'invoice_number'

    invoice_number   = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    supplier         = models.ForeignKey('masters.Supplier', on_delete=models.PROTECT, related_name='vas_invoices')
    invoice_date     = models.DateField()
    branch           = models.ForeignKey('accounts.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='vas_invoices')
    payment_type     = models.CharField(max_length=20, choices=PaymentType.choices, blank=True)
    pay_mode         = models.CharField(max_length=100, blank=True)
    payment_status   = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    expected_date    = models.DateField(null=True, blank=True, help_text='RSA invoices only')
    cash_account     = models.CharField(max_length=200, blank=True, help_text='RSA invoices only')
    total_amount     = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    pending_amount   = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            with transaction.atomic():
                last = VASSupplierInvoice.objects.select_for_update().order_by('-id').values_list('invoice_number', flat=True).first()
                next_seq = 1
                if last:
                    try:
                        next_seq = int(last.rsplit('-', 1)[-1]) + 1
                    except ValueError:
                        pass
                self.invoice_number = f'VAS-INV-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_number

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'VAS Supplier Invoices'


class VASSupplierInvoiceItem(models.Model):
    invoice       = models.ForeignKey(VASSupplierInvoice, on_delete=models.CASCADE, related_name='items')
    amc_type      = models.ForeignKey(AMCType, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    rsa_type      = models.ForeignKey(RSAType, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    warranty_type = models.ForeignKey(WarrantyType, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    quantity      = models.IntegerField(default=1)
    hsn_code      = models.CharField(max_length=20, blank=True)
    rate          = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    amount        = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    def clean(self):
        set_count = sum(bool(x) for x in [self.amc_type_id, self.rsa_type_id, self.warranty_type_id])
        if set_count != 1:
            raise ValidationError('Set exactly one of AMC Type / RSA Type / Warranty Type per line, not both or neither.')

    @property
    def plan_type(self):
        return self.amc_type or self.rsa_type or self.warranty_type

    def __str__(self):
        return f"{self.plan_type} x {self.quantity}"

    class Meta:
        verbose_name_plural = 'VAS Supplier Invoice Items'


# ---------------------------------------------------------------------------
# Signals: submitting a supplier invoice posts a purchase movement per item;
# submitting a sale-side package posts a sale (decrement) movement.
# ---------------------------------------------------------------------------

@receiver(post_save, sender=VASSupplierInvoice)
def on_vas_supplier_invoice_submitted(sender, instance, **kwargs):
    if instance.docstatus != VASSupplierInvoice.DocStatus.SUBMITTED:
        return
    for item in instance.items.all():
        if hasattr(item, 'stock_movement'):
            continue
        ledger = VASStockLedger.get_or_create_for(
            amc_type=item.amc_type, rsa_type=item.rsa_type, warranty_type=item.warranty_type,
        )
        VASStockMovement.objects.create(
            ledger=ledger, date=instance.invoice_date, branch=instance.branch, supplier=instance.supplier,
            movement_type=VASStockMovement.MovementType.PURCHASE, quantity=item.quantity,
            source_invoice_item=item,
        )


@receiver(post_save, sender=AMCPackage)
def on_amc_submitted(sender, instance, **kwargs):
    if instance.docstatus != AMCPackage.DocStatus.SUBMITTED or hasattr(instance, 'stock_movement'):
        return
    ledger = VASStockLedger.get_or_create_for(amc_type=instance.amc_type)
    VASStockMovement.objects.create(
        ledger=ledger, date=timezone.now().date(), movement_type=VASStockMovement.MovementType.SALE,
        quantity=-1, source_amc_package=instance,
    )
    _create_vas_invoice(instance, 'AMC-INV')


@receiver(post_save, sender=RSAPackage)
def on_rsa_submitted(sender, instance, **kwargs):
    if instance.docstatus != RSAPackage.DocStatus.SUBMITTED or hasattr(instance, 'stock_movement'):
        return
    ledger = VASStockLedger.get_or_create_for(rsa_type=instance.rsa_type)
    VASStockMovement.objects.create(
        ledger=ledger, date=timezone.now().date(), movement_type=VASStockMovement.MovementType.SALE,
        quantity=-1, source_rsa_package=instance,
    )
    _create_vas_invoice(instance, 'RSA-INV')


@receiver(post_save, sender=ProtectionPlusPackage)
def on_pp_submitted(sender, instance, **kwargs):
    if instance.docstatus != ProtectionPlusPackage.DocStatus.SUBMITTED or hasattr(instance, 'stock_movement'):
        return
    ledger = VASStockLedger.get_or_create_for(warranty_type=instance.warranty_type)
    VASStockMovement.objects.create(
        ledger=ledger, date=timezone.now().date(), movement_type=VASStockMovement.MovementType.SALE,
        quantity=-1, source_pp_package=instance,
    )
    _create_vas_invoice(instance, 'PP-INV')


def _create_vas_invoice(instance, prefix):
    """Reference: AMC/RSA/Warranty's on_submit calls a server method
    (amc_sales_invoice/rsa_sales_invoice/warranty_sales_invoice) that auto-creates a Sales
    Invoice -- the method body is unreachable, but the package record already carries its own
    computed amount/gst_amount/without_gst_amount and an unpopulated `invoice` FK built for
    exactly this purpose (Phase 5). billing.Invoice.sales_order is required, so this only runs
    when the package has one -- a standalone/aftermarket package with no sales_order is skipped,
    not errored."""
    if instance.invoice_id or not instance.sales_order_id:
        return
    from billing.models import Invoice
    invoice = Invoice.objects.create(
        sales_order=instance.sales_order,
        invoice_number=f'{prefix}-{instance.pk}',
        subtotal=instance.without_gst_amount or 0,
        gst_amount=instance.gst_amount or 0,
        final_amount=instance.amount or 0,
        invoice_date=timezone.now().date(),
    )
    type(instance).objects.filter(pk=instance.pk).update(invoice=invoice)
    instance.invoice_id = invoice.pk
