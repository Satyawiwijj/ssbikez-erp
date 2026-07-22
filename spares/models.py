from decimal import Decimal
from django.db import models, transaction
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver
from masters.models import SparesCategory, Supplier, Warehouse, Rack, Bin

from accounts.models import DocStatusMixin


def _stock_on_hand(item, warehouse, rack=None, bin=None):
    """Current StockLedger quantity for an item/location, 0 if no row exists yet."""
    ledger = StockLedger.objects.filter(item=item, warehouse=warehouse, rack=rack, bin=bin).first()
    return ledger.quantity if ledger else Decimal('0')


class SparesItem(models.Model):
    item_code = models.CharField(max_length=50, unique=True, editable=False)
    item_name = models.CharField(max_length=200)
    category = models.ForeignKey(SparesCategory, on_delete=models.SET_NULL, null=True, blank=True)
    item_group = models.CharField(max_length=100, blank=True, help_text='Item group classification (e.g. Engine, Electrical, Body)')
    item_sub_group = models.CharField(max_length=100, blank=True)
    hsn_sac = models.CharField(max_length=20, blank=True)
    uom = models.CharField(max_length=20, default='Nos')
    part_number = models.CharField(max_length=100, blank=True)
    brand = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    maintain_stock = models.BooleanField(default=True)
    allow_negative_stock = models.BooleanField(default=False)
    opening_stock = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    valuation_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    standard_selling_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    mrp = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    sgst = models.DecimalField(max_digits=5, decimal_places=2, default=9)
    cgst = models.DecimalField(max_digits=5, decimal_places=2, default=9)
    is_ineligible_for_itc = models.BooleanField(default=False)
    reorder_level = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    reorder_qty = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    warranty_period_days = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    def save(self, *args, **kwargs):
        if not self.item_code:
            with transaction.atomic():
                last = SparesItem.objects.select_for_update().order_by('-id').first()
                num = (last.id + 1) if last else 1
                self.item_code = f"SP-{num:05d}"
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_code} - {self.item_name}"

    class Meta:
        ordering = ['item_name']


class ItemRackBin(models.Model):
    item = models.ForeignKey(SparesItem, on_delete=models.CASCADE, related_name='rack_bins')
    rack = models.ForeignKey(Rack, on_delete=models.CASCADE)
    bin = models.ForeignKey(Bin, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.item.item_code} | {self.rack} | {self.bin}"


class StockLedger(models.Model):
    item = models.ForeignKey(SparesItem, on_delete=models.CASCADE, related_name='stock')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    rack = models.ForeignKey(Rack, on_delete=models.SET_NULL, null=True, blank=True)
    bin = models.ForeignKey(Bin, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['item', 'warehouse', 'rack', 'bin']

    def __str__(self):
        return f"{self.item.item_code} | {self.warehouse.name} | Qty: {self.quantity}"


class SupplierQuote(models.Model):
    STATUS = [
        ('draft', 'Draft'), ('submitted', 'Submitted'),
        ('ordered', 'Ordered'), ('cancelled', 'Cancelled'),
    ]
    quote_no = models.CharField(max_length=50, unique=True, editable=False)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    request_quotation = models.ForeignKey(
        'RequestSupplierQuote', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='supplier_quotes'
    )
    date = models.DateField()
    valid_till = models.DateField(null=True, blank=True)
    quotation_number = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='draft')
    is_reverse_charge = models.BooleanField(default=False)
    total_quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_taxes = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    additional_discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    additional_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    terms_and_conditions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    def save(self, *args, **kwargs):
        if not self.quote_no:
            with transaction.atomic():
                last = SupplierQuote.objects.select_for_update().order_by('-id').first()
                num = (last.id + 1) if last else 1
                self.quote_no = f"SQ-{num:05d}"
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.quote_no

    class Meta:
        ordering = ['-date']


class SupplierQuoteItem(models.Model):
    quote = models.ForeignKey(SupplierQuote, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(SparesItem, on_delete=models.PROTECT)
    required_date = models.DateField(null=True, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=3, validators=[MinValueValidator(0)])
    uom = models.CharField(max_length=20, default='Nos')
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.amount = self.quantity * self.rate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quote.quote_no} | {self.item.item_code}"


class PurchaseOrder(models.Model):
    STATUS = [
        ('draft', 'Draft'), ('submitted', 'Submitted'),
        ('received', 'Received'), ('cancelled', 'Cancelled'),
    ]
    po_no = models.CharField(max_length=50, unique=True, editable=False)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    supplier_name = models.CharField(max_length=200, blank=True)
    supplier_quote = models.ForeignKey(
        SupplierQuote, on_delete=models.SET_NULL, null=True, blank=True
    )
    date = models.DateField()
    required_by = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='draft')
    is_reverse_charge = models.BooleanField(default=False)
    supplier_gstin = models.CharField(max_length=20, blank=True)
    gst_category = models.CharField(max_length=50, blank=True)
    place_of_supply = models.CharField(max_length=100, blank=True)
    get_customer_order = models.BooleanField(default=False, verbose_name='Get Customer Order')
    get_estimation     = models.BooleanField(default=False, verbose_name='Get Estimation')
    customer_order = models.ForeignKey(
        'CounterSale', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='purchase_orders', help_text='Only meaningful when Get Customer Order is checked'
    )
    estimation = models.ForeignKey(
        'SparesPurchaseEstimationMaster', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='purchase_orders', help_text='Only meaningful when Get Estimation is checked'
    )
    load_status = models.CharField(max_length=50, blank=True)
    total_quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_taxes = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    terms_and_conditions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    def save(self, *args, **kwargs):
        if self.supplier and not self.supplier_name:
            self.supplier_name = self.supplier.supplier_name
        if not self.po_no:
            with transaction.atomic():
                last = PurchaseOrder.objects.select_for_update().order_by('-id').first()
                num = (last.id + 1) if last else 1
                self.po_no = f"PO-{num:05d}"
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.po_no

    class Meta:
        ordering = ['-date']


class TaxChargeLine(models.Model):
    """
    Document-level tax/charge breakup row — shown as its own table on the
    document (e.g. CGST/SGST on the net total), separate from any per-item
    tax fields. Mirrors the reference ERP's "Purchase Taxes and Charges"
    table on Purchase Order / Purchase Invoice / Supplier Quotation.
    """
    class ApplyType(models.TextChoices):
        NET_TOTAL  = 'on_net_total', 'On Net Total'
        PREV_ROW   = 'on_previous_row_amount', 'On Previous Row Amount'
        PREV_TOTAL = 'on_previous_row_total', 'On Previous Row Total'
        ACTUAL     = 'actual', 'Actual'

    apply_type   = models.CharField(max_length=30, choices=ApplyType.choices,
                                     default=ApplyType.NET_TOTAL, verbose_name='Type')
    account_head = models.CharField(max_length=200)
    tax_rate     = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    amount       = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        abstract = True
        ordering = ['pk']

    def __str__(self):
        return f"{self.account_head} | {self.tax_rate}% | Rs.{self.amount}"


class PurchaseOrderTax(TaxChargeLine):
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='taxes')


