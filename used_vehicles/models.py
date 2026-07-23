from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import DocStatusMixin


# ---------------------------------------------------------------------------
# Masters
# ---------------------------------------------------------------------------

class ManufacturingCompany(models.Model):
    """Reference: 'Manufacturing Company' master, linked from Add Used Vehicle."""
    name = models.CharField(max_length=200, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Manufacturing Companies'


class UsedVehicleSubGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Used Vehicle Sub Groups'


class UsedVehicleColor(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Used Vehicle Colors'


class UsedVehicleModel(models.Model):
    """Reference doctype: 'Add Used Vehicle' -- the used-bike model catalog
    (analogous to customers.BikeModel, but for pre-owned vehicles)."""
    class VehicleCategory(models.TextChoices):
        MOTORCYCLE = 'motorcycle', 'Motor Cycle'
        SCOOTER    = 'scooter',    'Scooter'
        MOPED      = 'moped',      'Moped'
        OTHER      = 'other',      'Other'

    disabled          = models.BooleanField(default=False)
    code              = models.CharField(max_length=50, unique=True, verbose_name='Used Vehicle Code')
    manufacturer      = models.ForeignKey(ManufacturingCompany, on_delete=models.PROTECT, related_name='used_vehicle_models')
    vehicle_category  = models.CharField(max_length=20, choices=VehicleCategory.choices, default=VehicleCategory.MOTORCYCLE)
    used_vehicle_name = models.CharField(max_length=200)
    model             = models.CharField(max_length=100, blank=True)
    sub_group         = models.ForeignKey(UsedVehicleSubGroup, on_delete=models.PROTECT, related_name='used_vehicle_models')
    created_at        = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} — {self.used_vehicle_name}"

    class Meta:
        ordering = ['used_vehicle_name']


class UsedVehicleRegisterNo(models.Model):
    """Reference: 'Used Vehicle Register No Master' -- per-unit pre-owned stock,
    analogous to customers.VehicleStock for new vehicles."""
    class StockStatus(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        RESERVED  = 'reserved',  'Reserved'
        SOLD      = 'sold',      'Sold'

    class WarehouseStatus(models.TextChoices):
        NOT_READY      = 'not_ready',      'Not Ready'
        MAINTENANCE    = 'maintenance',    'Maintenance'
        READY_FOR_SALE = 'ready_for_sale', 'Ready for Sale'

    class UnusedUsedStatus(models.TextChoices):
        UNUSED = 'unused', 'Unused'
        USED   = 'used',   'Used'

    class VehicleStatus(models.TextChoices):
        USED_VEHICLE     = 'used_vehicle',     'Used Vehicle'
        EXCHANGE_VEHICLE = 'exchange_vehicle', 'Exchange Vehicle'

    registration_no = models.CharField(max_length=50, unique=True)
    used_vehicle    = models.ForeignKey(UsedVehicleModel, on_delete=models.PROTECT, related_name='stock')
    color           = models.ForeignKey(UsedVehicleColor, on_delete=models.SET_NULL, null=True, blank=True)
    chassis_no      = models.CharField(max_length=100, blank=True)
    engine_no       = models.CharField(max_length=100, blank=True)
    branch          = models.ForeignKey('accounts.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='used_vehicle_stock')
    stock_status    = models.CharField(max_length=20, choices=StockStatus.choices, default=StockStatus.AVAILABLE, db_index=True)
    purchase_date   = models.DateField(null=True, blank=True)
    # Phase 8d — reference field-completeness. These are genuinely distinct
    # axes from stock_status (a sale-pipeline state), not renames of it: a
    # separate maintenance-readiness pipeline, a simple prior-use flag, and a
    # how-this-unit-entered-inventory flag.
    warehouse_status = models.CharField(max_length=20, choices=WarehouseStatus.choices, blank=True)
    status            = models.CharField(max_length=20, choices=UnusedUsedStatus.choices, blank=True, verbose_name='Unused/Used Status')
    vehicle_status     = models.CharField(max_length=20, choices=VehicleStatus.choices, blank=True)
    customer           = models.CharField(max_length=200, blank=True, help_text="Reference types this as free text (Data), not a Link -- preserved as-is")
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.registration_no} — {self.used_vehicle} ({self.stock_status})"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Used Vehicle Register Numbers'


# ---------------------------------------------------------------------------
# Purchase
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Phase 10 -- Purchase Order -> Purchase Receipt stage documents. Reference runs a 3-stage
# cycle (PO -> Receipt -> Invoice); Django previously only had the flat Invoice. Both new
# stages are DocStatusMixin, matching the reference's is_submittable=1 on both, and neither
# has a stock side effect of its own -- that still happens exclusively on Invoice submit,
# unchanged.
# ---------------------------------------------------------------------------

class UsedVehiclePurchaseOrder(DocStatusMixin, models.Model):
    _amend_reset_number_field = 'po_number'

    po_number      = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    supplier       = models.ForeignKey('masters.Supplier', on_delete=models.PROTECT, related_name='used_vehicle_purchase_orders')
    required_date  = models.DateField()
    branch         = models.ForeignKey('accounts.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='used_vehicle_purchase_orders')
    target_warehouse = models.CharField(max_length=200, blank=True,
                                         help_text="Reference types this as free text (Data) on the PO stage, unlike the real "
                                                    "Warehouse Link used later on Receipt/Invoice -- preserved as-is")
    total_quantity = models.IntegerField(default=0, blank=True)
    total_amount   = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    discount       = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True)
    grand_total    = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.po_number:
            with transaction.atomic():
                last = UsedVehiclePurchaseOrder.objects.select_for_update().order_by('-id').values_list('po_number', flat=True).first()
                next_seq = 1
                if last:
                    try:
                        next_seq = int(last.rsplit('-', 1)[-1]) + 1
                    except ValueError:
                        pass
                self.po_number = f'USED-VEH-PUR-ORD-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.po_number

    def cancel(self, user):
        # Phase-11 downstream-reference guard: don't let a PO be cancelled out from
        # under a Receipt/Invoice that's already submitted against it.
        submitted_receipt = self.receipts.filter(docstatus=UsedVehiclePurchaseReceipt.DocStatus.SUBMITTED).first()
        if submitted_receipt:
            raise ValueError(
                f"Cannot cancel: a submitted Purchase Receipt ({submitted_receipt}) already references this Purchase Order."
            )
        submitted_invoice = UsedVehiclePurchaseInvoice.objects.filter(
            purchase_receipt__purchase_order=self,
            docstatus=UsedVehiclePurchaseInvoice.DocStatus.SUBMITTED,
        ).first()
        if submitted_invoice:
            raise ValueError(
                f"Cannot cancel: a submitted Purchase Invoice ({submitted_invoice}) already references this Purchase Order."
            )
        super().cancel(user)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Used Vehicle Purchase Orders'


class UsedVehiclePurchaseOrderItem(models.Model):
    order           = models.ForeignKey(UsedVehiclePurchaseOrder, on_delete=models.CASCADE, related_name='purchase_items')
    item_code       = models.CharField(max_length=100, blank=True)
    register_number = models.CharField(max_length=50, blank=True)
    engine_number   = models.CharField(max_length=100, blank=True)
    chasis_number   = models.CharField(max_length=100, blank=True)
    color           = models.ForeignKey('UsedVehicleColor', on_delete=models.SET_NULL, null=True, blank=True)
    quantity        = models.DecimalField(max_digits=10, decimal_places=2, default=1, blank=True)
    uom             = models.CharField(max_length=20, default='Nos', blank=True)
    rate            = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    noc             = models.CharField(max_length=5, choices=[('', '—'), ('yes', 'Yes'), ('no', 'No')], blank=True, verbose_name='NOC')
    insurance       = models.CharField(max_length=5, choices=[('', '—'), ('yes', 'Yes'), ('no', 'No')], blank=True)
    to_received     = models.CharField(max_length=5, choices=[('', '—'), ('yes', 'Yes'), ('no', 'No')], blank=True, verbose_name='T.O. Received')
    model           = models.CharField(max_length=200, blank=True)
    rc_book_number  = models.CharField(max_length=100, blank=True)
    customer        = models.CharField(max_length=200, blank=True)
    sub_group       = models.ForeignKey('UsedVehicleSubGroup', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.item_code} — {self.chasis_number or '—'}"

    class Meta:
        verbose_name_plural = 'Used Vehicle Purchase Order Items'


class UsedVehiclePurchaseReceipt(DocStatusMixin, models.Model):
    _amend_reset_number_field = 'receipt_number'

    receipt_number = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    purchase_order  = models.ForeignKey(UsedVehiclePurchaseOrder, on_delete=models.PROTECT, related_name='receipts')
    supplier        = models.ForeignKey('masters.Supplier', on_delete=models.PROTECT, related_name='used_vehicle_purchase_receipts')
    branch          = models.ForeignKey('accounts.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='used_vehicle_purchase_receipts')
    required_date   = models.DateField()
    target_warehouse = models.ForeignKey('masters.Warehouse', on_delete=models.SET_NULL, null=True, blank=True, related_name='used_vehicle_purchase_receipts')
    total_quantity  = models.IntegerField(default=0, blank=True)
    total_amount    = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    discount        = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True)
    grand_total     = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    payment_bending_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            with transaction.atomic():
                last = UsedVehiclePurchaseReceipt.objects.select_for_update().order_by('-id').values_list('receipt_number', flat=True).first()
                next_seq = 1
                if last:
                    try:
                        next_seq = int(last.rsplit('-', 1)[-1]) + 1
                    except ValueError:
                        pass
                self.receipt_number = f'USED-VEH-REC-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.receipt_number

    def cancel(self, user):
        # Same class of downstream-reference guard as UsedVehiclePurchaseOrder.cancel().
        submitted_invoice = self.invoices.filter(docstatus=UsedVehiclePurchaseInvoice.DocStatus.SUBMITTED).first()
        if submitted_invoice:
            raise ValueError(
                f"Cannot cancel: a submitted Purchase Invoice ({submitted_invoice}) already references this Purchase Receipt."
            )
        super().cancel(user)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Used Vehicle Purchase Receipts'


class UsedVehiclePurchaseReceiptItem(models.Model):
    receipt         = models.ForeignKey(UsedVehiclePurchaseReceipt, on_delete=models.CASCADE, related_name='purchase_items')
    item_code       = models.CharField(max_length=100, blank=True)
    register_number = models.CharField(max_length=50, blank=True)
    engine_number   = models.CharField(max_length=100, blank=True)
    chasis_number   = models.CharField(max_length=100, blank=True)
    color           = models.CharField(max_length=50, blank=True,
                                        help_text='Reference types this row\'s color as free text (Data) here, unlike the PO row\'s real Link -- confirmed live, preserved as-is')
    quantity        = models.DecimalField(max_digits=10, decimal_places=2, default=1, blank=True)
    uom             = models.CharField(max_length=20, default='Nos', blank=True)
    rate            = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    rc_book_number  = models.CharField(max_length=100, blank=True)
    to_received     = models.CharField(max_length=5, choices=[('', '—'), ('yes', 'Yes'), ('no', 'No')], blank=True, verbose_name='T.O. Received')
    noc             = models.CharField(max_length=5, choices=[('', '—'), ('yes', 'Yes'), ('no', 'No')], blank=True, verbose_name='NOC')
    insurance       = models.CharField(max_length=5, choices=[('', '—'), ('yes', 'Yes'), ('no', 'No')], blank=True)
    model           = models.CharField(max_length=200, blank=True)
    customer        = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.item_code} — {self.chasis_number or '—'}"

    class Meta:
        verbose_name_plural = 'Used Vehicle Purchase Receipt Items'


class UsedVehiclePurchaseInvoice(DocStatusMixin, models.Model):
    class PaymentType(models.TextChoices):
        ADJUSTMENT = 'adjustment', 'Adjustment'
        CASH       = 'cash',       'Cash'

    class PaymentStatus(models.TextChoices):
        UNPAID = 'unpaid', 'Unpaid'
        PAID   = 'paid',   'Paid'

    _amend_reset_number_field = 'invoice_number'

    own_purchase      = models.BooleanField(default=False)
    supplier_purchase = models.BooleanField(default=True)
    invoice_number    = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    supplier          = models.ForeignKey('masters.Supplier', on_delete=models.SET_NULL, null=True, blank=True, related_name='used_vehicle_purchases')
    purchase_receipt  = models.ForeignKey(UsedVehiclePurchaseReceipt, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices',
                                           help_text='Optional -- own-purchase trade-ins (no PO/Receipt stage) continue to work with this left blank')
    required_date     = models.DateField(null=True, blank=True)
    branch            = models.ForeignKey('accounts.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='used_vehicle_purchases')
    payment_type      = models.CharField(max_length=20, choices=PaymentType.choices, blank=True)
    invoice_no        = models.CharField(max_length=100, blank=True, verbose_name='Invoice No',
                                          help_text="Mandatory in the reference spec (06_Used_Vehicle_Purchase.md) -- the supplier's "
                                                     "own invoice number, distinct from this record's auto-generated invoice_number. "
                                                     "Left blank=True here for additive-migration safety; enforced required in the form.")
    cash_account      = models.CharField(max_length=100, blank=True,
                                          help_text='No Chart of Accounts model exists in Django -- free text, matching the '
                                                     'from_account/to_account free-text fallback convention used elsewhere '
                                                     '(e.g. UsedVehicleInsuranceUpdate)')
    invoice_date      = models.DateField()
    customer_name     = models.CharField(max_length=200, blank=True, help_text='For own-purchase (trade-in from a customer, not a supplier)')
    phone_number      = models.CharField(max_length=20, blank=True)
    address           = models.TextField(blank=True)
    target_warehouse  = models.ForeignKey('masters.Warehouse', on_delete=models.SET_NULL, null=True, blank=True, related_name='used_vehicle_purchases')
    vehicle_status    = models.CharField(max_length=50, default='Not Ready')
    total_quantity    = models.IntegerField(default=0, blank=True)
    total_amount      = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    discount          = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    grand_total       = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    pending_amount    = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    payment_status    = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    created_at        = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            with transaction.atomic():
                last = UsedVehiclePurchaseInvoice.objects.select_for_update().order_by('-id').values_list('invoice_number', flat=True).first()
                next_seq = 1
                if last:
                    try:
                        next_seq = int(last.rsplit('-', 1)[-1]) + 1
                    except ValueError:
                        pass
                self.invoice_number = f'USED-PUR-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_number

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Used Vehicle Purchase Invoices'


class UsedVehiclePurchaseItem(models.Model):
    invoice         = models.ForeignKey(UsedVehiclePurchaseInvoice, on_delete=models.CASCADE, related_name='items')
    used_vehicle    = models.ForeignKey(UsedVehicleModel, on_delete=models.PROTECT)
    registration_no = models.CharField(max_length=50, blank=True, help_text='Assigned registration number for this unit')
    chassis_no      = models.CharField(max_length=100, blank=True)
    engine_no       = models.CharField(max_length=100, blank=True)
    color           = models.ForeignKey(UsedVehicleColor, on_delete=models.SET_NULL, null=True, blank=True)
    quantity        = models.DecimalField(max_digits=10, decimal_places=2, default=1, blank=True)
    rate            = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    amount          = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    def __str__(self):
        return f"{self.used_vehicle} — {self.registration_no or '—'}"

    class Meta:
        verbose_name_plural = 'Used Vehicle Purchase Items'


# ---------------------------------------------------------------------------
# Sale
# ---------------------------------------------------------------------------

class UsedVehicleSale(DocStatusMixin, models.Model):
    class FinanceClosing(models.TextChoices):
        YES = 'yes', 'Yes'
        NO  = 'no',  'No'

    class SaleStatus(models.TextChoices):
        BOOKED    = 'booked',    'Booked'
        INVOICED  = 'invoiced',  'Invoiced'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'

    _amend_reset_number_field = 'sale_number'

    sale_number           = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    customer              = models.ForeignKey('customers.Customer', on_delete=models.PROTECT, related_name='used_vehicle_sales')
    sales_executive       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='used_vehicle_sales_handled')
    vehicle_number         = models.ForeignKey(UsedVehicleRegisterNo, on_delete=models.PROTECT, related_name='sales')
    branch                = models.ForeignKey('accounts.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='used_vehicle_sales')
    phone_number          = models.CharField(max_length=20, blank=True)
    gst_category          = models.CharField(max_length=30, blank=True)
    delivery_date         = models.DateField()
    vehicle_value         = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    sale_amount           = models.DecimalField(max_digits=12, decimal_places=2)
    vehicle_amount        = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    has_exchange          = models.BooleanField(default=False, verbose_name='Has Exchange')
    finance_closing       = models.CharField(max_length=5, choices=FinanceClosing.choices, blank=True)
    exchange_amount       = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    items_qty             = models.IntegerField(default=0, blank=True)
    total                 = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    tax_amount            = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    base_rate             = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    additional_discount   = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    advance_payment       = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    balance_amount        = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    sale_status           = models.CharField(max_length=20, choices=SaleStatus.choices, default=SaleStatus.BOOKED, db_index=True)
    created_at            = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.sale_number:
            with transaction.atomic():
                last = UsedVehicleSale.objects.select_for_update().order_by('-id').values_list('sale_number', flat=True).first()
                next_seq = 1
                if last:
                    try:
                        next_seq = int(last.rsplit('-', 1)[-1]) + 1
                    except ValueError:
                        pass
                self.sale_number = f'USED-SALE-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sale_number} | {self.customer} — {self.vehicle_number}"

    def submit(self, user):
        # Phase-11 stock-safety guard: the same physical vehicle must never be
        # claimed by two different submitted Sales. A Sale can only be submitted
        # while its vehicle is still Available; submitting it immediately reserves
        # the vehicle (distinct from fully Sold, which only happens at Delivery
        # submit -- see on_used_vehicle_delivered below), matching the existing
        # convention of a stock guard raised as ValueError (vas.AMCPackage.submit()).
        with transaction.atomic():
            reg = UsedVehicleRegisterNo.objects.select_for_update().get(pk=self.vehicle_number_id)
            if reg.stock_status != UsedVehicleRegisterNo.StockStatus.AVAILABLE:
                raise ValueError(
                    f"{reg.registration_no} is not available for sale "
                    f"(current status: {reg.get_stock_status_display()})."
                )
            super().submit(user)
            reg.stock_status = UsedVehicleRegisterNo.StockStatus.RESERVED
            reg.save(update_fields=['stock_status'])

    def cancel(self, user):
        # Guard: block cancelling a Sale that already has a submitted Delivery
        # against it (Phase-11 downstream-reference guard, same class of bug as
        # UsedVehiclePurchaseOrder.cancel() below).
        if hasattr(self, 'delivery') and self.delivery.docstatus == UsedVehicleDelivery.DocStatus.SUBMITTED:
            raise ValueError(
                f"Cannot cancel: a submitted Delivery ({self.delivery}) already references this Sale."
            )
        with transaction.atomic():
            super().cancel(user)
            # sale_status was left stale on cancel before this fix -- reflect the
            # cancellation instead of leaving whatever booked/invoiced/delivered
            # value it last had.
            self.sale_status = self.SaleStatus.CANCELLED
            self.save(update_fields=['sale_status'])
            # Release the vehicle back to Available if this sale had reserved it
            # (a cancelled Sale should never leave stock stuck as Reserved).
            reg = self.vehicle_number
            if reg.stock_status == UsedVehicleRegisterNo.StockStatus.RESERVED:
                reg.stock_status = UsedVehicleRegisterNo.StockStatus.AVAILABLE
                reg.save(update_fields=['stock_status'])

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Used Vehicle Sales'


class UsedVehicleFitting(models.Model):
    sale        = models.ForeignKey(UsedVehicleSale, on_delete=models.CASCADE, related_name='fittings')
    item_code   = models.CharField(max_length=100, blank=True)
    item_name   = models.CharField(max_length=200)
    quantity    = models.DecimalField(max_digits=10, decimal_places=2, default=1, blank=True)
    rate        = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    amount      = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item_name} — Rs.{self.amount}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Used Vehicle Fittings'


class UsedVehicleSaleItem(models.Model):
    sale        = models.ForeignKey(UsedVehicleSale, on_delete=models.CASCADE, related_name='items')
    item_name   = models.CharField(max_length=200)
    rate        = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    quantity    = models.DecimalField(max_digits=10, decimal_places=2, default=1, blank=True)
    amount      = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item_name} — Rs.{self.amount}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Used Vehicle Sale Items'


