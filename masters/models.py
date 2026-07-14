from django.db import models, transaction
from django.conf import settings

from accounts.models import DocStatusMixin


class SparesCategory(models.Model):
    name = models.CharField(max_length=200, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Spares Categories'
        ordering = ['name']


class Supplier(models.Model):
    class SupplierType(models.TextChoices):
        COMPANY    = 'company',    'Company'
        INDIVIDUAL = 'individual', 'Individual'
        PARTNERSHIP = 'partnership', 'Partnership'

    supplier_name = models.CharField(max_length=200)
    supplier_group = models.CharField(max_length=100, blank=True, help_text='Supplier group e.g. OEM, Local, Distributor')
    country = models.CharField(max_length=100, default='India')
    supplier_type = models.CharField(max_length=20, choices=SupplierType.choices, default=SupplierType.COMPANY)
    is_transporter = models.BooleanField(default=False, verbose_name='Is Transporter')
    is_prepaid_supplier = models.BooleanField(default=False, verbose_name='Is Prepaid Supplier')
    supplier_limit_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                                  verbose_name='Supplier Limit Amount')
    contact_person = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    gstin = models.CharField(max_length=20, blank=True)
    gst_category = models.CharField(max_length=50, blank=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    place_of_supply = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return self.supplier_name

    class Meta:
        ordering = ['supplier_name']


class Warehouse(models.Model):
    WAREHOUSE_TYPES = [
        ('transit', 'Goods In Transit'),
        ('finished', 'Finished Goods'),
        ('wip', 'Work In Progress'),
        ('stores', 'Stores'),
        ('all', 'All Warehouses'),
        ('rejected', 'Rejected'),
    ]
    name = models.CharField(max_length=200)
    warehouse_type = models.CharField(max_length=20, choices=WAREHOUSE_TYPES, blank=True)
    is_group = models.BooleanField(default=False)
    parent_warehouse = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children'
    )
    is_rejected = models.BooleanField(default=False)
    phone = models.CharField(max_length=20, blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pin = models.CharField(max_length=10, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Rack(models.Model):
    name = models.CharField(max_length=100)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='racks')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.warehouse.name} / {self.name}"

    class Meta:
        ordering = ['warehouse', 'name']


class Bin(models.Model):
    name = models.CharField(max_length=100)
    rack = models.ForeignKey(Rack, on_delete=models.CASCADE, related_name='bins')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.rack} / {self.name}"

    class Meta:
        ordering = ['rack', 'name']