class PurchaseOrderItem(models.Model):
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(SparesItem, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    required_by = models.DateField(null=True, blank=True)
    quantity     = models.DecimalField(max_digits=10, decimal_places=3, validators=[MinValueValidator(0)])
    uom          = models.CharField(max_length=20, default='Nos')
    rate         = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    amount       = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    received_qty = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    # ERP alignment — stock intelligence columns. These are informational
    # reporting metrics (not core transactional data) with a sensible default
    # of 0, so they're optional at the form level -- previously they had no
    # blank=True, making them silently-required with no error ever rendered
    # in po_form.html for them (a real bug: a PO submit could fail validation
    # for these 5 fields with zero visible feedback to the user).
    used_qty      = models.IntegerField(default=0, blank=True, verbose_name='Used QTY')
    ordered_qty   = models.IntegerField(default=0, blank=True, verbose_name='Ordered QTY')
    average       = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, verbose_name='Average')
    stock_qty     = models.IntegerField(default=0, blank=True, verbose_name='Stock QTY')
    one_month_qty = models.IntegerField(default=0, blank=True, verbose_name='1 Month')
    part_no            = models.CharField(max_length=100, blank=True, verbose_name='Part No.')
    delivery_need_qty  = models.DecimalField(max_digits=10, decimal_places=3, default=0, blank=True)
    branch             = models.ForeignKey('accounts.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    def save(self, *args, **kwargs):
        self.amount = self.quantity * self.rate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order.po_no} | {self.item.item_code}"


class PurchaseInvoice(models.Model):
    STATUS = [
        ('draft', 'Draft'), ('submitted', 'Submitted'),
        ('paid', 'Paid'), ('cancelled', 'Cancelled'),
    ]
    invoice_no = models.CharField(max_length=50, unique=True, editable=False)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.SET_NULL, null=True, blank=True
    )
    date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='draft')
    is_reverse_charge = models.BooleanField(default=False)
    supplier_gstin = models.CharField(max_length=20, blank=True)
    gst_category = models.CharField(max_length=50, blank=True)
    place_of_supply = models.CharField(max_length=100, blank=True)
    total_quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_sgst = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_cgst = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_taxes = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, default='Unpaid')
    payment_type = models.CharField(
        max_length=20, blank=True,
        choices=[('adjustment', 'Adjustment'), ('cash', 'Cash')],
    )
    cash_account = models.CharField(max_length=200, blank=True)
    pay_mode = models.CharField(max_length=100, blank=True)
    has_tcs = models.BooleanField(default=False, verbose_name='Has TCS')
    tcs_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    remarks = models.TextField(blank=True)
    # Amend trail, same shape as DocStatusMixin.amended_from (this model
    # predates that mixin and uses its own plain status field instead).
    amended_from = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='amendments'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    def save(self, *args, **kwargs):
        if not self.invoice_no:
            with transaction.atomic():
                last = PurchaseInvoice.objects.select_for_update().order_by('-id').first()
                num = (last.id + 1) if last else 1
                self.invoice_no = f"PI-{num:05d}"
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def submit(self, user=None):
        """Explicit submit action for an invoice that was created as Draft
        (items added before status='submitted', so PurchaseInvoiceItem.save()'s
        own is_new-and-submitted check never fired for them at creation time)."""
        if self.status != 'draft':
            raise ValueError('Only a Draft invoice can be submitted.')
        self.status = 'submitted'
        self.save()
        for item in self.items.all():
            ledger, _ = StockLedger.objects.get_or_create(
                item=item.item, warehouse=item.warehouse, rack=item.rack, bin=item.bin,
                defaults={'quantity': 0},
            )
            StockLedger.objects.filter(pk=ledger.pk).update(quantity=F('quantity') + item.quantity)

    def cancel(self, user=None):
        """Reverses the stock credit. Safe without a separate posted/reversed
        marker: cancel() is only reachable while status=='submitted' (which
        implies the credit already happened, either via this submit() or via
        PurchaseInvoiceItem.save()'s own at-creation credit), and cancel()
        can only succeed once per invoice since status becomes 'cancelled'
        afterwards, blocking re-entry through this same check."""
        if self.status != 'submitted':
            raise ValueError('Only a Submitted invoice can be cancelled.')
        for item in self.items.all():
            ledger, _ = StockLedger.objects.get_or_create(
                item=item.item, warehouse=item.warehouse, rack=item.rack, bin=item.bin,
                defaults={'quantity': 0},
            )
            StockLedger.objects.filter(pk=ledger.pk).update(quantity=F('quantity') - item.quantity)
        self.status = 'cancelled'
        self.save()

    def amend(self):
        if self.status != 'cancelled':
            raise ValueError('Only a Cancelled invoice can be amended.')
        new = PurchaseInvoice.objects.get(pk=self.pk)
        new.pk = None
        new._state.adding = True
        new.invoice_no = ''
        new.status = 'draft'
        new.amended_from = self
        new.save()
        for item in self.items.all():
            item.pk = None
            item._state.adding = True
            item.invoice = new
            item.save()
        for tax in self.taxes.all():
            tax.pk = None
            tax._state.adding = True
            tax.invoice = new
            tax.save()
        return new

    def __str__(self):
        return self.invoice_no

    class Meta:
        ordering = ['-date']


class PurchaseInvoiceTax(TaxChargeLine):
    invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, related_name='taxes')


class SupplierQuoteTax(TaxChargeLine):
    quote = models.ForeignKey(SupplierQuote, on_delete=models.CASCADE, related_name='taxes')