class UsedVehicleAdvancePayment(models.Model):
    sale             = models.ForeignKey(UsedVehicleSale, on_delete=models.CASCADE, related_name='advance_payments')
    mode_of_payment  = models.CharField(max_length=100, blank=True)
    date             = models.DateField()
    amount           = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    to_account       = models.CharField(max_length=200, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.mode_of_payment} — Rs.{self.amount}"

    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'Used Vehicle Advance Payments'


class UsedVehicleFinanceLoan(models.Model):
    """Mirrors billing.FinanceLoan (Phase 1) -- reference: Used Vehicle Sales
    Finance + Used Vehicle Sales Finance Entry, collapsed into one model with
    the same HP-workflow fields already established."""
    class LoanStatus(models.TextChoices):
        ACTIVE   = 'active',   'Active'
        CLOSED   = 'closed',   'Closed'
        REJECTED = 'rejected', 'Rejected'

    HP_STATUS_CHOICES = [
        ('not_applicable', 'Not Applicable'),
        ('pending',         'Pending'),
        ('submitted',       'Submitted'),
        ('endorsed',        'Endorsed'),
        ('released',        'Released'),
    ]

    sale              = models.OneToOneField(UsedVehicleSale, on_delete=models.PROTECT, related_name='loan')
    bank_name         = models.CharField(max_length=100)
    loan_amount       = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate     = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    tenure_months     = models.IntegerField(null=True, blank=True)
    emi_amount        = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    loan_status       = models.CharField(max_length=20, choices=LoanStatus.choices, default=LoanStatus.ACTIVE)
    sanctioned_date   = models.DateField(null=True, blank=True)
    first_emi_date    = models.DateField(null=True, blank=True)
    hp_status         = models.CharField(max_length=20, choices=HP_STATUS_CHOICES, default='not_applicable')
    hp_bank_name      = models.CharField(max_length=200, blank=True)
    hp_submission_date  = models.DateField(null=True, blank=True)
    hp_endorsement_date = models.DateField(null=True, blank=True)
    hp_release_date     = models.DateField(null=True, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Loan for {self.sale} — {self.bank_name}"

    class Meta:
        verbose_name_plural = 'Used Vehicle Finance Loans'


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------

class UsedVehicleDelivery(DocStatusMixin, models.Model):
    class PaymentStatus(models.TextChoices):
        UNPAID    = 'unpaid',    'Unpaid'
        COMPLETED = 'completed', 'Completed'

    sale                        = models.OneToOneField(UsedVehicleSale, on_delete=models.PROTECT, related_name='delivery')
    delivery_date               = models.DateField()
    delivered_by                = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    remarks                     = models.TextField(blank=True)
    checklist_rc_book           = models.BooleanField(default=False)
    checklist_warranty          = models.BooleanField(default=False)
    checklist_toolkit           = models.BooleanField(default=False)
    checklist_accessories       = models.BooleanField(default=False)
    issue_gate_pass             = models.BooleanField(default=False)
    manager_approval_requested  = models.BooleanField(default=False)
    manager_approved            = models.BooleanField(default=False)
    finance_approved            = models.BooleanField(default=False)
    total_amount                = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    payment_status              = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    created_at                  = models.DateTimeField(auto_now_add=True)

    # Phase 10 -- warehouse/gst/exchange snapshot, petrol offer, totals cluster
    # (round-3 sweep: reference's Used Vehicle Delivery has all of these, none existed here)
    warehouse            = models.ForeignKey('masters.Warehouse', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    gst_category          = models.CharField(max_length=30, blank=True)
    has_exchange           = models.BooleanField(default=False)
    finance_closing        = models.CharField(max_length=5, choices=[('no', 'No'), ('yes', 'Yes')], blank=True)
    exchange_amount        = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    offer_petrol            = models.BooleanField(default=False)
    petrol_type             = models.CharField(max_length=10, choices=[('litre', 'Litre'), ('amount', 'Amount')], blank=True)
    petrol_litre             = models.IntegerField(null=True, blank=True)
    petrol_amount            = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    item_qty                = models.IntegerField(default=0, blank=True)
    finance_amount           = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    delivery_discount        = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    base_rate                = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    additional_discount      = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    advance_payment          = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    balance_amount           = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)

    def __str__(self):
        return f"Delivery for {self.sale}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Used Vehicle Deliveries'


class UsedVehicleDeliveryItem(models.Model):
    delivery          = models.ForeignKey(UsedVehicleDelivery, on_delete=models.CASCADE, related_name='delivery_items')
    item_code         = models.CharField(max_length=100, blank=True)
    warranty_rsa_amc  = models.CharField(max_length=50, blank=True,
                                          help_text='Reference uses a Dynamic Link here; no generic Django equivalent -- free text instead')
    rate              = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    def __str__(self):
        return f"{self.item_code} — Rs.{self.rate}"

    class Meta:
        verbose_name_plural = 'Used Vehicle Delivery Items'


class UsedVehicleDeliveryAdvancePayment(models.Model):
    delivery         = models.ForeignKey(UsedVehicleDelivery, on_delete=models.CASCADE, related_name='advance_payments')
    mode_of_payment  = models.CharField(max_length=100, blank=True)
    date             = models.DateField()
    amount           = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    to_account       = models.CharField(max_length=200, blank=True)
    draft_type       = models.CharField(max_length=100, blank=True,
                                         help_text='Reference links to Bank Draft Type Master; no Django equivalent -- free text instead')

    def __str__(self):
        return f"{self.mode_of_payment} — Rs.{self.amount}"

    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'Used Vehicle Delivery Advance Payments'


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------

class UsedVehicleInvoice(DocStatusMixin, models.Model):
    class PaymentType(models.TextChoices):
        CASH = 'cash', 'Cash'
        BANK = 'bank', 'Bank'

    class Status(models.TextChoices):
        UNPAID = 'unpaid', 'Unpaid'
        PAID   = 'paid',   'Paid'

    _amend_reset_number_field = 'invoice_number'

    sale                  = models.ForeignKey(UsedVehicleSale, on_delete=models.PROTECT, related_name='invoices')
    invoice_number        = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    subtotal              = models.DecimalField(max_digits=12, decimal_places=2)
    gst_amount            = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    gst_category          = models.CharField(max_length=30, blank=True)
    discount_amount       = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    final_amount          = models.DecimalField(max_digits=12, decimal_places=2, blank=True)
    invoice_date          = models.DateField()
    payment_type          = models.CharField(max_length=10, choices=PaymentType.choices, blank=True)
    payment_due_date      = models.DateField(null=True, blank=True)
    md_approval_requested = models.BooleanField(default=False)
    md_approved           = models.BooleanField(default=False)
    md_approved_by        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    md_approved_at        = models.DateTimeField(null=True, blank=True)
    status                = models.CharField(max_length=10, choices=Status.choices, default=Status.UNPAID)
    created_at            = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            with transaction.atomic():
                last = UsedVehicleInvoice.objects.select_for_update().order_by('-id').values_list('invoice_number', flat=True).first()
                next_seq = 1
                if last:
                    try:
                        next_seq = int(last.rsplit('-', 1)[-1]) + 1
                    except ValueError:
                        pass
                self.invoice_number = f'USED-INV-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def recompute_totals(self):
        """Re-derive gst_amount/final_amount from subtotal via billing.split_gst()
        so interstate customers get IGST instead of the flat-rate CGST/SGST
        split UsedVehicleInvoiceForm.clean() used to apply (same bug shape
        billing.Invoice had before e79e25f). subtotal is a directly-entered
        form field here, not summed from items -- UsedVehicleInvoiceItem rows
        have no per-item GST fields of their own, so there's nothing to
        re-derive it from. gst_amount stays a single collapsed field; the
        cgst/sgst/igst split is computed but summed back into it rather than
        stored separately, matching this model's existing schema."""
        from decimal import Decimal
        from accounts.models import CompanySettings
        from billing.models import split_gst

        if self.subtotal > Decimal('0'):
            company_settings = CompanySettings.get_instance()
            gst_rate = (company_settings.cgst_rate or Decimal('0')) + (company_settings.sgst_rate or Decimal('0'))
            gst_total = (self.subtotal * gst_rate / Decimal('100')).quantize(Decimal('0.01'))
        else:
            gst_total = Decimal('0')
        cgst, sgst, igst = split_gst(gst_total, customer=self.sale.customer)
        self.gst_amount = cgst + sgst + igst
        self.final_amount = self.subtotal + self.gst_amount - (self.discount_amount or Decimal('0'))
        self.save(update_fields=['gst_amount', 'final_amount'])

    def __str__(self):
        return self.invoice_number

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Used Vehicle Invoices'


class UsedVehicleInvoiceItem(models.Model):
    invoice   = models.ForeignKey(UsedVehicleInvoice, on_delete=models.CASCADE, related_name='items')
    item_code = models.CharField(max_length=100, blank=True)
    rate      = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    discount  = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    total     = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item_code} — Rs.{self.total}"

    class Meta:
        ordering = ['-created_at']