class FinanceCompany(models.Model):
    """Lender/finance-company master referenced by Sales Order (Sales Finance)."""
    name = models.CharField(max_length=200, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Finance Companies'


class BunkName(models.Model):
    """Fuel bunk/station master referenced by Vehicle Delivery's petrol-offer section."""
    name = models.CharField(max_length=200, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Bunk Names'


class LabourWork(models.Model):
    """Labour-work catalog (reference: 'New Vehicle Labour Work') referenced by
    Labor Charges Alteration's per-line labor_name field."""
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    standard_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} — {self.name}"

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Labour Work Catalog'


class JobcardComplaintMaster(models.Model):
    """Customer-complaint catalog referenced by Job Card Complaint Details (both
    New and Used Vehicle variants share this reference doctype)."""
    name_text = models.CharField(max_length=200, unique=True, verbose_name='Complaint')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name_text

    class Meta:
        ordering = ['name_text']
        verbose_name_plural = 'Jobcard Complaint Master'


class JobcardSupervisorObservationMaster(models.Model):
    """Supervisor-observation catalog referenced by Job Card Supervisor Observation
    (both New and Used Vehicle variants share this reference doctype)."""
    name_text = models.CharField(max_length=200, unique=True, verbose_name='Observation')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name_text

    class Meta:
        ordering = ['name_text']
        verbose_name_plural = 'Jobcard Supervisor Observation Master'


# ---------------------------------------------------------------------------
# Phase 8a — Order Form Settings (generator UI) & Order Form Series (the real
# naming-series ledger every reference sales/RTO/fuel doctype links to).
# ---------------------------------------------------------------------------

class OrderFormSettings(models.Model):
    """Frappe Single doctype 'Order Form Settings' -- singleton via pk=1, same
    pattern as accounts.CompanySettings.get_instance(). A generator UI, not a
    data table: configuring it and clicking Generate batch-creates
    OrderFormSeries rows."""
    new_vehicle  = models.BooleanField(default=False)
    used_vehicle = models.BooleanField(default=False)
    branch       = models.ForeignKey('accounts.Branch', on_delete=models.SET_NULL, null=True, blank=True)
    prefix       = models.CharField(max_length=20, blank=True)
    digits       = models.IntegerField(default=5, blank=True)
    from_no      = models.IntegerField(default=0, blank=True)
    count        = models.IntegerField(default=0, blank=True)
    to_no        = models.IntegerField(default=0, blank=True, help_text='Computed: from_no + count - 1')

    class Meta:
        verbose_name        = 'Order Form Settings'
        verbose_name_plural = 'Order Form Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'Order Form Settings'


class OrderFormSeries(DocStatusMixin, models.Model):
    """Reference: 'Order Form Series' -- the real naming-series ledger every
    Sales Form/GST Master/Fuel/Sales Enquiries doctype links to by Link field.
    Rows are machine-generated by OrderFormSettings' Generate action, not
    hand-entered."""
    SERIES_TYPES = [('new_vehicle', 'New Vehicle'), ('used_vehicle', 'Used Vehicle')]
    STATUS_CHOICES = [('', '—'), ('used', 'Used'), ('unused', 'Unused')]

    order_form_no        = models.CharField(max_length=50, unique=True)
    order_form_count     = models.IntegerField(default=0)
    branch                = models.ForeignKey('accounts.Branch', on_delete=models.PROTECT, related_name='order_form_series')
    status                = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True)
    allotment              = models.CharField(max_length=100, blank=True)
    sales_order_id         = models.CharField(max_length=100, blank=True)
    sales_order_status     = models.CharField(max_length=100, blank=True)
    rto_status             = models.CharField(max_length=50, default='available', blank=True)
    f20_status              = models.CharField(max_length=50, default='not done', blank=True)
    ex_change_vehicle_status = models.IntegerField(default=0, blank=True)
    series_type              = models.CharField(max_length=20, choices=SERIES_TYPES, blank=True)
    created_at               = models.DateTimeField(auto_now_add=True)
    created_by               = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.order_form_no

    class Meta:
        ordering = ['-order_form_no']
        verbose_name_plural = 'Order Form Series'


# ---------------------------------------------------------------------------
# Phase 8b — Vehicle Pricing Masters: Model and Price, Customer Price,
# Dealer Price List. All non-submittable (reference: is_submittable:0).
# ---------------------------------------------------------------------------

class ModelAndPrice(models.Model):
    """Reference: 'Model and Price' -- per-color-variant detailed pricing
    breakdown for a vehicle model. Distinct from customers.BikeModel's own
    simple ex_showroom_price/dealer_cost_price fields (which serve the sales
    flow elsewhere) -- the reference keeps these as separate doctypes."""
    price_no        = models.CharField(max_length=50, unique=True, blank=True, editable=False)
    model_code      = models.ForeignKey('customers.BikeModel', on_delete=models.PROTECT, related_name='price_records', verbose_name='Vehicle Code')
    model_name      = models.CharField(max_length=200, blank=True, verbose_name='Vehicle Name')
    sub_group       = models.CharField(max_length=100, blank=True)
    color           = models.CharField(max_length=50, blank=True)
    color_code      = models.CharField(max_length=20, blank=True)
    percentage      = models.IntegerField(default=0, blank=True)
    ex_show_room    = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, verbose_name='Ex Showroom')
    pdi             = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, verbose_name='PDI')
    rsa             = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, verbose_name='RSA')
    insurance       = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    updated_insurance_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, verbose_name='Updated Insurance Rate')
    amc             = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, verbose_name='AMC')
    warranty        = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, verbose_name='Protection Plus')
    charge_1        = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, verbose_name='Charge 1')
    charge_2        = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, verbose_name='Charge 2')
    charge_3        = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, verbose_name='Charge 3')
    created_at      = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.model_code_id and not self.model_name:
            self.model_name = str(self.model_code)
        if not self.price_no:
            with transaction.atomic():
                last = ModelAndPrice.objects.select_for_update().order_by('-id').values_list('price_no', flat=True).first()
                next_seq = 1
                if last:
                    try:
                        next_seq = int(last.rsplit('-', 1)[-1]) + 1
                    except ValueError:
                        pass
                self.price_no = f'MODEL-PRICE-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.price_no} | {self.model_name}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Model and Price'