class PurchaseInvoiceItem(models.Model):
    invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(SparesItem, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    rack = models.ForeignKey(Rack, on_delete=models.SET_NULL, null=True, blank=True)
    bin = models.ForeignKey(Bin, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    uom = models.CharField(max_length=20, default='Nos')
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sgst = models.DecimalField(max_digits=5, decimal_places=2, default=9)
    cgst = models.DecimalField(max_digits=5, decimal_places=2, default=9)
    sgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    item_category = models.CharField(max_length=100, blank=True)
    part_no       = models.CharField(max_length=100, blank=True, verbose_name='Part No.')

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        self.amount = self.quantity * self.rate
        self.sgst_amount = self.amount * self.sgst / 100
        self.cgst_amount = self.amount * self.cgst / 100
        self.total = self.amount + self.sgst_amount + self.cgst_amount
        super().save(*args, **kwargs)
        # Auto-update StockLedger when a new item is added to a submitted invoice
        if is_new and self.invoice.status == 'submitted':
            from django.db.models import F as _F
            sl, created = StockLedger.objects.get_or_create(
                item=self.item, warehouse=self.warehouse,
                rack=self.rack, bin=self.bin,
                defaults={'quantity': self.quantity},
            )
            if not created:
                StockLedger.objects.filter(pk=sl.pk).update(
                    quantity=_F('quantity') + self.quantity
                )

    def __str__(self):
        return f"{self.invoice.invoice_no} | {self.item.item_code}"


class CounterSale(models.Model):
    PAY_TYPES = [('cash', 'Cash'), ('card', 'Card'), ('upi', 'UPI'), ('credit', 'Credit')]
    STATUS = [('draft', 'Draft'), ('submitted', 'Submitted'), ('cancelled', 'Cancelled')]
    SALE_TYPES = [('sale', 'Sale'), ('order', 'Order')]
    sale_no = models.CharField(max_length=50, unique=True, editable=False)
    customer = models.CharField(max_length=200)
    mobile = models.CharField(max_length=20)
    gst_category = models.CharField(max_length=50, blank=True)
    godown = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    date = models.DateField()
    is_warranty = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS, default='draft')
    total_qty = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, default='Unpaid')
    pay_type = models.CharField(max_length=20, choices=PAY_TYPES, blank=True)
    sale_type          = models.CharField(max_length=10, choices=SALE_TYPES, default='sale', verbose_name='Type')
    spot_sale          = models.BooleanField(default=True)
    ledger_voucher_no  = models.ForeignKey('billing.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='counter_sales')
    accounts_from      = models.CharField(max_length=200, blank=True)
    accounts_to        = models.CharField(max_length=200, blank=True)
    bank_ref_no        = models.CharField(max_length=100, blank=True)
    bank_ref_date      = models.DateField(null=True, blank=True)
    balance_delivery_qty = models.DecimalField(max_digits=10, decimal_places=3, default=0, blank=True)
    counter_sale_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    # Idempotency markers for the StockLedger movement below -- same shape as
    # StockTransfer.stock_posted/stock_reversed. System-controlled only (excluded
    # from CounterSaleForm), never toggled directly by a user.
    stock_posted   = models.BooleanField(default=False)
    stock_reversed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    def save(self, *args, **kwargs):
        if not self.sale_no:
            with transaction.atomic():
                last = CounterSale.objects.select_for_update().order_by('-id').first()
                num = (last.id + 1) if last else 1
                self.sale_no = f"CS-{num:05d}"
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def check_stock_sufficiency(self):
        """Raise ValueError if selling any line would drive StockLedger negative.
        Mirrors vas.models' AMCPackage/RSAPackage/ProtectionPlusPackage.submit()
        stock-safety guard (raise before the movement is ever posted)."""
        for line in self.items.all():
            available = _stock_on_hand(line.item, self.godown, line.rack, line.bin)
            if available < line.quantity:
                raise ValueError(
                    f"Insufficient stock for {line.item.item_code} at {self.godown}: "
                    f"available {available}, requested {line.quantity}."
                )

    def submit(self, user=None):
        if self.status != 'draft':
            raise ValueError('Only a Draft counter sale can be submitted.')
        self.check_stock_sufficiency()
        self.status = 'submitted'
        self.save()

    def cancel(self, user=None):
        if self.status != 'submitted':
            raise ValueError('Only a Submitted counter sale can be cancelled.')
        self.status = 'cancelled'
        self.save()

    def __str__(self):
        return self.sale_no

    class Meta:
        ordering = ['-date']


class CounterSaleItem(models.Model):
    sale = models.ForeignKey(CounterSale, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(SparesItem, on_delete=models.PROTECT)
    rack = models.ForeignKey(Rack, on_delete=models.SET_NULL, null=True, blank=True)
    bin = models.ForeignKey(Bin, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=18)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    delivery_balance_qty = models.DecimalField(max_digits=10, decimal_places=3, default=0, blank=True)
    stock_qty            = models.DecimalField(max_digits=10, decimal_places=3, default=0, blank=True, help_text='Snapshot of on-hand stock at issue time')
    issue_status          = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.amount = self.quantity * self.rate
        self.total = self.amount + (self.amount * self.gst_percent / 100)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sale.sale_no} | {self.item.item_code}"


@receiver(post_save, sender=CounterSale)
def on_counter_sale_status_changed(sender, instance, **kwargs):
    """StockLedger movement for a Counter Sale -- a sale decrements stock on
    submit and the decrement is given back if the sale is later cancelled.
    Guarded by stock_posted/stock_reversed (not docstatus, since CounterSale
    predates DocStatusMixin in this app and uses its own plain status field)
    so the multiple .save() calls across create/submit/cancel never double-post."""
    if instance.status == 'submitted' and not instance.stock_posted:
        for line in instance.items.all():
            ledger, _ = StockLedger.objects.get_or_create(
                item=line.item, warehouse=instance.godown, rack=line.rack, bin=line.bin,
                defaults={'quantity': 0},
            )
            StockLedger.objects.filter(pk=ledger.pk).update(quantity=F('quantity') - line.quantity)
        CounterSale.objects.filter(pk=instance.pk).update(stock_posted=True)
        instance.stock_posted = True  # keep the in-memory instance in sync too,
        # so a chained submit(); cancel() on the same Python object (no
        # intervening DB refetch) sees the correct flag on its very next check
    elif instance.status == 'cancelled' and instance.stock_posted and not instance.stock_reversed:
        for line in instance.items.all():
            ledger, _ = StockLedger.objects.get_or_create(
                item=line.item, warehouse=instance.godown, rack=line.rack, bin=line.bin,
                defaults={'quantity': 0},
            )
            StockLedger.objects.filter(pk=ledger.pk).update(quantity=F('quantity') + line.quantity)
        CounterSale.objects.filter(pk=instance.pk).update(stock_reversed=True)
        instance.stock_reversed = True


class CounterSaleReturn(models.Model):
    STATUS = [('draft', 'Draft'), ('submitted', 'Submitted'), ('cancelled', 'Cancelled')]
    return_no = models.CharField(max_length=50, unique=True, editable=False)
    original_sale = models.ForeignKey(CounterSale, on_delete=models.PROTECT)
    return_date = models.DateField()
    reason = models.TextField(blank=True, null=True)
    # Not a lifecycle state -- a separate business flag the counter staff tick
    # once the physical stock has actually been walked back into the godown /
    # the refund handed over. Left as-is; status below is the new real
    # draft/submitted/cancelled lifecycle that actually drives StockLedger.
    stock_return_done = models.BooleanField(default=False)
    amount_refund_done = models.BooleanField(default=False)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    godown        = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name='counter_sale_returns')
    gst_category  = models.CharField(max_length=50, blank=True)
    accounts_from = models.CharField(max_length=200, blank=True)
    accounts_to   = models.CharField(max_length=200, blank=True)
    advance_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    discount        = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True, help_text='Discount %')
    # New real lifecycle -- not exposed on the create form (system-controlled):
    # the create view auto-submits a return right after its items are saved
    # (a return has always behaved as a single-step, already-final document in
    # this app's UI), and a separate cancel action reverses the stock credit.
    status         = models.CharField(max_length=20, choices=STATUS, default='draft')
    stock_posted   = models.BooleanField(default=False)
    stock_reversed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    def save(self, *args, **kwargs):
        if not self.return_no:
            with transaction.atomic():
                last = CounterSaleReturn.objects.select_for_update().order_by('-id').first()
                num = (last.id + 1) if last else 1
                self.return_no = f"CSR-{num:05d}"
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def submit(self, user=None):
        # No stock-quantity safety check here -- a return only ever adds
        # stock back. godown IS required though: the stock-reversal
        # post_save signal below silently no-ops without one, so allowing
        # submission without a godown would mark the return "submitted"
        # while the returned stock is never actually credited to any
        # warehouse -- silently lost from the ledger.
        if self.status != 'draft':
            raise ValueError('Only a Draft return can be submitted.')
        if not self.godown_id:
            raise ValueError('Godown is required to submit a return -- stock cannot be credited back without one.')
        self.status = 'submitted'
        self.save()

    def cancel(self, user=None):
        if self.status != 'submitted':
            raise ValueError('Only a Submitted return can be cancelled.')
        self.status = 'cancelled'
        self.save()

    def __str__(self):
        return self.return_no

    class Meta:
        ordering = ['-return_date']