# ---------------------------------------------------------------------------
# RC handover / issue
# ---------------------------------------------------------------------------

class UsedVehicleRCHandOver(DocStatusMixin, models.Model):
    """Reference: 'Used Vehicle RC Hand Over' -- tracks the original RC book
    handover from the trade-in/previous owner side of the sale.

    Round-4 sweep: reference declares this is_submittable=1 (Draft/Submitted/
    Cancelled + amended_from), matching the DocStatusMixin pattern already used
    by the sibling Purchase Order/Receipt/Invoice/Sale/Delivery/Invoice docs in
    this same file. `status` is kept unchanged as an independent sub-state field
    (Pending/Handed Over describing the physical handover, same relationship as
    UsedVehicleInvoice.status tracking payment independently of docstatus) --
    docstatus is the new document lifecycle, not a replacement for it. No
    _amend_reset_number_field: this doc has no auto-numbered field."""
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        HANDED_OVER = 'handed_over', 'Handed Over'

    YES_NO_CHOICES = [('', '—'), ('yes', 'Yes'), ('no', 'No')]

    sale        = models.ForeignKey(UsedVehicleSale, on_delete=models.CASCADE, related_name='rc_hand_overs')
    rc_number   = models.CharField(max_length=100, blank=True, help_text='Also serves as the reference\'s "RC Book Number" field')
    handover_date = models.DateField(null=True, blank=True)
    handed_over_by = models.CharField(max_length=200, blank=True)
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes       = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    # Phase 10 -- reference tracks these as 4 independent Yes/No checklist items rather than
    # one collapsed status enum; added purely additively, `status` above is kept unchanged.
    rc_book_received = models.CharField(max_length=5, choices=YES_NO_CHOICES, blank=True)
    noc               = models.CharField(max_length=5, choices=YES_NO_CHOICES, blank=True, verbose_name='NOC')
    vehicle_received  = models.CharField(max_length=5, choices=YES_NO_CHOICES, blank=True)
    to_received       = models.CharField(max_length=5, choices=YES_NO_CHOICES, blank=True, verbose_name='T.O. Received')

    def __str__(self):
        return f"RC Hand Over for {self.sale}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Used Vehicle RC Hand Overs'