class CustomerPrice(models.Model):
    """Reference: 'Customer Price' (workspace label 'Customer Price List')."""
    id_name     = models.CharField(max_length=50, unique=True, blank=True, editable=False)
    branch      = models.ForeignKey('accounts.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_prices')
    disable     = models.BooleanField(default=False)
    model_code  = models.ForeignKey('customers.BikeModel', on_delete=models.PROTECT, related_name='customer_prices', verbose_name='Vehicle Code')
    model_name  = models.CharField(max_length=200, blank=True, verbose_name='Vehicle Name')
    sub_group   = models.CharField(max_length=100, blank=True)
    color       = models.CharField(max_length=50, blank=True)
    total       = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.model_code_id and not self.model_name:
            self.model_name = str(self.model_code)
        if not self.id_name:
            with transaction.atomic():
                last = CustomerPrice.objects.select_for_update().order_by('-id').values_list('id_name', flat=True).first()
                next_seq = 1
                if last:
                    try:
                        next_seq = int(last.rsplit('-', 1)[-1]) + 1
                    except ValueError:
                        pass
                self.id_name = f'CP-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.id_name} | {self.model_name}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Customer Price List'


class CustomerPriceItem(models.Model):
    price      = models.ForeignKey(CustomerPrice, on_delete=models.CASCADE, related_name='items')
    price_type = models.CharField(max_length=100, verbose_name='Type')
    amount     = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.price.id_name} | {self.price_type}"

    class Meta:
        verbose_name_plural = 'Customer Price Items'


class DealerPriceList(models.Model):
    """Reference: 'Dealer Price List'. The reference's hidden legacy Int
    fields (ltrt_amount/insurance_amount/pdi_amount/other/discount/ex/pp) are
    dropped -- confirmed staged/superseded columns feeding the newer generic
    dealer_price_table, not live business data."""
    id_name     = models.CharField(max_length=50, unique=True, blank=True, editable=False)
    dealer_name = models.ForeignKey('customers.Customer', on_delete=models.PROTECT, related_name='dealer_price_lists')
    model_code  = models.ForeignKey('customers.BikeModel', on_delete=models.PROTECT, null=True, blank=True, related_name='dealer_price_lists', verbose_name='Model Code')
    model_name  = models.CharField(max_length=200, blank=True, verbose_name='Model Name')
    sub_group   = models.CharField(max_length=100, blank=True)
    color       = models.CharField(max_length=50, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.model_code_id and not self.model_name:
            self.model_name = str(self.model_code)
        if not self.id_name:
            with transaction.atomic():
                last = DealerPriceList.objects.select_for_update().order_by('-id').values_list('id_name', flat=True).first()
                next_seq = 1
                if last:
                    try:
                        next_seq = int(last.rsplit('-', 1)[-1]) + 1
                    except ValueError:
                        pass
                self.id_name = f'DPL-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.id_name} | {self.dealer_name}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Dealer Price Lists'


class DealerPriceItem(models.Model):
    price      = models.ForeignKey(DealerPriceList, on_delete=models.CASCADE, related_name='items')
    price_type = models.CharField(max_length=100, verbose_name='Type')
    amount     = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.price.id_name} | {self.price_type}"

    class Meta:
        verbose_name_plural = 'Dealer Price Items'