class CounterSaleReturnItem(models.Model):
    sale_return = models.ForeignKey(CounterSaleReturn, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(SparesItem, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=3, help_text="Original sale quantity -- matches the reference's own qty field")
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    issue_status          = models.BooleanField(default=False)
    delivery_balance_qty  = models.DecimalField(max_digits=10, decimal_places=3, default=0, blank=True)
    stock_qty             = models.DecimalField(max_digits=10, decimal_places=3, default=0, blank=True)
    return_qty             = models.DecimalField(max_digits=10, decimal_places=3, default=0, blank=True,
                                                  help_text='Quantity actually returned, distinct from the original sale quantity -- '
                                                             "confirmed live as the reference's own separate return_qty field")

    def save(self, *args, **kwargs):
        self.amount = self.quantity * self.rate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sale_return.return_no} | {self.item.item_code}"


@receiver(post_save, sender=CounterSaleReturn)
def on_counter_sale_return_status_changed(sender, instance, **kwargs):
    """A return gives stock back on submit; cancelling a submitted return
    takes it back out. Always uses return_qty (the actual quantity returned)
    directly -- a prior version fell back to the original sale quantity
    whenever return_qty was 0, which incorrectly also fired for a
    genuinely-zero return (e.g. a line kept on the return doc for record-
    keeping but not actually returned), not just legacy pre-field rows.
    Legacy rows were backfilled by migration 0015 so return_qty is now
    always the real, trustworthy value."""
    if not instance.godown_id:
        return  # godown is optional on this model; nothing to post against
    if instance.status == 'submitted' and not instance.stock_posted:
        for line in instance.items.all():
            qty = line.return_qty
            ledger, _ = StockLedger.objects.get_or_create(
                item=line.item, warehouse=instance.godown, rack=None, bin=None,
                defaults={'quantity': 0},
            )
            StockLedger.objects.filter(pk=ledger.pk).update(quantity=F('quantity') + qty)
        CounterSaleReturn.objects.filter(pk=instance.pk).update(stock_posted=True)
        instance.stock_posted = True
    elif instance.status == 'cancelled' and instance.stock_posted and not instance.stock_reversed:
        for line in instance.items.all():
            qty = line.return_qty
            ledger, _ = StockLedger.objects.get_or_create(
                item=line.item, warehouse=instance.godown, rack=None, bin=None,
                defaults={'quantity': 0},
            )
            StockLedger.objects.filter(pk=ledger.pk).update(quantity=F('quantity') - qty)
        CounterSaleReturn.objects.filter(pk=instance.pk).update(stock_reversed=True)
        instance.stock_reversed = True


class SparesIssueAlteration(models.Model):
    JOB_TYPES = [('service', 'Service'), ('repair', 'Repair'), ('warranty', 'Warranty')]
    # Reference-parity fix: this was a plain CharField label (not a real FK),
    # a data-integrity gap flagged during the Phase 2 gap analysis.
    job_card = models.ForeignKey(
        'service.JobCard', on_delete=models.PROTECT, null=True, blank=True,
        related_name='spares_issue_alterations'
    )
    # Phase 3b: the reference's "Used Vehicle Spares Issue" is the same doctype
    # shape reused for used-vehicle job cards -- exactly one of job_card /
    # used_vehicle_job_card must be set (enforced in clean()).
    used_vehicle_job_card = models.ForeignKey(
        'used_vehicles.UsedVehicleJobCard', on_delete=models.PROTECT, null=True, blank=True,
        related_name='spares_issue_alterations'
    )
    mechanic = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='spares_issue_alterations'
    )
    quotation_no = models.CharField(max_length=100, blank=True)
    indivitual = models.BooleanField(default=True, verbose_name='Individual Discount')
    common_discount = models.IntegerField(default=0, blank=True, verbose_name='Common Discount')
    party_name = models.CharField(max_length=200, blank=True)
    godown = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    job_type = models.CharField(max_length=20, choices=JOB_TYPES, default='service')
    date = models.DateField()
    BRAND_CHOICES = [('ss_bikes', 'SS Bikes'), ('euler', 'Euler')]
    brand = models.CharField(max_length=20, choices=BRAND_CHOICES, default='ss_bikes',
                              help_text="Collapses the reference's 'Euler Spares Issue Alteration' "
                                        "into this same model/table, tagged by brand")
    spares_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    labour_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    outwork_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    updated_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    engine_no    = models.CharField(max_length=100, blank=True)
    register_no  = models.CharField(max_length=50, blank=True)
    frame_no     = models.CharField(max_length=100, blank=True)
    model        = models.CharField(max_length=200, blank=True, verbose_name='Vehicle Model')
    vehicle_code = models.CharField(max_length=100, blank=True)
    phone_no     = models.CharField(max_length=20, blank=True)
    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    service_invoice_discount = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    # New real lifecycle -- system-controlled (excluded from the create form,
    # same reasoning as CounterSaleReturn.status): spares issued to a job card
    # leave inventory, so the create view auto-submits (with a stock-safety
    # check) right after the item rows are saved, and a separate cancel action
    # reverses the decrement.
    STATUS = [('draft', 'Draft'), ('submitted', 'Submitted'), ('cancelled', 'Cancelled')]
    status         = models.CharField(max_length=20, choices=STATUS, default='draft')
    stock_posted   = models.BooleanField(default=False)
    stock_reversed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    def clean(self):
        from django.core.exceptions import ValidationError
        if bool(self.job_card_id) == bool(self.used_vehicle_job_card_id):
            raise ValidationError('Set exactly one of Job Card or Used Vehicle Job Card, not both or neither.')

    def check_stock_sufficiency(self):
        """Raise ValueError if issuing any line would drive StockLedger negative."""
        for line in self.items.all():
            available = _stock_on_hand(line.item, self.godown, line.rack, line.bin)
            if available < line.quantity:
                raise ValueError(
                    f"Insufficient stock for {line.item.item_code} at {self.godown}: "
                    f"available {available}, requested {line.quantity}."
                )

    def submit(self, user=None):
        if self.status != 'draft':
            raise ValueError('Only a Draft issue alteration can be submitted.')
        self.check_stock_sufficiency()
        self.status = 'submitted'
        self.save()

    def cancel(self, user=None):
        if self.status != 'submitted':
            raise ValueError('Only a Submitted issue alteration can be cancelled.')
        self.status = 'cancelled'
        self.save()

    @property
    def target_job_card(self):
        return self.job_card or self.used_vehicle_job_card

    def __str__(self):
        return f"SIA-{self.pk:05d} | {self.target_job_card}"

    class Meta:
        ordering = ['-date']