class UsedVechileRCBookIssue(DocStatusMixin, models.Model):
    """Reference: 'Used Vechile RC Book Issue' (sic, reference's own spelling) --
    tracks issuing the NEW RC book to the buyer after RTO transfer.

    Round-4 sweep: same DocStatusMixin restructure as UsedVehicleRCHandOver above --
    see that model's docstring for the status-vs-docstatus rationale."""
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ISSUED  = 'issued',  'Issued'

    sale        = models.ForeignKey(UsedVehicleSale, on_delete=models.CASCADE, related_name='rc_book_issues')
    rc_number   = models.CharField(max_length=100, blank=True)
    issue_date  = models.DateField(null=True, blank=True)
    issued_to   = models.CharField(max_length=200, blank=True)
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes       = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"RC Book Issue for {self.sale}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Used Vehicle RC Book Issues'


# ---------------------------------------------------------------------------
# Phase 3b — Used Vehicle Job Card service pipeline (mirrors service.JobCard +
# stage documents from Phase 2, minus the Water Wash stage which the
# reference doesn't have for used vehicles).
# ---------------------------------------------------------------------------

class UsedVehicleJobCard(DocStatusMixin, models.Model):
    class ServiceStatus(models.TextChoices):
        PENDING          = 'pending',          'Pending'
        IN_BAY           = 'in_bay',           'In Bay'
        IN_PROGRESS      = 'in_progress',      'In Progress'
        OUTWORK          = 'outwork',          'Outwork'
        FINAL_INSPECTION = 'final_inspection', 'Final Inspection'
        READY            = 'ready',            'Ready'
        INVOICED         = 'invoiced',         'Invoiced'

    register_no          = models.ForeignKey(UsedVehicleRegisterNo, on_delete=models.PROTECT, related_name='job_cards')
    service_advisor      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='used_vehicle_job_cards_as_advisor')
    km                   = models.IntegerField(default=0, blank=True)
    customer_name        = models.CharField(max_length=200, blank=True)
    phone_no             = models.CharField(max_length=20, blank=True)
    email                = models.EmailField(blank=True)
    address              = models.TextField(blank=True)
    super_visor          = models.CharField(max_length=200, blank=True, verbose_name='Supervisor')
    service_status       = models.CharField(max_length=30, choices=ServiceStatus.choices, default=ServiceStatus.PENDING, db_index=True)
    created_at           = models.DateTimeField(auto_now_add=True)

    # Phase 10 -- header fields confirmed live on the reference, missing here entirely
    date                 = models.DateField(null=True, blank=True)
    frame_no             = models.CharField(max_length=100, blank=True)
    model                = models.CharField(max_length=200, blank=True)
    vehicle_name         = models.CharField(max_length=200, blank=True)
    service              = models.CharField(max_length=200, blank=True)
    engine_no            = models.CharField(max_length=100, blank=True)
    colour               = models.ForeignKey(UsedVehicleColor, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    total_estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    opening_time         = models.TimeField(null=True, blank=True)
    in_time              = models.TimeField(null=True, blank=True)
    closing_time         = models.TimeField(null=True, blank=True)
    e_cost               = models.CharField(max_length=50, blank=True, verbose_name='Estimation Cost',
                                             help_text="Reference types this as free text (Data), not a rate -- preserved as-is")
    p_date               = models.DateField(null=True, blank=True)
    p_time                = models.TimeField(null=True, blank=True)

    def __str__(self):
        return f"UJC-{self.pk} | {self.register_no} — {self.service_status}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Used Vehicle Job Cards'


def _advance_used_vehicle_job_card_status(job_card, new_status):
    if job_card.service_status != new_status:
        job_card.service_status = new_status
        job_card.save(update_fields=['service_status'])


class UsedVehicleBayIn(DocStatusMixin, models.Model):
    job_card     = models.ForeignKey(UsedVehicleJobCard, on_delete=models.PROTECT, related_name='bay_in_entries')
    mechanic     = models.ForeignKey('masters.Supplier', on_delete=models.SET_NULL, null=True, blank=True, related_name='used_vehicle_bay_in_entries')
    vehicle_name = models.CharField(max_length=200, blank=True)
    register_no  = models.CharField(max_length=50, blank=True)
    date         = models.DateTimeField()
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"UBAYIN-{self.pk} | JC-{self.job_card_id}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Used Vehicle Bay In'
        verbose_name_plural = 'Used Vehicle Bay Ins'


class UsedVehicleBayOut(DocStatusMixin, models.Model):
    job_card       = models.ForeignKey(UsedVehicleJobCard, on_delete=models.PROTECT, related_name='bay_out_entries')
    mechanic       = models.ForeignKey('masters.Supplier', on_delete=models.SET_NULL, null=True, blank=True, related_name='used_vehicle_bay_out_entries')
    vehicle_name   = models.CharField(max_length=200, blank=True)
    vehicle_number = models.CharField(max_length=50, blank=True)
    remarks        = models.TextField()
    date           = models.DateField()
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"UBAYOUT-{self.pk} | JC-{self.job_card_id}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Used Vehicle Bay Out'
        verbose_name_plural = 'Used Vehicle Bay Outs'


class UsedVehicleFinalInspection(DocStatusMixin, models.Model):
    job_card                 = models.ForeignKey(UsedVehicleJobCard, on_delete=models.PROTECT, related_name='final_inspections')
    rework                   = models.BooleanField(default=False)
    vehicle_name             = models.CharField(max_length=200, blank=True)
    chasis_number            = models.CharField(max_length=100, blank=True)
    mechanic_name            = models.CharField(max_length=200, blank=True)
    register_number          = models.CharField(max_length=50, blank=True)
    final_inspection_remarks = models.TextField()
    created_at               = models.DateTimeField(auto_now_add=True)

    # Phase 10 -- reference is a full rollup with its own complaints/supervisor/labor-charge/
    # spares-issue child tables plus outwork remarks; none of that existed here before.
    out_work_charge_form = models.CharField(max_length=100, blank=True)
    out_work_remarks     = models.CharField(max_length=255, blank=True, verbose_name='Bay Out Remarks',
                                             help_text="Reference types this as free text (Data) despite the name -- preserved as-is")

    def __str__(self):
        return f"UFI-{self.pk} | JC-{self.job_card_id}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Used Vehicle Final Inspections'


class UsedVehicleFinalInspectionLaborCharge(models.Model):
    final_inspection = models.ForeignKey(UsedVehicleFinalInspection, on_delete=models.CASCADE, related_name='labor_charges')
    date             = models.DateField(null=True, blank=True)
    labor_work       = models.ForeignKey('masters.LabourWork', on_delete=models.SET_NULL, null=True, blank=True)
    quantity         = models.IntegerField(default=0, blank=True)
    amount           = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    sgst             = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    cgst             = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    total            = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    def __str__(self):
        return f"{self.labor_work} — Rs.{self.total}"

    class Meta:
        verbose_name_plural = 'Used Vehicle Final Inspection Labor Charges'


class UsedVehicleFinalInspectionSpareItem(models.Model):
    final_inspection = models.ForeignKey(UsedVehicleFinalInspection, on_delete=models.CASCADE, related_name='spares_lists')
    item             = models.ForeignKey('spares.SparesItem', on_delete=models.SET_NULL, null=True, blank=True)
    item_name        = models.CharField(max_length=200, blank=True)
    qty              = models.IntegerField(default=1, blank=True)
    rate             = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    amount           = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    def save(self, *args, **kwargs):
        if self.item_id and not self.item_name:
            self.item_name = self.item.item_name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_name} — Rs.{self.amount}"

    class Meta:
        verbose_name_plural = 'Used Vehicle Final Inspection Spare Items'