# ---------------------------------------------------------------------------
# Phase 8c — Vehicle Fitting Spares (non-submittable config master, one row
# per BikeModel). NOTE: the reference's "Vehicle Service Master" doctype is
# NOT duplicated here -- service.VehicleServiceMaster + VehicleServiceSchedule
# (service/models.py) already implement it (same OneToOneField(BikeModel)
# shape, same service_type/days_from_purchase/km_from_purchase fields, built
# in an earlier round), discovered before migrating and reused as-is rather
# than creating a colliding duplicate model.
# ---------------------------------------------------------------------------

class VehicleFittingSpares(models.Model):
    """Reference: 'Vehicle Fitting Spares' (workspace label 'Vehicle Fitting
    Master') -- one row per vehicle model (autoname field:vehicle_name),
    holding the fitted-spares list with a computed total."""
    vehicle      = models.OneToOneField('customers.BikeModel', on_delete=models.CASCADE, related_name='fitting_spares', verbose_name='Vehicle Name')
    branch       = models.ForeignKey('accounts.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='vehicle_fitting_spares')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Fitting Spares | {self.vehicle}"

    class Meta:
        ordering = ['vehicle']
        verbose_name_plural = 'Vehicle Fitting Spares'


class VehicleFittingSpareItem(models.Model):
    fitting   = models.ForeignKey(VehicleFittingSpares, on_delete=models.CASCADE, related_name='items')
    item      = models.ForeignKey('spares.SparesItem', on_delete=models.SET_NULL, null=True, blank=True)
    item_name = models.CharField(max_length=200, blank=True)
    quantity  = models.IntegerField(default=1, blank=True)
    rate      = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    total     = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    uom       = models.CharField(max_length=20, blank=True, default='Nos')
    gst       = models.CharField(max_length=20, blank=True, help_text="Reference types this field as free text (Data), not a rate -- preserved as-is")

    def save(self, *args, **kwargs):
        if self.item_id and not self.item_name:
            self.item_name = self.item.item_name
        self.total = self.quantity * self.rate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.fitting} | {self.item_name}"

    class Meta:
        verbose_name_plural = 'Vehicle Fitting Spare Items'


class VehicleType(models.Model):
    """Reference: 'Vehicle Type' -- a trivial single-field category catalog (Motor Cycle /
    Premium Scooter / Scooter), confirmed live with real production data (round-3 sweep).
    Referenced by Normal Helmet Master's vehicle_category and several other doctypes' category
    filters that were previously dropped as free-text/CharField fallbacks -- built here as a
    real lookup master since it's this cheap and genuinely reused across several places."""
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Vehicle Types'


class NormalHelmetMaster(models.Model):
    """Reference: 'Normal Helmet Master' -- the helmet catalog backing VehicleSalesOrder's
    special-helmet cluster (sales/models.py). Confirmed live with real production data
    (part number, GST, UOM), not test scaffolding -- a genuine gap, found during the round-3
    live-verification sweep. NOTE: VehicleSalesOrder.helmet_name/default_helmet remain plain
    CharFields, not converted to a FK onto this master this round -- that's a structural change
    to an already-shipped, heavily-verified core Phase-1 model and is out of scope for this
    catalog addition; flagged as follow-up wiring, not silently assumed done."""
    disabled       = models.BooleanField(default=False)
    helmet_code    = models.CharField(max_length=50, unique=True)
    helmet_name    = models.CharField(max_length=200)
    vehicle_category = models.ForeignKey(VehicleType, on_delete=models.SET_NULL, null=True, blank=True, related_name='helmets')
    uom            = models.CharField(max_length=20, default='Nos')
    part_number    = models.CharField(max_length=100, blank=True)
    gst_percent    = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True,
                                          help_text='Reference links to an Item Tax Template; no such model exists in Django -- a plain percent field instead')
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.helmet_code} — {self.helmet_name}"

    class Meta:
        ordering = ['helmet_name']
        verbose_name_plural = 'Normal Helmet Masters'
