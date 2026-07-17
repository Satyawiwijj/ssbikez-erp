from django.db import models, transaction
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import DocStatusMixin


class Customer(models.Model):
    class GSTCategory(models.TextChoices):
        REGISTERED_REGULAR     = 'Registered Regular',     'Registered Regular'
        REGISTERED_COMPOSITION = 'Registered Composition', 'Registered Composition'
        UNREGISTERED           = 'Unregistered',            'Unregistered'
        SEZ                    = 'SEZ',                     'SEZ'
        OVERSEAS               = 'Overseas',                'Overseas'
        DEEMED_EXPORT          = 'Deemed Export',            'Deemed Export'
        UIN_HOLDERS            = 'UIN Holders',              'UIN Holders'
        TAX_DEDUCTOR           = 'Tax Deductor',              'Tax Deductor'
        TAX_COLLECTOR          = 'Tax Collector',             'Tax Collector'
        INPUT_SERVICE_DIST     = 'Input Service Distributor', 'Input Service Distributor'

    full_name    = models.CharField(max_length=200)
    phone        = models.CharField(max_length=15)
    email        = models.EmailField(blank=True, null=True)
    address      = models.TextField(blank=True, null=True)
    # Free-text like the other address fields on this model (and on
    # accounts.CompanySettings.state) -- no State master model in this
    # codebase, so no FK/choices here either. Blank means "unknown" and is
    # treated as intrastate (same state as the company) by billing.split_gst,
    # which keeps every pre-existing Customer row backward compatible.
    state        = models.CharField(max_length=100, blank=True)
    aadhaar_no   = models.CharField(max_length=20, blank=True, null=True)
    pan_no       = models.CharField(max_length=20, blank=True, null=True)
    gst_category = models.CharField(
        max_length=30, choices=GSTCategory.choices, default=GSTCategory.UNREGISTERED
    )
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['full_name']
        verbose_name_plural = 'Customers'

    def __str__(self):
        return f"{self.full_name} ({self.phone})"


class BikeModel(models.Model):
    class FuelType(models.TextChoices):
        PETROL   = 'petrol',   'Petrol'
        ELECTRIC = 'electric', 'Electric'
        HYBRID   = 'hybrid',   'Hybrid'

    brand             = models.CharField(max_length=100)
    model_name        = models.CharField(max_length=100)
    variant           = models.CharField(max_length=100, blank=True, null=True)
    fuel_type         = models.CharField(
        max_length=50,
        choices=FuelType.choices,
        default=FuelType.PETROL
    )
    # Informational only e.g. "Red, Blue, Black"
    # Actual per-unit color lives on VehicleStock
    available_colors  = models.TextField(blank=True, null=True)
    ex_showroom_price  = models.DecimalField(max_digits=10, decimal_places=2)
    dealer_cost_price  = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text='Dealer purchase price from manufacturer (used for profit calculations)'
    )
    created_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['brand', 'model_name']
        verbose_name_plural = 'Bike Models'

    def __str__(self):
        return f"{self.brand} {self.model_name} {self.variant or ''}".strip()