class UsedVehicleOutworkEntryIssue(DocStatusMixin, models.Model):
    class GatePass(models.TextChoices):
        YES = 'yes', 'Yes'
        NO  = 'no',  'No'

    job_card    = models.ForeignKey(UsedVehicleJobCard, on_delete=models.PROTECT, related_name='outwork_issues')
    vendor_name = models.ForeignKey('masters.Supplier', on_delete=models.PROTECT, related_name='used_vehicle_outwork_issues')
    godown      = models.ForeignKey('masters.Warehouse', on_delete=models.SET_NULL, null=True, blank=True, related_name='used_vehicle_outwork_issues')
    gate_pass   = models.CharField(max_length=5, choices=GatePass.choices, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"UOWI-{self.pk} | JC-{self.job_card_id} — {self.vendor_name}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Used Vehicle Outwork Entry Issues'

    @property
    def total_amount(self):
        from django.db.models import Sum
        from decimal import Decimal
        return self.work_details.aggregate(t=Sum('total_amount'))['t'] or Decimal('0.00')


class UsedVehicleOutworkWorkDetail(models.Model):
    outwork_issue = models.ForeignKey(UsedVehicleOutworkEntryIssue, on_delete=models.CASCADE, related_name='work_details')
    work_name     = models.CharField(max_length=200, blank=True)
    quantity      = models.DecimalField(max_digits=10, decimal_places=2, default=1, blank=True)
    amount        = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    total_amount  = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    def __str__(self):
        return f"{self.work_name} — Rs.{self.total_amount}"

    class Meta:
        verbose_name_plural = 'Used Vehicle Outwork Work Details'


class UsedVehicleOutworkSpareItem(models.Model):
    outwork_issue = models.ForeignKey(UsedVehicleOutworkEntryIssue, on_delete=models.CASCADE, related_name='outwork_spares')
    item          = models.ForeignKey('spares.SparesItem', on_delete=models.PROTECT)
    quantity      = models.DecimalField(max_digits=10, decimal_places=3, default=1, blank=True)
    rate          = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    total         = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    def __str__(self):
        return f"{self.item} x {self.quantity}"

    class Meta:
        verbose_name_plural = 'Used Vehicle Outwork Spare Items'


class UsedVehicleOutworkEntryReturn(DocStatusMixin, models.Model):
    class PaymentType(models.TextChoices):
        ADJUSTMENT = 'adjustment', 'Adjustment'
        CASH       = 'cash',       'Cash'

    outwork_issue  = models.ForeignKey(UsedVehicleOutworkEntryIssue, on_delete=models.PROTECT, related_name='returns')
    job_card       = models.ForeignKey(UsedVehicleJobCard, on_delete=models.PROTECT, related_name='outwork_returns')
    rework         = models.BooleanField(default=False)
    payment_type   = models.CharField(max_length=20, choices=PaymentType.choices, blank=True)
    supplier       = models.ForeignKey('masters.Supplier', on_delete=models.SET_NULL, null=True, blank=True, related_name='used_vehicle_outwork_returns')
    actual_amount  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    billing_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pending_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    # Phase 10 -- same class of total-computation gap Phase 9a fixed on the new-vehicle side,
    # but this doctype's confirmed live field set is genuinely simpler (no issue_spares_amount).
    invoice_no       = models.CharField(max_length=50, blank=True)
    total            = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    discount         = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, validators=[MinValueValidator(0)])
    updated_total    = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    payment_status   = models.CharField(max_length=30, blank=True,
                                         help_text="Reference types this as free text (Data), not a Select -- preserved as-is")

    def save(self, *args, **kwargs):
        self.total = (self.actual_amount or 0) + (self.billing_amount or 0)
        self.updated_total = self.total - (self.discount or 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"UOWR-{self.pk} | JC-{self.job_card_id}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Used Vehicle Outwork Entry Returns'


class UsedVehicleOutworkReturnDetail(models.Model):
    outwork_return = models.ForeignKey(UsedVehicleOutworkEntryReturn, on_delete=models.CASCADE, related_name='bill_details')
    work_name      = models.CharField(max_length=200, blank=True)
    quantity       = models.DecimalField(max_digits=10, decimal_places=2, default=1, blank=True)
    amount         = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    def __str__(self):
        return f"{self.work_name} — Rs.{self.amount}"

    class Meta:
        verbose_name_plural = 'Used Vehicle Outwork Return Details'


class UsedVehicleLaborCharge(DocStatusMixin, models.Model):
    job_card     = models.ForeignKey(UsedVehicleJobCard, on_delete=models.PROTECT, related_name='labor_charges')
    labour_name  = models.ForeignKey('masters.Supplier', on_delete=models.SET_NULL, null=True, blank=True, related_name='used_vehicle_labor_charges', verbose_name='Labor Name (Spares Used Mechanic)')
    created_at   = models.DateTimeField(auto_now_add=True)

    # Phase 10 -- header totals confirmed live on the reference; updated_total is recomputed in
    # the view after formset save, same convention as SparesPurchaseEstimationMaster (Phase 7b)
    discount       = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    updated_total  = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    def __str__(self):
        return f"ULC-{self.pk} | JC-{self.job_card_id}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Used Vehicle Labor Charges'

    @property
    def total_amount(self):
        from django.db.models import Sum
        from decimal import Decimal
        return self.labor_details.aggregate(t=Sum('total'))['t'] or Decimal('0.00')


class UsedVehicleLaborChargeRemoveItem(models.Model):
    """Reference: 'Labor Charge Removes' -- labor-work rows removed from the charge during
    editing. Genuinely typed as free text (Data), not a Link, unlike the main labor_details
    table's real Labour Work FK -- preserved faithfully."""
    charge     = models.ForeignKey(UsedVehicleLaborCharge, on_delete=models.CASCADE, related_name='labor_charge_removes')
    labor_work = models.CharField(max_length=200, blank=True)
    amount     = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    sgst       = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    cgst       = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    total      = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    def __str__(self):
        return f"{self.labor_work} — Rs.{self.total}"

    class Meta:
        verbose_name_plural = 'Used Vehicle Labor Charge Removed Items'


class UsedVehicleLaborDetailLine(models.Model):
    charge     = models.ForeignKey(UsedVehicleLaborCharge, on_delete=models.CASCADE, related_name='labor_details')
    labor_work = models.ForeignKey('masters.LabourWork', on_delete=models.PROTECT)
    quantity   = models.IntegerField(default=0, blank=True)
    amount     = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    sgst       = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    cgst       = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    total      = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    def __str__(self):
        return f"{self.labor_work} — Rs.{self.total}"

    class Meta:
        verbose_name_plural = 'Used Vehicle Labor Detail Lines'


class UsedVehicleLaborSpareItem(models.Model):
    charge   = models.ForeignKey(UsedVehicleLaborCharge, on_delete=models.CASCADE, related_name='spares_used')
    item     = models.ForeignKey('spares.SparesItem', on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=3, default=1, blank=True)
    rate     = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    total    = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    def __str__(self):
        return f"{self.item} x {self.quantity}"

    class Meta:
        verbose_name_plural = 'Used Vehicle Labor Spare Items'


class UsedVehicleServiceInvoice(DocStatusMixin, models.Model):
    job_card        = models.OneToOneField(UsedVehicleJobCard, on_delete=models.PROTECT, related_name='service_invoice')
    labor_total     = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    spares_total    = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    outwork_total   = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    subtotal        = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    gst_amount      = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    final_amount    = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    invoice_date    = models.DateField()
    created_at      = models.DateTimeField(auto_now_add=True)

    def calculate_totals(self):
        from decimal import Decimal
        subtotal = (self.labor_total or Decimal('0')) + (self.spares_total or Decimal('0')) + (self.outwork_total or Decimal('0'))
        self.subtotal = subtotal
        gst_rate = Decimal('18')
        try:
            from accounts.models import CompanySettings
            gst_rate = Decimal(str(CompanySettings.get_instance().gst_rate or 18))
        except Exception:
            pass
        self.gst_amount = (subtotal * gst_rate / Decimal('100')).quantize(Decimal('0.01'))
        self.final_amount = subtotal + self.gst_amount - (self.discount_amount or Decimal('0'))
        self.save(update_fields=['subtotal', 'gst_amount', 'final_amount'])

    def __str__(self):
        return f"USINV-{self.pk} | JC-{self.job_card_id} — Rs.{self.final_amount}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Used Vehicle Service Invoices'


# ---------------------------------------------------------------------------
# Phase 4 — Used Vehicle Job Card inspection-checklist child tables (embedded
# directly in Job Card Creation, mirroring service/models.py's New Vehicle set;
# no Table2/Table3 variants exist in the reference for used vehicles, and the
# 14 single-shape "<Part> Details Table" reference doctypes are collapsed into
# one UsedVehiclePartsCheckItem model with a `category` discriminator).
# ---------------------------------------------------------------------------

class UsedVehicleComplaintDetail(models.Model):
    class Status(models.TextChoices):
        PENDING   = 'pending',   'Pending'
        COMPLETED = 'completed', 'Completed'

    job_card           = models.ForeignKey(UsedVehicleJobCard, on_delete=models.CASCADE, null=True, blank=True, related_name='complaint_details')
    final_inspection   = models.ForeignKey('UsedVehicleFinalInspection', on_delete=models.CASCADE, null=True, blank=True, related_name='complaints_table',
                                            help_text='Phase 10 -- the reference reuses this same child doctype on Final Inspection. '
                                                       'Exactly one of job_card/final_inspection is set in practice -- enforced by which '
                                                       'inline formset a row is created through (see used_vehicles/forms.py), not a model '
                                                       'clean() check: Django sets an inline formset child\'s FK only at save() time, after '
                                                       'formset.is_valid() already ran, so a clean()-level exactly-one-set check would reject '
                                                       'every legitimate new row before the FK is ever assigned.')
    customer_complaint = models.ForeignKey('masters.JobcardComplaintMaster', on_delete=models.PROTECT, related_name='+')
    details             = models.TextField(blank=True)
    status               = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    complaint_check_box  = models.BooleanField(default=False)
    estimated_amount     = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    def __str__(self):
        return f"{self.customer_complaint} (JC-{self.job_card_id or self.final_inspection_id})"

    class Meta:
        verbose_name_plural = 'Used Vehicle Complaint Details'


class UsedVehicleSupervisorObservation(models.Model):
    job_card             = models.ForeignKey(UsedVehicleJobCard, on_delete=models.CASCADE, null=True, blank=True, related_name='supervisor_observations')
    final_inspection     = models.ForeignKey('UsedVehicleFinalInspection', on_delete=models.CASCADE, null=True, blank=True, related_name='supervisor_recomment',
                                              help_text='Phase 10 -- same dual-FK pattern as UsedVehicleComplaintDetail above, same reason '
                                                         'for not enforcing exactly-one-set via clean()')
    complaint            = models.ForeignKey('masters.JobcardSupervisorObservationMaster', on_delete=models.PROTECT, related_name='+')
    details              = models.TextField(blank=True)
    complaint_check_box  = models.BooleanField(default=False)
    estimated_amount     = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    def __str__(self):
        return f"{self.complaint} (JC-{self.job_card_id or self.final_inspection_id})"

    class Meta:
        verbose_name_plural = 'Used Vehicle Supervisor Observations'


class UsedVehicleEngineDetailRow(models.Model):
    job_card      = models.ForeignKey(UsedVehicleJobCard, on_delete=models.CASCADE, related_name='engine_details')
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

    def __str__(self):
        return f"{self.items} (JC-{self.job_card_id})"

    class Meta:
        verbose_name_plural = 'Used Vehicle Engine Detail Rows'


class UsedVehicleLightDetail(models.Model):
    job_card = models.ForeignKey(UsedVehicleJobCard, on_delete=models.CASCADE, related_name='light_details')
    items    = models.CharField(max_length=200, blank=True)
    yes      = models.BooleanField(default=False)
    no       = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.items} (JC-{self.job_card_id})"

    class Meta:
        verbose_name_plural = 'Used Vehicle Light Details'