class SparesIssueAlterationItem(models.Model):
    alteration = models.ForeignKey(
        SparesIssueAlteration, on_delete=models.CASCADE, related_name='items'
    )
    item = models.ForeignKey(SparesItem, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    rack = models.ForeignKey(Rack, on_delete=models.SET_NULL, null=True, blank=True)
    bin = models.ForeignKey(Bin, on_delete=models.SET_NULL, null=True, blank=True)
    uom = models.CharField(max_length=20, default='Nos', blank=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sgst = models.DecimalField(max_digits=5, decimal_places=2, default=9, blank=True)
    cgst = models.DecimalField(max_digits=5, decimal_places=2, default=9, blank=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_return_quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0, blank=True)
    tax_rate              = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True)
    ref_quantity          = models.DecimalField(max_digits=10, decimal_places=3, default=0, blank=True)
    stock_balance         = models.DecimalField(max_digits=10, decimal_places=3, default=0, blank=True)
    is_returned            = models.BooleanField(default=False, verbose_name='Returned')

    def save(self, *args, **kwargs):
        amount = self.quantity * self.rate
        net = amount - (amount * self.discount_percent / 100)
        self.total = net + (net * self.sgst / 100) + (net * self.cgst / 100)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"SIA-{self.alteration_id} | {self.item.item_code}"


@receiver(post_save, sender=SparesIssueAlteration)
def on_spares_issue_alteration_status_changed(sender, instance, **kwargs):
    """Spares issued to a job card leave inventory on submit; cancelling a
    submitted issue alteration gives that stock back."""
    if instance.status == 'submitted' and not instance.stock_posted:
        for line in instance.items.all():
            ledger, _ = StockLedger.objects.get_or_create(
                item=line.item, warehouse=instance.godown, rack=line.rack, bin=line.bin,
                defaults={'quantity': 0},
            )
            StockLedger.objects.filter(pk=ledger.pk).update(quantity=F('quantity') - line.quantity)
        SparesIssueAlteration.objects.filter(pk=instance.pk).update(stock_posted=True)
        instance.stock_posted = True
    elif instance.status == 'cancelled' and instance.stock_posted and not instance.stock_reversed:
        for line in instance.items.all():
            ledger, _ = StockLedger.objects.get_or_create(
                item=line.item, warehouse=instance.godown, rack=line.rack, bin=line.bin,
                defaults={'quantity': 0},
            )
            StockLedger.objects.filter(pk=ledger.pk).update(quantity=F('quantity') + line.quantity)
        SparesIssueAlteration.objects.filter(pk=instance.pk).update(stock_reversed=True)
        instance.stock_reversed = True


class SparesIssueAlterationDeletedItem(models.Model):
    """Reference: 'New Spares List' -- tracks spares removed from the issue
    during editing, a genuinely distinct concept from the live items table
    (not a Frappe modeling artifact)."""
    alteration = models.ForeignKey(
        SparesIssueAlteration, on_delete=models.CASCADE, related_name='deleted_items'
    )
    item     = models.ForeignKey(SparesItem, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    rack     = models.ForeignKey(Rack, on_delete=models.SET_NULL, null=True, blank=True)
    bin      = models.ForeignKey(Bin, on_delete=models.SET_NULL, null=True, blank=True)
    rate     = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    uom      = models.CharField(max_length=20, default='Nos', blank=True)

    def __str__(self):
        return f"SIA-{self.alteration_id} (deleted) | {self.item.item_code}"

    class Meta:
        verbose_name_plural = 'Spares Issue Alteration Deleted Items'


# ---------------------------------------------------------------------------
# Phase 7a — Stock Transfer (rack/bin/warehouse-to-warehouse movement with a
# real from/to audit trail; reuses the existing StockLedger model, no new
# stock-tracking model introduced).
# ---------------------------------------------------------------------------

class StockTransfer(DocStatusMixin, models.Model):
    transfer_no    = models.CharField(max_length=50, unique=True, blank=True, editable=False)
    date_and_time  = models.DateTimeField()
    warehouse      = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='stock_transfers', verbose_name='From Warehouse')
    branch         = models.ForeignKey('accounts.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_transfers')
    # Idempotency markers for the post_save movement below -- guards against
    # double-posting across the multiple .save() calls a submit/cancel cycle
    # triggers (the previous version had no guard at all: re-saving a still-
    # SUBMITTED transfer would silently re-apply the same delta again).
    stock_posted   = models.BooleanField(default=False)
    stock_reversed = models.BooleanField(default=False)
    created_at     = models.DateTimeField(auto_now_add=True)
    created_by     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.transfer_no:
            with transaction.atomic():
                last = StockTransfer.objects.select_for_update().order_by('-id').values_list('transfer_no', flat=True).first()
                next_seq = 1
                if last:
                    try:
                        next_seq = int(last.rsplit('-', 1)[-1]) + 1
                    except ValueError:
                        pass
                self.transfer_no = f'STOCK-TRANS-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def submit(self, user):
        # Stock-safety guard, same shape as vas.models' AMCPackage/RSAPackage/
        # ProtectionPlusPackage.submit(): raise before DocStatusMixin flips
        # docstatus (and before the post_save signal below posts the movement).
        for line in self.items.all():
            available = _stock_on_hand(line.item, self.warehouse, line.from_rack, line.from_bin)
            if available < line.quantity:
                raise ValueError(
                    f"Insufficient stock for {line.item.item_code} at {self.warehouse}: "
                    f"available {available}, requested {line.quantity}."
                )
        super().submit(user)

    def __str__(self):
        return self.transfer_no

    class Meta:
        ordering = ['-date_and_time']
        verbose_name_plural = 'Stock Transfers'


class StockTransferItem(models.Model):
    transfer      = models.ForeignKey(StockTransfer, on_delete=models.CASCADE, related_name='items')
    item          = models.ForeignKey(SparesItem, on_delete=models.PROTECT)
    quantity      = models.DecimalField(max_digits=10, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))])
    rate          = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    uom           = models.CharField(max_length=20, default='Nos', blank=True)
    from_rack     = models.ForeignKey(Rack, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    from_bin      = models.ForeignKey(Bin, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    to_warehouse  = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='+')
    to_rack       = models.ForeignKey(Rack, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    to_bin        = models.ForeignKey(Bin, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    def __str__(self):
        return f"{self.transfer.transfer_no} | {self.item.item_code} x {self.quantity}"

    class Meta:
        verbose_name_plural = 'Stock Transfer Items'


@receiver(post_save, sender=StockTransfer)
def on_stock_transfer_submitted(sender, instance, **kwargs):
    if instance.docstatus == StockTransfer.DocStatus.SUBMITTED and not instance.stock_posted:
        for line in instance.items.all():
            from_ledger, _ = StockLedger.objects.get_or_create(
                item=line.item, warehouse=instance.warehouse, rack=line.from_rack, bin=line.from_bin,
                defaults={'quantity': 0},
            )
            StockLedger.objects.filter(pk=from_ledger.pk).update(quantity=F('quantity') - line.quantity)

            to_ledger, _ = StockLedger.objects.get_or_create(
                item=line.item, warehouse=line.to_warehouse, rack=line.to_rack, bin=line.to_bin,
                defaults={'quantity': 0},
            )
            StockLedger.objects.filter(pk=to_ledger.pk).update(quantity=F('quantity') + line.quantity)
        StockTransfer.objects.filter(pk=instance.pk).update(stock_posted=True)
        instance.stock_posted = True
    elif instance.docstatus == StockTransfer.DocStatus.CANCELLED and instance.stock_posted and not instance.stock_reversed:
        for line in instance.items.all():
            from_ledger, _ = StockLedger.objects.get_or_create(
                item=line.item, warehouse=instance.warehouse, rack=line.from_rack, bin=line.from_bin,
                defaults={'quantity': 0},
            )
            StockLedger.objects.filter(pk=from_ledger.pk).update(quantity=F('quantity') + line.quantity)

            to_ledger, _ = StockLedger.objects.get_or_create(
                item=line.item, warehouse=line.to_warehouse, rack=line.to_rack, bin=line.to_bin,
                defaults={'quantity': 0},
            )
            StockLedger.objects.filter(pk=to_ledger.pk).update(quantity=F('quantity') - line.quantity)
        StockTransfer.objects.filter(pk=instance.pk).update(stock_reversed=True)
        instance.stock_reversed = True


# ---------------------------------------------------------------------------
# Phase 7a — Stock Count Update (the literal "Spares Stock Reconciliation"
# feature): physical count vs system stock, correcting StockLedger on submit.
# ---------------------------------------------------------------------------

class StockCountUpdate(DocStatusMixin, models.Model):
    count_no      = models.CharField(max_length=50, unique=True, blank=True, editable=False)
    date_and_time = models.DateField()
    warehouse     = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='stock_count_updates')
    branch        = models.ForeignKey('accounts.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_count_updates')
    # Reversal marker -- on cancel, each line's captured system_qty snapshot
    # (StockCountItem.system_qty, taken at row-creation time) is restored.
    stock_reversed = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)
    created_by    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.count_no:
            with transaction.atomic():
                last = StockCountUpdate.objects.select_for_update().order_by('-id').values_list('count_no', flat=True).first()
                next_seq = 1
                if last:
                    try:
                        next_seq = int(last.rsplit('-', 1)[-1]) + 1
                    except ValueError:
                        pass
                self.count_no = f'STOCK-COUNT-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.count_no

    class Meta:
        ordering = ['-date_and_time']
        verbose_name_plural = 'Stock Count Updates'


class StockCountItem(models.Model):
    count       = models.ForeignKey(StockCountUpdate, on_delete=models.CASCADE, related_name='items')
    item        = models.ForeignKey(SparesItem, on_delete=models.PROTECT)
    rack        = models.ForeignKey(Rack, on_delete=models.SET_NULL, null=True, blank=True)
    bin         = models.ForeignKey(Bin, on_delete=models.SET_NULL, null=True, blank=True)
    rate        = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    system_qty  = models.DecimalField(max_digits=10, decimal_places=3, default=0, blank=True, help_text='Auto-filled from current StockLedger at save time')
    counted_qty = models.DecimalField(max_digits=10, decimal_places=3, verbose_name='Update Quantity', validators=[MinValueValidator(0)])

    def save(self, *args, **kwargs):
        if not self.pk:
            ledger = StockLedger.objects.filter(
                item=self.item, warehouse=self.count.warehouse, rack=self.rack, bin=self.bin
            ).first()
            self.system_qty = ledger.quantity if ledger else 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.count.count_no} | {self.item.item_code} — system {self.system_qty}, counted {self.counted_qty}"

    class Meta:
        verbose_name_plural = 'Stock Count Items'


