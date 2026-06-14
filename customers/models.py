from django.db import models


class Customer(models.Model):
    full_name  = models.CharField(max_length=200)
    phone      = models.CharField(max_length=15)
    email      = models.EmailField(blank=True, null=True)
    address    = models.TextField(blank=True, null=True)
    aadhaar_no = models.CharField(max_length=20, blank=True, null=True)
    pan_no     = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