class UsedVehicleChasisDetailRow(models.Model):
    job_card   = models.ForeignKey(UsedVehicleJobCard, on_delete=models.CASCADE, related_name='chasis_details')
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

    def __str__(self):
        return f"{self.items} (JC-{self.job_card_id})"

    class Meta:
        verbose_name_plural = 'Used Vehicle Chasis Detail Rows'


class UsedVehiclePartsCheckItem(models.Model):
    """Collapses 14 reference doctypes (Brake/Fork/Cables/Bulb/Indicator/
    Rubbers/Foot Rest/Oil Seals/Packing/Handle Bar and Mount/Number Plate/
    Chain/Clutch/Body Parts Details Table) into one model -- all 14 share the
    exact same 3 fields (spares, change_need_yes, change_need_no) in the
    reference; only the section/category differs."""
    class Category(models.TextChoices):
        BRAKE       = 'brake',       'Brake'
        FORK        = 'fork',        'Fork'
        CABLES      = 'cables',      'Cables'
        BULB        = 'bulb',        'Bulb'
        INDICATOR   = 'indicator',   'Indicator'
        RUBBERS     = 'rubbers',     'Rubbers'
        FOOT_REST   = 'foot_rest',   'Foot Rest'
        OIL_SEALS   = 'oil_seals',   'Oil Seals'
        PACKING     = 'packing',     'Packing'
        HANDLE_BAR  = 'handle_bar',  'Handle Bar and Mount'
        NUMBER_PLATE = 'number_plate', 'Number Plate'
        CHAIN       = 'chain',       'Chain'
        CLUTCH      = 'clutch',      'Clutch'
        BODY_PARTS  = 'body_parts',  'Body Parts'

    job_card         = models.ForeignKey(UsedVehicleJobCard, on_delete=models.CASCADE, related_name='parts_check_items')
    category         = models.CharField(max_length=20, choices=Category.choices, db_index=True)
    spares           = models.CharField(max_length=200, blank=True)
    change_need_yes  = models.BooleanField(default=False)
    change_need_no   = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.get_category_display()}: {self.spares} (JC-{self.job_card_id})"

    class Meta:
        verbose_name_plural = 'Used Vehicle Parts Check Items'