@receiver(post_save, sender=StockCountUpdate)
def on_stock_count_submitted(sender, instance, **kwargs):
    if instance.docstatus == StockCountUpdate.DocStatus.SUBMITTED:
        # Naturally idempotent already: once quantity == counted_qty, re-saving
        # while still SUBMITTED is a no-op (no separate posted marker needed).
        for line in instance.items.all():
            ledger, _ = StockLedger.objects.get_or_create(
                item=line.item, warehouse=instance.warehouse, rack=line.rack, bin=line.bin,
                defaults={'quantity': line.counted_qty},
            )
            if ledger.quantity != line.counted_qty:
                StockLedger.objects.filter(pk=ledger.pk).update(quantity=line.counted_qty)
    elif instance.docstatus == StockCountUpdate.DocStatus.CANCELLED and not instance.stock_reversed:
        # Restore each line's pre-count snapshot (system_qty), same idea as a
        # transfer's reversal -- undo exactly what this document changed.
        for line in instance.items.all():
            ledger, _ = StockLedger.objects.get_or_create(
                item=line.item, warehouse=instance.warehouse, rack=line.rack, bin=line.bin,
                defaults={'quantity': line.system_qty},
            )
            if ledger.quantity != line.system_qty:
                StockLedger.objects.filter(pk=ledger.pk).update(quantity=line.system_qty)
        StockCountUpdate.objects.filter(pk=instance.pk).update(stock_reversed=True)
        instance.stock_reversed = True


# ---------------------------------------------------------------------------
# Phase 7a — Request Supplier Quote: the RFQ-to-multiple-suppliers step that
# precedes SupplierQuote (reference: SupplierQuote.request_quotation_id).
# ---------------------------------------------------------------------------

class RequestSupplierQuote(DocStatusMixin, models.Model):
    rsq_no     = models.CharField(max_length=50, unique=True, blank=True, editable=False)
    suppliers  = models.ManyToManyField(Supplier, related_name='requested_quotes', blank=True)
    date       = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.rsq_no:
            with transaction.atomic():
                last = RequestSupplierQuote.objects.select_for_update().order_by('-id').values_list('rsq_no', flat=True).first()
                next_seq = 1
                if last:
                    try:
                        next_seq = int(last.rsplit('-', 1)[-1]) + 1
                    except ValueError:
                        pass
                self.rsq_no = f'RSQ-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.rsq_no

    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'Request Supplier Quotes'


class RequestSupplierQuoteItem(models.Model):
    request  = models.ForeignKey(RequestSupplierQuote, on_delete=models.CASCADE, related_name='items')
    spare    = models.ForeignKey(SparesItem, on_delete=models.PROTECT, verbose_name='Spare Name')
    qty      = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    uom      = models.CharField(max_length=20, default='Nos', blank=True)

    def __str__(self):
        return f"{self.request.rsq_no} | {self.spare.item_code} x {self.qty}"

    class Meta:
        verbose_name_plural = 'Request Supplier Quote Items'


# ---------------------------------------------------------------------------
# Phase 7b — Spares Purchase Estimation Master (pre-purchase costing document
# referenced by PurchaseOrder.estimation).
# ---------------------------------------------------------------------------