class VehicleStock(models.Model):
    class StockStatus(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        RESERVED  = 'reserved',  'Reserved'
        SOLD      = 'sold',      'Sold'

    bike_model         = models.ForeignKey(
        BikeModel,
        on_delete=models.PROTECT,
        related_name='stock'
    )
    branch             = models.ForeignKey(
        'accounts.Branch',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='vehicle_stock'
    )
    engine_no          = models.CharField(max_length=100, unique=True, blank=True, null=True)
    chassis_no         = models.CharField(max_length=100, unique=True, blank=True, null=True)
    color              = models.CharField(max_length=50, blank=True, null=True)
    stock_status       = models.CharField(
        max_length=20,
        choices=StockStatus.choices,
        default=StockStatus.AVAILABLE
    )
    warehouse_location = models.CharField(max_length=100, blank=True, null=True)
    purchase_date      = models.DateField(blank=True, null=True)
    created_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Vehicle Stock'

    def __str__(self):
        return f"{self.bike_model} — {self.chassis_no or 'No Chassis'}"

    def save(self, *args, **kwargs):
        is_new = not self.pk
        old_status = None
        if not is_new:
            old_status = (
                VehicleStock.objects
                .filter(pk=self.pk)
                .values_list('stock_status', flat=True)
                .first()
            )
        super().save(*args, **kwargs)
        # Auto-create CustomerVehicle when status becomes 'sold'
        if not is_new and old_status != self.StockStatus.SOLD and self.stock_status == self.StockStatus.SOLD:
            try:
                from django.apps import apps
                SalesOrder   = apps.get_model('sales',            'VehicleSalesOrder')
                CustomerVehicle = apps.get_model('customer_vehicles', 'CustomerVehicle')
                order = SalesOrder.objects.filter(vehicle=self).select_related('customer').first()
                if order:
                    CustomerVehicle.objects.get_or_create(
                        customer=order.customer,
                        vehicle=self,
                    )
            except Exception:
                pass  # Never crash a save() due to auto-create failure


# ---------------------------------------------------------------------------
# Phase 8c — Vehicle Master Settings: the batch chassis/engine/color/book-no
# intake generator. Submit creates real VehicleStock rows -- the confirmed
# Django gap this reference doctype exists to fill (no bulk VehicleStock
# creation flow existed before this phase).
# ---------------------------------------------------------------------------

class VehicleMasterSettings(DocStatusMixin, models.Model):
    master_no            = models.CharField(max_length=50, unique=True, blank=True, editable=False)
    vehicle               = models.ForeignKey(BikeModel, on_delete=models.PROTECT, related_name='master_settings')
    has_exchange_vehicle  = models.BooleanField(default=False)
    service_settings      = models.ForeignKey(
        'service.VehicleServiceMaster', on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
        help_text='Reuses the existing service.VehicleServiceMaster (built in an earlier round) rather '
                   'than duplicating it under masters -- same OneToOneField(BikeModel) shape the '
                   'reference doctype implies'
    )
    exchange_vehicle_id   = models.ForeignKey(
        'sales.ExchangeVehicle', on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
        help_text='Reference Link target is a standalone Exchange Vehicle Master; Django has no such '
                   'freestanding master -- this points directly at sales.ExchangeVehicle, which is '
                   'normally reached via its owning VehicleSalesOrder'
    )
    created_at            = models.DateTimeField(auto_now_add=True)
    created_by            = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.master_no:
            with transaction.atomic():
                last = VehicleMasterSettings.objects.select_for_update().order_by('-id').values_list('master_no', flat=True).first()
                next_seq = 1
                if last:
                    try:
                        next_seq = int(last.rsplit('-', 1)[-1]) + 1
                    except ValueError:
                        pass
                self.master_no = f'VEH-MAS-{next_seq:05d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.master_no

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Vehicle Master Settings'


class VehicleMasterSettingsItem(models.Model):
    master       = models.ForeignKey(VehicleMasterSettings, on_delete=models.CASCADE, related_name='items')
    vehicle_name = models.ForeignKey(BikeModel, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    model        = models.CharField(max_length=200)
    chasis_no    = models.CharField(max_length=100, verbose_name='Chasis No')
    code         = models.CharField(max_length=100)
    engine       = models.CharField(max_length=100)
    color        = models.CharField(max_length=50, help_text='No Product Color master exists in Django -- free text, matching the existing VehicleStock.color precedent')
    book_no      = models.CharField(max_length=100, verbose_name='Book No')
    color_code   = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.master.master_no} | {self.chasis_no}"

    class Meta:
        verbose_name_plural = 'Vehicle Master Settings Items'


@receiver(post_save, sender=VehicleMasterSettings)
def on_vehicle_master_settings_submitted(sender, instance, **kwargs):
    if instance.docstatus != VehicleMasterSettings.DocStatus.SUBMITTED:
        return
    for row in instance.items.all():
        if VehicleStock.objects.filter(chassis_no=row.chasis_no).exists():
            continue  # Duplicate chassis number -- skip, don't crash on the unique constraint
        VehicleStock.objects.create(
            bike_model=instance.vehicle,
            engine_no=row.engine,
            chassis_no=row.chasis_no,
            color=row.color,
            stock_status=VehicleStock.StockStatus.AVAILABLE,
        )