class UsedVehicleOthersDetail(models.Model):
    """Reference: 'Job Card Others Table' -- distinct shape from the 14
    collapsed parts-check categories above (which include an 'Others' category
    of their own, i.e. reference's 'Others Details Table')."""
    job_card         = models.ForeignKey(UsedVehicleJobCard, on_delete=models.CASCADE, related_name='others_details')
    items            = models.CharField(max_length=200, blank=True)
    others_check_box = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.items} (JC-{self.job_card_id})"

    class Meta:
        verbose_name_plural = 'Used Vehicle Others Details'


@receiver(post_save, sender=UsedVehicleBayIn)
def on_used_vehicle_bay_in_submitted(sender, instance, **kwargs):
    if instance.docstatus == UsedVehicleBayIn.DocStatus.SUBMITTED:
        _advance_used_vehicle_job_card_status(instance.job_card, UsedVehicleJobCard.ServiceStatus.IN_BAY)


@receiver(post_save, sender=UsedVehicleBayOut)
def on_used_vehicle_bay_out_submitted(sender, instance, **kwargs):
    if instance.docstatus == UsedVehicleBayOut.DocStatus.SUBMITTED:
        _advance_used_vehicle_job_card_status(instance.job_card, UsedVehicleJobCard.ServiceStatus.IN_PROGRESS)


@receiver(post_save, sender=UsedVehicleOutworkEntryIssue)
def on_used_vehicle_outwork_issue_submitted(sender, instance, **kwargs):
    if instance.docstatus == UsedVehicleOutworkEntryIssue.DocStatus.SUBMITTED:
        _advance_used_vehicle_job_card_status(instance.job_card, UsedVehicleJobCard.ServiceStatus.OUTWORK)


@receiver(post_save, sender=UsedVehicleOutworkEntryReturn)
def on_used_vehicle_outwork_return_submitted(sender, instance, **kwargs):
    if instance.docstatus == UsedVehicleOutworkEntryReturn.DocStatus.SUBMITTED and not instance.rework:
        _advance_used_vehicle_job_card_status(instance.job_card, UsedVehicleJobCard.ServiceStatus.FINAL_INSPECTION)


@receiver(post_save, sender=UsedVehicleFinalInspection)
def on_used_vehicle_final_inspection_submitted(sender, instance, **kwargs):
    if instance.docstatus == UsedVehicleFinalInspection.DocStatus.SUBMITTED:
        status = UsedVehicleJobCard.ServiceStatus.FINAL_INSPECTION if instance.rework else UsedVehicleJobCard.ServiceStatus.READY
        _advance_used_vehicle_job_card_status(instance.job_card, status)


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

@receiver(post_save, sender=UsedVehicleDelivery)
def on_used_vehicle_delivered(sender, instance, **kwargs):
    """Same convention as sales.models.on_delivery_created (Phase 1): advance
    the sale status and mark the register-no stock sold, gated on submit."""
    if instance.docstatus != UsedVehicleDelivery.DocStatus.SUBMITTED:
        return
    sale = instance.sale
    if sale.sale_status != UsedVehicleSale.SaleStatus.DELIVERED:
        sale.sale_status = UsedVehicleSale.SaleStatus.DELIVERED
        sale.save(update_fields=['sale_status'])
    reg = sale.vehicle_number
    if reg.stock_status != UsedVehicleRegisterNo.StockStatus.SOLD:
        reg.stock_status = UsedVehicleRegisterNo.StockStatus.SOLD
        reg.save(update_fields=['stock_status'])


