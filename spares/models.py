from django.conf import settings
from django.db import models


class SparesCategory(models.Model):
    category_name = models.CharField(max_length=100, unique=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category_name']
        verbose_name_plural = 'Spares Categories'

    def __str__(self):
        return self.category_name


class SparePart(models.Model):
    category       = models.ForeignKey(
        SparesCategory,
        on_delete=models.PROTECT,
        related_name='spare_parts'
    )
    part_name      = models.CharField(max_length=255)
    part_number    = models.CharField(max_length=100, unique=True, blank=True, null=True)
    mrp            = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock_quantity = models.IntegerField(default=0)
    rack_location  = models.CharField(max_length=100, blank=True, null=True)
    bin_location   = models.CharField(max_length=100, blank=True, null=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['part_name']
        verbose_name_plural = 'Spare Parts'

    def __str__(self):
        return f"{self.part_name} ({self.part_number or 'No Part No.'})"


class Supplier(models.Model):
    supplier_name = models.CharField(max_length=255)
    phone         = models.CharField(max_length=15, blank=True, null=True)
    email         = models.EmailField(blank=True, null=True)
    address       = models.TextField(blank=True, null=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['supplier_name']
        verbose_name_plural = 'Suppliers'

    def __str__(self):
        return self.supplier_name


class PurchaseOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT     = 'draft',     'Draft'
        SENT      = 'sent',      'Sent'
        RECEIVED  = 'received',  'Received'
        CANCELLED = 'cancelled', 'Cancelled'

    supplier     = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='purchase_orders'
    )
    order_date   = models.DateField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status       = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-order_date']
        verbose_name_plural = 'Purchase Orders'

    def __str__(self):
        return f"PO-{self.pk} | {self.supplier} — Rs.{self.total_amount}"


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='items'
    )
    spare_part     = models.ForeignKey(
        SparePart,
        on_delete=models.PROTECT,
        related_name='purchase_order_items'
    )
    quantity       = models.IntegerField()
    price          = models.DecimalField(max_digits=10, decimal_places=2)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Purchase Order Items'

    def __str__(self):
        return f"{self.spare_part} x{self.quantity} (PO-{self.purchase_order_id})"

    @property
    def line_total(self):
        return self.quantity * self.price


class CounterSale(models.Model):
    customer       = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='counter_sales'
    )
    branch         = models.ForeignKey(
        'accounts.Branch',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='counter_sales'
    )
    invoice_number = models.CharField(max_length=100, unique=True)
    total_amount   = models.DecimalField(max_digits=10, decimal_places=2)
    sale_date      = models.DateField(auto_now_add=True)
    created_by     = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='counter_sales_created'
    )
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sale_date']
        verbose_name_plural = 'Counter Sales'

    def __str__(self):
        return f"{self.invoice_number} — Rs.{self.total_amount}"


class CounterSaleItem(models.Model):
    counter_sale = models.ForeignKey(
        CounterSale,
        on_delete=models.CASCADE,
        related_name='items'
    )
    spare_part   = models.ForeignKey(
        SparePart,
        on_delete=models.PROTECT,
        related_name='counter_sale_items'
    )
    quantity     = models.IntegerField()
    unit_price   = models.DecimalField(max_digits=10, decimal_places=2)
    total_price  = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name_plural = 'Counter Sale Items'

    def __str__(self):
        return f"{self.spare_part} x{self.quantity} ({self.counter_sale.invoice_number})"

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class SparesIssue(models.Model):
    """
    Tracks spare parts issued from stock to a job card.
    Enables stock deduction and per-job-card cost calculation.
    """
    job_card          = models.ForeignKey(
        'service.JobCard',
        on_delete=models.CASCADE,
        related_name='spares_issues'
    )
    spare_part        = models.ForeignKey(
        SparePart,
        on_delete=models.PROTECT,
        related_name='issues'
    )
    quantity_issued   = models.IntegerField()
    quantity_returned = models.IntegerField(default=0)
    unit_price        = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_price       = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    issued_by         = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='spares_issued'
    )
    issued_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-issued_at']
        verbose_name_plural = 'Spares Issues'

    def __str__(self):
        return f"{self.spare_part} x{self.quantity_issued} → JC-{self.job_card_id}"

    def save(self, *args, **kwargs):
        if self.unit_price is not None:
            self.total_price = self.quantity_issued * self.unit_price
        super().save(*args, **kwargs)

    @property
    def net_quantity(self):
        return self.quantity_issued - self.quantity_returned
