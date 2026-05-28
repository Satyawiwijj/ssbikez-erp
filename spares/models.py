from django.db import models
from django.conf import settings
from masters.models import SparesCategory, Supplier, Warehouse, Rack, Bin


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
            last = SparesItem.objects.order_by('-id').first()
            num = (last.id + 1) if last else 1
            self.item_code = f"SP-{num:05d}"
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
    date = models.DateField()
    valid_till = models.DateField(null=True, blank=True)
    quotation_number = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='draft')
    is_reverse_charge = models.BooleanField(default=False)
    total_quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    additional_discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    additional_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    terms_and_conditions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    def save(self, *args, **kwargs):
        if not self.quote_no:
            last = SupplierQuote.objects.order_by('-id').first()
            num = (last.id + 1) if last else 1
            self.quote_no = f"SQ-{num:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.quote_no

    class Meta:
        ordering = ['-date']


class SupplierQuoteItem(models.Model):
    quote = models.ForeignKey(SupplierQuote, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(SparesItem, on_delete=models.PROTECT)
    required_date = models.DateField(null=True, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    uom = models.CharField(max_length=20, default='Nos')
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
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
        if not self.po_no:
            last = PurchaseOrder.objects.order_by('-id').first()
            num = (last.id + 1) if last else 1
            self.po_no = f"PO-{num:05d}"
        if self.supplier and not self.supplier_name:
            self.supplier_name = self.supplier.supplier_name
        super().save(*args, **kwargs)

    def __str__(self):
        return self.po_no

    class Meta:
        ordering = ['-date']


class PurchaseOrderItem(models.Model):
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(SparesItem, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    required_by = models.DateField(null=True, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    uom = models.CharField(max_length=20, default='Nos')
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    received_qty = models.DecimalField(max_digits=10, decimal_places=3, default=0)

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
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    def save(self, *args, **kwargs):
        if not self.invoice_no:
            last = PurchaseInvoice.objects.order_by('-id').first()
            num = (last.id + 1) if last else 1
            self.invoice_no = f"PI-{num:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_no

    class Meta:
        ordering = ['-date']


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
    sale_no = models.CharField(max_length=50, unique=True, editable=False)
    customer = models.CharField(max_length=200)
    mobile = models.CharField(max_length=20)
    gst_category = models.CharField(max_length=50, blank=True)
    godown = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    date = models.DateField()
    is_warranty = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS, default='draft')
    total_qty = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, default='Unpaid')
    pay_type = models.CharField(max_length=20, choices=PAY_TYPES, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    def save(self, *args, **kwargs):
        if not self.sale_no:
            last = CounterSale.objects.order_by('-id').first()
            num = (last.id + 1) if last else 1
            self.sale_no = f"CS-{num:05d}"
        super().save(*args, **kwargs)

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

    def save(self, *args, **kwargs):
        self.amount = self.quantity * self.rate
        self.total = self.amount + (self.amount * self.gst_percent / 100)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sale.sale_no} | {self.item.item_code}"


class CounterSaleReturn(models.Model):
    return_no = models.CharField(max_length=50, unique=True, editable=False)
    original_sale = models.ForeignKey(CounterSale, on_delete=models.PROTECT)
    return_date = models.DateField()
    reason = models.TextField(blank=True, null=True)
    stock_return_done = models.BooleanField(default=False)
    amount_refund_done = models.BooleanField(default=False)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    def save(self, *args, **kwargs):
        if not self.return_no:
            last = CounterSaleReturn.objects.order_by('-id').first()
            num = (last.id + 1) if last else 1
            self.return_no = f"CSR-{num:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.return_no

    class Meta:
        ordering = ['-return_date']


class CounterSaleReturnItem(models.Model):
    sale_return = models.ForeignKey(CounterSaleReturn, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(SparesItem, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.amount = self.quantity * self.rate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sale_return.return_no} | {self.item.item_code}"


class SparesIssueAlteration(models.Model):
    JOB_TYPES = [('service', 'Service'), ('repair', 'Repair'), ('warranty', 'Warranty')]
    job_card = models.CharField(max_length=50)
    godown = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    job_type = models.CharField(max_length=20, choices=JOB_TYPES, default='service')
    date = models.DateField()
    spares_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    labour_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    outwork_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return f"SIA-{self.pk:05d} | {self.job_card}"

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
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        amount = self.quantity * self.rate
        self.total = amount - (amount * self.discount_percent / 100)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"SIA-{self.alteration_id} | {self.item.item_code}"