class SparesPurchaseEstimationMaster(DocStatusMixin, models.Model):
    estimation_no        = models.CharField(max_length=50, unique=True, blank=True, editable=False)
    date                 = models.DateField()
    customer_name        = models.CharField(max_length=200, blank=True)
    chasis_no            = models.CharField(max_length=100, blank=True, verbose_name='Chasis No',
                                             help_text='Reference: Vehicle Chasis Number Master link; no Django master exists, kept as a snapshot label')
    insurance_name       = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='spares_estimations')
    vehicle_code         = models.CharField(max_length=100, blank=True)
    vehicle_name         = models.CharField(max_length=200, blank=True)
    estimation_total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    balance_delivery_qty    = models.DecimalField(max_digits=10, decimal_places=3, default=0, blank=True)
    labor_total_amount      = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    total_amount            = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    created_at           = models.DateTimeField(auto_now_add=True)
    created_by           = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.estimation_no:
            with transaction.atomic():
                last = SparesPurchaseEstimationMaster.objects.select_for_update().order_by('-id').values_list('estimation_no', flat=True).first()
                next_seq = 1
                if last:
                    try:
                        next_seq = int(last.rsplit('-', 1)[-1]) + 1
                    except ValueError:
                        pass
                self.estimation_no = f'SPEM-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.estimation_no

    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'Spares Purchase Estimation Masters'


class SparesPurchaseEstimationItem(models.Model):
    estimation          = models.ForeignKey(SparesPurchaseEstimationMaster, on_delete=models.CASCADE, related_name='items')
    item                = models.ForeignKey(SparesItem, on_delete=models.PROTECT)
    qty                 = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    amount              = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    uom                 = models.CharField(max_length=20, default='Nos', blank=True)
    confirm             = models.BooleanField(default=False, verbose_name='Confirm To Order')
    gst                 = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True)
    total               = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    delivery_balance_qty = models.DecimalField(max_digits=10, decimal_places=3, default=0, blank=True)

    def save(self, *args, **kwargs):
        self.total = self.amount + (self.amount * self.gst / 100)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.estimation.estimation_no} | {self.item.item_code}"

    class Meta:
        verbose_name_plural = 'Spares Purchase Estimation Items'


class SparesPurchaseEstimationLabor(models.Model):
    estimation = models.ForeignKey(SparesPurchaseEstimationMaster, on_delete=models.CASCADE, related_name='labor_details')
    date       = models.DateField()
    labor_name = models.ForeignKey('masters.LabourWork', on_delete=models.PROTECT)
    quantity   = models.DecimalField(max_digits=10, decimal_places=2, default=1, blank=True)
    amount     = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sgst       = models.DecimalField(max_digits=5, decimal_places=2, default=9, blank=True)
    cgst       = models.DecimalField(max_digits=5, decimal_places=2, default=9, blank=True)
    total      = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    def save(self, *args, **kwargs):
        self.total = self.amount + (self.amount * self.sgst / 100) + (self.amount * self.cgst / 100)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.estimation.estimation_no} | {self.labor_name}"

    class Meta:
        verbose_name_plural = 'Spares Purchase Estimation Labor Charges'


# ---------------------------------------------------------------------------
# Phase 7c — Service Spares Issue Return: the return side of spares issued to
# a job card (SparesIssueAlteration is the issue side).
# ---------------------------------------------------------------------------

class ServiceSparesIssueReturn(DocStatusMixin, models.Model):
    return_no          = models.CharField(max_length=50, unique=True, blank=True, editable=False)
    spares_issue       = models.ForeignKey(SparesIssueAlteration, on_delete=models.PROTECT, related_name='returns')
    job_card           = models.ForeignKey(
        'service.JobCard', on_delete=models.SET_NULL, null=True, blank=True, related_name='spares_issue_returns',
        help_text='New-vehicle snapshot link; for a used-vehicle issue, derive via spares_issue.target_job_card instead'
    )
    phone_number       = models.CharField(max_length=20, blank=True)
    frame_no           = models.CharField(max_length=100, blank=True)
    register_no        = models.CharField(max_length=50, blank=True)
    party_name         = models.CharField(max_length=200, blank=True)
    spares_issue_date  = models.DateField(null=True, blank=True)
    godown             = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name='service_spares_issue_returns')
    total_qty          = models.DecimalField(max_digits=10, decimal_places=3, default=0, blank=True)
    total_amount       = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    stock_return_done  = models.BooleanField(default=False)
    created_at         = models.DateTimeField(auto_now_add=True)
    created_by         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.return_no:
            with transaction.atomic():
                last = ServiceSparesIssueReturn.objects.select_for_update().order_by('-id').values_list('return_no', flat=True).first()
                next_seq = 1
                if last:
                    try:
                        next_seq = int(last.rsplit('-', 1)[-1]) + 1
                    except ValueError:
                        pass
                self.return_no = f'SSI-Return-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.return_no

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Service Spares Issue Returns'


class ServiceSparesIssueReturnItem(models.Model):
    issue_return          = models.ForeignKey(ServiceSparesIssueReturn, on_delete=models.CASCADE, related_name='items')
    item                   = models.ForeignKey(SparesItem, on_delete=models.PROTECT)
    rack                   = models.ForeignKey(Rack, on_delete=models.SET_NULL, null=True, blank=True)
    bin                    = models.ForeignKey(Bin, on_delete=models.SET_NULL, null=True, blank=True)
    rate                   = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    uom                    = models.CharField(max_length=20, default='Nos', blank=True)
    last_return_quantity  = models.DecimalField(max_digits=10, decimal_places=3, default=0, blank=True)
    return_qty             = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    gst                    = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True)
    tax_rate               = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True)
    total                  = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    sgst                   = models.DecimalField(max_digits=5, decimal_places=2, default=9, blank=True)
    cgst                   = models.DecimalField(max_digits=5, decimal_places=2, default=9, blank=True)
    discount_percentage    = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True)
    is_returned            = models.BooleanField(default=True, verbose_name='Returned')
    ref_quantity           = models.DecimalField(max_digits=10, decimal_places=3, default=0, blank=True)
    stock_balance          = models.DecimalField(max_digits=10, decimal_places=3, default=0, blank=True)

    def save(self, *args, **kwargs):
        amount = self.return_qty * self.rate
        discount = amount * self.discount_percentage / 100
        net = amount - discount
        self.total = net + (net * self.sgst / 100) + (net * self.cgst / 100)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.issue_return.return_no} | {self.item.item_code}"

    class Meta:
        verbose_name_plural = 'Service Spares Issue Return Items'


# ---------------------------------------------------------------------------
# Phase 7d — Vehicle Spares Master (per-spare profit/rate master), Spares MRP
# Prices (bulk price-revision batch), settings singles, Service Spares
# Warranty (supplier warranty-claim tracking), and the Euler-brand collapse
# (brand field added to SparesIssueAlteration above).
# ---------------------------------------------------------------------------