@receiver(post_save, sender=UsedVehiclePurchaseInvoice)
def on_used_vehicle_purchased(sender, instance, **kwargs):
    """Submitting a Purchase Invoice makes its line-item register numbers
    available stock, mirroring sales.VehicleAllotment's save()-side-effect
    convention from Phase 1. Rejects reusing a registration number that's
    already Sold or Reserved, to prevent silently overwriting an existing
    vehicle's stock record."""
    if instance.docstatus != UsedVehiclePurchaseInvoice.DocStatus.SUBMITTED:
        return
    from django.core.exceptions import ValidationError
    for item in instance.items.all():
        if not item.registration_no:
            continue
        existing = UsedVehicleRegisterNo.objects.filter(registration_no=item.registration_no).first()
        if existing and existing.stock_status in (
            UsedVehicleRegisterNo.StockStatus.SOLD,
            UsedVehicleRegisterNo.StockStatus.RESERVED,
        ):
            raise ValidationError(
                f"Registration number {item.registration_no} is already recorded as "
                f"{existing.get_stock_status_display()} — cannot re-purchase a vehicle "
                f"still tied to an existing sold/reserved record."
            )
        UsedVehicleRegisterNo.objects.update_or_create(
            registration_no=item.registration_no,
            defaults={
                'used_vehicle': item.used_vehicle,
                'color': item.color,
                'chassis_no': item.chassis_no,
                'engine_no': item.engine_no,
                'branch': instance.branch,
                'stock_status': UsedVehicleRegisterNo.StockStatus.AVAILABLE,
                'purchase_date': instance.invoice_date,
            },
        )


# ---------------------------------------------------------------------------
# Phase 8c — Used Vehicle Master Settings: the used-vehicle counterpart of
# customers.VehicleMasterSettings. Submit creates real UsedVehicleRegisterNo
# rows -- the same confirmed-gap "batch intake" purpose, for used stock.
# ---------------------------------------------------------------------------

class UsedVehicleMasterSettings(DocStatusMixin, models.Model):
    master_no             = models.CharField(max_length=50, unique=True, blank=True, editable=False)
    vehicle                = models.ForeignKey(UsedVehicleModel, on_delete=models.PROTECT, related_name='master_settings')
    has_exchange_vehicle   = models.BooleanField(default=False)
    service_settings       = models.ForeignKey(
        'service.VehicleServiceMaster', on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
        help_text='Shared with the new-vehicle side -- reuses the existing service.VehicleServiceMaster '
                   'rather than a duplicate masters-app model'
    )
    exchange_vehicle_id    = models.ForeignKey(
        'sales.ExchangeVehicle', on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
        help_text='Reference Link target is a standalone Exchange Vehicle Master, shared with the '
                   'new-vehicle side; Django has no such freestanding master, so this points '
                   'directly at sales.ExchangeVehicle'
    )
    created_at             = models.DateTimeField(auto_now_add=True)
    created_by             = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.master_no:
            with transaction.atomic():
                last = UsedVehicleMasterSettings.objects.select_for_update().order_by('-id').values_list('master_no', flat=True).first()
                next_seq = 1
                if last:
                    try:
                        next_seq = int(last.rsplit('-', 1)[-1]) + 1
                    except ValueError:
                        pass
                self.master_no = f'USED-VEH-MAS-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.master_no

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Used Vehicle Master Settings'


class UsedVehicleMasterSettingsItem(models.Model):
    master          = models.ForeignKey(UsedVehicleMasterSettings, on_delete=models.CASCADE, related_name='items')
    vehicle_name    = models.ForeignKey(UsedVehicleModel, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    model           = models.CharField(max_length=200)
    register_number = models.CharField(max_length=50)
    chasis_no       = models.CharField(max_length=100, blank=True, verbose_name='Chasis No',
                                        help_text='Optional here, unlike the new-vehicle side -- used vehicles are identified primarily by registration number (reference-confirmed asymmetry)')
    engine          = models.CharField(max_length=100)
    color           = models.ForeignKey(UsedVehicleColor, on_delete=models.PROTECT, related_name='+')
    color_code      = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.master.master_no} | {self.register_number}"

    class Meta:
        verbose_name_plural = 'Used Vehicle Master Settings Items'


@receiver(post_save, sender=UsedVehicleMasterSettings)
def on_used_vehicle_master_settings_submitted(sender, instance, **kwargs):
    if instance.docstatus != UsedVehicleMasterSettings.DocStatus.SUBMITTED:
        return
    for row in instance.items.all():
        if UsedVehicleRegisterNo.objects.filter(registration_no=row.register_number).exists():
            continue  # Duplicate registration number -- skip, don't crash on the unique constraint
        UsedVehicleRegisterNo.objects.create(
            registration_no=row.register_number,
            used_vehicle=instance.vehicle,
            color=row.color,
            chassis_no=row.chasis_no,
            engine_no=row.engine,
            stock_status=UsedVehicleRegisterNo.StockStatus.AVAILABLE,
        )


# ---------------------------------------------------------------------------
# Phase 8d — Used Vehicle Sales Setting (non-submittable config master).
# ---------------------------------------------------------------------------

class UsedVehicleSalesSetting(models.Model):
    setting_no  = models.CharField(max_length=50, unique=True, blank=True, editable=False)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True,
                                       help_text='Reference marks this field hidden with no client-script consumer; kept as a real editable field here')
    created_at  = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.setting_no:
            with transaction.atomic():
                last = UsedVehicleSalesSetting.objects.select_for_update().order_by('-id').values_list('setting_no', flat=True).first()
                next_seq = 1
                if last:
                    try:
                        next_seq = int(last.rsplit('-', 1)[-1]) + 1
                    except ValueError:
                        pass
                self.setting_no = f'USED-VEH-SAL-SET-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.setting_no

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Used Vehicle Sales Settings'


class UsedVehicleSalesSettingItem(models.Model):
    setting       = models.ForeignKey(UsedVehicleSalesSetting, on_delete=models.CASCADE, related_name='items')
    vehicle_no    = models.ForeignKey(UsedVehicleRegisterNo, on_delete=models.SET_NULL, null=True, blank=True)
    purchase_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True,
                                         help_text='Reference computes this via an unreadable server method; kept manually editable here')
    maintain_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True,
                                         help_text='Reference computes this via an unreadable server method; kept manually editable here')
    base_rate     = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    gross_profit  = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True,
                                         help_text='Computed as base_rate - (purchase_cost + maintain_cost), '
                                                    'matching the reference Client Script formula exactly')

    def save(self, *args, **kwargs):
        self.gross_profit = (self.base_rate or 0) - ((self.purchase_cost or 0) + (self.maintain_cost or 0))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.setting.setting_no} | {self.vehicle_no or '—'}"

    class Meta:
        verbose_name_plural = 'Used Vehicle Sales Setting Items'


class UsedVehicleInsuranceUpdate(DocStatusMixin, models.Model):
    """Reference: 'Used Vehicle Insurance Update' -- purchasing/renewing insurance on a used
    vehicle that's in stock with no or expired cover. Found during the round-3 live-verification
    sweep (27_not_in_main_nav.md); a genuinely missing, cleanly-shaped document -- no unreadable
    server logic involved, unlike most of what's left in that bucket."""

    class InsuranceStatus(models.TextChoices):
        NO_INSURANCE = 'no_insurance', 'Vehicle with No Insurance'
        EXPIRED = 'expired', 'Vehicle with Expired Insurance'

    class PaymentMethod(models.TextChoices):
        CASH = 'cash', 'Cash'
        BANK = 'bank', 'Bank'

    _amend_reset_number_field = 'update_no'

    update_no        = models.CharField(max_length=50, unique=True, blank=True, editable=False)
    register_no       = models.ForeignKey(UsedVehicleRegisterNo, on_delete=models.PROTECT, related_name='insurance_updates')
    insurance_status  = models.CharField(max_length=20, choices=InsuranceStatus.choices)
    insurance_name    = models.ForeignKey('masters.Supplier', on_delete=models.PROTECT, related_name='+')
    policy_number     = models.CharField(max_length=100)
    start_date        = models.DateField()
    end_date          = models.DateField()
    amount            = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method    = models.CharField(max_length=10, choices=PaymentMethod.choices)
    from_account      = models.CharField(max_length=100, blank=True,
                                          help_text='No Chart of Accounts model exists in Django -- free text, '
                                                     'matching the accounts_from/accounts_to precedent used throughout')
    to_account        = models.CharField(max_length=100, blank=True)
    ref_no            = models.CharField(max_length=100, blank=True)
    ref_date          = models.DateField(null=True, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)
    created_by        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.update_no:
            with transaction.atomic():
                last = UsedVehicleInsuranceUpdate.objects.select_for_update().order_by('-id').values_list('update_no', flat=True).first()
                next_seq = 1
                if last:
                    try:
                        next_seq = int(last.rsplit('-', 1)[-1]) + 1
                    except ValueError:
                        pass
                self.update_no = f'UVIU-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.update_no

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Used Vehicle Insurance Updates'