class VehicleSparesMaster(models.Model):
    spare              = models.OneToOneField(SparesItem, on_delete=models.CASCADE, related_name='vehicle_spares_master')
    profit_percentage  = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True)
    purchase_rate      = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    mrp_rate           = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    total              = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    def save(self, *args, **kwargs):
        self.total = self.purchase_rate + (self.purchase_rate * self.profit_percentage / 100)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.spare.item_code} | Profit {self.profit_percentage}%"

    class Meta:
        ordering = ['spare__item_name']
        verbose_name_plural = 'Vehicle Spares Masters'


class SparesMRPPriceRevision(DocStatusMixin, models.Model):
    PRICE_LISTS = [('standard_selling', 'Standard Selling'), ('standard_buying', 'Standard Buying')]
    revision_no  = models.CharField(max_length=50, unique=True, blank=True, editable=False)
    date         = models.DateField()
    price_list   = models.CharField(max_length=20, choices=PRICE_LISTS, default='standard_selling')
    created_at   = models.DateTimeField(auto_now_add=True)
    created_by   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.revision_no:
            with transaction.atomic():
                last = SparesMRPPriceRevision.objects.select_for_update().order_by('-id').values_list('revision_no', flat=True).first()
                next_seq = 1
                if last:
                    try:
                        next_seq = int(last.rsplit('-', 1)[-1]) + 1
                    except ValueError:
                        pass
                self.revision_no = f'SPA-MRP-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.revision_no

    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'Spares MRP Price Revisions'


class SparesMRPPriceRevisionItem(models.Model):
    revision        = models.ForeignKey(SparesMRPPriceRevision, on_delete=models.CASCADE, related_name='items')
    item            = models.ForeignKey(SparesItem, on_delete=models.PROTECT)
    old_price       = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True,
                                           help_text='Snapshot of the current price at save time')
    current_price   = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    updated_price   = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        if not self.pk:
            if self.revision.price_list == 'standard_buying':
                self.old_price = self.item.valuation_rate
            else:
                self.old_price = self.item.mrp
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.revision.revision_no} | {self.item.item_code}"

    class Meta:
        verbose_name_plural = 'Spares MRP Price Revision Items'


@receiver(post_save, sender=SparesMRPPriceRevision)
def on_spares_mrp_price_revision_submitted(sender, instance, **kwargs):
    if instance.docstatus != SparesMRPPriceRevision.DocStatus.SUBMITTED:
        return
    for line in instance.items.all():
        if instance.price_list == 'standard_buying':
            SparesItem.objects.filter(pk=line.item_id).update(valuation_rate=line.updated_price)
        else:
            SparesItem.objects.filter(pk=line.item_id).update(mrp=line.updated_price)


class SparesProfitPercentageSettings(models.Model):
    """Frappe Single doctype 'Spares Profit Percentage' -- singleton via pk=1,
    same pattern as accounts.CompanySettings.get_instance()."""
    with_mrp     = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True)
    without_mrp  = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True)

    class Meta:
        verbose_name        = 'Spares Profit Percentage'
        verbose_name_plural = 'Spares Profit Percentage'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'Spares Profit Percentage'


class SparesPurchaseQtyDaysSettings(models.Model):
    """Frappe Single doctype 'Spares Purchase order Used or Order Qty Days' --
    singleton via pk=1, same pattern as accounts.CompanySettings.get_instance()."""
    used_or_order_qty_days = models.IntegerField(default=0, blank=True)

    class Meta:
        verbose_name        = 'Spares Purchase Order Qty Days Settings'
        verbose_name_plural = 'Spares Purchase Order Qty Days Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'Spares Purchase Order Qty Days Settings'


class ServiceSparesWarranty(DocStatusMixin, models.Model):
    """Supplier warranty-claim tracking for spares -- distinct from the
    customer-facing VAS 'Protection Plus' warranty (vas.ProtectionPlusPackage)."""
    STATUS_CHOICES = [
        ('open', 'Open'), ('claimed', 'Claimed'), ('dispatched', 'Dispatched'),
        ('received', 'Received'), ('closed', 'Closed'),
    ]
    BRAND_CHOICES = [('ss_bikes', 'SS Bikes'), ('euler', 'Euler')]
    warranty_no             = models.CharField(max_length=50, unique=True, blank=True, editable=False)
    vehicle_number          = models.CharField(max_length=50, blank=True)
    supplier                = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='service_spares_warranties')
    claim_no                = models.CharField(max_length=100, blank=True)
    claim_date               = models.DateField(null=True, blank=True)
    parts_dispatch_date      = models.DateField(null=True, blank=True)
    claim_received_date      = models.DateField(null=True, blank=True)
    invoice_no               = models.CharField(max_length=100, blank=True)
    invoice_date             = models.DateField(null=True, blank=True)
    chasis_no                = models.CharField(max_length=100, blank=True, verbose_name='Chasis No')
    status                   = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    branch                   = models.ForeignKey('accounts.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='service_spares_warranties')
    vehicle_name             = models.CharField(max_length=200, blank=True)
    history                  = models.TextField(blank=True)
    ndp_amount               = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    dispatch_on              = models.DateField(null=True, blank=True)
    dock_no                  = models.CharField(max_length=50, blank=True)
    claim_register_in_pymidol   = models.BooleanField(default=False)
    generate_invoice_in_pymidol = models.BooleanField(default=False)
    courier_parts             = models.BooleanField(default=False)
    courier_invoice_bill_on   = models.DateField(null=True, blank=True)
    claim_for                 = models.CharField(max_length=200, blank=True)
    payment_received_date     = models.DateField(null=True, blank=True)
    brand                     = models.CharField(max_length=20, choices=BRAND_CHOICES, default='ss_bikes',
                                                  help_text="Collapses the reference's 'Euler Service Spares Warranty' "
                                                            "into this same model/table, tagged by brand")
    created_at                = models.DateTimeField(auto_now_add=True)
    created_by                = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.warranty_no:
            with transaction.atomic():
                last = ServiceSparesWarranty.objects.select_for_update().order_by('-id').values_list('warranty_no', flat=True).first()
                next_seq = 1
                if last:
                    try:
                        next_seq = int(last.rsplit('-', 1)[-1]) + 1
                    except ValueError:
                        pass
                self.warranty_no = f'SERV-SPAR-WARTY-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.warranty_no

    class Meta:
        ordering = ['-claim_date']
        verbose_name_plural = 'Service Spares Warranties'


class ServiceSparesWarrantyItem(models.Model):
    warranty              = models.ForeignKey(ServiceSparesWarranty, on_delete=models.CASCADE, related_name='items')
    item                  = models.ForeignKey(SparesItem, on_delete=models.PROTECT)
    claim_warranty_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    cgst                  = models.DecimalField(max_digits=5, decimal_places=2, default=9, blank=True)
    sgst                  = models.DecimalField(max_digits=5, decimal_places=2, default=9, blank=True)
    total                 = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    ndp                   = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)

    def save(self, *args, **kwargs):
        self.total = self.claim_warranty_amount + (self.claim_warranty_amount * self.sgst / 100) + (self.claim_warranty_amount * self.cgst / 100)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.warranty.warranty_no} | {self.item.item_code}"

    class Meta:
        verbose_name_plural = 'Service Spares Warranty Items'
